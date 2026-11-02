//! Experimental billboard envelope; verification is supplied by the caller.
//! Decoding borrows the input and allocates nothing. Replay, authorization,
//! conflicts and application-time expiry remain the existing overlay policy.
#![no_std]
#![forbid(unsafe_code)]

#[cfg(feature = "alloc")]
extern crate alloc;

pub const VERSION: u8 = 1;
pub const HEADER_LEN: usize = 29;
pub const SIGNATURE_LEN: usize = 64;
/// Header + two 64-scalar UTF-8 identifiers + fact + receipt + signature.
pub const MAX_FRAME_LEN: usize = HEADER_LEN + 256 + 256 + 256 + 64 + SIGNATURE_LEN;
const MAGIC: &[u8; 4] = b"RPPB";
pub type Signature = [u8; SIGNATURE_LEN];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum Kind {
    Fact = 1,
    Rule = 2,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    Truncated,
    Oversize,
    BadMagic,
    UnsupportedVersion(u8),
    UnknownKind(u8),
    InvalidIdentifier,
    InvalidFact,
    InvalidReceipt,
    InvalidInterval,
    TrailingBytes,
    InvalidSignature,
    BufferTooSmall,
    TimeOutOfRange,
}

/// Outbound input is unverified and cannot construct a verified view.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Fields<'a> {
    pub machine: &'a str,
    pub kind: Kind,
    pub fact: &'a str,
    pub since: u64,
    pub until: u64,
    pub receipt: &'a str,
}

fn identifier(value: &str) -> bool {
    (1..=64).contains(&value.chars().count()) && value.len() <= 256
}

fn validate(fields: Fields<'_>, issuer: &str) -> Result<(), Error> {
    if !identifier(issuer) || !identifier(fields.machine) {
        return Err(Error::InvalidIdentifier);
    }
    if fields.fact.is_empty() || fields.fact.len() > 256 {
        return Err(Error::InvalidFact);
    }
    if !fields
        .fact
        .bytes()
        .all(|byte| (0x20..=0x7e).contains(&byte))
    {
        return Err(Error::InvalidFact);
    }
    if fields.receipt.is_empty()
        || fields.receipt.len() > 64
        || !fields
            .receipt
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"-_.".contains(&byte))
    {
        return Err(Error::InvalidReceipt);
    }
    if fields.since >= fields.until {
        return Err(Error::InvalidInterval);
    }
    Ok(())
}

fn write_fields(
    fields: Fields<'_>,
    issuer: &str,
    output: &mut [u8],
    signature: Option<&Signature>,
) -> Result<usize, Error> {
    validate(fields, issuer)?;
    let signed =
        HEADER_LEN + issuer.len() + fields.machine.len() + fields.fact.len() + fields.receipt.len();
    let total = signed
        + if signature.is_some() {
            SIGNATURE_LEN
        } else {
            0
        };
    if output.len() < total {
        return Err(Error::BufferTooSmall);
    }
    output[..4].copy_from_slice(MAGIC);
    output[4] = VERSION;
    output[5] = fields.kind as u8;
    output[6..8].copy_from_slice(&(issuer.len() as u16).to_be_bytes());
    output[8..10].copy_from_slice(&(fields.machine.len() as u16).to_be_bytes());
    output[10..12].copy_from_slice(&(fields.fact.len() as u16).to_be_bytes());
    output[12] = fields.receipt.len() as u8;
    output[13..21].copy_from_slice(&fields.since.to_be_bytes());
    output[21..29].copy_from_slice(&fields.until.to_be_bytes());
    let mut cursor = HEADER_LEN;
    for field in [issuer, fields.machine, fields.fact, fields.receipt] {
        output[cursor..cursor + field.len()].copy_from_slice(field.as_bytes());
        cursor += field.len();
    }
    if let Some(signature) = signature {
        output[signed..total].copy_from_slice(signature);
    }
    Ok(total)
}

/// Canonical bytes for the host's existing signing mechanism; no signing runs.
pub fn signing_bytes(fields: Fields<'_>, issuer: &str, output: &mut [u8]) -> Result<usize, Error> {
    write_fields(fields, issuer, output, None)
}

/// Require the same caller verification as decode before emitting a frame.
/// All errors leave the caller's output unchanged. This performs no signing.
pub fn encode<V: Verifier + ?Sized>(
    fields: Fields<'_>,
    issuer: &str,
    signature: &Signature,
    output: &mut [u8],
    verifier: &V,
) -> Result<usize, Error> {
    let mut frame = [0; MAX_FRAME_LEN];
    let size = write_fields(fields, issuer, &mut frame, Some(signature))?;
    if output.len() < size {
        return Err(Error::BufferTooSmall);
    }
    decode(&frame[..size], verifier)?;
    output[..size].copy_from_slice(&frame[..size]);
    Ok(size)
}

pub trait Verifier {
    fn verify(&self, issuer: &str, signing_bytes: &[u8], signature: &Signature) -> bool;
}

