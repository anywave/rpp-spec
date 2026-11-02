use core::cell::Cell;
use proptest::{
    prelude::*,
    test_runner::{Config, RngAlgorithm, TestRng, TestRunner},
};
use rpp_billboard::{
    decode, encode, signing_bytes, Error, Fields, Kind, Signature, Verifier, MAX_FRAME_LEN,
};
use rpp_input_hardening::*;

fn runner() -> TestRunner {
    TestRunner::new_with_rng(
        Config {
            cases: 256,
            max_shrink_iters: 1024,
            failure_persistence: None,
            ..Config::default()
        },
        TestRng::from_seed(RngAlgorithm::ChaCha, &[24; 32]),
    )
}
struct Bound<'a> {
    prefix: &'a [u8],
    signature: Signature,
    accept: bool,
}
impl Verifier for Bound<'_> {
    fn verify(&self, _: &str, prefix: &[u8], signature: &Signature) -> bool {
        self.accept && prefix == self.prefix && signature == &self.signature
    }
}
/// Failing mutations: lose fields/issuer/time endianness or ignore caller refusal.
#[test]
fn billboard_roundtrips_generated_fields_and_verifier_verdicts() {
    let id = || {
        prop::collection::vec(any::<char>(), 1..65).prop_map(|v| v.into_iter().collect::<String>())
    };
    let signature =
        prop::collection::vec(any::<u8>(), 64..65).prop_map(|v| Signature::try_from(v).unwrap());
    let strategy = (
        id(),
        id(),
        prop::collection::vec(32_u8..=126, 1..257),
        "[A-Za-z0-9_.-]{1,64}",
        any::<bool>(),
        0..u64::MAX,
        any::<u64>(),
        signature,
    );
    let result = runner().run(
        &strategy,
        |(issuer, machine, fact, receipt, rule, since, after, signature)| {
            let fact = String::from_utf8(fact).unwrap();
            let until = since + 1 + after % (u64::MAX - since);
            let fields = Fields {
                machine: &machine,
                fact: &fact,
                receipt: &receipt,
                kind: if rule { Kind::Rule } else { Kind::Fact },
                since,
                until,
            };
            let mut prefix = [0; MAX_FRAME_LEN];
            let n = signing_bytes(fields, &issuer, &mut prefix).unwrap();
            let bound = Bound {
                prefix: &prefix[..n],
                signature,
                accept: true,
            };
            let mut wire = [0; MAX_FRAME_LEN];
            let n = encode(fields, &issuer, &signature, &mut wire, &bound).unwrap();
            let view = decode(&wire[..n], &bound).unwrap();
            prop_assert_eq!(view.fields(), fields);
            prop_assert_eq!(view.issuer(), issuer.as_str());
            prop_assert_eq!(view.signature(), &signature);
            let refused = Bound {
                accept: false,
                ..bound
            };
            prop_assert_eq!(decode(&wire[..n], &refused), Err(Error::InvalidSignature));
            Ok(())
        },
    );
    assert_eq!(result, Ok(()));
}
/// Failing mutations: panic on hostile lengths or accept noncanonical/domain-invalid frames.
#[test]
fn billboard_arbitrary_bytes_reencode_without_panics() {
    let successes = Cell::new(0);
    let valid = valid_billboard();
    let mut escaped = valid.clone();
    escaped[rpp_billboard::HEADER_LEN + 2] = 0x1b;
    let mut trailing = valid.clone();
    trailing.push(0);
    let strategy = prop_oneof![
        Just(valid),
        Just(escaped),
        Just(trailing),
        prop::collection::vec(any::<u8>(), 0..=MAX_INPUT)
    ];
    let result = runner().run(&strategy, |input| {
        if billboard_bytes(&input) {
            successes.set(successes.get() + 1);
        }
        Ok(())
    });
    assert_eq!(result, Ok(()));
    assert!(successes.get() > 0);
}
/// Failing mutations: count duplicates twice, skip overlaps, complete early or reopen late duplicates.
#[test]
fn reassembly_random_orders_duplicates_and_overlaps_match_coverage() {
    let strategy = (
        prop::collection::vec(any::<u8>(), 0..=MAX_FRAGMENTS),
        any::<u64>(),
        0_usize..6,
        any::<bool>(),
    );
    let result = runner().run(&strategy, |(ops, sequence, kind, small)| {
        let mtu = if small { 20 } else { 51 };
        prop_assert_eq!(schedule(&ops, sequence, kind, mtu), 1);
        Ok(())
    });
    assert_eq!(result, Ok(()));
}
/// Failing mutations: panic on raw fragments or emit unverified/incorrect completion bytes.
#[test]
fn reassembly_arbitrary_bytes_never_panics_and_valid_seed_completes() {
    let successes = Cell::new(0);
    let mut forged = control(8, 3);
    forged[48] ^= 1;
    let strategy = prop_oneof![
        Just(valid_fragment_input()),
        Just(fragment_input(&forged)),
        prop::collection::vec(any::<u8>(), 0..=MAX_INPUT)
    ];
    let result = runner().run(&strategy, |input| {
        successes.set(successes.get() + arbitrary_fragments(&input));
        Ok(())
    });
    assert_eq!(result, Ok(()));
    assert!(successes.get() > 0);
}
