//! Codec/fixture tests only. Literal-byte fixtures do not implement cryptography.

use core::cell::Cell;
use rpp_control::{
    decode, ControlFrame, ControlKind, DecodeError, NodeId, Signature, Verifier, FRAME_LEN,
    HEADER_LEN,
};

#[derive(Clone, Copy)]
enum FixtureMode {
    Bound,
    SignatureOnly,
    Reject,
}

struct Fixture {
    mode: FixtureMode,
    expected_header: [u8; HEADER_LEN],
    expected_signature: Signature,
    calls: Cell<usize>,
}

impl Fixture {
    fn new(
        mode: FixtureMode,
        expected_header: [u8; HEADER_LEN],
        expected_signature: Signature,
    ) -> Self {
        Self {
            mode,
            expected_header,
            expected_signature,
            calls: Cell::new(0),
        }
    }
}

impl Verifier for Fixture {
    fn verify(&self, sender: &NodeId, header: &[u8; HEADER_LEN], signature: &Signature) -> bool {
        self.calls.set(self.calls.get() + 1);
        match self.mode {
            FixtureMode::Reject => false,
            FixtureMode::SignatureOnly => signature == &self.expected_signature,
            FixtureMode::Bound => {
                signature == &self.expected_signature
                    && header == &self.expected_header
                    && sender.as_slice() == &self.expected_header[16..32]
            }
        }
    }
}

fn sender() -> NodeId {
    core::array::from_fn(|index| index as u8)
}
fn recipient() -> NodeId {
    core::array::from_fn(|index| 128 + index as u8)
}
fn signature() -> Signature {
    core::array::from_fn(|index| index as u8)
}
fn baseline() -> ControlFrame {
    ControlFrame::new(ControlKind::Alive, 0, sender(), recipient(), signature())
}

fn from_hex(text: &str) -> Vec<u8> {
    if text == "-" {
        return Vec::new();
    }
    (0..text.len())
        .step_by(2)
        .map(|offset| u8::from_str_radix(&text[offset..offset + 2], 16).unwrap())
        .collect()
}

fn array<const N: usize>(text: &str) -> [u8; N] {
    from_hex(text).try_into().unwrap()
}

fn error_name(error: &DecodeError) -> &'static str {
    match error {
        DecodeError::Truncated => "Truncated",
        DecodeError::Oversize => "Oversize",
        DecodeError::BadMagic => "BadMagic",
        DecodeError::UnsupportedVersion(_) => "UnsupportedVersion",
        DecodeError::UnknownKind(_) => "UnknownKind",
        DecodeError::NonzeroReserved => "NonzeroReserved",
        DecodeError::WrongRecipient => "WrongRecipient",
        DecodeError::InvalidSignature => "InvalidSignature",
    }
}

/// Failing mutation: alter a kind/sequence packing field or reject a legal control kind.
/// This is also the unaffected clean control for the four required codec mutants.
#[test]
fn valid_roundtrip_accepts_all_six_kinds() {
    let labels = [
        "ALIVE",
        "MEMBER-CHANGED",
        "STOP",
        "PAUSE",
        "ROUTE-AROUND",
        "RESUME",
    ];
    let sequences = [
        0,
        1,
        127,
        128,
        255,
        256,
        65535,
        65536,
        (1_u64 << 24) - 1,
        1_u64 << 24,
        (1_u64 << 32) - 1,
        1_u64 << 32,
        (1_u64 << 40) - 1,
        1_u64 << 40,
        (1_u64 << 48) - 1,
        1_u64 << 48,
        (1_u64 << 56) - 1,
        1_u64 << 56,
        (1_u64 << 63) - 1,
        1_u64 << 63,
        u64::MAX,
    ];
    for (index, kind) in ControlKind::ALL.iter().copied().enumerate() {
        assert_eq!(kind as u8, index as u8 + 1);
        assert_eq!(kind.as_str(), labels[index]);
        for sequence in sequences {
            let frame = ControlFrame::new(kind, sequence, sender(), recipient(), signature());
            let bytes = frame.encode();
            assert_eq!(bytes.len(), FRAME_LEN);
            assert_eq!(&bytes[..4], b"RPPC");
            assert_eq!(&bytes[8..16], &sequence.to_be_bytes());
            let fixture = Fixture::new(FixtureMode::Bound, frame.header(), signature());
            let decoded = decode(&bytes, &recipient(), &fixture).unwrap();
            assert_eq!(decoded.kind(), kind);
            assert_eq!(decoded.sequence(), sequence);
            assert_eq!(decoded.sender().as_slice(), sender().as_slice());
            assert_eq!(decoded.recipient().as_slice(), recipient().as_slice());
            assert_eq!(decoded.signature().as_slice(), signature().as_slice());
            assert_eq!(decoded.encode(), bytes);
            assert_eq!(fixture.calls.get(), 1);
        }
    }
}

