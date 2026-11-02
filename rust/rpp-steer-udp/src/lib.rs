//! std-only loopback observations; caller policy/throughput are explicit inputs.
//! This bridge sends probes, not application traffic or permission grants.
#![forbid(unsafe_code)]
use rpp_link::{LinkAdapter, LinkKind, LinkReading};
use rpp_link_udp::{Config as UdpConfig, UdpAdapter, MAX_DATA_LEN};
use rpp_steer::{Candidate, CostClass, Decision, Hysteresis, MessageClass, Selector, MAX_LINKS};
use std::{net::SocketAddr, time::Duration};

#[derive(Clone, Copy, Debug)]
pub struct EndpointConfig {
    pub id: u32,
    pub local: SocketAddr,
    pub peer: SocketAddr,
    pub kind: LinkKind,
    pub timeout: Duration,
    /// Independently supplied by the caller; never inferred from RTT or loss.
    pub throughput_kbps: u64,
    pub cost: CostClass,
}
impl EndpointConfig {
    fn udp_config(&self) -> Result<UdpConfig, Error> {
        if !self.local.ip().is_loopback() || !self.peer.ip().is_loopback() {
            return Err(Error::NotLoopback);
        }
        UdpConfig::new(self.local, self.peer, self.kind, self.timeout).map_err(Error::Udp)
    }
}
#[derive(Clone, Copy, Debug)]
pub struct LossBands {
    pub lower_ppm: u32,
    pub upper_ppm: u32,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BulkGate {
    Eligible,
    AboveUpper,
    AwaitingLower,
}
#[derive(Debug)]
pub enum Error {
    InvalidBands,
    NotLoopback,
    InvalidBatch,
    DuplicateId,
    TooManyLinks,
    Udp(rpp_link_udp::Error),
    Steer(rpp_steer::Error),
}
#[derive(Clone, Copy, Debug)]
pub struct Observation {
    /// Raw UDP fields are preserved, including availability and observation tick.
    pub candidate: Candidate,
    pub bulk_gate: BulkGate,
}
#[derive(Debug)]
pub struct Batch {
    pub observations: Vec<Observation>,
    pub decision: Decision,
}
/// Saturating read-attempt/outcome telemetry, not kernel-confirmed send counts.
/// Matching replies are successful reads whose latest raw reading is available.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ProbeCounts {
    pub read_attempts: u64,
    pub completed: u64,
    pub matching_reply: u64,
    pub loss: u64,
    pub errors: u64,
}
struct Endpoint {
    adapter: UdpAdapter,
    id: u32,
    throughput_kbps: u64,
    cost: CostClass,
    bulk_open: bool,
    counts: ProbeCounts,
}
impl Endpoint {
    fn read(&mut self, tick: u64) -> Result<LinkReading, Error> {
        read_counted(&mut self.counts, || self.adapter.read(tick))
    }
}
pub struct Bridge {
    endpoints: Vec<Endpoint>,
    bands: LossBands,
    selector: Selector,
    clock: Option<u64>,
}
impl Bridge {
    /// Validate the entire bank and policy before opening any sockets.
    pub fn bind(
        configs: &[EndpointConfig],
        bands: LossBands,
        hysteresis: Hysteresis,
    ) -> Result<Self, Error> {
        if bands.lower_ppm > bands.upper_ppm || bands.upper_ppm > 1_000_000 {
            return Err(Error::InvalidBands);
        }
        let selector =
            Selector::with_loss_ceiling(hysteresis, bands.upper_ppm).map_err(Error::Steer)?;
        if configs.len() > MAX_LINKS {
            return Err(Error::TooManyLinks);
        }
        let mut prepared = Vec::new();
        for (index, config) in configs.iter().enumerate() {
            if configs[..index].iter().any(|old| old.id == config.id) {
                return Err(Error::DuplicateId);
            }
            prepared.push(config.udp_config()?);
        }
        let mut endpoints = Vec::new();
        for (config, udp) in configs.iter().zip(prepared) {
            endpoints.push(Endpoint {
                adapter: UdpAdapter::bind(udp).map_err(Error::Udp)?,
                id: config.id,
                throughput_kbps: config.throughput_kbps,
                cost: config.cost,
                bulk_open: false,
                counts: ProbeCounts::default(),
            });
        }
        Ok(Self {
            endpoints,
            bands,
            selector,
            clock: None,
        })
    }
    /// Endpoint order is stable. Physical I/O diagnostics survive aborted batches;
    /// selector, loss-gate and accepted-clock commits still require a full batch.
    pub fn probe_counts(&self) -> Vec<(u32, ProbeCounts)> {
        self.endpoints.iter().map(|e| (e.id, e.counts)).collect()
    }
    /// One decision batch:1..32 probes/link, at most64 total. Only final readings
    /// update loss gates. Actual I/O history cannot be rolled back after I/O errors.
    pub fn poll(
        &mut self,
        tick: u64,
        class: MessageClass,
        wire_bytes: usize,
        probes: &[u8],
    ) -> Result<Batch, Error> {
        if self.clock.is_some_and(|prior| tick < prior) {
            return Err(Error::Steer(rpp_steer::Error::ClockRollback));
        }
        if wire_bytes == 0 {
            return Err(Error::Steer(rpp_steer::Error::EmptyPayload));
        }
        validate_batch(self.endpoints.len(), probes)?;
        let mut observations = Vec::new();
        for (endpoint, count) in self.endpoints.iter_mut().zip(probes) {
            let mut reading = endpoint.read(tick)?;
            for _ in 1..*count {
                reading = endpoint.read(tick)?;
            }
            let bulk_gate = loss_gate(endpoint.bulk_open, reading.loss_ppm, self.bands);
            observations.push(Observation {
                candidate: measured_candidate(
                    endpoint.id,
                    endpoint.adapter.kind(),
                    reading,
                    endpoint.throughput_kbps,
                    endpoint.cost,
                ),
                bulk_gate,
            });
        }
        let candidates: Vec<_> = observations
            .iter()
            .filter(|observation| eligible_for_class(observation, class))
            .map(|observation| observation.candidate)
            .collect();
        let decision = self
            .selector
            .choose(tick, class, wire_bytes, &candidates)
            .map_err(Error::Steer)?;
        for (endpoint, observation) in self.endpoints.iter_mut().zip(&observations) {
            endpoint.bulk_open = observation.bulk_gate == BulkGate::Eligible;
        }
        self.clock = Some(tick);
        Ok(Batch {
            observations,
            decision,
        })
    }
}

