#![cfg(feature = "alloc")]
//! Rollback is the first resolver check, before validation or policy mutation.

mod support;

use rpp_core::overlay::Link;
use rpp_fleet::{
    endpoint::EndpointKind,
    identity::NodeIdentity,
    resolver::{FleetResolveError, FleetResolver, ResolutionStatus},
};
use rpp_link::TrafficPath;
use support::*;

fn prime(fleet: &mut FleetResolver<'_>) -> Vec<Link> {
    let known = fleet
        .resolve_data(target(), 10)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    assert_eq!(
        fleet
            .resolve_control(target(), 10, &verified(1), &known, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::Ready
    );
    known
}

/// Failing mutation: bypass the first data/control rollback guard and call core.
#[test]
fn rollback_tick_with_valid_input_is_rejected_without_spending_state() {
    let endpoints = vec![
        endpoint(1, EndpointKind::Lan, 10, 10),
        endpoint(4, EndpointKind::Ble, 1, 10),
    ];
    let mut exercised_records = registry(endpoints.clone());
    let mut clean_records = registry(endpoints);
    let mut fleet = resolver(&mut exercised_records);
    let mut clean = resolver(&mut clean_records);
    let known = prime(&mut fleet);
    let clean_known = prime(&mut clean);
    let before_stats = fleet.stats();
    let before_rows = fleet.policy_rows().to_vec();
    let before_registry = fleet.registry().clone();
    let frame = verified(2);

    assert_eq!(
        fleet.resolve_data(target(), 9),
        Err(FleetResolveError::ClockRollback)
    );
    assert_eq!(
        fleet.resolve_control(target(), 9, &frame, &known, TrafficPath::Control),
        Err(FleetResolveError::ClockRollback)
    );
    assert_eq!(fleet.stats(), before_stats);
    assert_eq!(fleet.policy_rows(), before_rows);
    assert_eq!(fleet.registry(), &before_registry);

    // Compare the next real transition with a clean context, including row and
    // request IDs, to detect hidden state spent by a rejected rollback.
    let next = fleet
        .resolve_control(target(), 10, &frame, &known, TrafficPath::Control)
        .unwrap();
    let expected = clean
        .resolve_control(target(), 10, &frame, &clean_known, TrafficPath::Control)
        .unwrap();
    assert_eq!(next.status, ResolutionStatus::Ready);
    assert_eq!(next, expected);
    assert_eq!(fleet.stats(), clean.stats());
    assert_eq!(fleet.policy_rows(), clean.policy_rows());
    assert_eq!(fleet.registry(), clean.registry());
}

/// Failing mutation: validate an invalid control path or target before rollback.
#[test]
fn rollback_tick_with_invalid_input_is_checked_first_and_preserves_state() {
    let endpoints = vec![
        endpoint(1, EndpointKind::Lan, 10, 10),
        endpoint(4, EndpointKind::Ble, 1, 10),
    ];
    let mut exercised_records = registry(endpoints.clone());
    let mut clean_records = registry(endpoints);
    let mut fleet = resolver(&mut exercised_records);
    let mut clean = resolver(&mut clean_records);
    let known = prime(&mut fleet);
    let clean_known = prime(&mut clean);
    let before_stats = fleet.stats();
    let before_rows = fleet.policy_rows().to_vec();
    let before_registry = fleet.registry().clone();
    let unknown = NodeIdentity::new([0x77; 16], [0x88; 16]);
    let frame = verified(2);
    let mut forged = known.clone();
    forged[0].failure_domain = "forged-domain".into();

    assert_eq!(
        fleet.resolve_data(unknown, 9),
        Err(FleetResolveError::ClockRollback)
    );
    for (recipient, reference, path) in [
        (target(), known.as_slice(), TrafficPath::Data),
        (target(), &[][..], TrafficPath::Control),
        (target(), forged.as_slice(), TrafficPath::Control),
        (unknown, known.as_slice(), TrafficPath::Control),
    ] {
        assert_eq!(
            fleet.resolve_control(recipient, 9, &frame, reference, path),
            Err(FleetResolveError::ClockRollback)
        );
        assert_eq!(fleet.stats(), before_stats);
        assert_eq!(fleet.policy_rows(), before_rows);
        assert_eq!(fleet.registry(), &before_registry);
    }

    let next = fleet
        .resolve_control(target(), 10, &frame, &known, TrafficPath::Control)
        .unwrap();
    let expected = clean
        .resolve_control(target(), 10, &frame, &clean_known, TrafficPath::Control)
        .unwrap();
    assert_eq!(next.status, ResolutionStatus::Ready);
    assert_eq!(next, expected);
    assert_eq!(fleet.stats(), clean.stats());
    assert_eq!(fleet.policy_rows(), clean.policy_rows());
    assert_eq!(fleet.registry(), clean.registry());
}
