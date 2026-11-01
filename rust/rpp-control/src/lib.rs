//! Experimental, unpublished fixed-size control envelope.
//!
//! The closed envelope has no payload, text, extension, grant, consent, key or
//! model field. Opaque identifiers and signatures are not scanned for text.
//! This crate implements no cryptography: the host supplies a verification
//! verdict. Membership, consent, replay tracking and control effects remain host
//! policy. Successful decoding is not a permission grant or an operation start.

#![no_std]
#![forbid(unsafe_code)]

/// Exact complete frame size, including its opaque signature.
pub const FRAME_LEN: usize = 112;
/// Exact canonical header passed to the caller's verifier.
pub const HEADER_LEN: usize = 48;
/// Size of an opaque host-provisioned identifier; it is not a key field.
pub const ID_LEN: usize = 16;
/// Size of the opaque signature; no algorithm is implemented or selected here.
pub const SIGNATURE_LEN: usize = 64;
/// Experimental codec version. This is not a published RPP wire version.
pub const VERSION: u8 = 1;

const MAGIC: [u8; 4] = *b"RPPC";

pub type NodeId = [u8; ID_LEN];
pub type Signature = [u8; SIGNATURE_LEN];

/// The entire control vocabulary; there is no START or arbitrary-content kind.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum ControlKind {
    Alive = 1,
    MemberChanged = 2,
    Stop = 3,
    Pause = 4,
    RouteAround = 5,
    Resume = 6,
}

impl ControlKind {
    pub const ALL: [Self; 6] = [
        Self::Alive,
        Self::MemberChanged,
        Self::Stop,
        Self::Pause,
        Self::RouteAround,
        Self::Resume,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Alive => "ALIVE",
            Self::MemberChanged => "MEMBER-CHANGED",
            Self::Stop => "STOP",
            Self::Pause => "PAUSE",
            Self::RouteAround => "ROUTE-AROUND",
            Self::Resume => "RESUME",
        }
    }
}

impl TryFrom<u8> for ControlKind {
    type Error = DecodeError;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            1 => Ok(Self::Alive),
            2 => Ok(Self::MemberChanged),
            3 => Ok(Self::Stop),
            4 => Ok(Self::Pause),
            5 => Ok(Self::RouteAround),
            6 => Ok(Self::Resume),
            other => Err(DecodeError::UnknownKind(other)),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DecodeError {
    Truncated,
    Oversize,
    BadMagic,
    UnsupportedVersion(u8),
    UnknownKind(u8),
    NonzeroReserved,
    WrongRecipient,
    InvalidSignature,
}

/// The caller verifies the exact header, including both identities and domain.
///
/// There is no default implementation. The opaque sender can select an existing
/// verifier context; it does not carry a verification key. A true verdict alone
/// does not establish current membership, consent or a fresh sequence number.
pub trait Verifier {
    fn verify(&self, sender: &NodeId, header: &[u8; HEADER_LEN], signature: &Signature) -> bool;
}

/// An outbound builder with closed kinds and caller-provided opaque signature.
///
/// This type is not evidence that a signature was checked. Receiving adapters
/// should require `VerifiedControlFrame`, produced only by `decode`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ControlFrame {
    kind: ControlKind,
    sequence: u64,
    sender: NodeId,
    recipient: NodeId,
    signature: Signature,
}

impl ControlFrame {
    pub const fn new(
        kind: ControlKind,
        sequence: u64,
        sender: NodeId,
        recipient: NodeId,
        signature: Signature,
    ) -> Self {
        Self {
            kind,
            sequence,
            sender,
            recipient,
            signature,
        }
    }

    /// Header bytes a host may pass to its existing signing mechanism.
    ///
    /// Magic and version distinguish this experimental envelope. The recipient
    /// is included, so verification binds the same endpoint pair as routing.
    pub fn signing_header(
        kind: ControlKind,
        sequence: u64,
        sender: NodeId,
        recipient: NodeId,
    ) -> [u8; HEADER_LEN] {
        let mut header = [0; HEADER_LEN];
        header[0..4].copy_from_slice(&MAGIC);
        header[4] = VERSION;
        header[5] = kind as u8;
        // Bytes 6..8 are reserved and remain zero.
        header[8..16].copy_from_slice(&sequence.to_be_bytes());
        header[16..32].copy_from_slice(&sender);
        header[32..48].copy_from_slice(&recipient);
        header
    }

    pub fn header(&self) -> [u8; HEADER_LEN] {
        Self::signing_header(self.kind, self.sequence, self.sender, self.recipient)
    }

    pub fn encode(&self) -> [u8; FRAME_LEN] {
        let mut bytes = [0; FRAME_LEN];
        bytes[..HEADER_LEN].copy_from_slice(&self.header());
        bytes[HEADER_LEN..FRAME_LEN].copy_from_slice(&self.signature);
        bytes
    }

