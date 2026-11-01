//! Python-oracle fixtures; test titles are fixed and do not embed corpus rows.
#![cfg(feature = "alloc")]

use rpp_core::canonical::{migrate_v1, CanonicalAddress, MigrationPolicy};

fn hex_bytes(text: &str) -> Vec<u8> {
    (0..text.len())
        .step_by(2)
        .map(|offset| u8::from_str_radix(&text[offset..offset + 2], 16).unwrap())
        .collect()
}

fn radius(text: &str) -> f64 {
    f64::from_bits(u64::from_str_radix(text, 16).unwrap())
}

fn assert_address(address: CanonicalAddress, fields: &[&str]) {
    assert_eq!(
        address.to_word(),
        u32::from_str_radix(fields[0], 16).unwrap()
    );
    assert_eq!(address.to_bytes().as_slice(), hex_bytes(fields[1]));
    assert_eq!(address.to_uri(), fields[2]);
    assert_eq!(address.is_valid(), fields[3] == "1");
    assert_eq!(address.is_reserved(), fields[4] == "1");
    assert_eq!(address.is_null(), fields[5] == "1");
    assert_eq!(address.is_wildcard(), fields[6] == "1");
    assert_eq!(address.sector().name(), fields[7]);
    assert_eq!(address.to_int(), address.to_word());
    assert_eq!(address.to_be_bytes(), address.to_bytes());
    assert_eq!(address.to_hex(), format!("0x{:08X}", address.to_word()));
}

/// Executed mutation: theta field shifted27→26; or half-even replaced by half-away.
/// A dropped corpus row also fails the exact count guard.
#[test]
fn constructor_corpus_matches_python_words_and_bytes() {
    let corpus = include_str!("data/address-construct.tsv");
    let mut count = 0;
    for line in corpus.lines().skip(1) {
        let columns: Vec<_> = line.split('\t').collect();
        let address = CanonicalAddress::new(
            columns[0].parse().unwrap(),
            columns[1].parse().unwrap(),
            columns[2].parse().unwrap(),
            radius(columns[4]),
            columns[3].parse().unwrap(),
        );
        if columns[5] == "ERR" {
            assert!(address.is_err());
        } else {
            assert_address(address.unwrap(), &columns[6..]);
        }
        count += 1;
    }
    assert_eq!(count, 4110);
}

/// Failing mutation: erase reserved bits, reverse byte order, or reject null raw words.
/// A dropped corpus row also fails the exact count guard.
#[test]
fn raw_word_corpus_matches_python_decoding_and_signed_masking() {
    let mut count = 0;
    for line in include_str!("data/address-raw.tsv").lines().skip(1) {
        let columns: Vec<_> = line.split('\t').collect();
        let input: i64 = columns[0].parse().unwrap();
        let address = CanonicalAddress::from_int(input);
        assert_eq!(address.theta() as i64, columns[1].parse::<i64>().unwrap());
        assert_eq!(address.phi() as i64, columns[2].parse::<i64>().unwrap());
        assert_eq!(address.omega() as i64, columns[3].parse::<i64>().unwrap());
        assert_eq!(
            address.reserved() as i64,
            columns[4].parse::<i64>().unwrap()
        );
        assert_eq!(address.radius().to_bits(), radius(columns[5]).to_bits());
        assert_address(address, &columns[6..]);
        assert_eq!(CanonicalAddress::from_word(input as u32), address);
        assert_eq!(
            CanonicalAddress::from_bytes(&address.to_bytes()).unwrap(),
            address
        );
        count += 1;
    }
    assert_eq!(count, 2119);
}

/// Failing mutation: require end-of-string, accept negative radii, or drop Unicode Nd parsing.
/// A dropped corpus row also fails the exact count guard.
#[test]
fn uri_corpus_preserves_python_prefix_and_negative_zero_behavior() {
    let mut count = 0;
    for line in include_str!("data/address-uri.tsv").lines().skip(1) {
        let columns: Vec<_> = line.split('\t').collect();
        let uri = String::from_utf8(hex_bytes(columns[0])).unwrap();
        let address = CanonicalAddress::from_uri(&uri);
        if columns[1] == "ERR" {
            assert!(address.is_err());
        } else {
            let address = address.unwrap();
            assert_eq!(address.radius().to_bits(), radius(columns[2]).to_bits());
            assert_address(address, &columns[3..]);
        }
        count += 1;
    }
    assert_eq!(count, 3268);
}

/// Failing mutation: accept NaN/infinity, drop a field bound, or permit non-four-byte input.
#[test]
fn invalid_constructor_and_byte_domains_are_rejected() {
    for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY, -0.1, 1.1] {
        assert!(CanonicalAddress::new(1, 1, 0, value, 0).is_err());
    }
    for values in [
        (-1, 1, 0, 0),
        (32, 1, 0, 0),
        (1, 0, 0, 0),
        (1, 9, 0, 0),
        (1, 1, -1, 0),
        (1, 1, 8, 0),
        (1, 1, 0, -1),
        (1, 1, 0, 8192),
    ] {
        assert!(CanonicalAddress::new(values.0, values.1, values.2, 0.5, values.3).is_err());
    }
    for length in [0, 1, 2, 3, 5, 8] {
        assert!(CanonicalAddress::from_bytes(&vec![0; length]).is_err());
    }
    assert!(CanonicalAddress::from_bytes(&[0; 4]).unwrap().is_null());
}

/// Failing mutation: pick one implicit radius policy or map a shell to the other policy.
#[test]
fn migration_requires_named_policy_and_retains_lossy_mapping() {
    assert!("".parse::<MigrationPolicy>().is_err());
    assert!("default".parse::<MigrationPolicy>().is_err());
    for shell in 0..=3 {
        let neutral = migrate_v1(shell, 511, 511, 255, "neutral-radius".parse().unwrap()).unwrap();
        let projected =
            migrate_v1(shell, 511, 511, 255, "shell-projection".parse().unwrap()).unwrap();
        assert_eq!(neutral.radius(), 0.5);
        assert_eq!(projected.radius(), shell as f64 / 3.0);
        assert_eq!(
            (neutral.theta(), neutral.phi(), neutral.omega()),
            (27, 6, 4)
        );
        assert_eq!(MigrationPolicy::NeutralRadius.as_str(), "neutral-radius");
        assert_eq!(
            MigrationPolicy::ShellProjection.as_str(),
            "shell-projection"
        );
    }
    for (theta, phi, harmonic, expected) in [
        (0, 0, 0, (1, 1, 0)),
        (64, 128, 64, (4, 2, 1)),
        (256, 256, 128, (14, 4, 2)),
    ] {
        let mapped = migrate_v1(0, theta, phi, harmonic, MigrationPolicy::NeutralRadius).unwrap();
        assert_eq!((mapped.theta(), mapped.phi(), mapped.omega()), expected);
    }
    for values in [
        (-1, 0, 0, 0),
        (4, 0, 0, 0),
        (0, 512, 0, 0),
        (0, 0, -1, 0),
        (0, 0, 0, 256),
    ] {
        assert!(migrate_v1(
            values.0,
            values.1,
            values.2,
            values.3,
            MigrationPolicy::NeutralRadius
        )
        .is_err());
    }
}
