use std::collections::{BTreeMap, BTreeSet};

use rpp_core::overlay::{
    Auth, Billboard, BillboardKind, ControlFrame, ControlKind, Link, PolicyError, Simulator,
    Status, Underlay,
};
use rpp_core::scenarios;

fn link(name: &str) -> Link {
    Link::new(name, "A", "B", Underlay::Lan)
}
fn data_links(tick: u64) -> Vec<Link> {
    let mut primary = link("lan");
    primary.observed = tick;
    let mut alternate = Link::new("internet", "A", "B", Underlay::Internet);
    alternate.observed = tick;
    alternate.latency = 30;
    vec![primary, alternate]
}
fn board(since: i128, until: i128, receipt: &str) -> Billboard {
    Billboard {
        machine: "B".into(),
        kind: BillboardKind::Rule,
        fact: "Pause the application.".into(),
        since,
        until,
        receipt: receipt.into(),
    }
}
fn notice(sequence: u64) -> ControlFrame {
    ControlFrame::notice("A", "B", ControlKind::Alive, sequence)
}

#[test]
fn scenario_artifacts_match_python_bytes_and_rerun_identically() {
    // Mutation changed-fixture-policy: any scenario route/status/order/render change breaks Python parity.
    let actual = scenarios::artifacts();
    assert_eq!(actual.csv, include_bytes!("data/overlay-scenarios.csv"));
    assert_eq!(actual.markdown, include_bytes!("data/overlay-scenarios.md"));
    assert_eq!(actual.json, include_bytes!("data/overlay-billboards.json"));
    assert_eq!(actual, scenarios::artifacts());
    let run = scenarios::run();
    assert_eq!(run.rows.len(), 17);
    assert_eq!(
        run.rows
            .iter()
            .map(|r| r.request)
            .collect::<BTreeSet<_>>()
            .len(),
        16
    );
}

#[test]
fn availability_all_masks_ranking_and_stable_ties() {
    // Mutation ignore-unavailable/constant-ranking: all eight masks and independent latency/loss/jitter costs discriminate.
    for mask in 0..8 {
        let links: Vec<_> = (0..3)
            .map(|index| {
                let mut l = link(&format!("link-{index}"));
                l.available = mask & (1 << index) != 0;
                l.latency = index + 1;
                l
            })
            .collect();
        let mut sim = scenarios::simulator();
        let chosen = sim.choose("A", "B", 0, &links).unwrap();
        let available: Vec<_> = links.iter().filter(|x| x.available).collect();
        assert_eq!(chosen.is_empty(), available.is_empty());
        if let Some(expected) = available.iter().min_by_key(|x| x.score()) {
            assert_eq!(chosen, vec![(**expected).clone()]);
        }
    }
    let mut slow = link("slow");
    slow.jitter = 40;
    let mut lossy = link("lossy");
    lossy.loss_ppm = 100_000;
    let mut fast = link("fast");
    fast.latency = 20;
    assert_eq!(
        scenarios::simulator()
            .choose("A", "B", 0, &[slow, lossy, fast])
            .unwrap()[0]
            .name,
        "fast"
    );
    assert_eq!(
        scenarios::simulator()
            .choose("A", "B", 0, &[link("z"), link("a")])
            .unwrap()[0]
            .name,
        "a"
    );
    assert_eq!(
        scenarios::simulator()
            .choose("A", "B", 0, &[link("a"), link("z")])
            .unwrap()[0]
            .name,
        "a"
    );
}

#[test]
fn relay_needs_member_and_each_directed_hop_consent() {
    // Mutation hop-consent-bypass/remove-relay: relay selection must require the complete authorized path.
    let ar = Link::new("ar", "A", "R", Underlay::Internet);
    let rb = Link::new("rb", "R", "B", Underlay::Internet);
    let path = scenarios::simulator()
        .choose("A", "B", 0, &[ar.clone(), rb.clone()])
        .unwrap();
    assert_eq!(path, vec![ar.clone(), rb.clone()]);
    let mut denied = Simulator::new(
        ["A", "B", "R"].into_iter().map(str::to_owned).collect(),
        BTreeSet::from([("A".into(), "B".into()), ("A".into(), "R".into())]),
        BTreeSet::new(),
    );
    assert!(denied.choose("A", "B", 0, &[ar, rb]).unwrap().is_empty());
}

