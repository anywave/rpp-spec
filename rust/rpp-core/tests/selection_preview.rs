#![cfg(feature = "alloc")]

use std::collections::{BTreeMap, BTreeSet};

use rpp_core::overlay::{
    Auth, ControlFrame, ControlKind, Link, PolicyError, Simulator, Status, Underlay,
};

fn simulator() -> Simulator {
    Simulator::new(
        ["A", "B", "C"].into_iter().map(str::to_owned).collect(),
        BTreeSet::from([("A".into(), "B".into()), ("A".into(), "C".into())]),
        BTreeSet::new(),
    )
}

fn data(tick: u64) -> Link {
    let mut link = Link::new("lan", "A", "B", Underlay::Lan);
    link.observed = tick;
    link
}

fn control(tick: u64) -> Link {
    let mut link = Link::new("bt", "A", "B", Underlay::Bluetooth);
    link.observed = tick;
    link
}

fn frame(sequence: u64) -> ControlFrame {
    ControlFrame::notice("A", "B", ControlKind::Pause, sequence)
}

fn path_names(path: &[Link]) -> String {
    path.iter()
        .map(|link| link.name.as_str())
        .collect::<Vec<_>>()
        .join("/")
}

#[test]
fn data_preview_preserves_validation_ranking_and_relay_outcomes() {
    // Mutation preview-always-ready/skip-data-guard: queries must enforce the real policy before ranking.
    let mut down = data(0);
    down.available = false;
    let mut invalid = data(0);
    invalid.loss_ppm = 1_000_001;
    let mut ble = control(0);
    ble.latency = 0;
    let cases = [
        (0, "A", "B", vec![data(0)], Status::Ok, "direct"),
        (0, "A", "B", vec![down], Status::NoChannel, ""),
        (0, "A", "B", vec![invalid], Status::InvalidInput, ""),
        (0, "A", "B", vec![ble], Status::NoChannel, ""),
        (6, "A", "B", vec![data(0)], Status::NoChannel, ""),
        (-1, "A", "B", vec![data(0)], Status::InvalidInput, ""),
        (0, "A", "A", vec![data(0)], Status::DeniedSelfTarget, ""),
        (0, "B", "A", vec![data(0)], Status::Denied, ""),
    ];
    for (tick, source, target, links, status, detail) in cases {
        let mut sim = simulator();
        let preview = sim.preview_data(tick, source, target, &links);
        assert_eq!((preview.status, preview.detail), (status, detail));
        assert!(sim.rows().is_empty());
        assert_eq!(sim.known_data_path_count(), 0);
        sim.send_data(tick, source, target, &links, &BTreeMap::new());
        assert_eq!(sim.rows().len(), 1);
        let row = &sim.rows()[0];
        assert_eq!(row.status, preview.status);
        assert_eq!(row.path, path_names(&preview.path));
        assert_eq!(row.detail, preview.detail);
    }
    let mut sim = Simulator::new(
        ["A", "B", "C"].into_iter().map(str::to_owned).collect(),
        BTreeSet::from([
            ("A".into(), "B".into()),
            ("A".into(), "C".into()),
            ("C".into(), "B".into()),
        ]),
        BTreeSet::new(),
    );
    let relay = [
        Link::new("ac", "A", "C", Underlay::Lan),
        Link::new("cb", "C", "B", Underlay::Lan),
    ];
    let preview = sim.preview_data(0, "A", "B", &relay);
    assert_eq!(preview.status, Status::Ok);
    assert_eq!(preview.detail, "relay");
    assert_eq!(preview.path, relay);
    sim.send_data(0, "A", "B", &relay, &BTreeMap::new());
    assert_eq!(sim.rows()[0].path, "ac/cb");
    let mut slow = data(0);
    slow.name = "slow".into();
    slow.latency = 40;
    assert_eq!(
        sim.preview_data(0, "A", "B", &[slow, data(0)]).path,
        [data(0)]
    );
}