fn read_counted(
    counts: &mut ProbeCounts,
    read: impl FnOnce() -> Result<LinkReading, rpp_link_udp::Error>,
) -> Result<LinkReading, Error> {
    counts.read_attempts = counts.read_attempts.saturating_add(1);
    match read() {
        Ok(reading) => {
            counts.completed = counts.completed.saturating_add(1);
            if reading.available {
                counts.matching_reply = counts.matching_reply.saturating_add(1);
            } else {
                counts.loss = counts.loss.saturating_add(1);
            }
            Ok(reading)
        }
        Err(error) => {
            counts.errors = counts.errors.saturating_add(1);
            Err(Error::Udp(error))
        }
    }
}
fn validate_batch(endpoint_count: usize, probes: &[u8]) -> Result<(), Error> {
    if probes.len() != endpoint_count
        || probes.iter().any(|count| !(1..=32).contains(count))
        || probes
            .iter()
            .map(|count| usize::from(*count))
            .sum::<usize>()
            > 64
    {
        return Err(Error::InvalidBatch);
    }
    Ok(())
}
fn measured_candidate(
    id: u32,
    kind: LinkKind,
    reading: LinkReading,
    throughput_kbps: u64,
    cost: CostClass,
) -> Candidate {
    Candidate {
        id,
        kind,
        reading,
        // Configured adapter payload ceiling, not measured PMTU.
        mtu: MAX_DATA_LEN as u16,
        throughput_kbps,
        cost,
    }
}
fn eligible_for_class(observation: &Observation, class: MessageClass) -> bool {
    class != MessageClass::Bulk || observation.bulk_gate == BulkGate::Eligible
}
fn loss_gate(previously_open: bool, loss: u32, bands: LossBands) -> BulkGate {
    let open = if previously_open {
        loss <= bands.upper_ppm
    } else {
        loss <= bands.lower_ppm
    };
    if open {
        BulkGate::Eligible
    } else if loss > bands.upper_ppm {
        BulkGate::AboveUpper
    } else {
        BulkGate::AwaitingLower
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn policy() -> Hysteresis {
        Hysteresis {
            hold_ticks: 3,
            control_margin_ppm: 0,
            bulk_margin_kbps: 100,
            billboard_margin_ppm: 0,
        }
    }
    /// Kills selector_default_ceiling_replaces_explicit_band and fixed_ceiling_ignores_caller_upper without I/O.
    #[test]
    fn selector_ceiling_uses_the_explicit_upper_band_without_network_io() {
        for (upper_ppm, loss_ppm, expected) in [
            (200_000, 250_000, None),
            (300_000, 250_000, Some(1)),
            (300_000, 300_000, Some(1)),
            (300_000, 300_001, None),
            (1_000_000, 1_000_000, None),
        ] {
            let mut bridge = Bridge::bind(
                &[],
                LossBands {
                    lower_ppm: 0,
                    upper_ppm,
                },
                policy(),
            )
            .unwrap();
            let reading = LinkReading {
                latency_ms: 0,
                jitter_ms: 0,
                loss_ppm,
                available: true,
                observed: 0,
            };
            let candidate = measured_candidate(1, LinkKind::Lan, reading, 1, CostClass::Unmetered);
            assert_eq!(
                bridge
                    .selector
                    .choose(0, MessageClass::Bulk, 1, &[candidate])
                    .unwrap()
                    .link_id,
                expected
            );
        }
    }
    /// Kills attempted_read_omitted, loss_counted_as_reply, and error_telemetry_erased without I/O.
    #[test]
    fn read_diagnostics_preserve_success_loss_and_error_attempts() {
        let mut counts = ProbeCounts::default();
        let reading = LinkReading {
            latency_ms: 7,
            jitter_ms: 2,
            loss_ppm: 0,
            available: true,
            observed: 5,
        };
        assert_eq!(read_counted(&mut counts, || Ok(reading)).unwrap(), reading);
        let loss = LinkReading {
            available: false,
            ..reading
        };
        assert_eq!(read_counted(&mut counts, || Ok(loss)).unwrap(), loss);
        assert!(matches!(
            read_counted(&mut counts, || Err(std::io::Error::from(
                std::io::ErrorKind::PermissionDenied
            )
            .into())),
            Err(Error::Udp(_))
        ));
        assert_eq!(
            counts,
            ProbeCounts {
                read_attempts: 3,
                completed: 2,
                matching_reply: 1,
                loss: 1,
                errors: 1,
            }
        );
    }
    /// Kills nonloopback_guard_removed without binding or sending any socket.
    #[test]
    fn nonloopback_endpoints_fail_pure_preflight() {
        let config = EndpointConfig {
            id: 1,
            local: "127.0.0.1:0".parse().unwrap(),
            peer: "100.64.0.1:9000".parse().unwrap(),
            kind: LinkKind::Lan,
            timeout: Duration::from_millis(10),
            throughput_kbps: 1,
            cost: CostClass::Unmetered,
        };
        assert!(matches!(config.udp_config(), Err(Error::NotLoopback)));
        let mut local = config;
        local.peer = "127.0.0.1:9000".parse().unwrap();
        assert!(local.udp_config().is_ok());
        local.local = "0.0.0.0:0".parse().unwrap();
        assert!(matches!(local.udp_config(), Err(Error::NotLoopback)));
    }
    /// Kills start_open, upper_inclusive_exit, and lower_exclusive_reentry.
    #[test]
    fn loss_bands_start_closed_and_preserve_both_boundary_rules() {
        let bands = LossBands {
            lower_ppm: 100_000,
            upper_ppm: 300_000,
        };
        assert_eq!(loss_gate(false, 100_001, bands), BulkGate::AwaitingLower);
        assert_eq!(loss_gate(false, 100_000, bands), BulkGate::Eligible);
        assert_eq!(loss_gate(true, 300_000, bands), BulkGate::Eligible);
        assert_eq!(loss_gate(true, 300_001, bands), BulkGate::AboveUpper);
        assert_eq!(loss_gate(false, 300_000, bands), BulkGate::AwaitingLower);
        let config = EndpointConfig {
            id: 1,
            local: "127.0.0.1:0".parse().unwrap(),
            peer: "127.0.0.1:9000".parse().unwrap(),
            kind: LinkKind::Lan,
            timeout: Duration::from_millis(10),
            throughput_kbps: 1,
            cost: CostClass::Unmetered,
        };
        let bridge = Bridge::bind(&[config], bands, policy()).unwrap();
        assert!(!bridge.endpoints[0].bulk_open);
    }
    /// Kills reading_fields_rewritten, mtu_includes_header, and throughput_estimated.
    #[test]
    fn raw_readings_and_caller_capacity_are_preserved() {
        let reading = LinkReading {
            latency_ms: 17,
            jitter_ms: 9,
            loss_ppm: 400_000,
            available: true,
            observed: 8,
        };
        let candidate = measured_candidate(7, LinkKind::Wifi, reading, 4321, CostClass::Metered);
        assert_eq!(candidate.reading, reading);
        assert_eq!(candidate.throughput_kbps, 4321);
        assert_eq!(candidate.mtu, 1198);
        assert_eq!(
            (candidate.id, candidate.kind, candidate.cost),
            (7, LinkKind::Wifi, CostClass::Metered)
        );
        let observation = Observation {
            candidate,
            bulk_gate: BulkGate::AboveUpper,
        };
        assert!(!eligible_for_class(&observation, MessageClass::Bulk));
        assert!(eligible_for_class(&observation, MessageClass::Control));
        assert!(eligible_for_class(&observation, MessageClass::Billboard));
        assert!(observation.candidate.reading.available);
    }
    /// Kills zero_probe, oversized_probe, and total_probe_bound_removed before I/O.
    #[test]
    fn probe_bounds_are_checked_without_opening_sockets() {
        for (count, probes) in [
            (1, vec![]),
            (1, vec![0]),
            (1, vec![33]),
            (3, vec![32, 32, 1]),
        ] {
            assert!(matches!(
                validate_batch(count, &probes),
                Err(Error::InvalidBatch)
            ));
        }
        assert!(validate_batch(2, &[32, 32]).is_ok());
    }
    /// Kills invalid_future_advances_clock and rollback_accepted_at_selector_boundary.
    #[test]
    fn invalid_future_batches_do_not_advance_the_accepted_clock() {
        let bands = LossBands {
            lower_ppm: 0,
            upper_ppm: 0,
        };
        let mut bridge = Bridge::bind(&[], bands, policy()).unwrap();
        assert!(bridge.poll(5, MessageClass::Bulk, 1, &[]).is_ok());
        assert!(matches!(
            bridge.poll(100, MessageClass::Bulk, 0, &[]),
            Err(Error::Steer(rpp_steer::Error::EmptyPayload))
        ));
        assert!(matches!(
            bridge.poll(100, MessageClass::Bulk, 1, &[0]),
            Err(Error::InvalidBatch)
        ));
        assert_eq!(bridge.clock, Some(5));
        assert!(bridge.poll(6, MessageClass::Bulk, 1, &[]).is_ok());
        assert!(matches!(
            bridge.poll(5, MessageClass::Bulk, 1, &[]),
            Err(Error::Steer(rpp_steer::Error::ClockRollback))
        ));
        assert_eq!(bridge.clock, Some(6));
    }
    /// Kills invalid_bands_accepted, duplicate_id_accepted, oversized_bank_accepted, and invalid_margin_accepted before I/O.
    #[test]
    fn invalid_policy_is_rejected_before_socket_construction() {
        let bands = LossBands {
            lower_ppm: 2,
            upper_ppm: 1,
        };
        assert!(matches!(
            Bridge::bind(&[], bands, policy()),
            Err(Error::InvalidBands)
        ));
        let bands = LossBands {
            lower_ppm: 0,
            upper_ppm: 1_000_001,
        };
        assert!(matches!(
            Bridge::bind(&[], bands, policy()),
            Err(Error::InvalidBands)
        ));
        let config = EndpointConfig {
            id: 1,
            local: "127.0.0.1:0".parse().unwrap(),
            peer: "127.0.0.1:9000".parse().unwrap(),
            kind: LinkKind::Lan,
            timeout: Duration::from_millis(10),
            throughput_kbps: 1,
            cost: CostClass::Unmetered,
        };
        let valid_bands = LossBands {
            lower_ppm: 0,
            upper_ppm: 0,
        };
        assert!(matches!(
            Bridge::bind(&[config, config], valid_bands, policy()),
            Err(Error::DuplicateId)
        ));
        assert!(matches!(
            Bridge::bind(&[config; MAX_LINKS + 1], valid_bands, policy()),
            Err(Error::TooManyLinks)
        ));
        let mut bad_policy = policy();
        bad_policy.control_margin_ppm = 1_000_001;
        assert!(matches!(
            Bridge::bind(
                &[],
                LossBands {
                    lower_ppm: 0,
                    upper_ppm: 0
                },
                bad_policy
            ),
            Err(Error::Steer(rpp_steer::Error::InvalidMargin))
        ));
    }
}
