use rpp_input_hardening::{arbitrary_fragments, billboard_bytes, schedule};
fn hex(text: &str) -> Vec<u8> {
    text.split_ascii_whitespace()
        .flat_map(|line| line.as_bytes().chunks_exact(2))
        .map(|pair| u8::from_str_radix(core::str::from_utf8(pair).unwrap(), 16).unwrap())
        .collect()
}
/// Mutation: corrupt a checked-in positive seed, replace it by always-rejected bytes, or lose an overlap/order case.
#[test]
fn checked_in_hex_seeds_exercise_valid_and_invalid_decoding() {
    assert!(billboard_bytes(&hex(include_str!(
        "../seeds/valid-fact.hex"
    ))));
    assert!(billboard_bytes(&hex(include_str!(
        "../seeds/valid-rule.hex"
    ))));
    assert!(!billboard_bytes(&hex(include_str!(
        "../seeds/dual-invalid.hex"
    ))));
    assert_eq!(
        arbitrary_fragments(&hex(include_str!("../seeds/valid-fragments.hex"))[1..]),
        1
    );
    assert_eq!(
        schedule(
            &hex(include_str!("../seeds/order-overlap.hex"))[1..],
            8,
            3,
            20
        ),
        1
    );
}
