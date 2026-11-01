//! Canonical v2 address binding to the current Python reference.
//!
//! Reserved/null states accepted by Python remain accepted here. URI parsing
//! intentionally retains Python's prefix-match behavior; formatting a negative
//! zero radius still produces a URI that this parser rejects. Typed Rust fields
//! do not represent Python bool-as-number constructor arguments.

#[cfg(feature = "alloc")]
use alloc::{format, string::String};
use core::fmt;
use core::str::FromStr;

#[derive(Clone, Debug, PartialEq)]
pub enum CanonicalError {
    FieldOutOfRange { field: &'static str, value: i64 },
    RadiusOutOfRange,
    InvalidByteLength,
    InvalidUri,
    UnknownMigrationPolicy,
}

impl fmt::Display for CanonicalError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::FieldOutOfRange { field, value } => write!(f, "{field} out of range: {value}"),
            Self::RadiusOutOfRange => f.write_str("radius must be finite and in 0..=1"),
            Self::InvalidByteLength => f.write_str("canonical address requires four bytes"),
            Self::InvalidUri => f.write_str("invalid SPIRAL URI"),
            Self::UnknownMigrationPolicy => f.write_str("explicit migration policy required"),
        }
    }
}

impl core::error::Error for CanonicalError {}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ThetaSector {
    Core,
    Gene,
    Memory,
    Witness,
    Dream,
    Bridge,
    Guardian,
    Shadow,
    Inverse,
    Meta,
}