/// Failing mutation: map an unknown kind to ALIVE instead of rejecting it.
/// The signature-only fixture cannot mask a missing structural kind guard.
#[test]
fn unknown_kind_is_rejected_before_verification() {
    for kind in 0..=u8::MAX {
        if (1..=6).contains(&kind) {
            continue;
        }
        let mut bytes = baseline().encode();
        bytes[5] = kind;
        let fixture = Fixture::new(FixtureMode::SignatureOnly, baseline().header(), signature());
        assert!(
            matches!(decode(&bytes, &recipient(), &fixture), Err(DecodeError::UnknownKind(value)) if value == kind)
        );
        assert_eq!(fixture.calls.get(), 0);
    }
}

/// Failing mutation: accept a valid 112-byte prefix with an appended START payload.
/// The signature-only fixture would accept that prefix if the length guard vanished.
#[test]
fn strict_length_rejects_appended_payload() {
    for extension in [
        b"START".as_slice(),
        b"GRANT",
        b"CONSENT",
        b"KEY",
        b"MODEL",
        b"PROMPT:fixture",
        b"ANSWER:fixture",
    ] {
        let mut bytes = baseline().encode().to_vec();
        bytes.extend_from_slice(extension);
        let fixture = Fixture::new(FixtureMode::SignatureOnly, baseline().header(), signature());
        assert!(matches!(
            decode(&bytes, &recipient(), &fixture),
            Err(DecodeError::Oversize)
        ));
        assert_eq!(fixture.calls.get(), 0);
    }
    for length in 0..FRAME_LEN {
        let bytes = baseline().encode();
        let fixture = Fixture::new(FixtureMode::SignatureOnly, baseline().header(), signature());
        assert!(matches!(
            decode(&bytes[..length], &recipient(), &fixture),
            Err(DecodeError::Truncated)
        ));
        assert_eq!(fixture.calls.get(), 0);
    }
}

/// Failing mutation: ignore a false caller-provided opaque-signature verdict.
#[test]
fn opaque_signature_verdict_is_required() {
    let fixture = Fixture::new(FixtureMode::Reject, baseline().header(), signature());
    assert!(matches!(
        decode(&baseline().encode(), &recipient(), &fixture),
        Err(DecodeError::InvalidSignature)
    ));
    assert_eq!(fixture.calls.get(), 1);
}

/// Failing mutation: add replay rejection or cache a verifier verdict in the codec.
/// Freshness belongs to host policy even when an identical frame decodes twice.
#[test]
fn decode_does_not_track_sequence_freshness_or_replays() {
    let frame = baseline();
    let bytes = frame.encode();
    let fixture = Fixture::new(FixtureMode::Bound, frame.header(), signature());
    let first = decode(&bytes, &recipient(), &fixture).unwrap();
    let repeated = decode(&bytes, &recipient(), &fixture).unwrap();
    assert_eq!(first, repeated);
    assert_eq!(first.sequence(), 0);
    assert_eq!(repeated.sequence(), 0);
    assert_eq!(fixture.calls.get(), 2);
}

