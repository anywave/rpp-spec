//! Experimental application policy, separate from every published RPP wire format.
//! No I/O, signing, key generation, persistence, clock or consent acquisition.
#![no_std]
#![forbid(unsafe_code)]

use ed25519_dalek::{Signature, VerifyingKey};
use rpp_core::mobius32::Mobius32Address;

const DOMAIN: &[u8; 16] = b"RPP-GATELIST-v1\0";
pub const MESSAGE_LEN: usize = 160;
pub const PACKET_LEN: usize = MESSAGE_LEN + 64;

/// A complete replacement of the 512 theta-sector grants; one bit per sector.
/// Signer is the public key identity, never a payload-selected trust root.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GateList {
    pub signer: [u8; 32],
    pub audience: [u8; 32],
    pub sequence: u64,
    /// Exclusive Unix-seconds deadline, from the host's trusted clock.
    pub expires_at: u64,
    pub grants: [u8; 64],
}

impl GateList {
    /// Exact domain-separated bytes to give an existing Ed25519 signer.
    pub fn message(&self) -> [u8; MESSAGE_LEN] {
        let mut bytes = [0; MESSAGE_LEN];
        bytes[..16].copy_from_slice(DOMAIN);
        bytes[16..48].copy_from_slice(&self.signer);
        bytes[48..80].copy_from_slice(&self.audience);
        bytes[80..88].copy_from_slice(&self.sequence.to_be_bytes());
        bytes[88..96].copy_from_slice(&self.expires_at.to_be_bytes());
        bytes[96..].copy_from_slice(&self.grants);
        bytes
    }

    pub fn packet(&self, signature: [u8; 64]) -> [u8; PACKET_LEN] {
        let mut bytes = [0; PACKET_LEN];
        bytes[..MESSAGE_LEN].copy_from_slice(&self.message());
        bytes[MESSAGE_LEN..].copy_from_slice(&signature);
        bytes
    }

    fn decode(bytes: &[u8]) -> Result<Self, Refusal> {
        if bytes.len() != PACKET_LEN || &bytes[..16] != DOMAIN {
            return Err(Refusal::Malformed);
        }
        // Exact length checked above; all slice conversions have fixed bounds.
        Ok(Self {
            signer: bytes[16..48].try_into().unwrap(),
            audience: bytes[48..80].try_into().unwrap(),
            sequence: u64::from_be_bytes(bytes[80..88].try_into().unwrap()),
            expires_at: u64::from_be_bytes(bytes[88..96].try_into().unwrap()),
            grants: bytes[96..160].try_into().unwrap(),
        })
    }
}

/// No Default implementation: hosts must select and display their policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Mode {
    Enforce,
    LogOnly,
}

impl Mode {
    pub const fn label(self) -> &'static str {
        match self {
            Self::Enforce => "enforce",
            Self::LogOnly => "log-only (admission refusals observed, not enforced)",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Refusal {
    Malformed,
    UnknownKey,
    WrongAudience,
    BadSignature,
    SequenceNotRising,
    Expired,
    ClockRollback,
    NoList,
    SectorDenied,
    NoConsent,
    AuditUnavailable,
}

/// An audit record emitted before the protected operation can run.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Admission {
    pub mode: Mode,
    pub refusal: Option<Refusal>,
    pub dispatched: bool,
    pub sequence: u64,
}

pub struct Request<'a> {
    /// If supplied, failure refuses THIS request in enforce mode, even if a
    /// prior list could admit it. Other requests retain the last good list.
    pub update: Option<&'a [u8]>,
    pub address: Mobius32Address,
    pub now: u64,
    /// Current host consent, checked independently even in log-only mode.
    pub consented: bool,
}

/// Host-owned state. Never serialize unverified input as a trusted checkpoint.
pub struct GateKeeper {
    pin: VerifyingKey,
    audience: [u8; 32],
    sequence: u64,
    last_now: u64,
    last_good: Option<GateList>,
    mode: Mode,
}

