#![cfg(feature = "alloc")]
//! Fleet composition tests; prior identity/signature/tunnel facts are fixtures.

use std::fmt::Write;

use rpp_control::{
    decode, ControlFrame, ControlKind, NodeId, Signature, VerifiedControlFrame, Verifier,
    HEADER_LEN,
};
use rpp_core::canonical::CanonicalAddress;
use rpp_core::overlay::{Auth, Underlay};
use rpp_fleet::endpoint::{Endpoint, EndpointCapabilities, EndpointKind};
use rpp_fleet::identity::{AddressBinding, AssignmentPolicy, NodeIdentity};
use rpp_fleet::registry::Registry;
use rpp_fleet::resolver::{
    ControlResolution, DataResolution, FleetResolveError, FleetResolver, ResolutionStatus,
};
use rpp_link::{DataOutcome, DispatchOutcome, LinkAdapter, LinkKind, LinkReading, TrafficPath};

fn source() -> NodeIdentity {
    NodeIdentity::new([0x11; 16], [1; 16])
}
fn target() -> NodeIdentity {
    NodeIdentity::new([0x22; 16], [2; 16])
}

fn reading(latency_ms: u64, observed: u64) -> LinkReading {
    LinkReading {
        latency_ms,
        loss_ppm: 0,
        jitter_ms: 0,
        available: true,
        observed,
    }
}

fn endpoint(id: u32, kind: EndpointKind, latency: u64, tick: u64) -> Endpoint {
    let uri = match id {
        1 => "ipv4://192.0.2.10:9000/rpp",
        2 => "ipv4://192.0.2.20:9000/rpp",
        3 => "ipv4://198.51.100.10:9000/rpp",
        4 => "bt://voice-device/control",
        5 => "lora://fleet/1",
        6 => "ws://voice-gateway.lan/xiaozhi",
        _ => "ipv4://192.0.2.30:9000/rpp",
    };
    Endpoint::new(
        id,
        kind,
        uri,
        reading(latency, tick),
        EndpointCapabilities {
            tunnel_verified: true,
            reviewed_adapter: false,
            observation_verified: true,
            control_capable: kind != EndpointKind::WebSocketGateway,
            failure_domain: match kind {
                EndpointKind::Ble => 2,
                EndpointKind::Lora => 3,
                _ => 1,
            },
        },
    )
    .unwrap()
}

fn base_endpoints() -> Vec<Endpoint> {
    // Deliberately not cost-sorted. BLE has the lowest latency but no data adapter.
    vec![
        endpoint(2, EndpointKind::Wifi, 40, 0),
        endpoint(1, EndpointKind::Lan, 10, 0),
        endpoint(3, EndpointKind::Internet, 100, 0),
        endpoint(4, EndpointKind::Ble, 1, 0),
    ]
}

fn registry(endpoints: Vec<Endpoint>) -> Registry {
    let mut registry = Registry::new();
    for (identity, theta, endpoints) in [(source(), 1, Vec::new()), (target(), 2, endpoints)] {
        registry
            .register(
                AddressBinding::new(
                    identity,
                    CanonicalAddress::new(theta, 1, 0, 0.0, 0).unwrap(),
                    AssignmentPolicy::ExplicitCallerAssignmentV1,
                ),
                endpoints,
            )
            .unwrap();
    }
    registry
}

fn resolver(registry: &mut Registry) -> FleetResolver<'_> {
    FleetResolver::new(
        registry,
        source(),
        Auth::fixture(&source().label(), true),
        &[source(), target()],
        &[(source(), target()), (target(), source())],
    )
}

struct LiteralVerifier {
    header: [u8; HEADER_LEN],
    signature: Signature,
}
impl Verifier for LiteralVerifier {
    fn verify(&self, sender: &NodeId, header: &[u8; HEADER_LEN], signature: &Signature) -> bool {
        header == &self.header
            && signature == &self.signature
            && sender.as_slice() == &self.header[16..32]
    }
}

fn verified(sequence: u64) -> VerifiedControlFrame {
    let signature = [0xa5; 64];
    let frame = ControlFrame::new(
        ControlKind::Stop,
        sequence,
        *source().device_id(),
        *target().device_id(),
        signature,
    );
    decode(
        &frame.encode(),
        target().device_id(),
        &LiteralVerifier {
            header: frame.header(),
            signature,
        },
    )
    .unwrap()
}

