//! Literal verification fixtures implement no cryptography or permission grant.
use rpp_billboard::{
    decode, encode, signing_bytes, Error, Fields, Kind, Signature, Verifier, MAX_FRAME_LEN,
};

struct Exact<'a> {
    prefix: &'a [u8],
    signature: Signature,
}
impl Verifier for Exact<'_> {
    fn verify(&self, _: &str, bytes: &[u8], signature: &Signature) -> bool {
        bytes == self.prefix && signature == &self.signature
    }
}
fn fields() -> Fields<'static> {
    Fields {
        machine: "B",
        kind: Kind::Fact,
        fact: "fixture",
        since: 0,
        until: 2,
        receipt: "r-1",
    }
}

/// Failing mutation: alter field order/endianness or omit any signing-prefix field.
#[test]
fn borrowed_roundtrip_preserves_fields_and_signing_bytes() {
    let mut output = [0; MAX_FRAME_LEN];
    let size = encode(fields(), "A", &[0xa5; 64], &mut output).unwrap();
    let verifier = Exact {
        prefix: &output[..size - 64],
        signature: [0xa5; 64],
    };
    let view = decode(&output[..size], &verifier).unwrap();
    assert_eq!(view.fields(), fields());
    assert_eq!(view.issuer(), "A");
    let mut signing = [0; MAX_FRAME_LEN];
    let signed = signing_bytes(fields(), "A", &mut signing).unwrap();
    assert_eq!(&signing[..signed], view.signing_bytes());
    assert_eq!(&output[..13], b"RPPB\x01\x01\x00\x01\x00\x01\x00\x07\x03");
}

/// Failing mutation: silently emit a partial frame or write before buffer validation.
#[test]
fn too_small_output_is_refused_atomically() {
    let mut output = [0x55; 10];
    assert_eq!(
        encode(fields(), "A", &[0; 64], &mut output),
        Err(Error::BufferTooSmall)
    );
    assert_eq!(output, [0x55; 10]);
}
