#![cfg(feature = "alloc")]
//! State-retention checks execute bounded deterministic workloads.

mod support;

use rpp_core::overlay::Auth;
use rpp_fleet::{
    endpoint::EndpointKind,
    identity::NodeIdentity,
    resolver::{FleetResolveError, FleetResolver, ResolutionStatus},
    MAX_RETAINED_METER_ROWS,
};
use rpp_link::TrafficPath;
use support::*;

/// Failing mutations: append every reading snapshot/reference, retain all meter rows, renumber rows, or consume state during preview.
#[test]
fn ten_thousand_live_reading_changes_keep_only_latest_reference_and_sixteen_meter_rows() {
    assert_eq!(MAX_RETAINED_METER_ROWS, 16);
    let mut records = registry(vec![
        endpoint(1, EndpointKind::Lan, 10, 0),
        endpoint(4, EndpointKind::Ble, 1, 0),
    ]);
    let mut fleet = resolver(&mut records);
    let mut last_reference = Vec::new();
    for tick in 0..10_000_u64 {
        // Each selection is a different full Link value. A deduplicating append
        // implementation therefore cannot pass by observing identical inputs.
        let mut lan = reading(10 + tick, tick);
        lan.jitter_ms = tick % 17;
        fleet.update_reading(&target(), 1, lan).unwrap();
        let mut ble = reading(1 + tick % 3, tick);
        ble.jitter_ms = tick % 5;
        fleet.update_reading(&target(), 4, ble).unwrap();
        let before_query = fleet.stats();
        let data = fleet.resolve_data(target(), tick).unwrap();
        assert_eq!(data.status, ResolutionStatus::Ready);
        let known = data.selected().unwrap().path().to_vec();
        if !last_reference.is_empty() {
            assert_ne!(last_reference, known);
        }
        assert_eq!(
            fleet.stats().retained_meter_rows,
            before_query.retained_meter_rows
        );
        assert_eq!(fleet.stats().known_data_references, 1);
        assert_eq!(fleet.stats().current_data_references, 1);
        let frame = verified(tick + 1);
        let control = fleet
            .resolve_control(target(), tick, &frame, &known, TrafficPath::Control)
            .unwrap();
        assert_eq!(control.status, ResolutionStatus::Ready);
        assert_eq!(control.failover_order, [4]);
        assert_eq!(control.meter.row, tick + 1);
        assert_eq!(control.meter.request, tick + 1);
        let stats = fleet.stats();
        assert_eq!(stats.retained_meter_rows, ((tick + 1) as usize).min(16));
        assert_eq!(stats.known_data_references, 1);
        assert_eq!(stats.current_data_references, 1);
        assert_eq!((stats.admitted_members, stats.consent_pairs), (2, 2));
        last_reference = known;
    }
    let rows = fleet.policy_rows();
    assert_eq!(rows.len(), 16);
    assert_eq!(rows.first().unwrap().row, 9_985);
    assert_eq!(rows.last().unwrap().row, 10_000);
    assert!(rows.windows(2).all(|pair| pair[1].row == pair[0].row + 1));
    // A preview at a later tick does not advance the accepted-control clock.
    let before_query = fleet.stats();
    let mut down = reading(10, 10_001);
    down.available = false;
    fleet.update_reading(&target(), 1, down).unwrap();
    assert_eq!(
        fleet.resolve_data(target(), 10_001).unwrap().status,
        ResolutionStatus::NoChannel
    );
    assert_eq!(fleet.stats(), before_query);
    // The next accepted control can still use tick 9,999, the last accepted
    // control tick. A future-observed BLE link is avoided by keeping its 9,999
    // reading unchanged; only historical data-reference identity is required.
    let next = verified(10_001);
    assert_eq!(
        fleet
            .resolve_control(
                target(),
                9_999,
                &next,
                &last_reference,
                TrafficPath::Control
            )
            .unwrap()
            .status,
        ResolutionStatus::Ready
    );
    let duplicate = fleet
        .resolve_control(
            target(),
            9_999,
            &next,
            &last_reference,
            TrafficPath::Control,
        )
        .unwrap();
    assert_eq!(duplicate.status, ResolutionStatus::Denied);
    assert!(duplicate.failover_order.is_empty());
    assert_eq!(fleet.stats().retained_meter_rows, 16);
    assert_eq!(fleet.stats().known_data_references, 1);
}

/// Failing mutations: retain unknown or duplicate constructor members/consents as unbounded policy context.
#[test]
fn constructor_filters_large_duplicate_and_unknown_inputs_to_registered_context() {
    let mut records = registry(vec![endpoint(1, EndpointKind::Lan, 10, 0)]);
    let unknown = NodeIdentity::new([0xee; 16], [0xfe; 16]);
    let mut members = Vec::new();
    let mut consents = Vec::new();
    for _ in 0..10_000 {
        members.extend([unknown, source(), target(), source()]);
        consents.extend([
            (source(), unknown),
            (unknown, target()),
            (source(), target()),
            (source(), target()),
        ]);
    }
    let mut fleet = FleetResolver::new(
        &mut records,
        source(),
        Auth::fixture(&source().label(), true),
        &members,
        &consents,
    );
    let stats = fleet.stats();
    assert_eq!((stats.admitted_members, stats.consent_pairs), (2, 1));
    assert_eq!(
        (stats.retained_meter_rows, stats.known_data_references),
        (0, 0)
    );
    assert_eq!(stats.current_data_references, 0);
    assert_eq!(
        fleet.resolve_data(target(), 0).unwrap().status,
        ResolutionStatus::Ready
    );
    let before = fleet.stats();
    assert_eq!(
        fleet.resolve_data(unknown, 0),
        Err(FleetResolveError::UnregisteredTarget)
    );
    assert_eq!(fleet.stats(), before);
}