#[test]
fn freshness_tunnel_and_radio_adapter_are_required() {
    // Mutation stale-reading/tunnel-bypass/radio-default: eligibility must fail closed for each independent guard.
    for age in 0..=5 {
        assert!(!scenarios::simulator()
            .choose("A", "B", age, &[link("fresh")])
            .unwrap()
            .is_empty());
    }
    assert!(scenarios::simulator()
        .choose("A", "B", 6, &[link("stale")])
        .unwrap()
        .is_empty());
    let mut future = link("future");
    future.observed = 1;
    assert!(scenarios::simulator()
        .choose("A", "B", 0, &[future])
        .unwrap()
        .is_empty());
    let mut unverified = link("unverified");
    unverified.observation_verified = false;
    assert!(scenarios::simulator()
        .choose("A", "B", 0, &[unverified])
        .unwrap()
        .is_empty());
    let mut tunnel = link("tunnel");
    tunnel.tunnel_verified = false;
    assert!(scenarios::simulator()
        .choose("A", "B", 0, &[tunnel])
        .unwrap()
        .is_empty());
    for radio in [Underlay::Bluetooth, Underlay::Lora] {
        let mut l = Link::new("radio", "A", "B", radio);
        assert!(scenarios::simulator()
            .choose("A", "B", 0, &[l.clone()])
            .unwrap()
            .is_empty());
        l.reviewed_adapter = true;
        assert_eq!(
            scenarios::simulator()
                .choose("A", "B", 0, &[l.clone()])
                .unwrap(),
            vec![l]
        );
    }
}

#[test]
fn retry_before_token_preserves_meter_rows() {
    // Mutation drop-failed-meter-row/disable-pretoken-retry: the failed attempt and successful retry both remain.
    let mut sim = scenarios::simulator();
    sim.send_data(
        0,
        "A",
        "B",
        &data_links(0),
        &BTreeMap::from([("lan".into(), 0)]),
    );
    assert_eq!(sim.rows().len(), 2);
    assert_eq!(
        (sim.rows()[0].status, sim.rows()[1].status),
        (Status::Failed, Status::Ok)
    );
    assert_eq!(
        (sim.rows()[0].path.as_str(), sim.rows()[1].path.as_str()),
        ("lan", "internet")
    );
    assert_eq!(sim.rows()[0].request, sim.rows()[1].request);
    assert_eq!(sim.rows()[0].tokens, 0);
}

#[test]
fn retry_stops_after_first_token() {
    // Mutation retry_after_first_token: bypassing the terminal boundary duplicates an emitted operation.
    for emitted in 1..=4 {
        let mut sim = scenarios::simulator();
        sim.send_data(
            0,
            "A",
            "B",
            &data_links(0),
            &BTreeMap::from([("lan".into(), emitted)]),
        );
        assert_eq!(sim.rows().len(), 1);
        assert_eq!(sim.rows()[0].status, Status::Failed);
        assert_eq!(i128::from(sim.rows()[0].tokens), emitted);
    }
}

#[test]
fn breaker_opens_after_two_failures_and_recovers_after_two_ticks() {
    // Mutation remove-breaker/wrong-cooldown: failed LAN cannot be selected during its open window.
    let mut sim = scenarios::simulator();
    for tick in [0, 1] {
        sim.send_data(
            i128::from(tick),
            "A",
            "B",
            &data_links(tick)[..1],
            &BTreeMap::from([("lan".into(), 0)]),
        );
    }
    assert!(sim
        .choose("A", "B", 2, &data_links(2)[..1])
        .unwrap()
        .is_empty());
    assert_eq!(
        sim.choose("A", "B", 3, &data_links(3)[..1]).unwrap()[0].name,
        "lan"
    );
}

#[test]
fn control_requires_known_separate_verified_path() {
    // Mutation unknown-reference/shared-domain/tunnel-bypass: all three independent control guards are required.
    let mut sim = scenarios::simulator();
    let lan = link("lan");
    let bt = Link::new("bt", "A", "B", Underlay::Bluetooth);
    let auth = Auth::fixture("A", true);
    assert_eq!(
        sim.send_control(0, &notice(0), Some(&auth), &[bt.clone()], &[])
            .status,
        Status::Denied
    );
    assert_eq!(
        sim.send_control(0, &notice(0), Some(&auth), &[bt.clone()], &[lan.clone()])
            .status,
        Status::Denied
    );
    let data = sim.choose("A", "B", 0, &[lan.clone()]).unwrap();
    assert_eq!(
        sim.send_control(0, &notice(0), Some(&auth), &[lan], &data)
            .status,
        Status::NoIndependentChannel
    );
    let mut unverified = bt.clone();
    unverified.tunnel_verified = false;
    assert_eq!(
        sim.send_control(0, &notice(0), Some(&auth), &[unverified], &data)
            .status,
        Status::NoIndependentChannel
    );
    assert_eq!(
        sim.send_control(0, &notice(0), Some(&auth), &[bt], &data)
            .status,
        Status::Ok
    );
}