fn status(value: ResolutionStatus) -> &'static str {
    match value {
        ResolutionStatus::Ready => "OK",
        ResolutionStatus::NoChannel => "NO_CHANNEL",
        ResolutionStatus::Denied => "DENIED",
    }
}

fn data_row(name: &str, result: DataResolution) -> [String; 7] {
    let selected = result.selected();
    [
        name.into(),
        "data".into(),
        status(result.status).into(),
        selected.map_or_else(|| "-".into(), |route| route.endpoint_id.to_string()),
        selected.map_or_else(|| "-".into(), |route| route.kind.as_str().into()),
        selected.map_or_else(|| "-".into(), |route| route.uri.clone()),
        if result.routes.is_empty() {
            "-".into()
        } else {
            result
                .failover_order()
                .iter()
                .map(u32::to_string)
                .collect::<Vec<_>>()
                .join(",")
        },
    ]
}

fn control_row(name: &str, result: ControlResolution<'_>) -> [String; 7] {
    let selected = result.route.as_ref().map(|route| route.endpoint());
    [
        name.into(),
        "control".into(),
        status(result.status).into(),
        selected.map_or_else(|| "-".into(), |route| route.endpoint_id.to_string()),
        selected.map_or_else(|| "-".into(), |route| route.kind.as_str().into()),
        selected.map_or_else(|| "-".into(), |route| route.uri.clone()),
        if result.failover_order.is_empty() {
            "-".into()
        } else {
            result
                .failover_order
                .iter()
                .map(u32::to_string)
                .collect::<Vec<_>>()
                .join(",")
        },
    ]
}

fn scripted_rows() -> Vec<[String; 7]> {
    let mut rows = Vec::new();
    let mut records = registry(base_endpoints());
    let mut fleet = resolver(&mut records);
    rows.push(data_row("lan-up", fleet.resolve_data(target(), 0).unwrap()));

    let mut endpoints = base_endpoints();
    endpoints[0].last_reading.latency_ms = 5;
    endpoints[1].last_reading.latency_ms = 50;
    let mut records = registry(endpoints);
    let mut fleet = resolver(&mut records);
    rows.push(data_row(
        "wifi-before-spike",
        fleet.resolve_data(target(), 0).unwrap(),
    ));
    let mut spike = reading(600, 1);
    spike.loss_ppm = 500_000;
    spike.jitter_ms = 90;
    fleet.update_reading(&target(), 2, spike).unwrap();
    rows.push(data_row(
        "wifi-spike",
        fleet.resolve_data(target(), 1).unwrap(),
    ));

    let mut records = registry(vec![
        endpoint(1, EndpointKind::Lan, 10, 0),
        endpoint(4, EndpointKind::Ble, 1, 1),
    ]);
    let mut fleet = resolver(&mut records);
    let known = fleet
        .resolve_data(target(), 0)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    let mut down = reading(10, 1);
    down.available = false;
    fleet.update_reading(&target(), 1, down).unwrap();
    rows.push(data_row(
        "ble-control-only-data",
        fleet.resolve_data(target(), 1).unwrap(),
    ));
    let notice = verified(1);
    rows.push(control_row(
        "ble-control-only-control",
        fleet
            .resolve_control(target(), 1, &notice, &known, TrafficPath::Control)
            .unwrap(),
    ));

    let mut reviewed = endpoint(4, EndpointKind::Ble, 1, 0);
    reviewed.capabilities.reviewed_adapter = true;
    let mut records = registry(vec![reviewed]);
    let mut fleet = resolver(&mut records);
    rows.push(data_row(
        "ble-reviewed-data",
        fleet.resolve_data(target(), 0).unwrap(),
    ));

    let mut records = registry(vec![
        endpoint(1, EndpointKind::Lan, 10, 0),
        endpoint(2, EndpointKind::Wifi, 5, 1),
        endpoint(4, EndpointKind::Ble, 1, 1),
    ]);
    let mut fleet = resolver(&mut records);
    let known = fleet
        .resolve_data(target(), 0)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    for (id, latency) in [(1, 10), (2, 5), (4, 1)] {
        let mut down = reading(latency, 1);
        down.available = false;
        fleet.update_reading(&target(), id, down).unwrap();
    }
    rows.push(data_row(
        "partition-data",
        fleet.resolve_data(target(), 1).unwrap(),
    ));
    let notice = verified(1);
    rows.push(control_row(
        "partition-control",
        fleet
            .resolve_control(target(), 1, &notice, &known, TrafficPath::Control)
            .unwrap(),
    ));

    let mut records = registry(vec![endpoint(6, EndpointKind::WebSocketGateway, 15, 0)]);
    let mut fleet = resolver(&mut records);
    rows.push(data_row(
        "xiaozhi-websocket-lan-gateway",
        fleet.resolve_data(target(), 0).unwrap(),
    ));
    rows
}

