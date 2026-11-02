//! Live loopback measurements passed to fleet policy with explicitly assumed
//! membership, consent and tunnel capabilities. These fixtures prove no tunnel.
use std::{
    error::Error as StdError,
    io,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    thread::{self, JoinHandle},
    time::Duration,
};

use rpp_control::{NodeId, Signature, Verifier, HEADER_LEN};
use rpp_core::{canonical::CanonicalAddress, overlay::Auth};
use rpp_fleet::{
    endpoint::{Endpoint, EndpointCapabilities, EndpointKind},
    identity::{AddressBinding, AssignmentPolicy, NodeIdentity},
    registry::Registry,
    resolver::FleetResolver,
};
use rpp_link::{LinkAdapter, LinkKind, LinkReading};

use crate::UdpAdapter;

type Result<T> = std::result::Result<T, Box<dyn StdError>>;

struct Deny;
impl Verifier for Deny {
    fn verify(&self, _: &NodeId, _: &[u8; HEADER_LEN], _: &Signature) -> bool {
        false
    }
}

struct Echo {
    stop: Arc<AtomicBool>,
    worker: Option<JoinHandle<std::result::Result<(), crate::Error>>>,
}
impl Echo {
    fn start(mut adapter: UdpAdapter) -> Self {
        let stop = Arc::new(AtomicBool::new(false));
        let flag = Arc::clone(&stop);
        let worker = thread::spawn(move || {
            while !flag.load(Ordering::Acquire) {
                // Probe handling is internal; this fixture refuses all control.
                let _ = adapter.receive(&[0; 16], &Deny)?;
            }
            Ok(())
        });
        Self {
            stop,
            worker: Some(worker),
        }
    }
    fn close(&mut self) -> Result<()> {
        self.stop.store(true, Ordering::Release);
        if let Some(worker) = self.worker.take() {
            worker
                .join()
                .map_err(|_| io::Error::other("echo worker panicked"))??;
        }
        Ok(())
    }
}
impl Drop for Echo {
    fn drop(&mut self) {
        let _ = self.close();
    }
}

#[derive(Debug)]
pub struct DemoReport {
    pub initial: [LinkReading; 2],
    pub after_close: [LinkReading; 2],
    pub selected_before: u32,
    pub selected_after: u32,
}

fn measured(adapter: &mut UdpAdapter, tick: u64) -> Result<LinkReading> {
    for _ in 0..4 {
        let reading = adapter.read(tick)?;
        if reading.available {
            return Ok(reading);
        }
    }
    Err(io::Error::other("loopback peer did not answer four probes").into())
}

/// Two real endpoint pairs, then closure and measured failover. No remote host.
/// The 10 ms per-probe timeout is a budget, not a latency acceptance threshold.
pub fn loopback_demo() -> Result<DemoReport> {
    let timeout = Duration::from_millis(10);
    let (first, peer_first) = UdpAdapter::loopback_pair(LinkKind::Lan, timeout)?;
    let (second, peer_second) = UdpAdapter::loopback_pair(LinkKind::Wifi, timeout)?;
    let mut echoes = [Echo::start(peer_first), Echo::start(peer_second)];
    let mut clients = [first, second];
    let initial = [measured(&mut clients[0], 0)?, measured(&mut clients[1], 0)?];
    let source = NodeIdentity::new([0x11; 16], [1; 16]);
    let target = NodeIdentity::new([0x22; 16], [2; 16]);
    let mut endpoints = Vec::new();
    for (index, kind) in [EndpointKind::Lan, EndpointKind::Wifi]
        .into_iter()
        .enumerate()
    {
        endpoints.push(
            Endpoint::new(
                index as u32 + 1,
                kind,
                format!("udp://{}", clients[index].peer_addr()),
                initial[index],
                EndpointCapabilities {
                    // Explicit loopback policy fixtures: the address allowlist does
                    // not establish encryption, admission or consent.
                    tunnel_verified: true,
                    observation_verified: true,
                    control_capable: true,
                    reviewed_adapter: false,
                    failure_domain: 1,
                },
            )
            .map_err(|_| io::Error::other("invalid demo endpoint"))?,
        );
    }
    let mut registry = Registry::new();
    for (identity, theta, endpoints) in [(source, 1, Vec::new()), (target, 2, endpoints)] {
        let address = CanonicalAddress::new(theta, 1, 0, 0.0, 0)
            .map_err(|_| io::Error::other("invalid demo address"))?;
        registry
            .register(
                AddressBinding::new(
                    identity,
                    address,
                    AssignmentPolicy::ExplicitCallerAssignmentV1,
                ),
                endpoints,
            )
            .map_err(|_| io::Error::other("invalid demo registry"))?;
    }
    let mut fleet = FleetResolver::new(
        &mut registry,
        source,
        Auth::fixture(&source.label(), true),
        &[source, target],
        &[(source, target)],
    );
    let selection = fleet
        .resolve_data(target, 0)
        .map_err(|_| io::Error::other("initial fleet resolution failed"))?;
    let before = selection
        .selected()
        .ok_or_else(|| io::Error::other("no live route"))?
        .endpoint_id;
    let closed = (before - 1) as usize;
    echoes[closed].close()?;
    let mut after_close = initial;
    for tick in 1..=32 {
        after_close[closed] = clients[closed].read(tick)?;
    }
    let other = 1 - closed;
    after_close[other] = measured(&mut clients[other], 33)?;
    for (index, reading) in after_close.into_iter().enumerate() {
        fleet
            .update_reading(&target, index as u32 + 1, reading)
            .map_err(|_| io::Error::other("fleet reading update failed"))?;
    }
    let selection = fleet
        .resolve_data(target, 33)
        .map_err(|_| io::Error::other("post-closure fleet resolution failed"))?;
    let after = selection
        .selected()
        .ok_or_else(|| io::Error::other("no surviving route"))?
        .endpoint_id;
    Ok(DemoReport {
        initial,
        after_close,
        selected_before: before,
        selected_after: after,
    })
}
