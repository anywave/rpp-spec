#![cfg(feature = "std")]

use rpp_control::ControlKind;
use rpp_core::{
    overlay::{Billboard, BillboardKind, Link, Status, Underlay},
    scenarios,
};
use rpp_link::simulated::{
    self, HostBridge, HostError, SendRecord, SimulatedAdapter, A_ID, B_ID, R_ID,
};
use rpp_link::{DataOutcome, LinkAdapter, LinkReading};
use std::collections::BTreeMap;

fn bridge() -> HostBridge {
    HostBridge::new(
        scenarios::simulator(),
        BTreeMap::from([(A_ID, "A".into()), (B_ID, "B".into()), (R_ID, "R".into())]),
    )
}
fn lan(tick: u64) -> SimulatedAdapter {
    let mut l = Link::new("lan", "A", "B", Underlay::Lan);
    l.observed = tick;
    SimulatedAdapter::from_link(l)
}
fn internet(tick: u64) -> SimulatedAdapter {
    let mut l = Link::new("internet", "A", "B", Underlay::Internet);
    l.observed = tick;
    l.latency = 30;
    SimulatedAdapter::from_link(l)
}
fn board(since: i128, until: i128) -> Billboard {
    Billboard {
        machine: "B".into(),
        kind: BillboardKind::Rule,
        fact: "Pause.".into(),
        since,
        until,
        receipt: "r1".into(),
    }
}