/// Only decode constructs this type. A successful verifier is not consent,
/// freshness, current membership or permission to interpret an agent rule.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct VerifiedBillboard<'a> {
    fields: Fields<'a>,
    issuer: &'a str,
    signing: &'a [u8],
    signature: &'a Signature,
}

impl<'a> VerifiedBillboard<'a> {
    pub const fn fields(&self) -> Fields<'a> {
        self.fields
    }
    pub const fn issuer(&self) -> &'a str {
        self.issuer
    }
    pub const fn signing_bytes(&self) -> &'a [u8] {
        self.signing
    }
    pub const fn signature(&self) -> &'a Signature {
        self.signature
    }
    #[cfg(feature = "alloc")]
    pub fn to_core(&self) -> rpp_core::overlay::Billboard {
        use alloc::string::ToString;
        rpp_core::overlay::Billboard {
            machine: self.fields.machine.to_string(),
            kind: match self.fields.kind {
                Kind::Fact => rpp_core::overlay::BillboardKind::Fact,
                Kind::Rule => rpp_core::overlay::BillboardKind::Rule,
            },
            fact: self.fields.fact.to_string(),
            since: i128::from(self.fields.since),
            until: i128::from(self.fields.until),
            receipt: self.fields.receipt.to_string(),
        }
    }
}

#[cfg(feature = "alloc")]
impl<'a> Fields<'a> {
    /// Refuse core-valid inputs outside the informative wire's narrower domain.
    pub fn from_core(board: &'a rpp_core::overlay::Billboard) -> Result<Self, Error> {
        let value = Self {
            machine: &board.machine,
            kind: match board.kind {
                rpp_core::overlay::BillboardKind::Fact => Kind::Fact,
                rpp_core::overlay::BillboardKind::Rule => Kind::Rule,
            },
            fact: &board.fact,
            since: u64::try_from(board.since).map_err(|_| Error::TimeOutOfRange)?,
            until: u64::try_from(board.until).map_err(|_| Error::TimeOutOfRange)?,
            receipt: &board.receipt,
        };
        validate(value, "fixture")?;
        Ok(value)
    }
}

pub fn decode<'a, V: Verifier + ?Sized>(
    input: &'a [u8],
    verifier: &V,
) -> Result<VerifiedBillboard<'a>, Error> {
    if input.len() < HEADER_LEN + SIGNATURE_LEN {
        return Err(Error::Truncated);
    }
    if input.len() > MAX_FRAME_LEN {
        return Err(Error::Oversize);
    }
    if &input[..4] != MAGIC {
        return Err(Error::BadMagic);
    }
    if input[4] != VERSION {
        return Err(Error::UnsupportedVersion(input[4]));
    }
    let kind = match input[5] {
        1 => Kind::Fact,
        2 => Kind::Rule,
        other => return Err(Error::UnknownKind(other)),
    };
    let issuer_len = usize::from(u16::from_be_bytes([input[6], input[7]]));
    let machine_len = usize::from(u16::from_be_bytes([input[8], input[9]]));
    let fact_len = usize::from(u16::from_be_bytes([input[10], input[11]]));
    let receipt_len = usize::from(input[12]);
    let mut end = HEADER_LEN;
    let mut ends = [0; 4];
    for (index, length) in [issuer_len, machine_len, fact_len, receipt_len]
        .iter()
        .enumerate()
    {
        end = end.checked_add(*length).ok_or(Error::Oversize)?;
        ends[index] = end;
    }
    let total = end.checked_add(SIGNATURE_LEN).ok_or(Error::Oversize)?;
    if input.len() < total {
        return Err(Error::Truncated);
    }
    if input.len() > total {
        return Err(Error::TrailingBytes);
    }
    let issuer =
        core::str::from_utf8(&input[HEADER_LEN..ends[0]]).map_err(|_| Error::InvalidIdentifier)?;
    let machine =
        core::str::from_utf8(&input[ends[0]..ends[1]]).map_err(|_| Error::InvalidIdentifier)?;
    let fact = core::str::from_utf8(&input[ends[1]..ends[2]]).map_err(|_| Error::InvalidFact)?;
    let receipt =
        core::str::from_utf8(&input[ends[2]..ends[3]]).map_err(|_| Error::InvalidReceipt)?;
    let fields = Fields {
        machine,
        kind,
        fact,
        since: u64::from_be_bytes(input[13..21].try_into().map_err(|_| Error::Truncated)?),
        until: u64::from_be_bytes(input[21..29].try_into().map_err(|_| Error::Truncated)?),
        receipt,
    };
    validate(fields, issuer)?;
    let signature = input[end..total].try_into().map_err(|_| Error::Truncated)?;
    let signing = &input[..end];
    if !verifier.verify(issuer, signing, signature) {
        return Err(Error::InvalidSignature);
    }
    Ok(VerifiedBillboard {
        fields,
        issuer,
        signing,
        signature,
    })
}
