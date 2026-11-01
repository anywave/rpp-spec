#![cfg(feature = "alloc")]
//! Bounded hostile inputs exercise the fleet boundary, without network or cryptography.

mod support;

use rpp_fleet::{
    endpoint::{Endpoint, EndpointError, EndpointKind},
    identity::NodeIdentity,
    registry::RegistryError,
    resolver::{FleetResolveError, ResolutionStatus},
    MAX_URI_LEN,
};
use rpp_link::TrafficPath;
use support::*;

/// Failing mutations: allow URI limit plus one or mutate registry ownership before URI rejection.
#[test]
fn uri_byte_limit_accepts_exactly_limit_and_rejects_plus_one_atomically() {
    assert_eq!(MAX_URI_LEN, 192);
    let mut exact = endpoint(1, EndpointKind::Lan, 10, 0);
    exact.uri = format!("ipv4://{}", "a".repeat(MAX_URI_LEN - 7));
    assert_eq!(exact.uri.len(), MAX_URI_LEN);
    assert!(exact.valid());
    let mut records = registry(vec![exact.clone()]);
    let mut oversized = exact.clone();
    oversized.uri.push('a');
    assert_eq!(oversized.uri.len(), MAX_URI_LEN + 1);
    assert_eq!(oversized.validate(), Err(EndpointError::Capacity));
    assert_eq!(
        Endpoint::new(
            oversized.id,
            oversized.kind,
            oversized.uri.clone(),
            oversized.last_reading,
            oversized.capabilities,
        ),
        Err(EndpointError::Capacity)
    );
    let before = records.clone();
    let rejected = NodeIdentity::new([3; 16], [3; 16]);
    assert_eq!(
        records.register(binding(rejected, 3), vec![oversized.clone()]),
        Err(RegistryError::InvalidEndpoint)
    );
    assert_eq!(records, before);
    assert_eq!(
        records.replace_endpoints(&target(), vec![oversized]),
        Err(RegistryError::InvalidEndpoint)
    );
    assert_eq!(records, before);
    assert!(records.get(&rejected).is_none());
    records.replace_endpoints(&target(), vec![exact]).unwrap();
    assert_eq!(records, before);
}

/// Failing mutations: admit non-ASCII invisibles, empty/userinfo hosts, empty ports or ASCII controls.
#[test]
fn hostile_uri_characters_and_empty_websocket_authorities_are_rejected() {
    let ordinary = endpoint(1, EndpointKind::Lan, 10, 0);
    for uri in [
        "".to_owned(),
        "ipv4://host/\u{200b}".to_owned(),
        "ipv4://host/\u{202e}".to_owned(),
        "ipv4://host/\n".to_owned(),
        "ipv4://host/\u{7f}".to_owned(),
    ] {
        assert_eq!(
            Endpoint::new(
                ordinary.id,
                ordinary.kind,
                uri,
                ordinary.last_reading,
                ordinary.capabilities,
            ),
            Err(EndpointError::InvalidUri)
        );
    }
    for uri in [
        "ws://@x",
        "ws://:",
        "ws://",
        "ws:///path",
        "ws://host:/path",
    ] {
        assert_eq!(
            Endpoint::new(
                2,
                EndpointKind::WebSocketGateway,
                uri,
                ordinary.last_reading,
                ordinary.capabilities,
            ),
            Err(EndpointError::InvalidUri),
            "{uri}"
        );
    }
}

/// Failing mutations: accept sentinel/overflow readings, write them before validation, or poison later routes.
#[test]
fn rejected_reading_updates_preserve_good_data_control_and_registry_state() {
    let mut records = registry(vec![
        endpoint(1, EndpointKind::Lan, 10, 0),
        endpoint(4, EndpointKind::Ble, 1, 0),
    ]);
    let mut fleet = resolver(&mut records);
    let known = fleet
        .resolve_data(target(), 0)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    let good = reading(10, 0);
    for (index, invalid) in [
        rpp_link::LinkReading {
            latency_ms: u64::MAX,
            ..good
        },
        rpp_link::LinkReading {
            jitter_ms: u64::MAX,
            ..good
        },
        rpp_link::LinkReading {
            loss_ppm: 1_000_001,
            ..good
        },
    ]
    .into_iter()
    .enumerate()
    {
        let before_registry = fleet.registry().clone();
        let before_rows = fleet.policy_rows().to_vec();
        let literal = Endpoint {
            last_reading: invalid,
            ..endpoint(1, EndpointKind::Lan, 10, 0)
        };
        assert_eq!(literal.validate(), Err(EndpointError::InvalidReading));
        assert_eq!(
            Endpoint::new(
                literal.id,
                literal.kind,
                &literal.uri,
                invalid,
                literal.capabilities,
            ),
            Err(EndpointError::InvalidReading)
        );
        assert_eq!(
            fleet.update_reading(&target(), 1, invalid),
            Err(RegistryError::InvalidReading)
        );
        assert_eq!(fleet.registry(), &before_registry);
        assert_eq!(fleet.policy_rows(), before_rows);
        let data = fleet.resolve_data(target(), 0).unwrap();
        assert_eq!(data.status, ResolutionStatus::Ready);
        assert_eq!(data.selected().unwrap().path(), known);
        let frame = verified(index as u64 + 1);
        let control = fleet
            .resolve_control(target(), 0, &frame, &known, TrafficPath::Control)
            .unwrap();
        assert_eq!(control.status, ResolutionStatus::Ready);
        assert_eq!(control.route.unwrap().endpoint().endpoint_id, 4);
    }
}