#[test]
fn adapter_driven_scenarios_match_three_python_artifacts() {
    // Mutation adapter-bypass/changed-reading: selection and delivery must preserve every Python scenario byte and deterministic reruns.
    let actual = simulated::artifacts();
    assert_eq!(
        actual.csv,
        include_bytes!("../../rpp-core/tests/data/overlay-scenarios.csv")
    );
    assert_eq!(
        actual.markdown,
        include_bytes!("../../rpp-core/tests/data/overlay-scenarios.md")
    );
    assert_eq!(
        actual.json,
        include_bytes!("../../rpp-core/tests/data/overlay-billboards.json")
    );
    assert_eq!(actual, simulated::artifacts());
    let trace = simulated::run();
    assert_eq!(trace.run.rows.len(), 17);
    assert_eq!(trace.run.rows.iter().map(|r| r.request).max(), Some(16));
    assert!(trace.audit.readings > 16);
    assert_eq!(trace.audit.control_hops, 2);
    assert_eq!(trace.audit.attempts.len(), 8);
    assert_eq!(trace.audit.data_hops, 11);
}
#[test]
fn actual_adapter_readings_determine_data_path_and_dispatch() {
    // Mutation ignore-readings: lower measured latency must select and dispatch Wi-Fi instead of LAN.
    let mut slow = Link::new("lan", "A", "B", Underlay::Lan);
    slow.latency = 1;
    let mut fast = Link::new("wifi", "A", "B", Underlay::Wifi);
    fast.latency = 100;
    let mut adapters = [
        SimulatedAdapter::from_link(slow).with_reading(LinkReading {
            latency_ms: 100,
            loss_ppm: 0,
            jitter_ms: 0,
            available: true,
            observed: 0,
        }),
        SimulatedAdapter::from_link(fast).with_reading(LinkReading {
            latency_ms: 5,
            loss_ppm: 0,
            jitter_ms: 0,
            available: true,
            observed: 0,
        }),
    ];
    let mut host = bridge();
    host.send_data(0, "A", "B", &mut adapters).unwrap();
    assert_eq!(host.policy().rows()[0].path, "wifi");
    assert_eq!((adapters[0].reads(), adapters[1].reads()), (1, 1));
    assert!(adapters[0].sent().is_empty());
    assert_eq!(adapters[1].sent().len(), 1);
}
#[test]
fn dispatched_failures_retry_only_before_first_token() {
    // Mutation retry-after-token: a partial send must not invoke the fallback adapter; a zero-token failure must.
    for tokens in [0, 1] {
        let mut adapters = [
            lan(0).with_outcome(DataOutcome::Failed {
                emitted_tokens: tokens,
            }),
            internet(0),
        ];
        let mut host = bridge();
        host.send_data(0, "A", "B", &mut adapters).unwrap();
        assert_eq!(adapters[0].sent().len(), 1);
        assert_eq!(adapters[1].sent().len(), usize::from(tokens == 0));
        assert_eq!(host.policy().rows().len(), if tokens == 0 { 2 } else { 1 });
        assert_eq!(host.policy().rows()[0].tokens, tokens);
    }
}
#[test]
fn denied_invalid_and_clock_rollback_do_not_dispatch() {
    // Mutation send-before-policy: denial, stale/future/duplicate readings and clock rollback must not call an adapter send.
    let mut host = bridge();
    let mut adapters = [lan(0)];
    host.send_data(0, "A", "UNKNOWN", &mut adapters).unwrap();
    assert_eq!(host.policy().rows().last().unwrap().status, Status::Denied);
    host.send_data(6, "A", "B", &mut adapters).unwrap();
    assert_eq!(
        host.policy().rows().last().unwrap().status,
        Status::NoChannel
    );
    let mut duplicate = [lan(0), lan(0)];
    host.send_data(0, "A", "B", &mut duplicate).unwrap();
    assert_eq!(
        host.policy().rows().last().unwrap().status,
        Status::InvalidInput
    );
    assert!(adapters[0].sent().is_empty());
    assert!(duplicate.iter().all(|x| x.sent().is_empty()));
    let mut accepted = [lan(2)];
    host.send_data(2, "A", "B", &mut accepted).unwrap();
    host.send_data(1, "A", "B", &mut adapters).unwrap();
    assert_eq!(
        host.policy().rows().last().unwrap().status,
        Status::InvalidInput
    );
    assert!(adapters[0].sent().is_empty());
}
#[test]
fn verified_control_still_needs_known_independent_tunnel_and_current_consent() {
    // Mutation control-policy-bypass: decoding a frame does not supply a known independent path, consent or a tunnel.
    let mut host = bridge();
    let frame = simulated::verified_fixture(ControlKind::Alive, 0);
    let mut bt = [SimulatedAdapter::from_link(Link::new(
        "bt",
        "A",
        "B",
        Underlay::Bluetooth,
    ))];
    assert_eq!(
        host.send_verified_control(0, &frame, &mut bt, &[])
            .unwrap()
            .status,
        Status::Denied
    );
    assert!(bt[0].sent().is_empty());
    let data = host
        .choose_data_reference(0, "A", "B", &mut [lan(0)])
        .unwrap();
    let mut shared = [lan(0)];
    assert_eq!(
        host.send_verified_control(0, &frame, &mut shared, &data)
            .unwrap()
            .status,
        Status::NoIndependentChannel
    );
    let mut bad = Link::new("bt", "A", "B", Underlay::Bluetooth);
    bad.tunnel_verified = false;
    let mut bad = [SimulatedAdapter::from_link(bad)];
    assert_eq!(
        host.send_verified_control(0, &frame, &mut bad, &data)
            .unwrap()
            .status,
        Status::NoIndependentChannel
    );
    assert!(bad[0].sent().is_empty());
    assert_eq!(
        host.send_verified_control(0, &frame, &mut bt, &data)
            .unwrap()
            .status,
        Status::Ok
    );
    assert!(matches!(bt[0].sent(), [SendRecord::Control { .. }]));
    assert_eq!(
        host.send_verified_control(0, &frame, &mut bt, &data)
            .unwrap()
            .status,
        Status::Denied
    );
    assert_eq!(bt[0].sent().len(), 1);
}
#[test]
fn accepted_future_billboard_uses_data_but_replay_and_expired_do_not_send() {
    // Mutation send-denied-billboard: held future records are delivered once as data; replay/expiry never invoke the adapter.
    let mut host = bridge();
    let b = board(1, 2);
    let mut adapters = [lan(0)];
    assert_eq!(
        host.send_billboard(0, &b, &mut adapters).unwrap().status,
        Status::HeldUntilSince
    );
    assert!(matches!(adapters[0].sent(), [SendRecord::Data { .. }]));
    assert_eq!(
        host.send_billboard(0, &b, &mut adapters).unwrap().status,
        Status::Denied
    );
    let mut expired = [lan(2)];
    assert_eq!(
        host.send_billboard(2, &b, &mut expired).unwrap().status,
        Status::Denied
    );
    assert_eq!(adapters[0].sent().len(), 1);
    assert!(expired[0].sent().is_empty());
}
#[test]
fn unsupported_billboard_failure_fixture_fails_before_storage_or_dispatch() {
    // Mutation accept-unmodeled-billboard-loss: partial transport fixtures must not be reported as delivered by the CX007 model.
    let mut host = bridge();
    let mut adapters = [lan(0).with_outcome(DataOutcome::Failed { emitted_tokens: 1 })];
    assert_eq!(
        host.send_billboard(0, &board(0, 2), &mut adapters),
        Err(HostError::UnsupportedBillboardFailure)
    );
    assert!(adapters[0].sent().is_empty());
    assert!(host.policy().rows().is_empty());
}
#[test]
fn invalid_reading_and_unknown_identity_fail_closed() {
    // Mutation skip-read-validation/identity-binding: invalid loss and unmapped verified identities cannot reach a send hook.
    let mut bad = Link::new("bad", "A", "B", Underlay::Lan);
    bad.loss_ppm = 1_000_001;
    let mut adapter = SimulatedAdapter::from_link(bad);
    assert!(adapter.read(0).is_err());
    let mut adapters = [adapter];
    assert!(bridge().send_data(0, "A", "B", &mut adapters).is_err());
    assert!(adapters[0].sent().is_empty());
    let mut host = HostBridge::new(scenarios::simulator(), BTreeMap::new());
    assert_eq!(
        host.send_verified_control(
            0,
            &simulated::verified_fixture(ControlKind::Stop, 0),
            &mut adapters,
            &[]
        ),
        Err(HostError::UnknownIdentity)
    );
}

