use rpp_control::{ControlFrame, ControlKind, NodeId, Signature, Verifier, HEADER_LEN};
use rpp_frag::{Fragmenter, Reassembler};
struct Check;
impl Verifier for Check {
    fn verify(&self, sender: &NodeId, _: &[u8; HEADER_LEN], signature: &Signature) -> bool {
        *sender == core::array::from_fn(|i| i as u8)
            && *signature == core::array::from_fn(|i| i as u8)
    }
}
#[test]
fn mtu20_and_51_vectors_match_independent_python_layout_and_verified_output() {
    // Mutations changed-offset/header-budget/payload: every emitted byte is independently fixed.
    let rows: Vec<_> = include_str!("data/frag-corpus.tsv")
        .lines()
        .skip(1)
        .collect();
    assert_eq!(rows.len(), 66);
    let mut row = 0;
    for mtu in [20, 51] {
        for kind in ControlKind::ALL {
            let recipient = core::array::from_fn(|i| (128 + i) as u8);
            let frame = ControlFrame::new(
                kind,
                0,
                core::array::from_fn(|i| i as u8),
                recipient,
                core::array::from_fn(|i| i as u8),
            )
            .encode();
            let mut writer = Fragmenter::<112>::new(&frame, 4660, mtu).unwrap();
            let mut receiver = Reassembler::<1>::new(10).unwrap();
            let mut output = [0; 51];
            let mut index = 0;
            let mut decoded = None;
            while let Some(n) = writer.write_next(&mut output).unwrap() {
                let columns: Vec<_> = rows[row].split('\t').collect();
                assert_eq!(columns.len(), 5);
                assert_eq!(
                    columns[..4],
                    [
                        mtu.to_string(),
                        (kind as u8).to_string(),
                        "4660".into(),
                        index.to_string()
                    ]
                );
                let expected: Vec<_> = columns[4]
                    .as_bytes()
                    .chunks_exact(2)
                    .map(|pair| {
                        u8::from_str_radix(core::str::from_utf8(pair).unwrap(), 16).unwrap()
                    })
                    .collect();
                assert_eq!(output[..n], expected);
                decoded = receiver
                    .push([1; 16], &expected, 0, &recipient, &Check)
                    .unwrap();
                row += 1;
                index += 1;
            }
            assert_eq!(decoded.unwrap().encode(), frame);
        }
    }
    assert_eq!(row, rows.len());
}