/// Failing mutation: turn an empty endpoint set into implicit fallback or a fabricated channel.
#[test]
fn empty_endpoint_list_returns_explicit_no_channel() {
    let mut records = registry(Vec::new());
    let mut fleet = resolver(&mut records);
    let data = fleet.resolve_data(target(), 0).unwrap();
    assert_eq!(data.status, ResolutionStatus::NoChannel);
    assert!(data.routes.is_empty());
    assert!(data.failover_order().is_empty());
    assert!(fleet.policy_rows().is_empty());
}

/// Failing mutation: rank equal-score endpoints by insertion order instead of the core path key.
#[test]
fn exact_cost_tie_selects_smaller_endpoint_id_through_core_ranking() {
    let mut records = registry(vec![
        endpoint(8, EndpointKind::Wifi, 10, 0),
        endpoint(2, EndpointKind::Lan, 10, 0),
    ]);
    let mut fleet = resolver(&mut records);
    let data = fleet.resolve_data(target(), 0).unwrap();
    assert_eq!(data.status, ResolutionStatus::Ready);
    assert_eq!(data.failover_order(), [2, 8]);
    assert!(data.routes[0].path()[0].name.ends_with("-ep00000002"));
}

/// Failing mutations: accept empty/forged references or consume a sequence/meter row while rejecting them.
#[test]
fn invalid_reference_errors_precede_all_policy_state_changes() {
    let mut records = registry(vec![
        endpoint(1, EndpointKind::Lan, 10, 0),
        endpoint(4, EndpointKind::Ble, 1, 0),
    ]);
    let mut fleet = resolver(&mut records);
    let known = fleet
        .resolve_data(target(), 0)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    let mut forged = known.clone();
    forged[0].latency += 1;
    let notice = verified(1);
    let before_rows = fleet.policy_rows().to_vec();
    let before_registry = fleet.registry().clone();
    let before_stats = fleet.stats();
    for path in [&[][..], forged.as_slice()] {
        assert_eq!(
            fleet.resolve_control(target(), 0, &notice, path, TrafficPath::Control),
            Err(FleetResolveError::InvalidDataReference)
        );
        assert_eq!(fleet.policy_rows(), before_rows);
        assert_eq!(fleet.registry(), &before_registry);
        assert_eq!(fleet.stats(), before_stats);
    }
    assert_eq!(
        fleet
            .resolve_control(target(), 0, &notice, &known, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::Ready
    );
}

/// Failing mutations: classify future observations as malformed input or label every invalid input as clock rollback.
#[test]
fn future_observations_are_no_channel_and_rollback_uses_its_specific_error() {
    let mut records = registry(vec![
        endpoint(1, EndpointKind::Lan, 10, 10),
        endpoint(4, EndpointKind::Ble, 1, 10),
    ]);
    let mut fleet = resolver(&mut records);
    assert_eq!(
        fleet.resolve_data(target(), 9).unwrap().status,
        ResolutionStatus::NoChannel
    );
    assert_eq!(fleet.stats().known_data_references, 0);
    let known = fleet
        .resolve_data(target(), 10)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    let notice = verified(1);
    assert_eq!(
        fleet
            .resolve_control(target(), 10, &notice, &known, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::Ready
    );
    let rows = fleet.policy_rows().to_vec();
    assert_eq!(
        fleet.resolve_data(target(), 9),
        Err(FleetResolveError::ClockRollback)
    );
    assert_eq!(fleet.policy_rows(), rows);
    let next = verified(2);
    assert_eq!(
        fleet.resolve_control(target(), 9, &next, &known, TrafficPath::Control),
        Err(FleetResolveError::ClockRollback)
    );
    assert_eq!(
        fleet
            .resolve_control(target(), 10, &next, &known, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::Ready
    );
}