fn rendered(rows: &[[String; 7]]) -> (Vec<u8>, Vec<u8>) {
    let mut tsv = String::from("scenario\ttraffic\tstatus\tendpoint\tkind\turi\tfailover\n");
    let mut markdown = String::from("# Scripted fleet endpoint selection\n\nThe existing merged overlay policy chooses paths from these supplied readings.\nIdentity assignments and prior verification are fixtures; no radio, discovery or cryptography runs.\n\n| Scenario | Traffic | Status | Endpoint | Kind | URI | Failover order |\n|---|---|---|---:|---|---|---|\n");
    for row in rows {
        writeln!(&mut tsv, "{}", row.join("\t")).unwrap();
        writeln!(&mut markdown, "| {} |", row.join(" | ")).unwrap();
    }
    (tsv.into_bytes(), markdown.into_bytes())
}

/// Failing mutation: reorder failover routes, allow unreviewed BLE data or change ws mapping.
/// Golden rows come from actual existing Python core policy, not identity hashing.
#[test]
fn scenario_tables_match_merged_python_policy_bytes_and_reruns() {
    let first = rendered(&scripted_rows());
    assert_eq!(
        first.0.as_slice(),
        include_bytes!("data/fleet-scenarios.tsv")
    );
    assert_eq!(
        first.1.as_slice(),
        include_bytes!("data/fleet-scenarios.md")
    );
    assert_eq!(first, rendered(&scripted_rows()));
    assert_eq!(scripted_rows().len(), 9);
}

/// Failing mutation: use endpoint insertion order or reverse the existing core ranking.
#[test]
fn reading_changes_reorder_routes_using_existing_core_policy() {
    let mut endpoints = base_endpoints();
    endpoints[0].last_reading.latency_ms = 5;
    endpoints[1].last_reading.latency_ms = 50;
    let mut records = registry(endpoints);
    let word = records.address(&target()).unwrap().to_word();
    let mut fleet = resolver(&mut records);
    assert_eq!(
        fleet.resolve_data(target(), 0).unwrap().failover_order(),
        [2, 1, 3]
    );
    let mut spike = reading(600, 1);
    spike.loss_ppm = 500_000;
    spike.jitter_ms = 90;
    fleet.update_reading(&target(), 2, spike).unwrap();
    let changed = fleet.resolve_data(target(), 1).unwrap();
    assert_eq!(changed.failover_order(), [1, 3, 2]);
    assert_eq!(changed.selected().unwrap().endpoint_id, 1);
    assert_eq!(fleet.registry().address(&target()).unwrap().to_word(), word);
}

/// Failing mutation: treat BLE as IP or invent reviewed_adapter=true before core selection.
#[test]
fn unreviewed_ble_is_not_data_route() {
    let mut records = registry(vec![endpoint(4, EndpointKind::Ble, 1, 0)]);
    let mut fleet = resolver(&mut records);
    assert_eq!(
        fleet.resolve_data(target(), 0).unwrap().status,
        ResolutionStatus::NoChannel
    );
    let mut reviewed = endpoint(4, EndpointKind::Ble, 1, 0);
    reviewed.capabilities.reviewed_adapter = true;
    let mut records = registry(vec![reviewed.clone()]);
    let mut fleet = resolver(&mut records);
    assert_eq!(
        fleet
            .resolve_data(target(), 0)
            .unwrap()
            .selected()
            .unwrap()
            .endpoint_id,
        4
    );
    reviewed.capabilities.tunnel_verified = false;
    let mut records = registry(vec![reviewed]);
    let mut fleet = resolver(&mut records);
    assert_eq!(
        fleet.resolve_data(target(), 0).unwrap().status,
        ResolutionStatus::NoChannel
    );
}

