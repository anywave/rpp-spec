use core::cell::Cell;
use rpp_control::{ControlFrame, ControlKind, NodeId, Signature, Verifier, HEADER_LEN};
use rpp_frag::{Error, Fragmenter, Reassembler};
const PEER: NodeId = [1; 16];
const TARGET: NodeId = [2; 16];
struct Check {
    calls: Cell<usize>,
    accept: bool,
}
impl Verifier for Check {
    fn verify(&self, _: &NodeId, _: &[u8; HEADER_LEN], signature: &Signature) -> bool {
        self.calls.set(self.calls.get() + 1);
        self.accept && *signature == [3; 64]
    }
}
fn verifier() -> Check {
    Check {
        calls: Cell::new(0),
        accept: true,
    }
}
fn fragments(tag: u16) -> Vec<Vec<u8>> {
    let frame = ControlFrame::new(ControlKind::Pause, 8, PEER, TARGET, [3; 64]).encode();
    let mut writer = Fragmenter::<112>::new(&frame, tag, 20).unwrap();
    let mut output = [0; 20];
    let mut result = vec![];
    while let Some(n) = writer.write_next(&mut output).unwrap() {
        result.push(output[..n].to_vec());
    }
    result
}
fn push<const S: usize>(
    r: &mut Reassembler<S, 112>,
    f: &[u8],
    t: u64,
    v: &Check,
) -> Result<bool, Error> {
    r.push(PEER, f, t, &TARGET, v).map(|frame| frame.is_some())
}
#[test]
fn out_of_order_valid_and_forged_frames_require_caller_verifier() {
    // Mutation decode-bypass: only caller-verified complete frames are returned.
    for accept in [true, false] {
        let v = verifier();
        let mut pieces = fragments(1);
        if !accept {
            *pieces.last_mut().unwrap().last_mut().unwrap() ^= 1;
        }
        let mut r = Reassembler::<4, 112>::new(10).unwrap();
        let mut result = Ok(false);
        for f in pieces.iter().rev() {
            result = push(&mut r, f, 0, &v);
        }
        assert_eq!(
            result,
            if accept {
                Ok(true)
            } else {
                Err(Error::Decode(rpp_control::DecodeError::InvalidSignature))
            }
        );
        assert_eq!(v.calls.get(), 1);
        assert_eq!(r.retained_slots(), 0);
    }
}
#[test]
fn different_byte_overlap_is_rejected_without_poisoning_uncovered_prefix() {
    // Mutation overlap-accepted: a late conflict must reject the entire fragment.
    let f = fragments(1);
    let v = verifier();
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    assert_eq!(push(&mut r, &f[1], 0, &v), Ok(false));
    let mut mixed = f[0].clone();
    mixed.extend_from_slice(&f[1][5..]);
    mixed[20] ^= 1;
    assert_eq!(push(&mut r, &mixed, 0, &v), Err(Error::Overlap));
    for part in &f[1..] {
        assert_eq!(push(&mut r, part, 0, &v), Ok(false));
    }
    assert_eq!(push(&mut r, &f[0], 0, &v), Ok(true));
}
#[test]
fn offset_plus_length_beyond_total_is_rejected_before_any_copy() {
    // Mutation bounds-accepted: short total must never permit a payload past it.
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    let v = verifier();
    let mut f = fragments(1)[0].clone();
    f[1] = 100;
    f[4] = 95;
    assert_eq!(push(&mut r, &f, 0, &v), Err(Error::OutOfBounds));
    f[1] = 113;
    assert_eq!(push(&mut r, &f, 0, &v), Err(Error::TooLarge));
    assert_eq!(r.retained_slots(), 0);
    assert_eq!(v.calls.get(), 0);
}
#[test]
fn duplicates_do_not_count_twice_or_complete_without_last_fragment() {
    // Mutation duplicate-counted-twice: covered bytes are a set, not a byte counter.
    let f = fragments(1);
    let v = verifier();
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    for _ in 0..20 {
        assert_eq!(push(&mut r, &f[0], 0, &v), Ok(false));
    }
    for part in &f[1..f.len() - 1] {
        assert_eq!(push(&mut r, part, 0, &v), Ok(false));
    }
    assert_eq!(v.calls.get(), 0);
    assert_eq!(push(&mut r, f.last().unwrap(), 0, &v), Ok(true));
}
#[test]
fn missing_last_fragment_never_completes() {
    // Mutation missing-last-completes: completion requires every byte, not a prefix.
    let f = fragments(1);
    let v = verifier();
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    for part in &f[..f.len() - 1] {
        assert_eq!(push(&mut r, part, 0, &v), Ok(false));
    }
    assert_eq!(v.calls.get(), 0);
    assert_eq!(r.retained_slots(), 1);
}
#[test]
fn timeout_is_half_open_and_duplicates_never_refresh_deadline() {
    // Mutation timeout-never-fires/duplicate-refresh: expiry uses the first fragment tick.
    let f = fragments(1);
    let v = verifier();
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    assert_eq!(push(&mut r, &f[0], 0, &v), Ok(false));
    assert_eq!(push(&mut r, &f[0], 9, &v), Ok(false));
    assert_eq!(push(&mut r, &f[1], 10, &v), Err(Error::Expired));
    assert_eq!(r.retained_slots(), 0);
    assert_eq!(v.calls.get(), 0);
}
#[test]
fn slots_full_refuses_new_tag_without_eviction() {
    // Mutation slots-full-evicts: the original frame must still finish intact.
    let f = fragments(1);
    let v = verifier();
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    assert_eq!(push(&mut r, &f[0], 0, &v), Ok(false));
    assert_eq!(push(&mut r, &fragments(2)[0], 0, &v), Err(Error::SlotsFull));
    for part in &f[1..f.len() - 1] {
        assert_eq!(push(&mut r, part, 0, &v), Ok(false));
    }
    assert_eq!(push(&mut r, f.last().unwrap(), 0, &v), Ok(true));
}
#[test]
fn two_peers_with_same_tag_never_merge_coverage() {
    // Mutation peer-key-omitted: another peer's suffix cannot complete this peer.
    let f = fragments(1);
    let v = verifier();
    let mut r = Reassembler::<2, 112>::new(10).unwrap();
    assert_eq!(push(&mut r, &f[0], 0, &v), Ok(false));
    for part in &f[1..] {
        assert!(r.push([9; 16], part, 0, &TARGET, &v).unwrap().is_none());
    }
    assert_eq!(v.calls.get(), 0);
    assert_eq!(r.retained_slots(), 2);
}
#[test]
fn malformed_input_rollback_and_deadline_overflow_do_not_advance_state() {
    // Mutations rollback-accepted, empty-progress and unchecked-deadline-addition.
    let f = fragments(1);
    let v = verifier();
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    assert_eq!(push(&mut r, &f[0], 5, &v), Ok(false));
    assert_eq!(push(&mut r, &f[1], 4, &v), Err(Error::ClockRollback));
    assert_eq!(push(&mut r, &f[0][..5], 100, &v), Err(Error::InvalidHeader));
    assert_eq!(push(&mut r, &f[1], 6, &v), Ok(false));
    let mut fresh = Reassembler::<1, 112>::new(10).unwrap();
    assert_eq!(
        push(&mut fresh, &f[0], u64::MAX, &v),
        Err(Error::InvalidTimeout)
    );
    assert_eq!(fresh.retained_slots(), 0);
}