#[test]
fn control_closed_kinds_verification_sequence_and_consent() {
    // Mutation allow-start/skip-auth/skip-sequence: typed decoding and current authorization must deny each case.
    let mut sim = scenarios::simulator();
    let data = sim.choose("A", "B", 0, &[link("lan")]).unwrap();
    let bt = [Link::new("bt", "A", "B", Underlay::Bluetooth)];
    let original_members = sim.members().clone();
    let original_consents = sim.consents().clone();
    for rejected in [
        "START", "grant", "consent", "key", "model", "prompt", "answer",
    ] {
        assert!(ControlKind::parse(rejected).is_none());
        assert_eq!(
            sim.send_control(
                0,
                &ControlFrame::from_kind("A", "B", rejected, 0),
                Some(&Auth::fixture("A", true)),
                &bt,
                &data
            )
            .status,
            Status::Denied
        );
    }
    assert_eq!(
        sim.send_control(0, &notice(0), None, &bt, &data).status,
        Status::Denied
    );
    assert_eq!(
        sim.send_control(0, &notice(0), Some(&Auth::fixture("A", false)), &bt, &data)
            .status,
        Status::Denied
    );
    assert_eq!(
        sim.send_control(0, &notice(0), Some(&Auth::fixture("R", true)), &bt, &data)
            .status,
        Status::Denied
    );
    for (sequence, kind) in [
        ControlKind::Alive,
        ControlKind::MemberChanged,
        ControlKind::Stop,
        ControlKind::Pause,
        ControlKind::RouteAround,
        ControlKind::Resume,
    ]
    .into_iter()
    .enumerate()
    {
        assert_eq!(
            sim.send_control(
                0,
                &ControlFrame::notice("A", "B", kind, sequence as u64),
                Some(&Auth::fixture("A", true)),
                &bt,
                &data
            )
            .status,
            Status::Ok
        );
    }
    assert_eq!(
        sim.send_control(0, &notice(5), Some(&Auth::fixture("A", true)), &bt, &data)
            .status,
        Status::Denied
    );
    assert_eq!(sim.members(), &original_members);
    assert_eq!(sim.consents(), &original_consents);
    let mut denied = Simulator::new(
        ["A", "B"].into_iter().map(str::to_owned).collect(),
        BTreeSet::new(),
        BTreeSet::new(),
    );
    assert_eq!(
        denied
            .send_control(0, &notice(0), Some(&Auth::fixture("A", true)), &bt, &data)
            .status,
        Status::Denied
    );
}

#[test]
fn billboard_expiry_and_clock_rollback() {
    // Mutation expired_billboard_applied: removing the upper bound applies an expired rule.
    let mut sim = scenarios::simulator();
    let b = board(2, 4, "r1");
    assert_eq!(
        sim.deliver_billboard(
            0,
            Some(&b),
            Some(&Auth::fixture("A", true)),
            "A",
            "B",
            &[link("lan")]
        )
        .status,
        Status::HeldUntilSince
    );
    assert!(sim.active_billboards(1, "B").unwrap().is_empty());
    assert_eq!(sim.active_billboards(2, "B").unwrap(), vec![b.clone()]);
    assert_eq!(sim.active_billboards(3, "B").unwrap(), vec![b]);
    assert!(sim.active_billboards(4, "B").unwrap().is_empty());
    assert_eq!(
        sim.active_billboards(3, "B"),
        Err(PolicyError::ClockRollback)
    );
}

#[test]
fn billboard_unexpired_delivery() {
    // Mutation drop-accepted-board: a current verified rule must be delivered and returned before expiry; clean control.
    let mut sim = scenarios::simulator();
    let b = board(0, 2, "r1");
    assert_eq!(
        sim.deliver_billboard(
            0,
            Some(&b),
            Some(&Auth::fixture("A", true)),
            "A",
            "B",
            &[link("lan")]
        )
        .status,
        Status::Delivered
    );
    assert_eq!(sim.active_billboards(1, "B").unwrap(), vec![b]);
}