/// Failing mutation: remove the data-path control guard or consume sequence on that error.
#[test]
fn control_resolution_rejects_data_path_without_consuming_sequence() {
    let mut records = registry(vec![
        endpoint(1, EndpointKind::Lan, 10, 0),
        endpoint(4, EndpointKind::Ble, 1, 1),
    ]);
    let mut fleet = resolver(&mut records);
    let known = fleet
        .resolve_data(target(), 0)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    let notice = verified(1);
    let before = fleet.policy_rows().len();
    assert!(matches!(
        fleet.resolve_control(target(), 1, &notice, &known, TrafficPath::Data),
        Err(FleetResolveError::ControlOnDataPath)
    ));
    assert_eq!(fleet.policy_rows().len(), before);
    let valid = fleet
        .resolve_control(target(), 1, &notice, &known, TrafficPath::Control)
        .unwrap();
    assert_eq!(valid.status, ResolutionStatus::Ready);
    assert_eq!(valid.route.unwrap().endpoint().endpoint_id, 4);
}

#[derive(Default)]
struct CallCounter {
    controls: usize,
    data: usize,
    kind: Option<LinkKind>,
}
impl LinkAdapter for CallCounter {
    type Error = ();
    fn kind(&self) -> LinkKind {
        self.kind.unwrap_or(LinkKind::Ble)
    }
    fn read(&mut self, tick: u64) -> Result<LinkReading, Self::Error> {
        Ok(reading(1, tick))
    }
    fn send_verified_control_frame(&mut self, _: &VerifiedControlFrame) -> Result<(), Self::Error> {
        self.controls += 1;
        Ok(())
    }
    fn send_data(&mut self, _: &[u8]) -> Result<DataOutcome, Self::Error> {
        self.data += 1;
        Ok(DataOutcome::Sent)
    }
}

/// Failing mutation: hand a checked control frame to the rpp-link data path.
#[test]
fn verified_control_route_dispatch_uses_control_hook_only() {
    let mut records = registry(vec![
        endpoint(1, EndpointKind::Lan, 10, 0),
        endpoint(4, EndpointKind::Ble, 1, 1),
    ]);
    let mut fleet = resolver(&mut records);
    let known = fleet
        .resolve_data(target(), 0)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    let notice = verified(1);
    let resolved = fleet
        .resolve_control(target(), 1, &notice, &known, TrafficPath::Control)
        .unwrap();
    let route = resolved.route.unwrap();
    assert_eq!(route.frame().encode(), notice.encode());
    let mut adapter = CallCounter::default();
    assert_eq!(route.dispatch(&mut adapter), Ok(DispatchOutcome::Control));
    assert_eq!((adapter.controls, adapter.data), (1, 0));
    let notice = verified(2);
    let route = fleet
        .resolve_control(target(), 1, &notice, &known, TrafficPath::Control)
        .unwrap()
        .route
        .unwrap();
    let mut wrong_kind = CallCounter {
        kind: Some(LinkKind::Wifi),
        ..CallCounter::default()
    };
    assert_eq!(
        route.dispatch(&mut wrong_kind),
        Err(rpp_fleet::resolver::ControlDispatchError::AdapterKindMismatch)
    );
    assert_eq!((wrong_kind.controls, wrong_kind.data), (0, 0));
}

