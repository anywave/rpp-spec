use rpp_link::{LinkKind, LinkReading};
use rpp_steer::{best_link, Candidate, CostClass, Error, MessageClass, MAX_LINKS};

pub fn link(id: u32, loss: u32, throughput: u64) -> Candidate {
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
        throughput_kbps: throughput,
        cost: CostClass::Unmetered,
    }
}
#[test]
fn control_and_billboard_prefer_loss_while_bulk_uses_measured_throughput() {
    // Mutations reliability-after-speed and throughput-ignored invert these choices.
    let links = [link(1, 0, 10), link(2, 1, 100)];
    for class in [MessageClass::Control, MessageClass::Billboard] {
        assert_eq!(best_link(0, class, 20, &links), Ok(Some(1)));
    }
    assert_eq!(best_link(0, MessageClass::Bulk, 20, &links), Ok(Some(2)));
}
#[test]
fn down_and_missing_links_never_win() {
    // Mutation down-eligible admits the otherwise best dead link.
    let mut dead = link(1, 0, 1000);
    dead.reading.available = false;
    assert_eq!(
        best_link(0, MessageClass::Bulk, 20, &[dead, link(2, 1, 1)]),
        Ok(Some(2))
    );
    assert_eq!(best_link(0, MessageClass::Control, 20, &[dead]), Ok(None));
    assert_eq!(best_link(0, MessageClass::Control, 20, &[]), Ok(None));
}
#[test]
fn ble_and_control_only_never_carry_bulk_or_billboards() {
    // Mutations BLE-data and mislabeled-BLE-billboard remove independent exclusions.
    for (kind, cost) in [
        (LinkKind::Ble, CostClass::Unmetered),
        (LinkKind::Lan, CostClass::ControlOnly),
    ] {
        let mut restricted = link(1, 0, 1000);
        restricted.kind = kind;
        restricted.cost = cost;
        for class in [MessageClass::Bulk, MessageClass::Billboard] {
            assert_eq!(best_link(0, class, 20, &[restricted]), Ok(None));
        }
        assert_eq!(
            best_link(0, MessageClass::Control, 20, &[restricted]),
            Ok(Some(1))
        );
    }
}
#[test]
fn equal_scores_choose_smallest_id_in_either_input_order() {
    // Mutation input-order-tie drops the final stable identity comparison.
    for links in [
        [link(2, 0, 100), link(1, 0, 100)],
        [link(1, 0, 100), link(2, 0, 100)],
    ] {
        for class in [
            MessageClass::Control,
            MessageClass::Bulk,
            MessageClass::Billboard,
        ] {
            assert_eq!(best_link(0, class, 20, &links), Ok(Some(1)));
        }
    }
}
#[test]
fn mtu_means_atomic_payload_bytes_not_a_reassembled_control_frame() {
    // Mutation mtu-ignored would claim a 112-byte envelope fits a 20-byte chunk.
    let mut small = link(1, 0, 1);
    small.mtu = 20;
    assert_eq!(
        best_link(0, MessageClass::Control, 20, &[small]),
        Ok(Some(1))
    );
    assert_eq!(best_link(0, MessageClass::Control, 21, &[small]), Ok(None));
    assert_eq!(best_link(0, MessageClass::Control, 112, &[small]), Ok(None));
}
#[test]
fn invalid_banks_are_refused_before_partial_selection() {
    // Mutations unchecked-loss/future/duplicate/count/MTU permit malformed banks.
    let mut invalid = link(2, 1_000_001, 1);
    assert_eq!(
        best_link(0, MessageClass::Bulk, 1, &[link(1, 0, 1), invalid]),
        Err(Error::InvalidReading)
    );
    invalid = link(2, 0, 1);
    invalid.reading.observed = 1;
    assert_eq!(
        best_link(0, MessageClass::Bulk, 1, &[invalid]),
        Err(Error::InvalidReading)
    );
    invalid.reading.observed = 0;
    invalid.mtu = 0;
    assert_eq!(
        best_link(0, MessageClass::Bulk, 1, &[invalid]),
        Err(Error::InvalidMtu)
    );
    assert_eq!(
        best_link(0, MessageClass::Bulk, 1, &[link(1, 0, 1); 2]),
        Err(Error::DuplicateId)
    );
    assert_eq!(
        best_link(0, MessageClass::Bulk, 1, &[link(1, 0, 1); MAX_LINKS + 1]),
        Err(Error::TooManyLinks)
    );
    assert_eq!(
        best_link(0, MessageClass::Bulk, 0, &[]),
        Err(Error::EmptyPayload)
    );
}
#[test]
fn full_width_metrics_compare_without_sum_or_negation_overflow() {
    // Mutation signed-throughput or summed-cost overflows at the valid u64 endpoints.
    let mut high = link(1, 0, u64::MAX);
    high.reading.latency_ms = u64::MAX;
    high.reading.jitter_ms = u64::MAX;
    assert_eq!(
        best_link(0, MessageClass::Bulk, 1, &[high, link(2, 0, 0)]),
        Ok(Some(1))
    );
    assert_eq!(
        best_link(0, MessageClass::Control, 1, &[high, link(2, 0, 0)]),
        Ok(Some(2))
    );
}
