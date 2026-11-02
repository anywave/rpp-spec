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
    let mut signing = [0; MAX_FRAME_LEN];
    let signed = signing_bytes(fields(), "A", &mut signing).unwrap();
    let verifier = Exact {
        prefix: &signing[..signed],
        signature: [0xa5; 64],
    };
    let size = encode(fields(), "A", &[0xa5; 64], &mut output, &verifier).unwrap();
    let view = decode(&output[..size], &verifier).unwrap();
    assert_eq!(view.fields(), fields());
    assert_eq!(view.issuer(), "A");
    assert_eq!(&signing[..signed], view.signing_bytes());
    assert_eq!(&output[..13], b"RPPB\x01\x01\x00\x01\x00\x01\x00\x07\x03");
}

/// Failing mutation: silently emit a partial frame or write before buffer validation.
#[test]
fn too_small_output_is_refused_atomically() {
    let mut output = [0x55; 10];
    assert_eq!(
        encode(
            fields(),
            "A",
            &[0; 64],
            &mut output,
            &Exact {
                prefix: &[],
                signature: [0; 64]
            }
        ),
        Err(Error::BufferTooSmall)
    );
    assert_eq!(output, [0x55; 10]);
}

fn raw(value: Fields<'_>, issuer: &str) -> Vec<u8> {
    let mut bytes = vec![0; 29];
    bytes[..6].copy_from_slice(b"RPPB\x01\x01");
    bytes[5] = value.kind as u8;
    bytes[6..8].copy_from_slice(&(issuer.len() as u16).to_be_bytes());
    bytes[8..10].copy_from_slice(&(value.machine.len() as u16).to_be_bytes());
    bytes[10..12].copy_from_slice(&(value.fact.len() as u16).to_be_bytes());
    bytes[12] = value.receipt.len() as u8;
    bytes[13..21].copy_from_slice(&value.since.to_be_bytes());
    bytes[21..29].copy_from_slice(&value.until.to_be_bytes());
    for text in [issuer, value.machine, value.fact, value.receipt] {
        bytes.extend_from_slice(text.as_bytes());
    }
    bytes.extend_from_slice(&[0xa5; 64]);
    bytes
}

fn refusal(bytes: &[u8], error: Error) {
    let verifier = Exact {
        prefix: &bytes[..bytes.len() - 64],
        signature: [0xa5; 64],
    };
    assert_eq!(decode(bytes, &verifier), Err(error));
}

/// Failing mutation billboard_trailing_byte: accept bytes outside the declared envelope.
#[test]
fn trailing_byte_is_rejected() {
    let mut bytes = raw(fields(), "A");
    let prefix = bytes[..bytes.len() - 64].to_vec();
    bytes.push(0);
    assert_eq!(
        decode(
            &bytes,
            &Exact {
                prefix: &prefix,
                signature: [0xa5; 64]
            }
        ),
        Err(Error::TrailingBytes)
    );
}

/// Failing mutation billboard_empty_interval: accept since == until.
#[test]
fn empty_interval_is_rejected() {
    refusal(
        &raw(
            Fields {
                until: 0,
                ..fields()
            },
            "A",
        ),
        Error::InvalidInterval,
    );
}

/// Failing mutation billboard_fact_escape: permit ESC in an otherwise valid fact.
#[test]
fn fact_escape_is_rejected() {
    refusal(
        &raw(
            Fields {
                fact: "rule\x1b",
                ..fields()
            },
            "A",
        ),
        Error::InvalidFact,
    );
}

/// Failing mutation billboard_fact_bidi: permit UTF-8 U+202E in fact text.
#[test]
fn fact_bidi_is_rejected() {
    refusal(
        &raw(
            Fields {
                fact: "rule\u{202e}",
                ..fields()
            },
            "A",
        ),
        Error::InvalidFact,
    );
}

/// Failing mutation billboard_fact_257: accept a 257-byte fact.
#[test]
fn fact_257_bytes_is_rejected() {
    refusal(
        &raw(
            Fields {
                fact: &"x".repeat(257),
                ..fields()
            },
            "A",
        ),
        Error::InvalidFact,
    );
}

/// Failing mutation billboard_receipt_slash: admit receipt namespace separators.
#[test]
fn receipt_slash_is_rejected() {
    refusal(
        &raw(
            Fields {
                receipt: "r/1",
                ..fields()
            },
            "A",
        ),
        Error::InvalidReceipt,
    );
}

/// Failing mutation billboard_kind_three: alias an unknown kind to FACT.
#[test]
fn kind_three_and_unknown_version_are_rejected() {
    let mut bytes = raw(fields(), "A");
    bytes[5] = 3;
    refusal(&bytes, Error::UnknownKind(3));
    bytes[5] = 1;
    bytes[4] = 2;
    refusal(&bytes, Error::UnsupportedVersion(2));
}

struct Refuse;
impl Verifier for Refuse {
    fn verify(&self, _: &str, _: &[u8], _: &Signature) -> bool {
        false
    }
}

