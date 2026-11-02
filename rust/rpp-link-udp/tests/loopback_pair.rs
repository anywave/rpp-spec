#![cfg(feature = "fleet-demo")]
use std::time::{Duration, Instant};

#[test]
fn closed_peer_loss_is_measured_and_fleet_selects_the_surviving_endpoint() {
    // Mutations: suppress closed-peer loss, keep a dead link available, or
    // ignore measured readings in fleet failover. No latency threshold is used.
    let start = Instant::now();
    let result = rpp_link_udp::demo::loopback_demo();
    assert!(result.is_ok(), "{result:?}");
    let report = result.unwrap();
    assert!(matches!(report.selected_before, 1 | 2));
    assert_eq!(report.selected_after, 3 - report.selected_before);
    assert!(report.initial.iter().all(|reading| reading.available));
    let closed = (report.selected_before - 1) as usize;
    assert!(!report.after_close[closed].available);
    assert_eq!(report.after_close[closed].loss_ppm, 1_000_000);
    assert!(report.after_close[1 - closed].available);
    assert!(start.elapsed() <= Duration::from_secs(2));
}
