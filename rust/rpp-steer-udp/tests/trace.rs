use rpp_link::LinkKind;
use rpp_steer::{CostClass, Hysteresis, MessageClass, Reason};
use rpp_steer_udp::{Batch, Bridge, BulkGate, EndpointConfig, Error, LossBands, ProbeCounts};
use std::{
    io,
    net::{SocketAddr, UdpSocket},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    thread::{self, JoinHandle},
    time::{Duration, Instant},
};

fn fixture_peer_allowed(peer: SocketAddr) -> bool {
    peer.ip().is_loopback()
}
const STOP: &[u8] = b"CX026-fixture-stop";
const STOP_BUFFER_BYTES: usize = STOP.len() + 1;
const SOCKET_BUDGET: Duration = Duration::from_secs(4);
const PROBE_REPLY_BUDGET: Duration = Duration::from_millis(250);
/// Failing mutation: shortened_probe_reply_budget no longer reaches the adapter's allowed maximum.
#[test]
fn fixture_probe_budget_reaches_the_adapter_maximum_without_network_io() {
    let local = "127.0.0.1:0".parse().unwrap();
    let peer = "127.0.0.1:9000".parse().unwrap();
    assert!(rpp_link_udp::Config::new(local, peer, LinkKind::Lan, PROBE_REPLY_BUDGET).is_ok());
    assert!(matches!(
        rpp_link_udp::Config::new(
            local,
            peer,
            LinkKind::Lan,
            PROBE_REPLY_BUDGET + Duration::from_millis(1)
        ),
        Err(rpp_link_udp::Error::InvalidConfig)
    ));
}
fn fixture_stop(peer: SocketAddr, bytes: &[u8], waker: SocketAddr, requested: bool) -> bool {
    requested && fixture_peer_allowed(peer) && peer == waker && bytes == STOP
}
/// Failing mutation: raw_fixture_accepts_nonloopback_source; no socket is opened here.
#[test]
fn fixture_refuses_nonloopback_sources_without_network_io() {
    assert!(fixture_peer_allowed("127.0.0.1:9000".parse().unwrap()));
    assert!(fixture_peer_allowed("[::1]:9000".parse().unwrap()));
    assert!(!fixture_peer_allowed("192.0.2.1:9000".parse().unwrap()));
    assert!(!fixture_peer_allowed("100.64.0.1:9000".parse().unwrap()));
}
/// Failing mutations: unrequested_STOP, any_loopback_waker, STOP_prefix, nonloopback_STOP, truncated_STOP_buffer.
#[test]
fn fixture_stop_requires_exact_waker_and_bytes_after_shutdown_without_network_io() {
    let waker = "127.0.0.1:9000".parse().unwrap();
    assert!(STOP_BUFFER_BYTES > STOP.len());
    assert!(fixture_stop(waker, STOP, waker, true));
    assert!(!fixture_stop(waker, STOP, waker, false));
    assert!(!fixture_stop(
        "127.0.0.1:9001".parse().unwrap(),
        STOP,
        waker,
        true
    ));
    for address in ["192.0.2.1:9000", "100.64.0.1:9000"] {
        let peer = address.parse().unwrap();
        assert!(!fixture_stop(peer, STOP, peer, true));
    }
    let mut oversized = STOP.to_vec();
    oversized.push(0);
    for bytes in [b"".as_slice(), &STOP[..STOP.len() - 1], &oversized] {
        assert!(!fixture_stop(waker, bytes, waker, true));
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
struct ResponderCounts {
    probes_received: u64,
    replies_sent: u64,
    scripted_drops: u64,
    stop_received: u64,
}
#[derive(Debug)]
struct ResponderOutcome {
    counts: ResponderCounts,
    error: Option<io::Error>,
}
impl ResponderOutcome {
    fn new(counts: ResponderCounts, result: io::Result<()>) -> Self {
        Self {
            counts,
            error: result.err(),
        }
    }
}
struct Responder {
    address: SocketAddr,
    stop: Arc<AtomicBool>,
    waker: UdpSocket,
    worker: Option<JoinHandle<ResponderOutcome>>,
    outcome: Option<ResponderOutcome>,
}
impl Responder {
    fn start(drops: &'static [u64]) -> Self {
        let socket = UdpSocket::bind("127.0.0.1:0").expect("loopback bind I/O");
        socket
            .set_read_timeout(Some(SOCKET_BUDGET))
            .expect("bounded fixture read I/O");
        socket
            .set_write_timeout(Some(SOCKET_BUDGET))
            .expect("bounded fixture write I/O");
        let address = socket.local_addr().expect("loopback address I/O");
        let waker = UdpSocket::bind("127.0.0.1:0").expect("loopback waker bind I/O");
        waker
            .set_write_timeout(Some(SOCKET_BUDGET))
            .expect("bounded wake I/O");
        let wake_address = waker.local_addr().expect("loopback waker address I/O");
        let stop = Arc::new(AtomicBool::new(false));
        let flag = Arc::clone(&stop);
        let worker = thread::spawn(move || {
            // These are fixed blocking-I/O watchdogs, not a strict 4s wall limit:
            // a receive and write begun before this deadline can each overrun it.
            let deadline = Instant::now() + SOCKET_BUDGET;
            let mut counts = ResponderCounts::default();
            // STOP+1 prevents a truncated oversized STOP prefix from matching.
            let mut bytes = [0; STOP_BUFFER_BYTES];
            let result = (|| {
                loop {
                    if Instant::now() >= deadline {
                        return Err(io::Error::new(
                            io::ErrorKind::TimedOut,
                            "responder deadline",
                        ));
                    }
                    let (size, peer) = socket.recv_from(&mut bytes)?;
                    if fixture_stop(
                        peer,
                        &bytes[..size],
                        wake_address,
                        flag.load(Ordering::Acquire),
                    ) {
                        counts.stop_received += 1;
                        break;
                    }
                    if peer == wake_address || !fixture_peer_allowed(peer) {
                        continue;
                    }
                    if size != 10 || bytes[..2] != [1, 1] {
                        return Err(io::Error::new(
                            io::ErrorKind::InvalidData,
                            "unexpected probe envelope",
                        ));
                    }
                    let nonce = u64::from_be_bytes(bytes[2..10].try_into().unwrap());
                    counts.probes_received += 1;
                    if nonce != counts.probes_received {
                        return Err(io::Error::new(
                            io::ErrorKind::InvalidData,
                            "unexpected probe nonce",
                        ));
                    }
                    if drops.contains(&nonce) {
                        counts.scripted_drops += 1;
                        continue;
                    }
                    bytes[1] = 2;
                    if socket.send_to(&bytes[..10], peer)? != 10 {
                        return Err(io::Error::new(
                            io::ErrorKind::WriteZero,
                            "short probe reply",
                        ));
                    }
                    counts.replies_sent += 1;
                }
                Ok(())
            })();
            ResponderOutcome::new(counts, result)
        });
        Self {
            address,
            stop,
            waker,
            worker: Some(worker),
            outcome: None,
        }
    }
    fn close(&mut self) -> &ResponderOutcome {
        if let Some(worker) = self.worker.take() {
            self.stop.store(true, Ordering::Release);
            let wake = self.waker.send_to(STOP, self.address).and_then(|size| {
                if size == STOP.len() {
                    Ok(())
                } else {
                    Err(io::Error::new(io::ErrorKind::WriteZero, "short wake"))
                }
            });
            // Join even if wake failed; fixed socket watchdogs are the fallback.
            let mut outcome = worker.join().unwrap_or_else(|_| {
                ResponderOutcome::new(
                    ResponderCounts::default(),
                    Err(io::Error::other("responder panic; counts unavailable")),
                )
            });
            if outcome.error.is_none() {
                outcome.error = wake.err();
            }
            self.outcome = Some(outcome);
        }
        self.outcome
            .as_ref()
            .expect("responder joined exactly once")
    }
}
impl Drop for Responder {
    fn drop(&mut self) {
        let _ = self.close();
    }
}
/// Failing mutation: count_STOP_as_probe; STOP acknowledges a once-joined idle worker, never a probe.
#[test]
fn idle_responder_close_wakes_joins_once_and_preserves_stop_count() {
    let mut responder = Responder::start(&[]);
    let first = responder.close();
    assert!(first.error.is_none(), "{first:?}");
    let counts = ResponderCounts {
        stop_received: 1,
        ..ResponderCounts::default()
    };
    assert_eq!(first.counts, counts);
    assert!(responder.worker.is_none());
    let second = responder.close();
    assert!(second.error.is_none(), "{second:?}");
    assert_eq!(second.counts, counts);
}
/// Failing mutation: discard_error_stats; completed physical history survives a worker error.
#[test]
fn responder_error_outcome_preserves_prior_counts_without_network_io() {
    let counts = ResponderCounts {
        probes_received: 5,
        replies_sent: 4,
        scripted_drops: 1,
        stop_received: 0,
    };
    let outcome = ResponderOutcome::new(counts, Err(io::ErrorKind::InvalidData.into()));
    assert_eq!(outcome.counts, counts);
    assert_eq!(
        outcome.error.as_ref().map(io::Error::kind),
        Some(io::ErrorKind::InvalidData)
    );
}
fn reject_io<T>(result: &Result<T, Error>) {
    if matches!(result, Err(Error::Udp(rpp_link_udp::Error::Io(_)))) {
        panic!("loopback adapter I/O: {:?}", result.as_ref().err());
    }
}
fn checked<T>(result: Result<T, Error>) -> T {
    reject_io(&result);
    assert!(result.is_ok());
    result.unwrap()
}
struct Fixture {
    bridge: Bridge,
    a: Responder,
    b: Responder,
}
impl Fixture {
    fn start(margin: u64, drops: &'static [u64]) -> Self {
        let mut a = Responder::start(drops);
        let mut b = Responder::start(&[]);
        let configs =
            [(1, a.address, 1000), (2, b.address, 800)].map(|(id, peer, rate)| EndpointConfig {
                id,
                peer,
                local: "127.0.0.1:0".parse().unwrap(),
                kind: LinkKind::Lan,
                timeout: PROBE_REPLY_BUDGET,
                throughput_kbps: rate,
                cost: CostClass::Unmetered,
            });
        let result = Bridge::bind(
            &configs,
            LossBands {
                lower_ppm: 100_000,
                upper_ppm: 300_000,
            },
            Hysteresis {
                hold_ticks: 3,
                bulk_margin_kbps: margin,
                control_margin_ppm: 0,
                billboard_margin_ppm: 0,
            },
        );
        if result.is_err() {
            a.close();
            b.close();
        }
        Self {
            bridge: checked(result),
            a,
            b,
        }
    }
    fn close(&mut self) -> (ResponderCounts, ResponderCounts) {
        let a = self.a.close();
        let b = self.b.close();
        assert!(a.error.is_none(), "responder A I/O: {a:?}");
        assert!(b.error.is_none(), "responder B I/O: {b:?}");
        (a.counts, b.counts)
    }
}
fn trace(margin: u64) -> Vec<Batch> {
    let mut fixture = Fixture::start(margin, &[3, 6, 7]);
    let results: Vec<_> = [2, 2, 4, 2, 21, 1]
        .into_iter()
        .enumerate()
        .map(|(tick, count)| {
            fixture
                .bridge
                .poll(tick as u64, MessageClass::Bulk, 10, &[count, 1])
        })
        .collect();
    let bridge_counts = fixture.bridge.probe_counts();
    let peers = fixture.close();
    let counts = (peers.0.probes_received, peers.1.probes_received);
    for result in &results {
        reject_io(result);
    }
    assert_eq!(counts, (32, 6));
    assert_eq!(
        bridge_counts,
        vec![
            (
                1,
                ProbeCounts {
                    read_attempts: 32,
                    completed: 32,
                    matching_reply: 29,
                    loss: 3,
                    errors: 0
                }
            ),
            (
                2,
                ProbeCounts {
                    read_attempts: 6,
                    completed: 6,
                    matching_reply: 6,
                    loss: 0,
                    errors: 0
                }
            ),
        ]
    );
    assert_eq!(
        peers,
        (
            ResponderCounts {
                probes_received: 32,
                replies_sent: 29,
                scripted_drops: 3,
                stop_received: 1
            },
            ResponderCounts {
                probes_received: 6,
                replies_sent: 6,
                scripted_drops: 0,
                stop_received: 1
            },
        )
    );
    results.into_iter().map(checked).collect()
}
/// Failing mutations: erase raw readings, invert loss bands, bypass hold, or replace measured selection.
/// selector_default_ceiling_replaces_explicit_band rejects the 250000 ppm incumbent too early.
#[test]
fn measured_loss_bands_and_selector_hold_preserve_the_six_phase_trace() {
    let batches = trace(100);
    let losses = [0, 250_000, 375_000, 300_000, 96_774, 93_750];
    let gates = [
        BulkGate::Eligible,
        BulkGate::Eligible,
        BulkGate::AboveUpper,
        BulkGate::AwaitingLower,
        BulkGate::Eligible,
        BulkGate::Eligible,
    ];
    let ids = [1, 1, 2, 2, 2, 1];
    let reasons = [
        Reason::Initial,
        Reason::Best,
        Reason::Ineligible,
        Reason::Best,
        Reason::Hold,
        Reason::Improved,
    ];
    for (tick, batch) in batches.iter().enumerate() {
        assert_eq!(batch.observations.len(), 2);
        let a = batch.observations[0];
        let b = batch.observations[1];
        assert_eq!(
            (a.candidate.id, a.candidate.reading.loss_ppm),
            (1, losses[tick])
        );
        assert!(a.candidate.reading.available);
        assert_eq!(a.candidate.reading.observed, tick as u64);
        assert_eq!(a.bulk_gate, gates[tick]);
        assert_eq!((b.candidate.id, b.candidate.reading.loss_ppm), (2, 0));
        assert!(b.candidate.reading.available);
        assert_eq!(b.candidate.reading.observed, tick as u64);
        assert_eq!(b.bulk_gate, BulkGate::Eligible);
        assert_eq!(batch.decision.link_id, Some(ids[tick]));
        assert_eq!(batch.decision.reason, reasons[tick]);
    }
}
/// Failing mutation: replace the caller's201kbps margin with100 so the final200kbps improvement switches.
#[test]
fn caller_bulk_margin_201_keeps_the_final_endpoint() {
    let batches = trace(201);
    assert_eq!(batches[5].decision.link_id, Some(2));
    assert_eq!(batches[5].decision.reason, Reason::Margin);
}
/// Failing mutations: probe before rollback/batch/payload checks, or advance clock on rejected future inputs.
#[test]
fn rollback_and_invalid_future_batches_do_not_probe() {
    let mut fixture = Fixture::start(100, &[]);
    let first = fixture.bridge.poll(5, MessageClass::Bulk, 10, &[1, 1]);
    let rollback = fixture.bridge.poll(4, MessageClass::Bulk, 10, &[1, 1]);
    let batch = fixture.bridge.poll(100, MessageClass::Bulk, 10, &[0, 1]);
    let empty = fixture.bridge.poll(100, MessageClass::Bulk, 0, &[1, 1]);
    let final_poll = fixture.bridge.poll(6, MessageClass::Bulk, 10, &[1, 1]);
    let bridge_counts = fixture.bridge.probe_counts();
    let peers = fixture.close();
    let counts = (peers.0.probes_received, peers.1.probes_received);
    for result in [&first, &rollback, &batch, &empty, &final_poll] {
        reject_io(result);
    }
    assert_eq!(counts, (2, 2));
    let expected = ProbeCounts {
        read_attempts: 2,
        completed: 2,
        matching_reply: 2,
        loss: 0,
        errors: 0,
    };
    assert_eq!(bridge_counts, vec![(1, expected), (2, expected)]);
    let expected = ResponderCounts {
        probes_received: 2,
        replies_sent: 2,
        scripted_drops: 0,
        stop_received: 1,
    };
    assert_eq!(peers, (expected, expected));
    assert_eq!(checked(first).observations[0].candidate.reading.observed, 5);
    assert!(matches!(
        rollback,
        Err(Error::Steer(rpp_steer::Error::ClockRollback))
    ));
    assert!(matches!(batch, Err(Error::InvalidBatch)));
    assert!(matches!(
        empty,
        Err(Error::Steer(rpp_steer::Error::EmptyPayload))
    ));
    assert_eq!(
        checked(final_poll).observations[0]
            .candidate
            .reading
            .observed,
        6
    );
}