/// Failing mutation billboard_verifier_bypass: ignore caller refusal in decode or checked encode.
#[test]
fn verifier_refusal_is_required_and_encoding_is_atomic() {
    let bytes = raw(fields(), "A");
    assert_eq!(decode(&bytes, &Refuse), Err(Error::InvalidSignature));
    let mut output = [0x55; MAX_FRAME_LEN];
    assert_eq!(
        encode(fields(), "A", &[0xa5; 64], &mut output, &Refuse),
        Err(Error::InvalidSignature)
    );
    assert_eq!(output, [0x55; MAX_FRAME_LEN]);
}

/// Failing mutation billboard_issuer_unsigned: omit issuer from the verification prefix.
#[test]
fn issuer_is_bound_into_signing_bytes() {
    let mut bytes = raw(fields(), "owner-A");
    let prefix = bytes[..bytes.len() - 64].to_vec();
    let verifier = Exact {
        prefix: &prefix,
        signature: [0xa5; 64],
    };
    let decoded = decode(&bytes, &verifier);
    assert!(decoded.is_ok());
    assert_eq!(decoded.unwrap().issuer(), "owner-A");
    bytes[29] ^= 1;
    assert_eq!(decode(&bytes, &verifier), Err(Error::InvalidSignature));
}

/// Failing mutations: count identifier bytes as characters or reject Unicode/opaque ID controls.
#[test]
fn identifiers_preserve_core_scalar_domain_and_maximum_frame() {
    let issuer = "\u{1f642}".repeat(64);
    let machine = "\u{1f643}".repeat(64);
    let fact = "x".repeat(256);
    let receipt = "r".repeat(64);
    let value = Fields {
        machine: &machine,
        fact: &fact,
        receipt: &receipt,
        ..fields()
    };
    let bytes = raw(value, &issuer);
    assert_eq!(bytes.len(), MAX_FRAME_LEN);
    let view = decode(
        &bytes,
        &Exact {
            prefix: &bytes[..bytes.len() - 64],
            signature: [0xa5; 64],
        },
    )
    .unwrap();
    assert_eq!(view.fields(), value);
    assert_eq!(view.issuer(), issuer);
    refusal(
        &raw(
            Fields {
                machine: &"a".repeat(65),
                ..fields()
            },
            "A",
        ),
        Error::InvalidIdentifier,
    );
    let bytes = raw(fields(), "opaque\0id");
    assert!(decode(
        &bytes,
        &Exact {
            prefix: &bytes[..bytes.len() - 64],
            signature: [0xa5; 64]
        }
    )
    .is_ok());
}

/// Failing mutations: encoder omits a structural guard or decoder indexes a truncated prefix.
#[test]
fn encoder_and_decoder_share_structural_refusals_and_prefix_safety() {
    for (value, error) in [
        (
            Fields {
                fact: "bad\n",
                ..fields()
            },
            Error::InvalidFact,
        ),
        (
            Fields {
                receipt: "bad/",
                ..fields()
            },
            Error::InvalidReceipt,
        ),
        (
            Fields {
                until: 0,
                ..fields()
            },
            Error::InvalidInterval,
        ),
    ] {
        let mut output = [0x55; MAX_FRAME_LEN];
        assert_eq!(
            encode(value, "A", &[0; 64], &mut output, &Refuse),
            Err(error)
        );
        assert_eq!(output, [0x55; MAX_FRAME_LEN]);
    }
    let bytes = raw(fields(), "A");
    let verifier = Exact {
        prefix: &bytes[..bytes.len() - 64],
        signature: [0xa5; 64],
    };
    for length in 0..bytes.len() {
        assert!(decode(&bytes[..length], &verifier).is_err());
    }
}

/// Failing mutation: alloc convenience conversion changes fields from the borrowed no_std view.
#[cfg(feature = "alloc")]
#[test]
fn borrowed_decode_matches_alloc_core_fields() {
    let bytes = raw(fields(), "A");
    let view = decode(
        &bytes,
        &Exact {
            prefix: &bytes[..bytes.len() - 64],
            signature: [0xa5; 64],
        },
    )
    .unwrap();
    let owned = view.to_core();
    assert!(owned.valid());
    assert_eq!(Fields::from_core(&owned), Ok(view.fields()));
}

/// Failing mutation: quietly narrow i128 timestamps or permit non-ASCII core-valid facts.
#[cfg(feature = "alloc")]
#[test]
fn core_valid_unencodable_billboards_are_refused() {
    let bytes = raw(fields(), "A");
    let mut board = decode(
        &bytes,
        &Exact {
            prefix: &bytes[..bytes.len() - 64],
            signature: [0xa5; 64],
        },
    )
    .unwrap()
    .to_core();
    for text in ["bad\n", "bad\x1b", "bad\u{7f}", "caf\u{e9}"] {
        board.fact = text.into();
        assert!(board.valid());
        assert_eq!(Fields::from_core(&board), Err(Error::InvalidFact));
    }
    board.fact = "valid".into();
    board.until = i128::from(u64::MAX) + 1;
    assert!(board.valid());
    assert_eq!(Fields::from_core(&board), Err(Error::TimeOutOfRange));
}