/// Failing mutation: omit recipient equality while a verifier accepts the frame.
/// This fixture intentionally does not check the caller's expected recipient.
#[test]
fn frame_for_other_recipient_is_rejected_before_verification() {
    let frame = ControlFrame::new(ControlKind::Stop, 1, sender(), [42; 16], signature());
    let fixture = Fixture::new(FixtureMode::SignatureOnly, frame.header(), signature());
    assert!(matches!(
        decode(&frame.encode(), &recipient(), &fixture),
        Err(DecodeError::WrongRecipient)
    ));
    assert_eq!(fixture.calls.get(), 0);
}

/// Failing mutation: pass an unbound header/sender/signature to the verifier.
#[test]
fn verification_binds_sender_header_and_signature() {
    let original = baseline();
    for offset in [5, 8, 15, 16, 31, 32, 47, 48, 111] {
        let mut bytes = original.encode();
        bytes[offset] = if offset == 5 {
            ControlKind::Stop as u8
        } else {
            bytes[offset] ^ 1
        };
        let expected_recipient: NodeId = bytes[32..48].try_into().unwrap();
        let fixture = Fixture::new(FixtureMode::Bound, original.header(), signature());
        assert!(matches!(
            decode(&bytes, &expected_recipient, &fixture),
            Err(DecodeError::InvalidSignature)
        ));
        assert_eq!(fixture.calls.get(), 1);
    }
}

/// Failing mutation: ignore magic/version/reserved bytes or verify before structure.
#[test]
fn malformed_headers_never_reach_verifier() {
    for offset in [0, 1, 2, 3, 4, 6, 7] {
        let mut bytes = baseline().encode();
        bytes[offset] ^= 0xff;
        let fixture = Fixture::new(FixtureMode::SignatureOnly, baseline().header(), signature());
        assert!(decode(&bytes, &recipient(), &fixture).is_err());
        assert_eq!(fixture.calls.get(), 0);
    }
}

/// Failing mutation: relax a field/length/authentication guard or drop a corpus row.
/// Corpus verdicts model the provisional layout and literal fixtures, not crypto.
#[test]
fn corpus_rows_match_provisional_layout_and_fixture_verdicts() {
    let mut count = 0;
    let mut accepted = 0;
    for line in include_str!("data/control-corpus.tsv").lines().skip(1) {
        let fields: Vec<_> = line.split('\t').collect();
        assert_eq!(fields.len(), 9);
        let expected_recipient = array(fields[5]);
        let header = array(fields[6]);
        let signature = array(fields[7]);
        let bytes = from_hex(fields[8]);
        let mode = match fields[4] {
            "bound" => FixtureMode::Bound,
            "signature-only" => FixtureMode::SignatureOnly,
            "reject" => FixtureMode::Reject,
            _ => panic!("unrecognized fixture mode"),
        };
        let fixture = Fixture::new(mode, header, signature);
        let decoded = decode(&bytes, &expected_recipient, &fixture);
        if fields[2] == "OK" {
            let decoded = decoded.unwrap();
            assert_eq!(decoded.encode().as_slice(), bytes);
            assert_eq!(decoded.kind() as u8, bytes[5]);
            assert_eq!(
                decoded.sequence(),
                u64::from_be_bytes(bytes[8..16].try_into().unwrap())
            );
            assert_eq!(decoded.recipient(), &expected_recipient);
            accepted += 1;
        } else {
            assert_eq!(error_name(&decoded.unwrap_err()), fields[2]);
        }
        assert_eq!(fixture.calls.get(), fields[3].parse::<usize>().unwrap());
        count += 1;
    }
    assert_eq!(count, 1373);
    assert_eq!(accepted, 147);
}
