use proptest::{
    prelude::*,
    test_runner::{Config, RngAlgorithm, TestRng, TestRunner},
};
use rpp_link_udp::{
    framed::{decode_one, encode, FrameError},
    MAX_DATAGRAM_LEN, MAX_DATA_LEN,
};

fn runner() -> TestRunner {
    TestRunner::new_with_rng(
        Config {
            cases: 256,
            max_shrink_iters: 1024,
            failure_persistence: None,
            ..Config::default()
        },
        TestRng::from_seed(RngAlgorithm::ChaCha, &[27; 32]),
    )
}
/// Failing mutations: little-endian lengths, lost payload bytes or consuming a second frame.
#[test]
fn generated_data_roundtrips_and_keeps_coalesced_successor() {
    let result = runner().run(
        &prop::collection::vec(any::<u8>(), 0..=MAX_DATA_LEN),
        |body| {
            let envelope = [&[1, 4][..], body.as_slice()].concat();
            let encoded = encode(&envelope);
            prop_assert!(encoded.is_ok());
            let wire = encoded.unwrap();
            prop_assert_eq!(wire.len(), envelope.len() + 2);
            prop_assert_eq!(&wire[..2], &(envelope.len() as u16).to_be_bytes());
            let successor = encode(&[1, 4, 99]);
            prop_assert!(successor.is_ok());
            let next = successor.unwrap();
            let joined = [wire.as_slice(), next.as_slice()].concat();
            prop_assert_eq!(decode_one(&joined), Ok((envelope.as_slice(), wire.len())));
            prop_assert_eq!(&joined[wire.len()..], next.as_slice());
            Ok(())
        },
    );
    assert_eq!(result, Ok(()));
}
/// Failing mutations: wrong fixed envelope lengths or altered probe/control body bytes.
#[test]
fn generated_probe_reply_and_control_shapes_roundtrip() {
    let result = runner().run(&(any::<u64>(), any::<u8>()), |(nonce, byte)| {
        for envelope in [
            [&[1, 1][..], nonce.to_be_bytes().as_slice()].concat(),
            [&[1, 2][..], nonce.to_be_bytes().as_slice()].concat(),
            [&[1, 3][..], &[byte; 112]].concat(),
        ] {
            let encoded = encode(&envelope);
            prop_assert!(encoded.is_ok());
            let wire = encoded.unwrap();
            prop_assert_eq!(decode_one(&wire), Ok((envelope.as_slice(), wire.len())));
        }
        Ok(())
    });
    assert_eq!(result, Ok(()));
}
/// Failing mutations: accepting partial prefixes/bodies or checking oversized lengths too late.
#[test]
fn generated_frames_reject_every_truncation_and_oversized_prefix() {
    let result = runner().run(
        &prop::collection::vec(any::<u8>(), 0..=MAX_DATA_LEN),
        |body| {
            let encoded = encode(&[&[1, 4][..], body.as_slice()].concat());
            prop_assert!(encoded.is_ok());
            let wire = encoded.unwrap();
            for end in 0..wire.len() {
                prop_assert_eq!(decode_one(&wire[..end]), Err(FrameError::Truncated));
            }
            for size in [MAX_DATAGRAM_LEN as u16 + 1, u16::MAX] {
                let prefix = size.to_be_bytes();
                prop_assert_eq!(decode_one(&prefix), Err(FrameError::InvalidLength));
            }
            Ok(())
        },
    );
    assert_eq!(result, Ok(()));
}
/// Failing mutations: accepting zero/one lengths, a 1201-byte envelope, unknown tags or short control.
#[test]
fn fixed_length_and_envelope_domains_are_checked() {
    for size in [0_u16, 1] {
        assert_eq!(
            decode_one(&size.to_be_bytes()),
            Err(FrameError::InvalidLength)
        );
    }
    let mut maximum = [0; MAX_DATAGRAM_LEN];
    maximum[..2].copy_from_slice(&[1, 4]);
    assert!(encode(&maximum).is_ok());
    let mut oversized = [0; MAX_DATAGRAM_LEN + 1];
    oversized[..2].copy_from_slice(&[1, 4]);
    assert_eq!(encode(&oversized), Err(FrameError::InvalidLength));
    for envelope in [[0, 4], [1, 0], [1, 5], [1, 1], [1, 2], [1, 3]] {
        assert_eq!(encode(&envelope), Err(FrameError::InvalidEnvelope));
    }
}
