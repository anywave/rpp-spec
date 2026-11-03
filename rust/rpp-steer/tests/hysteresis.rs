use rpp_link::{LinkKind, LinkReading};
use rpp_steer::{
    best_link, best_link_with_ceiling, Candidate, CostClass, Error, Hysteresis, MessageClass as C,
    Reason, Selector,
};
fn link(id: u32, loss: u32, speed: u64) -> Candidate {
    Candidate {
        id,
        kind: LinkKind::Lan,
        reading: LinkReading {
            latency_ms: 1,
            loss_ppm: loss,
            jitter_ms: 0,
            available: true,
            observed: 0,
        },
        mtu: 1200,
        throughput_kbps: speed,
        cost: CostClass::Unmetered,
    }
}
fn params(hold_ticks: u64, margin: u32) -> Hysteresis {
    Hysteresis {
        hold_ticks,
        control_margin_ppm: margin,
        bulk_margin_kbps: u64::from(margin),
        billboard_margin_ppm: margin,
    }
}
#[test]
fn hold_then_absolute_margin_switches_at_exact_boundaries() {
    // Mutations hold-omitted, hold-inclusive and margin-inclusive change these rows.
    let mut s = Selector::new(params(10, 10)).unwrap();
    assert_eq!(
        s.choose(0, C::Control, 20, &[link(1, 1000, 0)])
            .unwrap()
            .reason,
        Reason::Initial
    );
    assert_eq!(
        s.choose(9, C::Control, 20, &[link(1, 1000, 0), link(2, 900, 0)])
            .unwrap()
            .reason,
        Reason::Hold
    );
    assert_eq!(
        s.choose(10, C::Control, 20, &[link(1, 1000, 0), link(2, 995, 0)])
            .unwrap()
            .reason,
        Reason::Margin
    );
    let d = s
        .choose(11, C::Control, 20, &[link(1, 1000, 0), link(2, 990, 0)])
        .unwrap();
    assert_eq!((d.link_id, d.reason), (Some(2), Reason::Improved));
}
#[test]
fn zero_and_maximum_margins_use_subtraction_without_overflow() {
    // Mutation strict-margin breaks zero/equal boundaries; score addition overflows MAX.
    let mut s = Selector::new(params(0, 0)).unwrap();
    s.choose(0, C::Control, 1, &[link(2, 0, 0)]).unwrap();
    assert_eq!(
        s.choose(0, C::Control, 1, &[link(2, 0, 0), link(1, 0, 0)])
            .unwrap()
            .link_id,
        Some(1)
    );
    let mut p = params(0, 0);
    p.bulk_margin_kbps = u64::MAX;
    let mut s = Selector::new(p).unwrap();
    s.choose(0, C::Bulk, 1, &[link(1, 0, 1)]).unwrap();
    assert_eq!(
        s.choose(1, C::Bulk, 1, &[link(1, 0, 1), link(2, 0, u64::MAX - 1)])
            .unwrap()
            .reason,
        Reason::Margin
    );
    assert_eq!(
        s.choose(u64::MAX, C::Bulk, 1, &[link(1, 0, 1), link(2, 0, u64::MAX)])
            .unwrap()
            .reason,
        Reason::Margin
    );
    p.bulk_margin_kbps = u64::MAX - 1;
    let mut boundary = Selector::new(p).unwrap();
    boundary.choose(0, C::Bulk, 1, &[link(1, 0, 1)]).unwrap();
    assert_eq!(
        boundary
            .choose(1, C::Bulk, 1, &[link(1, 0, 1), link(2, 0, u64::MAX)])
            .unwrap()
            .link_id,
        Some(2)
    );
    let mut s = Selector::new(params(2, 0)).unwrap();
    s.choose(u64::MAX - 1, C::Control, 1, &[link(1, 100, 0)])
        .unwrap();
    assert_eq!(
        s.choose(u64::MAX, C::Control, 1, &[link(1, 100, 0), link(2, 0, 0)])
            .unwrap()
            .reason,
        Reason::Hold
    );
}
#[test]
fn down_missing_and_too_small_incumbents_bypass_hold_and_margin() {
    // Mutation retain-ineligible keeps a dead/missing/too-small incumbent behind hold.
    for mode in 0..5 {
        let mut s = Selector::new(params(u64::MAX, 1_000_000)).unwrap();
        s.choose(0, C::Bulk, 20, &[link(1, 0, u64::MAX)]).unwrap();
        let mut old = link(1, 0, u64::MAX);
        match mode {
            0 => old.reading.available = false,
            1 => old.mtu = 20,
            2 => old.kind = LinkKind::Ble,
            3 => old.cost = CostClass::ControlOnly,
            _ => {}
        }
        let bank = if mode == 4 {
            vec![link(2, 1, 1)]
        } else {
            vec![old, link(2, 1, 1)]
        };
        let d = s.choose(1, C::Bulk, 21, &bank).unwrap();
        assert_eq!((d.link_id, d.reason), (Some(2), Reason::Ineligible));
    }
}
#[test]
fn classes_have_independent_hold_state() {
    // Mutation one-shared-state resets bulk/billboard hold when control switches.
    let mut s = Selector::new(params(10, 0)).unwrap();
    for class in [C::Control, C::Bulk, C::Billboard] {
        s.choose(0, class, 1, &[link(1, 100, 1)]).unwrap();
    }
    for class in [C::Control, C::Bulk, C::Billboard] {
        let d = s
            .choose(10, class, 1, &[link(1, 100, 1), link(2, 0, 2)])
            .unwrap();
        assert_eq!((d.link_id, d.reason), (Some(2), Reason::Improved));
    }
}
#[test]
fn invalid_inputs_and_rollback_preserve_all_state_and_clock() {
    // Mutations clock-before-validation and rollback-misclassified alter follow-up decisions.
    let mut s = Selector::new(params(10, 0)).unwrap();
    s.choose(5, C::Control, 1, &[link(1, 0, 1)]).unwrap();
    let before = s;
    let mut future = link(2, 0, 1);
    future.reading.observed = 100;
    assert_eq!(
        s.choose(50, C::Bulk, 1, &[future]),
        Err(Error::InvalidReading)
    );
    assert_eq!(s, before);
    assert_eq!(
        s.choose(50, C::Control, 1, &[link(1, 0, 1); 2]),
        Err(Error::DuplicateId)
    );
    assert_eq!(s, before);
    assert_eq!(
        s.choose(4, C::Control, 0, &[future]),
        Err(Error::ClockRollback)
    );
    assert_eq!(s, before);
    assert_eq!(
        s.choose(6, C::Control, 1, &[link(1, 0, 1)]).unwrap().reason,
        Reason::Best
    );
    let mut bad = params(0, 0);
    bad.billboard_margin_ppm = 1_000_001;
    assert_eq!(Selector::new(bad), Err(Error::InvalidMargin));
}
#[test]
fn no_channel_clears_hold_before_a_new_initial_selection() {
    // Mutation retain-old-state-after-outage imposes a stale hold on recovery.
    let mut s = Selector::new(params(u64::MAX, 1_000_000)).unwrap();
    s.choose(0, C::Control, 1, &[link(1, 0, 1)]).unwrap();
    let d = s.choose(1, C::Control, 1, &[]).unwrap();
    assert_eq!((d.link_id, d.reason.as_str()), (None, "no-channel"));
    let d = s.choose(2, C::Control, 1, &[link(2, 0, 1)]).unwrap();
    assert_eq!((d.link_id, d.reason), (Some(2), Reason::Initial));
}
#[test]
fn bulk_loss_ceiling_is_inclusive_configurable_and_overrides_hold() {
    // Mutations ceiling_ignored/exclusive, configuration_ignored and total_loss_allowed.
    for loss in [0, 200_000, 200_001, 999_999, 1_000_000] {
        let bank = [link(1, loss, u64::MAX)];
        let expected = (loss <= 200_000).then_some(1);
        assert_eq!(best_link(0, C::Bulk, 1, &bank), Ok(expected));
        let mut s = Selector::new(params(0, 0)).unwrap();
        assert_eq!(s.choose(0, C::Bulk, 1, &bank).unwrap().link_id, expected);
        for class in [C::Control, C::Billboard] {
            assert_eq!(best_link(0, class, 1, &bank), Ok(Some(1)));
        }
        for ceiling in [0, 300_000, 1_000_000] {
            let expected = (loss <= ceiling && loss < 1_000_000).then_some(1);
            assert_eq!(
                best_link_with_ceiling(0, C::Bulk, 1, &bank, ceiling),
                Ok(expected)
            );
            let mut s = Selector::with_loss_ceiling(params(0, 0), ceiling).unwrap();
            assert_eq!(s.choose(0, C::Bulk, 1, &bank).unwrap().link_id, expected);
        }
    }
    assert_eq!(
        Selector::with_loss_ceiling(params(0, 0), 1_000_001),
        Err(Error::InvalidLossCeiling)
    );
    assert_eq!(
        best_link_with_ceiling(0, C::Bulk, 1, &[], 1_000_001),
        Err(Error::InvalidLossCeiling)
    );
    let mut s = Selector::new(params(u64::MAX, 1_000_000)).unwrap();
    s.choose(0, C::Bulk, 1, &[link(1, 0, u64::MAX)]).unwrap();
    let d = s
        .choose(1, C::Bulk, 1, &[link(1, 200_001, u64::MAX), link(2, 0, 1)])
        .unwrap();
    assert_eq!((d.link_id, d.reason), (Some(2), Reason::Ineligible));
}