#[test]
fn separator_alias_names_fail_before_control_billboard_policy_or_callbacks() {
    // Mutation slash-name-bypass: a/b must never be decoded into unselected adapters a and b.
    for control in [true, false] {
        let mut host = bridge();
        let reference = host
            .choose_data_reference(0, "A", "B", &mut [lan(0)])
            .unwrap();
        let mut compound = Link::new("a/b", "A", "B", Underlay::Lan);
        compound.latency = 1;
        let mut a = Link::new("a", "A", "B", Underlay::Lan);
        a.latency = 100;
        let mut b = Link::new("b", "A", "B", Underlay::Lan);
        b.latency = 100;
        let mut adapters = [
            SimulatedAdapter::from_link(compound),
            SimulatedAdapter::from_link(a),
            SimulatedAdapter::from_link(b),
        ];
        let result = if control {
            host.send_verified_control(
                0,
                &simulated::verified_fixture(ControlKind::Alive, 0),
                &mut adapters,
                &reference,
            )
        } else {
            host.send_billboard(0, &board(0, 2), &mut adapters)
        };
        assert_eq!(result, Err(HostError::UnsupportedLinkName));
        assert!(host.policy().rows().is_empty());
        assert_eq!(host.policy().clock(), 0);
        assert!(adapters
            .iter()
            .all(|adapter| adapter.reads() == 0 && adapter.sent().is_empty()));
        // The failed alias bank consumed neither the receipt nor application time.
        assert_eq!(
            host.send_billboard(0, &board(0, 2), &mut [lan(0)])
                .unwrap()
                .status,
            Status::Delivered
        );
    }
}