#[test]
fn identical_duplicate_does_not_advance_remembered_tick() {
    // Mutation duplicate-advances-clock: the same new fragment at tick 6 stays admissible.
    let f = fragments(1);
    let v = verifier();
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    assert_eq!(push(&mut r, &f[0], 5, &v), Ok(false));
    assert_eq!(push(&mut r, &f[0], 9, &v), Ok(false));
    for part in &f[1..f.len() - 1] {
        assert_eq!(push(&mut r, part, 6, &v), Ok(false));
    }
    assert_eq!(push(&mut r, f.last().unwrap(), 6, &v), Ok(true));
}

fn finish<const S: usize>(
    r: &mut Reassembler<S, 112>,
    peer: NodeId,
    parts: &[Vec<u8>],
    tick: u64,
    v: &Check,
) -> Result<bool, Error> {
    let mut complete = false;
    for part in parts {
        complete = r.push(peer, part, tick, &TARGET, v)?.is_some();
    }
    Ok(complete)
}
/// Mutations: omit recent-key rejection, refresh its deadline, or call the verifier again.
#[test]
fn completed_duplicates_do_not_reopen_or_extend_original_deadline() {
    let v = verifier();
    let f = fragments(1);
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    assert_eq!(finish(&mut r, PEER, &f, 0, &v), Ok(true));
    assert_eq!(push(&mut r, &f[0], 9, &v), Err(Error::RecentlyCompleted));
    let mut changed = f[0].clone();
    changed[5] ^= 1;
    assert_eq!(push(&mut r, &changed, 9, &v), Err(Error::RecentlyCompleted));
    assert_eq!((r.retained_slots(), v.calls.get()), (0, 1));
    assert_eq!(push(&mut r, &f[0], 10, &v), Ok(false));
}
/// Mutations: duplicate reorders FIFO, cache has more than two keys, or peer is omitted.
#[test]
fn completion_cache_is_fifo_two_keys_and_peer_scoped() {
    let v = verifier();
    let mut r = Reassembler::<2, 112>::new(10).unwrap();
    assert_eq!(finish(&mut r, PEER, &fragments(1), 0, &v), Ok(true));
    assert_eq!(finish(&mut r, PEER, &fragments(2), 1, &v), Ok(true));
    assert_eq!(
        push(&mut r, &fragments(1)[0], 2, &v),
        Err(Error::RecentlyCompleted)
    );
    assert_eq!(finish(&mut r, PEER, &fragments(3), 2, &v), Ok(true));
    assert_eq!(push(&mut r, &fragments(1)[0], 2, &v), Ok(false));
    assert_eq!(
        push(&mut r, &fragments(2)[0], 2, &v),
        Err(Error::RecentlyCompleted)
    );
    assert_eq!(finish(&mut r, [9; 16], &fragments(3), 2, &v), Ok(true));
}
/// Mutation: record completion before the caller's verification succeeds.
#[test]
fn failed_verification_does_not_poison_completion_cache() {
    let v = Check {
        calls: Cell::new(0),
        accept: false,
    };
    let f = fragments(1);
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    assert_eq!(
        finish(&mut r, PEER, &f, 0, &v),
        Err(Error::Decode(rpp_control::DecodeError::InvalidSignature))
    );
    assert_eq!(push(&mut r, &f[0], 0, &v), Ok(false));
}
/// Mutations: silently reclaim an expired key, consume incoming bytes, or prefer another expiry over an empty slot.
#[test]
fn expired_old_key_is_observable_and_one_identical_retry_accepts() {
    let v = verifier();
    let f = fragments(1);
    let mut r = Reassembler::<2, 112>::new(10).unwrap();
    assert_eq!(push(&mut r, &f[0], 0, &v), Ok(false));
    assert_eq!(r.push([9; 16], &fragments(2)[0], 0, &TARGET, &v), Ok(None));
    let incoming = fragments(3);
    assert_eq!(
        r.push([8; 16], &incoming[0], 10, &TARGET, &v),
        Err(Error::ExpiredKey { peer: PEER, tag: 1 })
    );
    assert_eq!(r.retained_slots(), 1);
    assert_eq!(r.push([8; 16], &incoming[0], 10, &TARGET, &v), Ok(None));
    // A malformed far-future call must neither erase this session nor lock its clock.
    assert_eq!(
        r.push([8; 16], &[0], u64::MAX, &TARGET, &v),
        Err(Error::InvalidHeader)
    );
    assert_eq!(finish(&mut r, [8; 16], &incoming[1..], 10, &v), Ok(true));
}