#[test]
fn control_preview_preserves_auth_reference_independence_and_sequence_guards() {
    // Mutation preview-bypasses-auth/reference/sequence/domain: preview and actual acceptance share every guard.
    let mut sim = simulator();
    let path = sim.choose_latest("A", "B", 0, &[data(0)]).unwrap();
    let good_auth = Auth::fixture("A", true);
    let bad_auth = Auth::fixture("A", false);
    let foreign_auth = Auth::fixture("C", true);
    let mut shared = control(0);
    shared.failure_domain = "lan".into();
    let mut invalid = control(0);
    invalid.loss_ppm = 1_000_001;
    let unknown = [data(1)];
    let cases = [
        (
            frame(1),
            Some(&good_auth),
            vec![control(0)],
            path.as_slice(),
            Status::Ok,
            "PAUSE",
        ),
        (
            frame(1),
            None,
            vec![control(0)],
            path.as_slice(),
            Status::Denied,
            "",
        ),
        (
            frame(1),
            Some(&bad_auth),
            vec![control(0)],
            path.as_slice(),
            Status::Denied,
            "",
        ),
        (
            frame(1),
            Some(&foreign_auth),
            vec![control(0)],
            path.as_slice(),
            Status::Denied,
            "",
        ),
        (
            frame(1),
            Some(&good_auth),
            vec![control(0)],
            unknown.as_slice(),
            Status::Denied,
            "unknown-data-path",
        ),
        (
            frame(1),
            Some(&good_auth),
            vec![shared],
            path.as_slice(),
            Status::NoIndependentChannel,
            "",
        ),
        (
            frame(1),
            Some(&good_auth),
            vec![invalid],
            path.as_slice(),
            Status::InvalidInput,
            "",
        ),
        (
            ControlFrame::from_kind("A", "B", "START", 1),
            Some(&good_auth),
            vec![control(0)],
            path.as_slice(),
            Status::Denied,
            "",
        ),
    ];
    for (notice, auth, links, reference, status, detail) in cases {
        let preview = sim.preview_control(0, &notice, auth, &links, reference);
        assert_eq!((preview.status, preview.detail), (status, detail));
        let mut actual = sim.clone();
        let row = actual.send_control(0, &notice, auth, &links, reference);
        assert_eq!(row.status, preview.status);
        assert_eq!(row.path, path_names(&preview.path));
        assert_eq!(row.detail, preview.detail);
        if status == Status::InvalidInput {
            assert!(row.source.is_empty() && row.target.is_empty());
        }
    }
    assert_eq!(
        sim.send_control(0, &frame(1), Some(&good_auth), &[control(0)], &path)
            .status,
        Status::Ok
    );
    assert_eq!(
        sim.preview_control(0, &frame(1), Some(&good_auth), &[control(0)], &path)
            .status,
        Status::Denied
    );
    assert_eq!(
        sim.preview_control(-1, &frame(2), Some(&good_auth), &[control(0)], &path)
            .status,
        Status::InvalidInput
    );
}

#[test]
fn ten_thousand_previews_do_not_spend_clock_sequence_requests_rows_or_references() {
    // Mutation preview-reserves-state: repeated future queries must not deny the first real current operation.
    let mut sim = simulator();
    let path = sim.choose_latest("A", "B", 0, &[data(0)]).unwrap();
    let auth = Auth::fixture("A", true);
    for tick in 1..=10_000 {
        assert_eq!(
            sim.preview_data(tick.into(), "A", "B", &[data(tick)])
                .status,
            Status::Ok
        );
        assert_eq!(
            sim.preview_control(tick.into(), &frame(1), Some(&auth), &[control(tick)], &path)
                .status,
            Status::Ok
        );
    }
    assert_eq!(sim.clock(), 0);
    assert!(sim.rows().is_empty());
    assert_eq!(sim.known_data_path_count(), 1);
    let row = sim.send_control(0, &frame(1), Some(&auth), &[control(0)], &path);
    assert_eq!((row.status, row.row, row.request), (Status::Ok, 1, 1));
}

#[test]
fn latest_paths_bound_varying_snapshots_and_preserve_each_other_pair() {
    // Mutation latest-appends-history/removes-other-pairs: changing readings must replace only this endpoint pair.
    let mut sim = simulator();
    let other = Link::new("ac", "A", "C", Underlay::Lan);
    sim.choose_latest("A", "C", 0, &[other]).unwrap();
    let first = sim.choose_latest("A", "B", 0, &[data(0)]).unwrap();
    let mut latest = first.clone();
    for tick in 1..=10_000 {
        let mut reading = data(tick);
        reading.latency = tick + 1;
        reading.jitter = tick;
        latest = sim
            .choose_latest("A", "B", tick.into(), &[reading])
            .unwrap();
        assert_eq!(sim.known_data_path_count(), 2);
    }
    assert_eq!(sim.clock(), 0);
    assert!(sim.rows().is_empty());
    let auth = Auth::fixture("A", true);
    assert_eq!(
        sim.preview_control(10_000, &frame(1), Some(&auth), &[control(10_000)], &first)
            .detail,
        "unknown-data-path"
    );
    assert_eq!(
        sim.preview_control(10_000, &frame(1), Some(&auth), &[control(10_000)], &latest)
            .status,
        Status::Ok
    );
}