impl ThetaSector {
    pub fn from_theta(theta: u8) -> Self {
        match theta {
            0 => Self::Inverse,
            1..=3 => Self::Core,
            4..=6 => Self::Gene,
            7..=10 => Self::Memory,
            11..=13 => Self::Witness,
            14..=17 => Self::Dream,
            18..=20 => Self::Bridge,
            21..=24 => Self::Guardian,
            25..=27 => Self::Shadow,
            _ => Self::Meta,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::Core => "CORE",
            Self::Gene => "GENE",
            Self::Memory => "MEMORY",
            Self::Witness => "WITNESS",
            Self::Dream => "DREAM",
            Self::Bridge => "BRIDGE",
            Self::Guardian => "GUARDIAN",
            Self::Shadow => "SHADOW",
            Self::Inverse => "INVERSE",
            Self::Meta => "META",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct CanonicalAddress {
    theta: u8,
    phi: u8,
    omega: u8,
    radius: f64,
    reserved: u16,
}

impl CanonicalAddress {
    pub fn new(
        theta: i64,
        phi: i64,
        omega: i64,
        radius: f64,
        reserved: i64,
    ) -> Result<Self, CanonicalError> {
        for (field, value, min, max) in [
            ("theta", theta, 0, 31),
            ("phi", phi, 1, 8),
            ("omega", omega, 0, 7),
            ("reserved", reserved, 0, 8191),
        ] {
            if !(min..=max).contains(&value) {
                return Err(CanonicalError::FieldOutOfRange { field, value });
            }
        }
        if !radius.is_finite() || !(0.0..=1.0).contains(&radius) {
            return Err(CanonicalError::RadiusOutOfRange);
        }
        Ok(Self {
            theta: theta as u8,
            phi: phi as u8,
            omega: omega as u8,
            radius,
            reserved: reserved as u16,
        })
    }

    pub fn theta(self) -> u8 {
        self.theta
    }
    pub fn phi(self) -> u8 {
        self.phi
    }
    pub fn omega(self) -> u8 {
        self.omega
    }
    pub fn radius(self) -> f64 {
        self.radius
    }
    pub fn reserved(self) -> u16 {
        self.reserved
    }

    pub fn is_valid(self) -> bool {
        (1..=27).contains(&self.theta) && self.phi <= 6 && self.omega <= 4
    }

    pub fn is_reserved(self) -> bool {
        self.theta == 0 || self.theta >= 28 || self.phi >= 7 || self.omega >= 5
    }

    pub fn is_null(self) -> bool {
        self.theta == 0
    }
    pub fn is_wildcard(self) -> bool {
        self.theta == 31 || self.phi == 8 || self.omega == 7
    }
    pub fn sector(self) -> ThetaSector {
        ThetaSector::from_theta(self.theta)
    }

    pub fn to_word(self) -> u32 {
        let radius_encoded = quantize_radius(self.radius);
        ((self.theta as u32) << 27)
            | (((self.phi as u32) - 1) << 24)
            | ((self.omega as u32) << 21)
            | (radius_encoded << 13)
            | self.reserved as u32
    }

    pub fn to_int(self) -> u32 {
        self.to_word()
    }
    pub fn to_bytes(self) -> [u8; 4] {
        self.to_word().to_be_bytes()
    }
    pub fn to_be_bytes(self) -> [u8; 4] {
        self.to_bytes()
    }

    pub fn from_word(raw: u32) -> Self {
        Self {
            theta: ((raw >> 27) & 31) as u8,
            phi: (((raw >> 24) & 7) + 1) as u8,
            omega: ((raw >> 21) & 7) as u8,
            radius: ((raw >> 13) & 255) as f64 / 255.0,
            reserved: (raw & 8191) as u16,
        }
    }

    /// Python from_int masks its input; signed i64 inputs preserve that behavior.
    pub fn from_int(raw: i64) -> Self {
        Self::from_word(raw as u32)
    }

    pub fn from_bytes(bytes: &[u8]) -> Result<Self, CanonicalError> {
        let bytes: [u8; 4] = bytes
            .try_into()
            .map_err(|_| CanonicalError::InvalidByteLength)?;
        Ok(Self::from_word(u32::from_be_bytes(bytes)))
    }

    /// Write to a caller-provided formatter without requiring a heap.
    pub fn write_hex(self, output: &mut impl fmt::Write) -> fmt::Result {
        write!(output, "0x{:08X}", self.to_word())
    }

    #[cfg(feature = "alloc")]
    pub fn to_hex(self) -> String {
        format!("0x{:08X}", self.to_word())
    }

    /// Write to a caller-provided formatter without requiring a heap.
    pub fn write_uri(self, output: &mut impl fmt::Write) -> fmt::Result {
        write!(
            output,
            "spiral://θ:{}/φ:{}/h:{}/r:{:.2}",
            self.theta, self.phi, self.omega, self.radius
        )
    }

    #[cfg(feature = "alloc")]
    pub fn to_uri(self) -> String {
        format!(
            "spiral://θ:{}/φ:{}/h:{}/r:{:.2}",
            self.theta, self.phi, self.omega, self.radius
        )
    }

    /// Heap-free parser for ASCII numeric fields, retaining prefix semantics.
    /// The Unicode digit normalizing compatibility parser needs `alloc`.
    pub fn from_uri_ascii(uri: &str) -> Result<Self, CanonicalError> {
        let rest = uri
            .strip_prefix("spiral://θ:")
            .ok_or(CanonicalError::InvalidUri)?;
        let (theta, rest) = decimal_field_ascii(rest, 31)?;
        let rest = rest.strip_prefix("/φ:").ok_or(CanonicalError::InvalidUri)?;
        let (phi, rest) = decimal_field_ascii(rest, 8)?;
        let rest = rest.strip_prefix("/h:").ok_or(CanonicalError::InvalidUri)?;
        let (omega, rest) = decimal_field_ascii(rest, 7)?;
        let rest = rest.strip_prefix("/r:").ok_or(CanonicalError::InvalidUri)?;
        let length = rest
            .bytes()
            .take_while(|byte| byte.is_ascii_digit() || *byte == b'.')
            .count();
        // A non-ASCII decimal digit belongs to the numeric token in Python's
        // grammar. Reject it here instead of silently parsing a shorter value.
        if rest[length..]
            .chars()
            .next()
            .is_some_and(|character| decimal_digit(character).is_some())
        {
            return Err(CanonicalError::InvalidUri);
        }
        let radius = rest[..length]
            .parse::<f64>()
            .map_err(|_| CanonicalError::InvalidUri)?;
        Self::new(theta, phi, omega, radius, 0)
    }

    /// Prefix parser matching the shipped Python re.match, including suffixes.
    #[cfg(feature = "alloc")]
    pub fn from_uri(uri: &str) -> Result<Self, CanonicalError> {
        let rest = uri
            .strip_prefix("spiral://θ:")
            .ok_or(CanonicalError::InvalidUri)?;
        let (theta, rest) = decimal_field(rest, 31)?;
        let rest = rest.strip_prefix("/φ:").ok_or(CanonicalError::InvalidUri)?;
        let (phi, rest) = decimal_field(rest, 8)?;
        let rest = rest.strip_prefix("/h:").ok_or(CanonicalError::InvalidUri)?;
        let (omega, rest) = decimal_field(rest, 7)?;
        let rest = rest.strip_prefix("/r:").ok_or(CanonicalError::InvalidUri)?;
        let mut radius = String::new();
        for character in rest.chars() {
            if let Some(digit) = decimal_digit(character) {
                radius.push(char::from(b'0' + digit));
            } else if character == '.' {
                radius.push('.');
            } else {
                break;
            }
        }
        let radius = radius
            .parse::<f64>()
            .map_err(|_| CanonicalError::InvalidUri)?;
        Self::new(theta, phi, omega, radius, 0)
    }
}

// The validated radius is in 0..=1, so truncation gives a nonnegative floor.
// This preserves Python half-even at the exact binary64 product and requires
// neither std floating-point rounding methods nor a libm dependency.
fn quantize_radius(radius: f64) -> u32 {
    let scaled = radius * 255.0;
    let lower = scaled as u32;
    let fraction = scaled - lower as f64;
    if fraction > 0.5 || (fraction == 0.5 && lower & 1 != 0) {
        lower + 1
    } else {
        lower
    }
}

fn decimal_field_ascii(text: &str, maximum: i64) -> Result<(i64, &str), CanonicalError> {
    let mut value = 0_i64;
    let mut consumed = 0;
    for byte in text.bytes().take_while(u8::is_ascii_digit) {
        value = value
            .checked_mul(10)
            .and_then(|number| number.checked_add((byte - b'0') as i64))
            .ok_or(CanonicalError::InvalidUri)?;
        if value > maximum {
            return Err(CanonicalError::InvalidUri);
        }
        consumed += 1;
    }
    if consumed == 0 {
        return Err(CanonicalError::InvalidUri);
    }
    Ok((value, &text[consumed..]))
}

#[cfg(feature = "alloc")]
fn decimal_field(text: &str, maximum: i64) -> Result<(i64, &str), CanonicalError> {
    let mut value = 0_i64;
    let mut consumed = 0;
    for (offset, character) in text.char_indices() {
        let Some(digit) = decimal_digit(character) else {
            break;
        };
        value = value
            .checked_mul(10)
            .and_then(|n| n.checked_add(digit as i64))
            .ok_or(CanonicalError::InvalidUri)?;
        if value > maximum {
            return Err(CanonicalError::InvalidUri);
        }
        consumed = offset + character.len_utf8();
    }
    if consumed == 0 {
        return Err(CanonicalError::InvalidUri);
    }
    Ok((value, &text[consumed..]))
}

// Unicode 15.0.0 Nd zero codepoints, derived from Python's unicodedata.
// The corpus exercises every one of these decimal digit sets independently.
fn decimal_digit(character: char) -> Option<u8> {
    const ZERO: &[u32] = &[
        0x30, 0x660, 0x6f0, 0x7c0, 0x966, 0x9e6, 0xa66, 0xae6, 0xb66, 0xbe6, 0xc66, 0xce6, 0xd66,
        0xde6, 0xe50, 0xed0, 0xf20, 0x1040, 0x1090, 0x17e0, 0x1810, 0x1946, 0x19d0, 0x1a80, 0x1a90,
        0x1b50, 0x1bb0, 0x1c40, 0x1c50, 0xa620, 0xa8d0, 0xa900, 0xa9d0, 0xa9f0, 0xaa50, 0xabf0,
        0xff10, 0x104a0, 0x10d30, 0x11066, 0x110f0, 0x11136, 0x111d0, 0x112f0, 0x11450, 0x114d0,
        0x11650, 0x116c0, 0x11730, 0x118e0, 0x11950, 0x11c50, 0x11d50, 0x11da0, 0x11f50, 0x16a60,
        0x16ac0, 0x16b50, 0x1d7ce, 0x1d7d8, 0x1d7e2, 0x1d7ec, 0x1d7f6, 0x1e140, 0x1e2f0, 0x1e4f0,
        0x1e950, 0x1fbf0,
    ];
    let code = character as u32;
    ZERO.iter().find_map(|zero| {
        code.checked_sub(*zero)
            .filter(|value| *value < 10)
            .map(|value| value as u8)
    })
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MigrationPolicy {
    NeutralRadius,
    ShellProjection,
}

impl MigrationPolicy {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::NeutralRadius => "neutral-radius",
            Self::ShellProjection => "shell-projection",
        }
    }
}

impl FromStr for MigrationPolicy {
    type Err = CanonicalError;
    fn from_str(policy: &str) -> Result<Self, Self::Err> {
        match policy {
            "neutral-radius" => Ok(Self::NeutralRadius),
            "shell-projection" => Ok(Self::ShellProjection),
            _ => Err(CanonicalError::UnknownMigrationPolicy),
        }
    }
}

/// Lossy named projection; the policy argument has no default.
pub fn migrate_v1(
    shell: i64,
    theta: i64,
    phi: i64,
    harmonic: i64,
    policy: MigrationPolicy,
) -> Result<CanonicalAddress, CanonicalError> {
    for (field, value, maximum) in [
        ("shell", shell, 3),
        ("theta", theta, 511),
        ("phi", phi, 511),
        ("harmonic", harmonic, 255),
    ] {
        if !(0..=maximum).contains(&value) {
            return Err(CanonicalError::FieldOutOfRange { field, value });
        }
    }
    let radius = match policy {
        MigrationPolicy::NeutralRadius => 0.5,
        MigrationPolicy::ShellProjection => shell as f64 / 3.0,
    };
    CanonicalAddress::new(
        theta * 27 / 512 + 1,
        phi * 6 / 512 + 1,
        harmonic * 5 / 256,
        radius,
        0,
    )
}

#[cfg(test)]
mod codec_core_tests {
    use super::CanonicalAddress;
    use core::fmt;

    struct StackText {
        bytes: [u8; 96],
        length: usize,
    }

    impl StackText {
        fn new() -> Self {
            Self {
                bytes: [0; 96],
                length: 0,
            }
        }
        fn as_str(&self) -> &str {
            core::str::from_utf8(&self.bytes[..self.length]).unwrap()
        }
    }

    impl fmt::Write for StackText {
        fn write_str(&mut self, value: &str) -> fmt::Result {
            let end = self.length.checked_add(value.len()).ok_or(fmt::Error)?;
            if end > self.bytes.len() {
                return Err(fmt::Error);
            }
            self.bytes[self.length..end].copy_from_slice(value.as_bytes());
            self.length = end;
            Ok(())
        }
    }

    /// Failing mutation: shift a field, round every half away, or require a heap.
    /// This exact test also runs with default features and with none enabled.
    #[test]
    fn canonical_golden_bytes_and_ascii_uri_without_heap() {
        for (theta, phi, omega, radius, reserved, word, hexadecimal, uri) in [
            (
                1,
                1,
                0,
                0.0,
                0,
                0x0800_0000_u32,
                "0x08000000",
                "spiral://θ:1/φ:1/h:0/r:0.00",
            ),
            (
                14,
                3,
                2,
                0.5,
                0,
                0x7250_0000,
                "0x72500000",
                "spiral://θ:14/φ:3/h:2/r:0.50",
            ),
            (
                27,
                6,
                4,
                1.0,
                8191,
                0xdd9f_ffff,
                "0xDD9FFFFF",
                "spiral://θ:27/φ:6/h:4/r:1.00",
            ),
            (
                31,
                8,
                7,
                1.0,
                8191,
                0xffff_ffff,
                "0xFFFFFFFF",
                "spiral://θ:31/φ:8/h:7/r:1.00",
            ),
            (
                0,
                1,
                0,
                -0.0,
                0,
                0,
                "0x00000000",
                "spiral://θ:0/φ:1/h:0/r:-0.00",
            ),
        ] {
            let address = CanonicalAddress::new(theta, phi, omega, radius, reserved).unwrap();
            assert_eq!(address.to_bytes(), word.to_be_bytes());
            assert_eq!(
                CanonicalAddress::from_bytes(&word.to_be_bytes())
                    .unwrap()
                    .to_word(),
                word
            );
            let mut text = StackText::new();
            address.write_uri(&mut text).unwrap();
            assert_eq!(text.as_str(), uri);
            let mut hex_text = StackText::new();
            address.write_hex(&mut hex_text).unwrap();
            assert_eq!(hex_text.as_str(), hexadecimal);
        }
        for (radius, byte) in [(1.0 / 510.0, 0), (5.0 / 510.0, 2), (0.5, 128)] {
            let address = CanonicalAddress::new(1, 1, 0, radius, 0).unwrap();
            assert_eq!((address.to_word() >> 13) & 255, byte);
        }
        let parsed =
            CanonicalAddress::from_uri_ascii("spiral://θ:14/φ:3/h:2/r:0.50suffix").unwrap();
        assert_eq!(parsed.to_bytes(), 0x7250_0000_u32.to_be_bytes());
        assert!(CanonicalAddress::from_uri_ascii("spiral://θ:0/φ:1/h:0/r:-0.00").is_err());
        assert!(CanonicalAddress::from_uri_ascii("spiral://θ:١/φ:1/h:0/r:0.50").is_err());
        assert!(CanonicalAddress::from_uri_ascii("spiral://θ:1/φ:1/h:0/r:0.٥").is_err());
        for (suffix, expected_radius) in [
            (".5", 0.5),
            ("1.", 1.0),
            ("0.5e-1", 0.5),
            ("0.50/extra", 0.5),
        ] {
            let mut text = StackText::new();
            fmt::Write::write_fmt(&mut text, format_args!("spiral://θ:1/φ:1/h:0/r:{suffix}"))
                .unwrap();
            let parsed = CanonicalAddress::from_uri_ascii(text.as_str()).unwrap();
            assert_eq!(parsed.radius(), expected_radius);
        }
    }
}
