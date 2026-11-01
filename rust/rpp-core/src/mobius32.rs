//! The separate Mobius32 address profile from the defensive publication.
//!
//! This profile uses shell `[31:30]`, theta `[29:21]`, phi `[20:12]`,
//! reserved-zero `[11:8]`, and harmonic `[7:0]`. It has no implicit conversion
//! to the Ra-Canonical-v2 profile. Integer inputs are rejected rather than
//! masked when they are outside their declared ranges.

use core::fmt;

const MBZ_MASK: u32 = 0x0000_0f00;

/// A validation failure in the Mobius32 profile.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Mobius32Error {
    /// A field is negative or exceeds its profile maximum.
    FieldOutOfRange {
        field: &'static str,
        value: i64,
        max: i64,
    },
    /// A supplied integer cannot represent an unsigned 32-bit word.
    WordOutOfRange { word: i64 },
    /// At least one reserved-zero bit `[11:8]` is set.
    NonzeroReservedBits { word: u32 },
}

impl fmt::Display for Mobius32Error {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::FieldOutOfRange { field, value, max } => {
                write!(formatter, "{field}={value} out of range 0..{max}")
            }
            Self::WordOutOfRange { word } => {
                write!(formatter, "word={word} is not an unsigned 32-bit value")
            }
            Self::NonzeroReservedBits { word } => {
                write!(
                    formatter,
                    "Mobius32 reserved bits [11:8] nonzero in 0x{word:08X}"
                )
            }
        }
    }
}

/// A validated Mobius32 address, distinct from every canonical address type.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub struct Mobius32Address {
    shell: u8,
    theta: u16,
    phi: u16,
    harmonic: u8,
}

impl Mobius32Address {
    /// Validate the four integer fields before constructing an address.
    ///
    /// The signed interface permits explicit rejection of negative fields.
    /// Rust's type system excludes floats, booleans and other non-integers.
    pub fn new(shell: i64, theta: i64, phi: i64, harmonic: i64) -> Result<Self, Mobius32Error> {
        for (field, value, max) in [
            ("shell", shell, 3),
            ("theta", theta, 511),
            ("phi", phi, 511),
            ("harmonic", harmonic, 255),
        ] {
            if value < 0 || value > max {
                return Err(Mobius32Error::FieldOutOfRange { field, value, max });
            }
        }
        Ok(Self {
            shell: shell as u8,
            theta: theta as u16,
            phi: phi as u16,
            harmonic: harmonic as u8,
        })
    }

    /// Validate an integer word, including its range and reserved-zero bits.
    pub fn from_word(word: i64) -> Result<Self, Mobius32Error> {
        if !(0..=i64::from(u32::MAX)).contains(&word) {
            return Err(Mobius32Error::WordOutOfRange { word });
        }
        Self::from_u32(word as u32)
    }

    /// Decode an unsigned word, rejecting any nonzero reserved bit.
    pub fn from_u32(word: u32) -> Result<Self, Mobius32Error> {
        if word & MBZ_MASK != 0 {
            return Err(Mobius32Error::NonzeroReservedBits { word });
        }
        Ok(Self {
            shell: ((word >> 30) & 0x3) as u8,
            theta: ((word >> 21) & 0x1ff) as u16,
            phi: ((word >> 12) & 0x1ff) as u16,
            harmonic: (word & 0xff) as u8,
        })
    }

    /// Encode validated fields. Reserved bits `[11:8]` are always zero.
    pub const fn to_u32(self) -> u32 {
        ((self.shell as u32) << 30)
            | ((self.theta as u32) << 21)
            | ((self.phi as u32) << 12)
            | (self.harmonic as u32)
    }

    pub const fn shell(self) -> u8 {
        self.shell
    }

    pub const fn theta(self) -> u16 {
        self.theta
    }

    pub const fn phi(self) -> u16 {
        self.phi
    }

    pub const fn harmonic(self) -> u8 {
        self.harmonic
    }

    pub const fn fields(self) -> (u8, u16, u16, u8) {
        (self.shell, self.theta, self.phi, self.harmonic)
    }
}

impl TryFrom<u32> for Mobius32Address {
    type Error = Mobius32Error;

    fn try_from(word: u32) -> Result<Self, Self::Error> {
        Self::from_u32(word)
    }
}

impl TryFrom<i64> for Mobius32Address {
    type Error = Mobius32Error;

    fn try_from(word: i64) -> Result<Self, Self::Error> {
        Self::from_word(word)
    }
}

impl From<Mobius32Address> for u32 {
    fn from(address: Mobius32Address) -> Self {
        address.to_u32()
    }
}

/// Convenience counterpart of the standalone Mobius32 golden encoder.
pub fn encode(shell: i64, theta: i64, phi: i64, harmonic: i64) -> Result<u32, Mobius32Error> {
    Mobius32Address::new(shell, theta, phi, harmonic).map(Mobius32Address::to_u32)
}

/// Convenience counterpart of the standalone Mobius32 golden decoder.
pub fn decode(word: i64) -> Result<(u8, u16, u16, u8), Mobius32Error> {
    Mobius32Address::from_word(word).map(Mobius32Address::fields)
}