#[test]
fn billboard_replay_keys_include_issuer() {
    // Mutation global-receipt: one authorized issuer must not burn another issuer's receipt identifier.
    let mut sim = Simulator::new(
        ["A", "B", "R"].into_iter().map(str::to_owned).collect(),
        BTreeSet::from([("A".into(), "B".into()), ("R".into(), "B".into())]),
        BTreeSet::from([
            ("A".into(), "B".into(), BillboardKind::Rule),
            ("R".into(), "B".into(), BillboardKind::Rule),
        ]),
    );
    let b = board(0, 2, "shared-id");
    assert_eq!(
        sim.deliver_billboard(
            0,
            Some(&b),
            Some(&Auth::fixture("A", true)),
            "A",
            "B",
            &[link("lan")]
        )
        .status,
        Status::Delivered
    );
    assert_eq!(
        sim.deliver_billboard(
            0,
            Some(&b),
            Some(&Auth::fixture("R", true)),
            "R",
            "B",
            &[Link::new("rb", "R", "B", Underlay::Lan)]
        )
        .status,
        Status::Delivered
    );
    assert_eq!(sim.active_billboards(0, "B").unwrap().len(), 2);
    assert_eq!(
        sim.deliver_billboard(
            0,
            Some(&b),
            Some(&Auth::fixture("A", true)),
            "A",
            "B",
            &[link("lan")]
        )
        .status,
        Status::Denied
    );
}

#[test]
fn billboard_authority_shape_delivery_expiry_and_target_fail_closed() {
    // Mutation skip-board-validation/scope/arrival-expiry: malformed, unauthorized and already-expired records never deliver.
    let mut sim = scenarios::simulator();
    let b = board(0, 2, "r1");
    let links = [link("lan")];
    for auth in [
        None,
        Some(Auth::fixture("A", false)),
        Some(Auth::fixture("R", true)),
    ] {
        assert_eq!(
            sim.deliver_billboard(0, Some(&b), auth.as_ref(), "A", "B", &links)
                .status,
            Status::Denied
        );
    }
    assert_eq!(
        sim.deliver_billboard(0, None, Some(&Auth::fixture("A", true)), "A", "B", &links)
            .status,
        Status::Denied
    );
    let mut bad = b.clone();
    bad.receipt.clear();
    assert_eq!(
        sim.deliver_billboard(
            0,
            Some(&bad),
            Some(&Auth::fixture("A", true)),
            "A",
            "B",
            &links
        )
        .status,
        Status::Denied
    );
    bad = b.clone();
    bad.since = 2;
    assert_eq!(
        sim.deliver_billboard(
            0,
            Some(&bad),
            Some(&Auth::fixture("A", true)),
            "A",
            "B",
            &links
        )
        .status,
        Status::Denied
    );
    bad = b.clone();
    bad.fact = "x".repeat(257);
    assert_eq!(
        sim.deliver_billboard(
            0,
            Some(&bad),
            Some(&Auth::fixture("A", true)),
            "A",
            "B",
            &links
        )
        .status,
        Status::Denied
    );
    let mut future_links = links.clone();
    future_links[0].observed = 2;
    assert_eq!(
        sim.deliver_billboard(
            2,
            Some(&b),
            Some(&Auth::fixture("A", true)),
            "A",
            "B",
            &future_links
        )
        .status,
        Status::Denied
    );
    assert_eq!(sim.clock(), 0);
}

#[test]
fn invalid_future_calls_do_not_poison_clock_and_every_call_is_metered() {
    // Mutation premature-clock/drop-denial-row: rejected future inputs cannot block later accepted work or vanish from accounting.
    let mut sim = scenarios::simulator();
    let b = board(0, 2, "r1");
    sim.send_data(
        10000,
        "A",
        "B",
        &data_links(10000),
        &BTreeMap::from([("lan".into(), -1)]),
    );
    sim.send_data(10000, "UNKNOWN", "B", &data_links(10000), &BTreeMap::new());
    sim.send_data(10000, "A", "B", &[], &BTreeMap::new());
    sim.send_control(10000, &notice(0), None, &data_links(10000), &[]);
    sim.deliver_billboard(
        10000,
        Some(&b),
        Some(&Auth::fixture("A", true)),
        "A",
        "B",
        &data_links(10000),
    );
    assert_eq!(
        sim.active_billboards(10000, "UNKNOWN"),
        Err(PolicyError::UnknownRecipient)
    );
    assert_eq!(sim.clock(), 0);
    assert_eq!(sim.rows().len(), 5);
    sim.send_data(1, "A", "B", &data_links(1), &BTreeMap::new());
    assert_eq!(sim.rows().last().unwrap().status, Status::Ok);
    assert_eq!(sim.clock(), 1);
    sim.send_data(0, "A", "B", &data_links(0), &BTreeMap::new());
    assert_eq!(sim.rows().last().unwrap().status, Status::InvalidInput);
}

