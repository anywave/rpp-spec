//! Opaque fleet identity and an explicit caller-assignment proposal.
//!
//! No specification rule derives a compact canonical address from these bytes.
//! The full pair is retained; it is not NETWORK's hashed public-key NodeRecord ID.
//! Assignment depends on an owner-supplied binding and delegates encoding to
//! rpp-core. It establishes no ownership, membership, consent or global uniqueness.

#[cfg(feature = "alloc")]
use alloc::{format, string::String};
use core::fmt;
use rpp_core::canonical::{CanonicalAddress, CanonicalError};

pub type LenderKeyId = [u8; 16];
pub type DeviceId = [u8; 16];

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub struct NodeIdentity {
    lender_key_id: LenderKeyId,
    device_id: DeviceId,
}

impl NodeIdentity {
    pub const fn new(lender_key_id: LenderKeyId, device_id: DeviceId) -> Self {
        Self {
            lender_key_id,
            device_id,
        }
    }

    pub const fn lender_key_id(&self) -> &LenderKeyId {
        &self.lender_key_id
    }

    pub const fn device_id(&self) -> &DeviceId {
        &self.device_id
    }

    /// Reversible 64-lowercase-hex label: lender bytes followed by device bytes.
    pub fn write_label(&self, output: &mut impl fmt::Write) -> fmt::Result {
        for byte in self.lender_key_id.iter().chain(self.device_id.iter()) {
            write!(output, "{byte:02x}")?;
        }
        Ok(())
    }

    #[cfg(feature = "alloc")]
    pub fn label(&self) -> String {
        format!("{self}")
    }
}

impl fmt::Display for NodeIdentity {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.write_label(output)
    }
}

/// Informative proposal only; callers must explicitly select the assignment mode.
/// There is deliberately no Default or identity-only projection/hash policy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AssignmentPolicy {
    ExplicitCallerAssignmentV1,
}

impl AssignmentPolicy {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ExplicitCallerAssignmentV1 => "explicit-caller-assignment-v1",
        }
    }
}

/// Caller-supplied fields; validation and quantization belong to rpp-core.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct CanonicalFields {
    pub theta: i64,
    pub phi: i64,
    pub omega: i64,
    pub radius: f64,
    pub reserved: i64,
}

impl CanonicalFields {
    pub fn to_address(self) -> Result<CanonicalAddress, CanonicalError> {
        CanonicalAddress::new(self.theta, self.phi, self.omega, self.radius, self.reserved)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AssignmentError {
    Unassigned,
    IdentityMismatch,
    Canonical(CanonicalError),
}

impl fmt::Display for AssignmentError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Unassigned => output.write_str("identity has no explicit address assignment"),
            Self::IdentityMismatch => {
                output.write_str("assignment belongs to another full identity")
            }
            Self::Canonical(error) => error.fmt(output),
        }
    }
}

impl core::error::Error for AssignmentError {}

impl From<CanonicalError> for AssignmentError {
    fn from(error: CanonicalError) -> Self {
        Self::Canonical(error)
    }
}

/// Immutable association with an existing core-accepted canonical value.
/// Registry admission additionally requires core's ordinary-address predicate.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct AddressBinding {
    identity: NodeIdentity,
    address: CanonicalAddress,
    policy: AssignmentPolicy,
}

impl AddressBinding {
    pub const fn new(
        identity: NodeIdentity,
        address: CanonicalAddress,
        policy: AssignmentPolicy,
    ) -> Self {
        Self {
            identity,
            address,
            policy,
        }
    }

    pub fn from_fields(
        identity: NodeIdentity,
        fields: CanonicalFields,
        policy: AssignmentPolicy,
    ) -> Result<Self, AssignmentError> {
        Ok(Self::new(identity, fields.to_address()?, policy))
    }

    pub fn from_word(identity: NodeIdentity, word: u32, policy: AssignmentPolicy) -> Self {
        Self::new(identity, CanonicalAddress::from_word(word), policy)
    }

    pub const fn identity(&self) -> NodeIdentity {
        self.identity
    }

    pub const fn identity_ref(&self) -> &NodeIdentity {
        &self.identity
    }

    pub const fn address(&self) -> CanonicalAddress {
        self.address
    }

    pub fn word(&self) -> u32 {
        self.address.to_word()
    }

    pub const fn policy(&self) -> AssignmentPolicy {
        self.policy
    }
}

/// Deterministic explicit binding lookup, never a context-free identity hash.
/// A successful value is not proof of ownership, authorization or routability.
pub fn derive(
    identity: &NodeIdentity,
    binding: Option<&AddressBinding>,
) -> Result<CanonicalAddress, AssignmentError> {
    let binding = binding.ok_or(AssignmentError::Unassigned)?;
    if binding.identity != *identity {
        return Err(AssignmentError::IdentityMismatch);
    }
    Ok(binding.address)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn explicit_binding_preserves_core_encoding_and_checks_full_identity() {
        // Failing mutation: use device ID alone or invent an identity-only projection.
        let identity = NodeIdentity::new([1; 16], [2; 16]);
        let address = CanonicalAddress::new(14, 3, 2, 0.5, 9).unwrap();
        let binding = AddressBinding::new(
            identity,
            address,
            AssignmentPolicy::ExplicitCallerAssignmentV1,
        );
        assert_eq!(
            derive(&identity, Some(&binding)).unwrap().to_word(),
            address.to_word()
        );
        assert_eq!(derive(&identity, None), Err(AssignmentError::Unassigned));
        let other_lender = NodeIdentity::new([3; 16], [2; 16]);
        assert_eq!(
            derive(&other_lender, Some(&binding)),
            Err(AssignmentError::IdentityMismatch)
        );
        assert_eq!(binding.policy().as_str(), "explicit-caller-assignment-v1");
    }

    #[test]
    fn explicit_fields_use_core_validation_and_half_even_quantization() {
        // Failing mutation: replace core validation/rounding with a local rule.
        let identity = NodeIdentity::new([1; 16], [2; 16]);
        let fields = CanonicalFields {
            theta: 1,
            phi: 1,
            omega: 0,
            radius: 5.0 / 510.0,
            reserved: 0,
        };
        let binding = AddressBinding::from_fields(
            identity,
            fields,
            AssignmentPolicy::ExplicitCallerAssignmentV1,
        )
        .unwrap();
        assert_eq!((binding.word() >> 13) & 255, 2);
        let invalid = CanonicalFields {
            radius: f64::NAN,
            ..fields
        };
        assert_eq!(
            AddressBinding::from_fields(
                identity,
                invalid,
                AssignmentPolicy::ExplicitCallerAssignmentV1
            ),
            Err(AssignmentError::Canonical(CanonicalError::RadiusOutOfRange))
        );
    }
}
