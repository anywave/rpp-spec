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
        let v = Check {
            calls: Cell::new(0),
            accept,
        };
        let mut r = Reassembler::<4, 112>::new(10).unwrap();
        let mut result = Ok(false);
        for f in fragments(1).iter().rev() {
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