#[test]
fn unavailable_or_invalid_latest_selection_preserves_historical_reference_without_new_ttl() {
    // Mutation latest-clears-on-outage/extra-reference-ttl: failed queries must not erase an earlier selected path.
    let mut sim = simulator();
    let path = sim.choose_latest("A", "B", 0, &[data(0)]).unwrap();
    assert!(sim.choose_latest("A", "B", 10_000, &[]).unwrap().is_empty());
    let mut invalid = data(10_000);
    invalid.loss_ppm = 1_000_001;
    assert_eq!(
        sim.choose_latest("A", "B", 10_000, &[invalid]),
        Err(PolicyError::InvalidLinks)
    );
    assert_eq!(sim.known_data_path_count(), 1);
    let row = sim.send_control(
        10_000,
        &frame(1),
        Some(&Auth::fixture("A", true)),
        &[control(10_000)],
        &path,
    );
    assert_eq!(row.status, Status::Ok);
    let mut legacy = simulator();
    let first = legacy.choose("A", "B", 0, &[data(0)]).unwrap();
    legacy.choose("A", "B", 1, &[data(1)]).unwrap();
    assert_eq!(legacy.known_data_path_count(), 2);
    assert_eq!(
        legacy
            .preview_control(
                10_000,
                &frame(1),
                Some(&Auth::fixture("A", true)),
                &[control(10_000)],
                &first
            )
            .status,
        Status::Ok
    );
}

#[test]
fn retained_meter_window_stays_flat_and_preserves_global_ids_across_ten_thousand_controls() {
    // Mutation retention-noop/reset-global-ids/preview-consumes-sequence: bounded storage must preserve the external ledger IDs.
    let mut sim = simulator();
    let path = sim.choose_latest("A", "B", 0, &[data(0)]).unwrap();
    let auth = Auth::fixture("A", true);
    for sequence in 1..=10_000 {
        let notice = frame(sequence);
        let links = [control(sequence)];
        assert_eq!(
            sim.preview_control(sequence.into(), &notice, Some(&auth), &links, &path)
                .status,
            Status::Ok
        );
        let row = sim.send_control(sequence.into(), &notice, Some(&auth), &links, &path);
        assert_eq!(
            (row.status, row.row, row.request),
            (Status::Ok, sequence, sequence)
        );
        sim.retain_meter_rows(16);
        assert_eq!(sim.rows().len(), (sequence as usize).min(16));
        assert_eq!(sim.known_data_path_count(), 1);
    }
    assert_eq!(sim.rows().first().unwrap().row, 9_985);
    assert_eq!(sim.rows().last().unwrap().row, 10_000);
    assert_eq!(sim.clock(), 10_000);
    sim.retain_meter_rows(0);
    assert!(sim.rows().is_empty());
    let row = sim.send_control(
        10_000,
        &frame(10_001),
        Some(&auth),
        &[control(10_000)],
        &path,
    );
    assert_eq!((row.row, row.request), (10_001, 10_001));
}

#[test]
fn retention_preserves_retry_rows_with_one_request_and_default_history() {
    // Mutation row-id-from-vector-length/request-id-from-row: trimming cannot reset rows or split one retried request.
    let mut sim = simulator();
    sim.send_data(0, "A", "B", &[data(0)], &BTreeMap::new());
    sim.retain_meter_rows(0);
    let mut alternate = data(1);
    alternate.name = "alternate".into();
    alternate.failure_domain = "alternate".into();
    alternate.latency = 20;
    sim.send_data(
        1,
        "A",
        "B",
        &[data(1), alternate],
        &BTreeMap::from([("lan".into(), 0)]),
    );
    assert_eq!(sim.rows().len(), 2);
    assert_eq!((sim.rows()[0].row, sim.rows()[1].row), (2, 3));
    assert_eq!((sim.rows()[0].request, sim.rows()[1].request), (2, 2));
    assert_eq!(
        (sim.rows()[0].status, sim.rows()[1].status),
        (Status::Failed, Status::Ok)
    );
    assert_eq!(sim.known_data_path_count(), 3);
    sim.retain_meter_rows(1);
    assert_eq!((sim.rows()[0].row, sim.rows()[0].request), (3, 2));
}