    pub const fn kind(&self) -> ControlKind {
        self.kind
    }

    pub const fn sequence(&self) -> u64 {
        self.sequence
    }

    pub const fn sender(&self) -> &NodeId {
        &self.sender
    }

    pub const fn recipient(&self) -> &NodeId {
        &self.recipient
    }

    pub const fn signature(&self) -> &Signature {
        &self.signature
    }
}

/// A structurally valid frame with a successful caller verification verdict.
///
/// Fields and construction are private. This evidence must still be combined
/// with current host authorization, consent and replay policy before any effect.
/// Sequence freshness and replay are not checked by `decode`: the same bytes
/// may decode repeatedly when the caller's verifier accepts them each time.
/// The host must enforce freshness before acting, for example with the strictly
/// increasing per-endpoint sequence check in `rpp_core::overlay::Simulator`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct VerifiedControlFrame {
    frame: ControlFrame,
}

impl VerifiedControlFrame {
    pub const fn kind(&self) -> ControlKind {
        self.frame.kind()
    }

    pub const fn sequence(&self) -> u64 {
        self.frame.sequence()
    }

    pub const fn sender(&self) -> &NodeId {
        self.frame.sender()
    }

    pub const fn recipient(&self) -> &NodeId {
        self.frame.recipient()
    }

    pub const fn signature(&self) -> &Signature {
        self.frame.signature()
    }

    pub fn encode(&self) -> [u8; FRAME_LEN] {
        self.frame.encode()
    }
}