#[test]
fn duplicate_links_bad_identifiers_and_same_node_are_explicit_outcomes() {
    // Mutation ignore-link-validation/same-target: duplicate identities and self-target calls must not create a network attempt.
    let mut sim = scenarios::simulator();
    assert_eq!(
        sim.choose("A", "B", 0, &[link("same"), link("same")]),
        Err(PolicyError::InvalidLinks)
    );
    sim.send_data(0, "A", "B", &[link("same"), link("same")], &BTreeMap::new());
    assert_eq!(sim.rows().last().unwrap().status, Status::InvalidInput);
    let mut bad = link("invalid");
    bad.loss_ppm = 1_000_001;
    assert_eq!(
        sim.choose("A", "B", 0, &[bad]),
        Err(PolicyError::InvalidLinks)
    );
    let mut unicode = link(&"é".repeat(64));
    assert!(unicode.valid());
    unicode.name.push('é');
    assert!(!unicode.valid());
    sim.send_data(0, "A", "A", &[link("lan")], &BTreeMap::new());
    assert_eq!(sim.rows().last().unwrap().status, Status::DeniedSelfTarget);
    assert_eq!(
        sim.send_control(
            0,
            &ControlFrame::notice("A", "A", ControlKind::Stop, 0),
            None,
            &[link("lan")],
            &[]
        )
        .status,
        Status::DeniedSelfTarget
    );
    assert_eq!(
        sim.deliver_billboard(0, None, None, "A", "A", &[link("lan")])
            .status,
        Status::DeniedSelfTarget
    );
    assert_eq!(sim.clock(), 0);
}

#[test]
fn typed_input_boundaries_and_large_scores_fail_closed_without_overflow() {
    // Mutation unchecked-time/loss/underlay: typed and validated boundaries reject unsupported inputs and avoid score overflow.
    assert!(Underlay::parse("unknown").is_none());
    assert!(BillboardKind::parse("grant").is_none());
    let mut sim = scenarios::simulator();
    for tick in [-1, i128::from(u64::MAX) + 1] {
        sim.send_data(tick, "A", "B", &[link("lan")], &BTreeMap::new());
        assert_eq!(sim.rows().last().unwrap().status, Status::InvalidInput);
    }
    let mut large = link("large");
    large.latency = u64::MAX;
    large.jitter = u64::MAX;
    assert!(large.score() > u128::from(u64::MAX));
    assert_eq!(
        sim.choose("A", "B", 0, &[large.clone()]).unwrap(),
        vec![large]
    );
}

#[test]
fn json_utf8_and_control_character_escaping_is_deterministic() {
    // Mutation omit-json-escaping: literal quotes, slash and controls cannot corrupt the in-memory JSON artifact.
    let mut b = board(0, 2, "r1");
    b.fact = "é\"\\\n\t\u{01}".into();
    let json = scenarios::render_json(&[("0".into(), vec![b])]);
    let text = String::from_utf8(json).unwrap();
    assert!(text.contains("\"fact\": \"é\\\"\\\\\\n\\t\\u0001\""));
}

#[test]
fn csv_quotes_commas_quotes_and_both_line_endings_like_python() {
    // Mutation omit-csv-escaping: carriage returns must be quoted as well as LF, comma and quote.
    let run = scenarios::run();
    let template = run.rows[0].clone();
    for (source, encoded) in [
        ("a,b", "\"a,b\""),
        ("a\"b", "\"a\"\"b\""),
        ("a\nb", "\"a\nb\""),
        ("a\rb", "\"a\rb\""),
    ] {
        let mut row = template.clone();
        row.source = source.into();
        let csv = rpp_core::overlay::serialize_csv(&[row]);
        let text = String::from_utf8(csv).unwrap();
        assert!(text.ends_with(&format!("1,0,1,data,{encoded},B,lan,OK,3,direct\n")));
    }
}
