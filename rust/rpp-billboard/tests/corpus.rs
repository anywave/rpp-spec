//! Independent stdlib wire fixtures; byte recognition is not cryptography.
use core::cell::Cell;
use rpp_billboard::{decode, encode, Signature, Verifier, MAX_FRAME_LEN};

fn hex(text: &str) -> Vec<u8> {
    if text == "-" {
        return Vec::new();
    }
    text.as_bytes()
        .chunks_exact(2)
        .map(|pair| u8::from_str_radix(core::str::from_utf8(pair).unwrap(), 16).unwrap())
        .collect()
}
fn rows() -> impl Iterator<Item = Vec<&'static str>> {
    include_str!("data/billboard-corpus.tsv")
        .lines()
        .skip(1)
        .map(|line| line.split('\t').collect())
}
struct Exact {
    prefix: Vec<u8>,
    signature: Signature,
    reject: bool,
    calls: Cell<usize>,
}
impl Verifier for Exact {
    fn verify(&self, _: &str, bytes: &[u8], signature: &Signature) -> bool {
        self.calls.set(self.calls.get() + 1);
        !self.reject && bytes == self.prefix && signature == &self.signature
    }
}
fn fixture(row: &[&str]) -> Exact {
    Exact {
        prefix: hex(row[5]),
        signature: hex(row[6]).try_into().unwrap(),
        reject: row[4] == "reject",
        calls: Cell::new(0),
    }
}

/// Failing mutations: change wire offsets, length bounds, UTF-8 rules or verifier ordering.
#[test]
fn all_fifty_corpus_cases_match_independent_layout_oracle() {
    let mut counts = (0, 0);
    for row in rows() {
        assert_eq!(row.len(), 9);
        let input = hex(row[7]);
        let verifier = fixture(&row);
        match decode(&input, &verifier) {
            Ok(view) => {
                assert_eq!(row[2], "OK");
                let mut output = [0; MAX_FRAME_LEN];
                let size = encode(
                    view.fields(),
                    view.issuer(),
                    view.signature(),
                    &mut output,
                    &verifier,
                )
                .unwrap();
                assert_eq!(&output[..size], input);
                counts.0 += 1;
            }
            Err(error) => {
                assert_eq!(format!("{error:?}").split('(').next().unwrap(), row[2]);
                counts.1 += 1;
            }
        }
        // Checked encoding also calls the verifier on successful cases.
        assert_eq!(
            verifier.calls.get(),
            row[3].parse::<usize>().unwrap() + usize::from(row[2] == "OK")
        );
    }
    assert_eq!(counts, (13, 37));
}

/// Failing mutation: make fields depend on std/alloc or change the independent semantic snapshot.
#[test]
fn std_and_no_std_decode_share_all_thirteen_field_snapshots() {
    fn hex(bytes: &[u8]) -> String {
        use core::fmt::Write;
        bytes.iter().fold(String::new(), |mut output, byte| {
            write!(&mut output, "{byte:02x}").unwrap();
            output
        })
    }
    let mut snapshot = String::from(
        "case\tissuer_hex\tmachine_hex\tkind\tfact_hex\tsince\tuntil\treceipt_hex\tsignature_hex\n",
    );
    for row in rows().filter(|row| row[2] == "OK") {
        let input = crate::hex(row[7]);
        let verifier = fixture(&row);
        let view = decode(&input, &verifier).unwrap();
        let fields = view.fields();
        snapshot.push_str(
            &[
                row[1].into(),
                hex(view.issuer().as_bytes()),
                hex(fields.machine.as_bytes()),
                (fields.kind as u8).to_string(),
                hex(fields.fact.as_bytes()),
                fields.since.to_string(),
                fields.until.to_string(),
                hex(fields.receipt.as_bytes()),
                hex(view.signature()),
            ]
            .join("\t"),
        );
        snapshot.push('\n');
    }
    assert_eq!(
        snapshot.as_bytes(),
        include_bytes!("data/billboard-fields.tsv")
    );
}

/// Failing mutations: skip verification/trailing checks or panic on prefix/length/UTF-8 corruption.
#[test]
fn every_prefix_and_all_single_byte_xor_changes_error_or_decode_identically() {
    let mut totals = (0, 0);
    for row in rows() {
        let input = hex(row[7]);
        // One fixed exact verifier per original frame, independent of the corpus
        // refusal mode. Every input byte belongs to its prefix or signature.
        let split = input.len().saturating_sub(64);
        let verifier = Exact {
            prefix: input[..split].to_vec(),
            signature: if input.len() >= 64 {
                input[split..].try_into().unwrap()
            } else {
                [0; 64]
            },
            reject: false,
            calls: Cell::new(0),
        };
        let original = decode(&input, &verifier).ok();
        for length in 0..=input.len() {
            if let Ok(view) = decode(&input[..length], &verifier) {
                assert_eq!(Some(view), original);
            }
            totals.0 += 1;
        }
        let mut changed = input.clone();
        for offset in 0..input.len() {
            for mask in 1..=255_u8 {
                changed[offset] = input[offset] ^ mask;
                if let Ok(view) = decode(&changed, &verifier) {
                    assert_eq!(Some(view), original);
                }
                totals.1 += 1;
            }
            changed[offset] = input[offset];
        }
    }
    assert_eq!(totals, (8028, 2_034_390));
}

/// Failing mutation: replace core replay/half-open/future storage with codec-local policy.
#[cfg(feature = "alloc")]
#[test]
fn decoded_corpus_billboards_reproduce_existing_overlay_json_bytes() {
    use rpp_core::{
        overlay::{Auth, Link, Status, Underlay},
        scenarios,
    };
    let mut policy = scenarios::simulator();
    let mut lan = Link::new("lan", "A", "B", Underlay::Lan);
    lan.observed = 8;
    let links = [lan];
    for row in rows().filter(|row| row[1].starts_with("overlay-")) {
        let input = hex(row[7]);
        let verifier = fixture(&row);
        let decoded = decode(&input, &verifier).unwrap();
        let board = decoded.to_core();
        let expected = if row[1] == "overlay-rule" {
            Status::Delivered
        } else {
            Status::HeldUntilSince
        };
        assert_eq!(
            policy
                .deliver_billboard(
                    8,
                    Some(&board),
                    Some(&Auth::fixture(decoded.issuer(), true)),
                    "A",
                    "B",
                    &links
                )
                .status,
            expected
        );
        assert_eq!(
            policy
                .deliver_billboard(
                    8,
                    Some(&board),
                    Some(&Auth::fixture(decoded.issuer(), true)),
                    "A",
                    "B",
                    &links
                )
                .status,
            Status::Denied
        );
    }
    let active = [8, 9, 10, 11]
        .into_iter()
        .map(|tick| {
            (
                tick.to_string(),
                policy.active_billboards(tick, "B").unwrap(),
            )
        })
        .collect::<Vec<_>>();
    assert_eq!(
        scenarios::render_json(&active),
        include_bytes!("../../rpp-core/tests/data/overlay-billboards.json")
    );
}
