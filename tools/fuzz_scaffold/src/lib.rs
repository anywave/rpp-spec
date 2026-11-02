//! Developer-only structural/state oracles. Fixtures implement no cryptography.
#![forbid(unsafe_code)]
use rpp_billboard::{decode, encode, Fields, Kind, Signature, Verifier, MAX_FRAME_LEN};
use rpp_control::{ControlFrame, ControlKind, NodeId};
use rpp_frag::{Error, Fragmenter, Reassembler};

pub const MAX_INPUT: usize = 4096;
pub const MAX_FRAGMENTS: usize = 64;
pub const PEER: NodeId = [1; 16];
pub const TARGET: NodeId = [2; 16];
/// Accept structurally valid frames to exercise parsing, never authenticity.
pub struct Structural;
impl Verifier for Structural {
    fn verify(&self, _: &str, _: &[u8], _: &Signature) -> bool {
        true
    }
}
pub fn valid_billboard() -> Vec<u8> {
    let fields = Fields {
        machine: "B",
        kind: Kind::Fact,
        fact: "fixture",
        since: 1,
        until: 2,
        receipt: "r-1",
    };
    let mut out = [0; MAX_FRAME_LEN];
    let n = encode(fields, "A", &[3; 64], &mut out, &Structural).unwrap();
    out[..n].to_vec()
}
pub fn billboard_bytes(input: &[u8]) -> bool {
    let input = &input[..input.len().min(MAX_INPUT)];
    let Ok(view) = decode(input, &Structural) else {
        return false;
    };
    let f = view.fields();
    assert!((1..=64).contains(&view.issuer().chars().count()));
    assert!((1..=64).contains(&f.machine.chars().count()));
    assert!((1..=256).contains(&f.fact.len()));
    assert!(f.fact.bytes().all(|b| (32..=126).contains(&b)));
    assert!((1..=64).contains(&f.receipt.len()));
    assert!(f
        .receipt
        .bytes()
        .all(|b| b.is_ascii_alphanumeric() || b"-_.".contains(&b)));
    assert!(f.since < f.until);
    let mut out = [0; MAX_FRAME_LEN];
    let n = encode(f, view.issuer(), view.signature(), &mut out, &Structural).unwrap();
    assert_eq!(&out[..n], input);
    true
}
pub struct ExactControl(pub [u8; 112]);
impl rpp_control::Verifier for ExactControl {
    fn verify(
        &self,
        sender: &NodeId,
        header: &[u8; 48],
        signature: &rpp_control::Signature,
    ) -> bool {
        sender == &PEER && header == &self.0[..48] && signature == &self.0[48..]
    }
}
pub fn control(sequence: u64, kind: usize) -> [u8; 112] {
    ControlFrame::new(ControlKind::ALL[kind % 6], sequence, PEER, TARGET, [3; 64]).encode()
}
pub fn fragments(frame: &[u8], mtu: usize) -> Vec<Vec<u8>> {
    let mut writer = Fragmenter::<112>::new(frame, 7, mtu).unwrap();
    let mut out = [0; 51];
    let mut parts = Vec::new();
    while let Some(n) = writer.write_next(&mut out).unwrap() {
        let start = parts.len() * (mtu - 5);
        assert_eq!(usize::from(out[4]), start);
        assert_eq!(&out[5..n], &frame[start..start + n - 5]);
        assert!(n <= mtu);
        parts.push(out[..n].to_vec());
    }
    parts
}
fn part(
    r: &mut Reassembler<1, 112>,
    parts: &[Vec<u8>],
    seen: &mut [bool],
    index: usize,
    exact: &ExactControl,
) -> usize {
    let done = seen.iter().all(|bit| *bit);
    let result = r.push(PEER, &parts[index], 0, &TARGET, exact);
    if done {
        assert_eq!(result, Err(Error::RecentlyCompleted));
        assert_eq!(r.retained_slots(), 0);
        return 0;
    }
    seen[index] = true;
    if seen.iter().all(|bit| *bit) {
        assert_eq!(result.map(|f| f.map(|v| v.encode())), Ok(Some(exact.0)));
        assert_eq!(r.retained_slots(), 0);
        1
    } else {
        assert_eq!(result, Ok(None));
        assert_eq!(r.retained_slots(), 1);
        0
    }
}
/// Independent coverage bitmap; one session completes, then late parts stay refused.
pub fn schedule(input: &[u8], sequence: u64, kind: usize, mtu: usize) -> usize {
    let exact = ExactControl(control(sequence, kind));
    let parts = fragments(&exact.0, if mtu == 51 { 51 } else { 20 });
    let mut seen = vec![false; parts.len()];
    let mut r = Reassembler::<1, 112>::new(10).unwrap();
    let mut completed = 0;
    // Reserve pushes for conflict setup, missing parts and one late duplicate.
    for byte in input.iter().take(MAX_FRAGMENTS - parts.len() - 2) {
        let index = usize::from(*byte) % parts.len();
        if seen.iter().all(|bit| *bit) {
            completed += part(&mut r, &parts, &mut seen, index, &exact);
            continue;
        }
        match (usize::from(*byte) / parts.len()) % 3 {
            0 => completed += part(&mut r, &parts, &mut seen, index, &exact),
            1 => {
                let existing = seen.iter().position(|bit| *bit).unwrap_or(index);
                completed += part(&mut r, &parts, &mut seen, existing, &exact);
            }
            _ => {
                let existing = match seen.iter().position(|bit| *bit) {
                    Some(i) => i,
                    None => {
                        completed += part(&mut r, &parts, &mut seen, index, &exact);
                        index
                    }
                };
                let mut changed = parts[existing].clone();
                changed[5] ^= 1;
                assert_eq!(
                    r.push(PEER, &changed, 0, &TARGET, &exact),
                    Err(Error::Overlap)
                );
                assert_eq!(r.retained_slots(), 1);
            }
        }
    }
    let missing = seen
        .iter()
        .enumerate()
        .filter_map(|(i, bit)| (!bit).then_some(i))
        .collect::<Vec<_>>();
    for i in missing {
        completed += part(&mut r, &parts, &mut seen, i, &exact);
    }
    assert_eq!(completed, 1);
    part(&mut r, &parts, &mut seen, 0, &exact);
    completed
}
/// Each byte length prefixes a packet of at most64 bytes; at most64 packets run.
pub fn arbitrary_fragments(input: &[u8]) -> usize {
    let exact = ExactControl(control(8, 3));
    let mut r = Reassembler::<4, 112>::new(10).unwrap();
    let mut rest = &input[..input.len().min(MAX_INPUT)];
    let mut accepted = 0;
    for _ in 0..MAX_FRAGMENTS {
        let Some((&length, tail)) = rest.split_first() else {
            break;
        };
        let n = (usize::from(length) % 65).min(tail.len());
        let packet = &tail[..n];
        rest = &tail[n..];
        if let Ok(Some(frame)) = r.push(PEER, packet, 0, &TARGET, &exact) {
            assert_eq!(frame.encode(), exact.0);
            accepted += 1;
        }
        assert!(r.retained_slots() <= 4);
    }
    accepted
}
pub fn fragment_input(frame: &[u8]) -> Vec<u8> {
    fragments(frame, 20)
        .into_iter()
        .flat_map(|part| {
            let mut packet = vec![part.len() as u8];
            packet.extend(part);
            packet
        })
        .collect()
}

pub fn valid_fragment_input() -> Vec<u8> {
    fragment_input(&control(8, 3))
}