#[cfg(test)]
mod tests {
    use super::*;

    const GOLDEN: [((i64, i64, i64, i64), u32); 4] = [
        ((1, 100, 170, 2), 0x4c8a_a002),
        ((1, 300, 170, 2), 0x658a_a002),
        ((3, 511, 511, 255), 0xffff_f0ff),
        ((0, 0, 0, 0), 0x0000_0000),
    ];

    /// Failing mutation: shift theta by 20 instead of 21 when packing.
    #[test]
    fn golden_vectors_encode() {
        for ((shell, theta, phi, harmonic), word) in GOLDEN {
            assert_eq!(encode(shell, theta, phi, harmonic), Ok(word));
        }
    }

    /// Failing mutation: extract phi from bit 13 instead of bit 12.
    #[test]
    fn golden_vectors_decode() {
        for ((shell, theta, phi, harmonic), word) in GOLDEN {
            assert_eq!(
                decode(i64::from(word)),
                Ok((shell as u8, theta as u16, phi as u16, harmonic as u8))
            );
        }
    }

    /// Failing mutation: mask overflowing fields or cast negative ones before validation.
    #[test]
    fn encode_rejects_out_of_range() {
        for (shell, theta, phi, harmonic) in [
            (4, 0, 0, 0),
            (-1, 0, 0, 0),
            (0, 512, 0, 0),
            (0, 999, 0, 0),
            (0, -1, 0, 0),
            (0, 0, 512, 0),
            (0, 0, -1, 0),
            (0, 0, 0, 256),
            (0, 0, 0, 4095),
            (0, 0, 0, -1),
        ] {
            assert!(encode(shell, theta, phi, harmonic).is_err());
        }
        for extreme in [i64::MIN, i64::MAX] {
            assert!(encode(extreme, 0, 0, 0).is_err());
            assert!(encode(0, extreme, 0, 0).is_err());
            assert!(encode(0, 0, extreme, 0).is_err());
            assert!(encode(0, 0, 0, extreme).is_err());
        }
    }

    /// Failing mutation: remove the reserved-zero guard or check fewer than four bits.
    #[test]
    fn nonzero_mbz_is_refused() {
        assert!(decode(0x4c8a_a102).is_err());
        for (_, word) in GOLDEN {
            for reserved_nibble in 1..=15_u32 {
                assert_eq!(
                    Mobius32Address::from_u32(word | (reserved_nibble << 8)),
                    Err(Mobius32Error::NonzeroReservedBits {
                        word: word | (reserved_nibble << 8)
                    })
                );
            }
        }
    }

    /// Failing mutation: overlap phi/theta or leak harmonic bits into the reserved nibble.
    #[test]
    fn round_trip_and_mbz_always_zero() {
        let edge = [0, 1, 2, 100, 255, 256, 300, 510, 511];
        let mut checked = 0;
        for shell in 0..=3 {
            for theta in edge {
                for phi in edge {
                    for harmonic in [0, 1, 2, 127, 128, 255] {
                        let address = Mobius32Address::new(shell, theta, phi, harmonic).unwrap();
                        let word = address.to_u32();
                        assert_eq!(word & MBZ_MASK, 0);
                        assert_eq!(Mobius32Address::from_u32(word), Ok(address));
                        assert_eq!(
                            decode(i64::from(word)),
                            Ok((shell as u8, theta as u16, phi as u16, harmonic as u8))
                        );
                        checked += 1;
                    }
                }
            }
        }
        assert_eq!(checked, 1944);
    }

    /// Failing mutation: truncate an out-of-range signed word to u32 before validation.
    #[test]
    fn decoder_rejects_outside_u32_word() {
        for word in [-1, i64::MIN, 0x1_0000_0000, i64::MAX] {
            assert_eq!(
                Mobius32Address::from_word(word),
                Err(Mobius32Error::WordOutOfRange { word })
            );
        }
        assert!(Mobius32Address::from_u32(u32::MAX).is_err());
        assert_eq!(Mobius32Address::from_u32(0x8000_0000).unwrap().shell(), 2);
    }

    /// Failing mutation: narrow theta/phi to eight bits or lose any shell/harmonic bit.
    #[test]
    fn round_trip_each_field_all_values_and_top_bit() {
        let mut checked = 0;
        for value in 0..=511 {
            for address in [
                Mobius32Address::new(3, value, 511, 255).unwrap(),
                Mobius32Address::new(3, 511, value, 255).unwrap(),
            ] {
                assert_eq!(Mobius32Address::from_u32(address.to_u32()), Ok(address));
                checked += 1;
            }
        }
        for value in 0..=255 {
            let address = Mobius32Address::new(3, 511, 511, value).unwrap();
            assert_eq!(Mobius32Address::from_u32(address.to_u32()), Ok(address));
            checked += 1;
        }
        for value in 0..=3 {
            let address = Mobius32Address::new(value, 511, 511, 255).unwrap();
            assert_eq!(Mobius32Address::from_u32(address.to_u32()), Ok(address));
            checked += 1;
        }
        assert_eq!(checked, 1284);
    }
}