/// Decode an exact envelope and require a caller-supplied verification verdict.
///
/// Length is checked before any indexing. All malformed structural fields and
/// a wrong target are rejected before invoking the verifier. There is no raw
/// parse API that can produce the verified transport type without this check.
/// This function keeps no sequence or replay state. Successful decoding does
/// not establish freshness; the host must apply its replay/sequence policy,
/// such as `rpp_core::overlay::Simulator`'s monotonic control-sequence check,
/// before any effect. A verifier may enforce additional host policy itself.
pub fn decode<V: Verifier + ?Sized>(
    input: &[u8],
    expected_recipient: &NodeId,
    verifier: &V,
) -> Result<VerifiedControlFrame, DecodeError> {
    if input.len() < FRAME_LEN {
        return Err(DecodeError::Truncated);
    }
    if input.len() > FRAME_LEN {
        return Err(DecodeError::Oversize);
    }
    if input[0..4] != MAGIC {
        return Err(DecodeError::BadMagic);
    }
    if input[4] != VERSION {
        return Err(DecodeError::UnsupportedVersion(input[4]));
    }
    let kind = ControlKind::try_from(input[5])?;
    if input[6] != 0 || input[7] != 0 {
        return Err(DecodeError::NonzeroReserved);
    }
    let mut sequence = [0; 8];
    sequence.copy_from_slice(&input[8..16]);
    let sequence = u64::from_be_bytes(sequence);
    let mut sender = [0; ID_LEN];
    sender.copy_from_slice(&input[16..32]);
    let mut recipient = [0; ID_LEN];
    recipient.copy_from_slice(&input[32..48]);
    if recipient != *expected_recipient {
        return Err(DecodeError::WrongRecipient);
    }
    let mut signature = [0; SIGNATURE_LEN];
    signature.copy_from_slice(&input[HEADER_LEN..FRAME_LEN]);
    let mut header = [0; HEADER_LEN];
    header.copy_from_slice(&input[..HEADER_LEN]);
    if !verifier.verify(&sender, &header, &signature) {
        return Err(DecodeError::InvalidSignature);
    }
    Ok(VerifiedControlFrame {
        frame: ControlFrame::new(kind, sequence, sender, recipient, signature),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use core::cell::Cell;

    const SENDER: NodeId = [0x11; ID_LEN];
    const RECIPIENT: NodeId = [0x22; ID_LEN];
    const SIGNATURE: Signature = [0xa5; SIGNATURE_LEN];

    struct FixtureVerifier {
        expected: [u8; HEADER_LEN],
    }

    impl Verifier for FixtureVerifier {
        fn verify(
            &self,
            sender: &NodeId,
            header: &[u8; HEADER_LEN],
            signature: &Signature,
        ) -> bool {
            sender == &SENDER && header == &self.expected && signature == &SIGNATURE
        }
    }

    struct RejectVerifier {
        calls: Cell<usize>,
    }

    impl Verifier for RejectVerifier {
        fn verify(&self, _: &NodeId, _: &[u8; HEADER_LEN], _: &Signature) -> bool {
            self.calls.set(self.calls.get() + 1);
            false
        }
    }

    fn fixture(kind: ControlKind, sequence: u64) -> ControlFrame {
        ControlFrame::new(kind, sequence, SENDER, RECIPIENT, SIGNATURE)
    }

    fn header_fixture(bytes: &[u8]) -> FixtureVerifier {
        let mut expected = [0; HEADER_LEN];
        expected.copy_from_slice(&bytes[..HEADER_LEN]);
        FixtureVerifier { expected }
    }

    #[test]
    fn header_has_fixed_golden_offsets() {
        // Failing mutation: shift or little-endian encode the sequence or either ID.
        let frame = fixture(ControlKind::Alive, 0x0102_0304_0506_0708);
        let bytes = frame.encode();
        assert_eq!(
            &bytes[..16],
            &[b'R', b'P', b'P', b'C', 1, 1, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8]
        );
        assert_eq!(&bytes[16..32], &SENDER);
        assert_eq!(&bytes[32..48], &RECIPIENT);
        assert_eq!(&bytes[48..112], &SIGNATURE);
    }

    #[test]
    fn round_trip_all_six() {
        // Failing mutation: alias a kind code or change any accepted field on decode.
        for kind in ControlKind::ALL {
            for sequence in [0, 1, u64::MAX] {
                let frame = fixture(kind, sequence);
                let bytes = frame.encode();
                let verified = decode(&bytes, &RECIPIENT, &header_fixture(&bytes)).unwrap();
                assert_eq!(verified.kind(), kind);
                assert_eq!(verified.sequence(), sequence);
                assert_eq!(verified.sender(), &SENDER);
                assert_eq!(verified.recipient(), &RECIPIENT);
                assert_eq!(verified.signature(), &SIGNATURE);
                assert_eq!(verified.encode(), bytes);
            }
        }
    }

    #[test]
    fn rejects_unknown_kind() {
        // Failing mutation: decode an unknown tag as ALIVE.
        let mut bytes = fixture(ControlKind::Alive, 1).encode();
        bytes[5] = 0;
        assert_eq!(
            decode(&bytes, &RECIPIENT, &header_fixture(&bytes)),
            Err(DecodeError::UnknownKind(0))
        );
    }

    #[test]
    fn rejects_trailing_content() {
        // Failing mutation: accept oversized frames and ignore appended START bytes.
        let frame = fixture(ControlKind::Stop, 1).encode();
        let mut bytes = [0; FRAME_LEN + 5];
        bytes[..FRAME_LEN].copy_from_slice(&frame);
        bytes[FRAME_LEN..].copy_from_slice(b"START");
        assert_eq!(
            decode(&bytes, &RECIPIENT, &header_fixture(&frame)),
            Err(DecodeError::Oversize)
        );
    }

    #[test]
    fn requires_verifier_acceptance() {
        // Failing mutation: skip the caller's negative verification verdict.
        let frame = fixture(ControlKind::Pause, 1).encode();
        let verifier = RejectVerifier {
            calls: Cell::new(0),
        };
        assert_eq!(
            decode(&frame, &RECIPIENT, &verifier),
            Err(DecodeError::InvalidSignature)
        );
        assert_eq!(verifier.calls.get(), 1);
    }

    #[test]
    fn binds_recipient() {
        // Failing mutation: omit comparison with the caller's expected recipient.
        let frame = fixture(ControlKind::Resume, 1).encode();
        let other_recipient = [0x33; ID_LEN];
        assert_eq!(
            decode(&frame, &other_recipient, &header_fixture(&frame)),
            Err(DecodeError::WrongRecipient)
        );
    }

    #[test]
    fn malformed_headers_do_not_invoke_verifier() {
        // Failing mutation: validate magic/version/reserved bytes after verification.
        for (index, value, error) in [
            (0, b'X', DecodeError::BadMagic),
            (4, 2, DecodeError::UnsupportedVersion(2)),
            (6, 1, DecodeError::NonzeroReserved),
            (7, 1, DecodeError::NonzeroReserved),
        ] {
            let mut frame = fixture(ControlKind::Alive, 1).encode();
            frame[index] = value;
            let verifier = RejectVerifier {
                calls: Cell::new(0),
            };
            assert_eq!(decode(&frame, &RECIPIENT, &verifier), Err(error));
            assert_eq!(verifier.calls.get(), 0);
        }
    }

    #[test]
    fn every_truncated_length_is_rejected_first() {
        // Failing mutation: index header fields before enforcing the fixed length.
        let frame = fixture(ControlKind::Alive, 1).encode();
        for length in 0..FRAME_LEN {
            let verifier = RejectVerifier {
                calls: Cell::new(0),
            };
            assert_eq!(
                decode(&frame[..length], &RECIPIENT, &verifier),
                Err(DecodeError::Truncated)
            );
            assert_eq!(verifier.calls.get(), 0);
        }
    }
}