impl GateKeeper {
    /// The host supplies an independently provisioned pin and audience, and a
    /// durable sequence floor. After restart no list is active until updated.
    pub fn new(
        pin: [u8; 32],
        audience: [u8; 32],
        sequence_floor: u64,
        mode: Mode,
    ) -> Result<Self, Refusal> {
        let pin = VerifyingKey::from_bytes(&pin).map_err(|_| Refusal::UnknownKey)?;
        if pin.is_weak() {
            return Err(Refusal::UnknownKey);
        }
        Ok(Self {
            pin,
            audience,
            sequence: sequence_floor,
            last_now: 0,
            last_good: None,
            mode,
        })
    }

    pub const fn mode(&self) -> Mode {
        self.mode
    }

    pub const fn sequence(&self) -> u64 {
        self.sequence
    }

    pub const fn last_good(&self) -> Option<&GateList> {
        self.last_good.as_ref()
    }

    /// Validate completely before changing any state, in either mode.
    /// Host must durably checkpoint sequence() before allowing effects after an
    /// accepted update; this in-memory component cannot promise crash safety.
    pub fn update(&mut self, packet: &[u8], now: u64) -> Result<(), Refusal> {
        let list = GateList::decode(packet)?;
        if list.signer != self.pin.to_bytes() {
            return Err(Refusal::UnknownKey);
        }
        if list.audience != self.audience {
            return Err(Refusal::WrongAudience);
        }
        let signature = Signature::from_bytes(packet[MESSAGE_LEN..].try_into().unwrap());
        self.pin
            .verify_strict(&packet[..MESSAGE_LEN], &signature)
            .map_err(|_| Refusal::BadSignature)?;
        if list.sequence <= self.sequence {
            return Err(Refusal::SequenceNotRising);
        }
        if list.expires_at <= now {
            return Err(Refusal::Expired);
        }
        if now < self.last_now {
            return Err(Refusal::ClockRollback);
        }
        self.sequence = list.sequence;
        self.last_now = now;
        self.last_good = Some(list);
        Ok(())
    }

    fn check(&self, request: &Request<'_>) -> Result<(), Refusal> {
        if !request.consented {
            return Err(Refusal::NoConsent);
        }
        if request.now < self.last_now {
            return Err(Refusal::ClockRollback);
        }
        let list = self.last_good.as_ref().ok_or(Refusal::NoList)?;
        if list.expires_at <= request.now {
            return Err(Refusal::Expired);
        }
        let theta = usize::from(request.address.theta());
        if list.grants[theta / 8] & (1 << (theta % 8)) == 0 {
            return Err(Refusal::SectorDenied);
        }
        Ok(())
    }

    /// An actual call boundary: audit first, then call the operation only when
    /// this explicit mode permits it. A failing audit cannot start the operation.
    /// A host restoring a sequence floor must persist accepted updates itself.
    pub fn dispatch(
        &mut self,
        request: Request<'_>,
        audit: impl FnOnce(Admission) -> bool,
        operation: impl FnOnce(),
    ) -> Admission {
        let update_result = request
            .update
            .map_or(Ok(()), |p| self.update(p, request.now));
        let refusal = if !request.consented {
            Some(Refusal::NoConsent)
        } else {
            update_result.and_then(|()| self.check(&request)).err()
        };
        let dispatched = refusal.is_none()
            || (self.mode == Mode::LogOnly && refusal != Some(Refusal::NoConsent));
        let admission = Admission {
            mode: self.mode,
            refusal,
            dispatched,
            sequence: self.sequence,
        };
        if !audit(admission) {
            return Admission {
                refusal: Some(Refusal::AuditUnavailable),
                dispatched: false,
                ..admission
            };
        }
        if dispatched {
            if refusal.is_none() {
                self.last_now = request.now;
            }
            operation();
        }
        admission
    }
}