/// Failing mutation: treat voice WebSocket metadata as internet or create a control capability.
#[test]
fn xiaozhi_websocket_gateway_uses_lan_policy() {
    let gateway = endpoint(6, EndpointKind::WebSocketGateway, 15, 0);
    assert_eq!(gateway.kind.link_kind(), LinkKind::Lan);
    assert!(!gateway.capabilities.control_capable);
    let mut records = registry(vec![gateway]);
    let mut fleet = resolver(&mut records);
    let data = fleet.resolve_data(target(), 0).unwrap();
    let route = data.selected().unwrap();
    assert_eq!(route.kind, EndpointKind::WebSocketGateway);
    assert_eq!(route.uri, "ws://voice-gateway.lan/xiaozhi");
    assert_eq!(route.path()[0].underlay, Underlay::Lan);
    let known = route.path().to_vec();
    let notice = verified(1);
    assert_eq!(
        fleet
            .resolve_control(target(), 1, &notice, &known, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::NoChannel
    );
}

/// Failing mutation: drop the last data reference during outage or advance sequence on no path.
#[test]
fn partition_is_explicit_and_recovery_keeps_independent_control_available() {
    let mut records = registry(vec![
        endpoint(1, EndpointKind::Lan, 10, 0),
        endpoint(4, EndpointKind::Ble, 1, 1),
    ]);
    let mut fleet = resolver(&mut records);
    let known = fleet
        .resolve_data(target(), 0)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    for (id, latency) in [(1, 10), (4, 1)] {
        let mut down = reading(latency, 1);
        down.available = false;
        fleet.update_reading(&target(), id, down).unwrap();
    }
    assert_eq!(
        fleet.resolve_data(target(), 1).unwrap().status,
        ResolutionStatus::NoChannel
    );
    let notice = verified(1);
    assert_eq!(
        fleet
            .resolve_control(target(), 1, &notice, &known, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::NoChannel
    );
    fleet.update_reading(&target(), 4, reading(1, 2)).unwrap();
    assert_eq!(
        fleet
            .resolve_control(target(), 2, &notice, &known, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::Ready
    );
}

/// Failing mutation: retain older or caller-forged references after another path is selected.
#[test]
fn control_requires_the_last_actual_data_selection_for_its_target() {
    let mut endpoints = base_endpoints();
    endpoints[0].last_reading.latency_ms = 5;
    endpoints[1].last_reading.latency_ms = 50;
    let mut records = registry(endpoints);
    let mut fleet = resolver(&mut records);
    let old = fleet
        .resolve_data(target(), 0)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    fleet.update_reading(&target(), 2, reading(600, 1)).unwrap();
    let current = fleet
        .resolve_data(target(), 1)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    assert_ne!(old, current);
    let notice = verified(1);
    let before = fleet.policy_rows().to_vec();
    let before_stats = fleet.stats();
    assert_eq!(
        fleet.resolve_control(target(), 1, &notice, &old, TrafficPath::Control),
        Err(FleetResolveError::InvalidDataReference)
    );
    assert_eq!(fleet.policy_rows(), before);
    assert_eq!(fleet.stats(), before_stats);
    assert_eq!(
        fleet
            .resolve_control(target(), 1, &notice, &current, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::Ready
    );
}

/// Failing mutation: infer consent, membership or a verified issuer from registration alone.
#[test]
fn registration_never_supplies_admission_or_consent() {
    let mut records = registry(base_endpoints());
    let mut fleet = FleetResolver::new(
        &mut records,
        source(),
        Auth::fixture(&source().label(), true),
        &[],
        &[],
    );
    assert_eq!(
        fleet.resolve_data(target(), 0).unwrap().status,
        ResolutionStatus::Denied
    );
    let mut records = registry(base_endpoints());
    let mut fleet = FleetResolver::new(
        &mut records,
        source(),
        Auth::fixture(&source().label(), true),
        &[source(), target()],
        &[],
    );
    assert_eq!(
        fleet.resolve_data(target(), 0).unwrap().status,
        ResolutionStatus::Denied
    );
    let mut records = registry(base_endpoints());
    let mut fleet = FleetResolver::new(
        &mut records,
        source(),
        Auth::fixture(&source().label(), false),
        &[source(), target()],
        &[(source(), target())],
    );
    assert_eq!(
        fleet.resolve_data(target(), 0).unwrap().status,
        ResolutionStatus::Denied
    );
}

/// Failing mutation: invent a historic data-reference TTL or ignore fresh control readings.
#[test]
fn historical_data_reference_survives_outage_but_control_reading_must_be_fresh() {
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
    let mut down = reading(10, 6);
    down.available = false;
    fleet.update_reading(&target(), 1, down).unwrap();
    assert_eq!(
        fleet.resolve_data(target(), 6).unwrap().status,
        ResolutionStatus::NoChannel
    );
    let notice = verified(1);
    assert_eq!(
        fleet
            .resolve_control(target(), 6, &notice, &known, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::NoChannel
    );
    fleet.update_reading(&target(), 4, reading(1, 6)).unwrap();
    assert_eq!(
        fleet
            .resolve_control(target(), 6, &notice, &known, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::Ready
    );
}

/// Failing mutation: infer control compatibility from BLE's kind or tunnel metadata.
#[test]
fn control_requires_explicit_adapter_compatibility() {
    let mut ble = endpoint(4, EndpointKind::Ble, 1, 1);
    ble.capabilities.control_capable = false;
    let mut records = registry(vec![endpoint(1, EndpointKind::Lan, 10, 0), ble]);
    let mut fleet = resolver(&mut records);
    let known = fleet
        .resolve_data(target(), 0)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    let notice = verified(1);
    assert_eq!(
        fleet
            .resolve_control(target(), 1, &notice, &known, TrafficPath::Control)
            .unwrap()
            .status,
        ResolutionStatus::NoChannel
    );
}

/// Failing mutation: omit the registered address prefix from equal per-node endpoint IDs.
#[test]
fn endpoint_namespace_is_reversible_and_references_remain_target_bound() {
    let third = NodeIdentity::new([0x33; 16], [3; 16]);
    let mut records = registry(vec![endpoint(1, EndpointKind::Lan, 10, 0)]);
    records
        .register(
            AddressBinding::new(
                third,
                CanonicalAddress::new(3, 1, 0, 0.0, 0).unwrap(),
                AssignmentPolicy::ExplicitCallerAssignmentV1,
            ),
            vec![endpoint(1, EndpointKind::Lan, 10, 0)],
        )
        .unwrap();
    let first_word = records.address(&target()).unwrap().to_word();
    let other_word = records.address(&third).unwrap().to_word();
    let mut fleet = FleetResolver::new(
        &mut records,
        source(),
        Auth::fixture(&source().label(), true),
        &[source(), target(), third],
        &[(source(), target()), (source(), third)],
    );
    let first = fleet.resolve_data(target(), 0).unwrap();
    let other = fleet.resolve_data(third, 0).unwrap();
    let first_path = first.selected().unwrap().path().to_vec();
    let other_path = other.selected().unwrap().path().to_vec();
    assert_eq!(fleet.stats().known_data_references, 2);
    assert_eq!(fleet.stats().current_data_references, 2);
    assert_eq!(
        first.selected().unwrap().endpoint_id,
        other.selected().unwrap().endpoint_id
    );
    assert_eq!(first_path[0].name, format!("n{first_word:08x}-ep00000001"));
    assert_eq!(other_path[0].name, format!("n{other_word:08x}-ep00000001"));
    assert_ne!(first_path[0].name, other_path[0].name);
    assert!(first_path[0].name.len() <= 64 && !first_path[0].name.contains('/'));
    let signature = [0xa5; 64];
    let frame = ControlFrame::new(
        ControlKind::Stop,
        1,
        *source().device_id(),
        *third.device_id(),
        signature,
    );
    let notice = decode(
        &frame.encode(),
        third.device_id(),
        &LiteralVerifier {
            header: frame.header(),
            signature,
        },
    )
    .unwrap();
    let before = fleet.policy_rows().to_vec();
    let before_stats = fleet.stats();
    assert_eq!(
        fleet.resolve_control(third, 1, &notice, &first_path, TrafficPath::Control),
        Err(FleetResolveError::InvalidDataReference)
    );
    assert_eq!(fleet.policy_rows(), before);
    assert_eq!(fleet.stats(), before_stats);
}

/// Failing mutation: enumerate control alternatives in real state or reserve the sequence twice.
#[test]
fn control_failover_order_uses_core_ranking_with_one_real_transition() {
    let mut records = registry(vec![
        endpoint(1, EndpointKind::Lan, 10, 0),
        endpoint(5, EndpointKind::Lora, 30, 1),
        endpoint(4, EndpointKind::Ble, 20, 1),
    ]);
    let mut fleet = resolver(&mut records);
    let known = fleet
        .resolve_data(target(), 0)
        .unwrap()
        .selected()
        .unwrap()
        .path()
        .to_vec();
    let notice = verified(1);
    let before = fleet.policy_rows().len();
    let control = fleet
        .resolve_control(target(), 1, &notice, &known, TrafficPath::Control)
        .unwrap();
    assert_eq!(control.status, ResolutionStatus::Ready);
    assert_eq!(control.failover_order, [4, 5]);
    assert_eq!(control.route.unwrap().endpoint().endpoint_id, 4);
    assert_eq!(fleet.policy_rows().len(), before + 1);
    let repeated = fleet
        .resolve_control(target(), 1, &notice, &known, TrafficPath::Control)
        .unwrap();
    assert_eq!(repeated.status, ResolutionStatus::Denied);
    assert!(repeated.failover_order.is_empty());
}
