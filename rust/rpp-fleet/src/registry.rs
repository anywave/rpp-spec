//! In-memory explicit assignment registry. Registration grants no authority.
//!
//! Address and identity bindings are immutable after insertion. Only validated
//! endpoint replacement or reading updates may mutate transport metadata. Map
//! iteration is lexicographic over the complete identity, not address derivation.

use alloc::{
    collections::{BTreeMap, BTreeSet},
    vec::Vec,
};
use rpp_core::canonical::CanonicalAddress;
use rpp_link::LinkReading;

use crate::endpoint::{validate_reading, Endpoint};
use crate::identity::{lookup_binding, AddressBinding, AssignmentError, DeviceId, NodeIdentity};
use crate::limits::{MAX_ENDPOINTS_PER_NODE, MAX_NODES};

#[derive(Clone, Debug, PartialEq)]
pub struct RegisteredNode {
    binding: AddressBinding,
    endpoints: Vec<Endpoint>,
}

impl RegisteredNode {
    pub const fn identity(&self) -> NodeIdentity {
        self.binding.identity()
    }

    pub const fn device_id(&self) -> &DeviceId {
        self.binding.identity_ref().device_id()
    }

    pub const fn address(&self) -> CanonicalAddress {
        self.binding.address()
    }

    pub const fn binding(&self) -> &AddressBinding {
        &self.binding
    }

    pub fn endpoints(&self) -> &[Endpoint] {
        &self.endpoints
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegistryError {
    /// Local implementation node or per-node endpoint count limit exceeded.
    Capacity,
    InvalidAddress,
    DuplicateIdentity,
    DuplicateDeviceId,
    AddressCollision {
        word: u32,
    },
    InvalidEndpoint,
    DuplicateEndpointId,
    UnknownIdentity,
    UnknownEndpoint,
    InvalidReading,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct Registry {
    nodes: BTreeMap<NodeIdentity, RegisteredNode>,
    address_owners: BTreeMap<u32, NodeIdentity>,
    device_owners: BTreeMap<DeviceId, NodeIdentity>,
}

impl Registry {
    pub fn new() -> Self {
        Self::default()
    }

    /// Insert exactly one ordinary address and one control-device ID per full pair.
    /// Count limits are checked before endpoint validation or index changes.
    /// Errors leave all existing records and indices unchanged.
    pub fn register(
        &mut self,
        binding: AddressBinding,
        endpoints: Vec<Endpoint>,
    ) -> Result<&RegisteredNode, RegistryError> {
        if self.nodes.len() >= MAX_NODES {
            return Err(RegistryError::Capacity);
        }
        if endpoints.len() > MAX_ENDPOINTS_PER_NODE {
            return Err(RegistryError::Capacity);
        }
        let identity = binding.identity();
        let device_id = *identity.device_id();
        let word = binding.word();
        if !binding.address().is_valid() {
            return Err(RegistryError::InvalidAddress);
        }
        if self.nodes.contains_key(&identity) {
            return Err(RegistryError::DuplicateIdentity);
        }
        if self.device_owners.contains_key(&device_id) {
            return Err(RegistryError::DuplicateDeviceId);
        }
        if self.address_owners.contains_key(&word) {
            return Err(RegistryError::AddressCollision { word });
        }
        validate_endpoints(&endpoints)?;
        self.address_owners.insert(word, identity);
        self.device_owners.insert(device_id, identity);
        let node = self
            .nodes
            .entry(identity)
            .or_insert(RegisteredNode { binding, endpoints });
        Ok(node)
    }

    pub fn get(&self, identity: &NodeIdentity) -> Option<&RegisteredNode> {
        self.nodes.get(identity)
    }

    pub fn get_by_address(&self, word: u32) -> Option<&RegisteredNode> {
        self.address_owners
            .get(&word)
            .and_then(|identity| self.nodes.get(identity))
    }

    pub fn get_by_device_id(&self, device_id: &DeviceId) -> Option<&RegisteredNode> {
        self.device_owners
            .get(device_id)
            .and_then(|identity| self.nodes.get(identity))
    }

    pub fn iter(&self) -> impl Iterator<Item = (&NodeIdentity, &RegisteredNode)> {
        self.nodes.iter()
    }

    pub fn address(&self, identity: &NodeIdentity) -> Result<CanonicalAddress, AssignmentError> {
        lookup_binding(
            identity,
            self.nodes.get(identity).map(RegisteredNode::binding),
        )
    }

    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    pub fn update_reading(
        &mut self,
        identity: &NodeIdentity,
        endpoint_id: u32,
        reading: LinkReading,
    ) -> Result<(), RegistryError> {
        let node = self
            .nodes
            .get_mut(identity)
            .ok_or(RegistryError::UnknownIdentity)?;
        let endpoint = node
            .endpoints
            .iter_mut()
            .find(|endpoint| endpoint.id == endpoint_id)
            .ok_or(RegistryError::UnknownEndpoint)?;
        if validate_reading(reading).is_err() {
            return Err(RegistryError::InvalidReading);
        }
        endpoint.last_reading = reading;
        Ok(())
    }

    pub fn replace_endpoints(
        &mut self,
        identity: &NodeIdentity,
        endpoints: Vec<Endpoint>,
    ) -> Result<(), RegistryError> {
        if endpoints.len() > MAX_ENDPOINTS_PER_NODE {
            return Err(RegistryError::Capacity);
        }
        if !self.nodes.contains_key(identity) {
            return Err(RegistryError::UnknownIdentity);
        }
        validate_endpoints(&endpoints)?;
        let node = self
            .nodes
            .get_mut(identity)
            .ok_or(RegistryError::UnknownIdentity)?;
        node.endpoints = endpoints;
        Ok(())
    }
}

fn validate_endpoints(endpoints: &[Endpoint]) -> Result<(), RegistryError> {
    let mut ids = BTreeSet::new();
    for endpoint in endpoints {
        if !endpoint.valid() {
            return Err(RegistryError::InvalidEndpoint);
        }
        if !ids.insert(endpoint.id) {
            return Err(RegistryError::DuplicateEndpointId);
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::identity::AssignmentPolicy;

    fn binding(lender: u8, device: u8, theta: i64, radius: f64) -> AddressBinding {
        AddressBinding::new(
            NodeIdentity::new([lender; 16], [device; 16]),
            CanonicalAddress::new(theta, 1, 0, radius, 7).unwrap(),
            AssignmentPolicy::ExplicitCallerAssignmentV1,
        )
    }

    #[test]
    fn collisions_and_duplicate_insertions_preserve_existing_assignment() {
        // Failing mutation: overwrite an identity, encoded-word alias or device-ID owner.
        let mut registry = Registry::new();
        let first = binding(1, 2, 1, 0.0);
        registry.register(first, Vec::new()).unwrap();
        let before = registry.clone();
        assert_eq!(
            registry.register(first, Vec::new()),
            Err(RegistryError::DuplicateIdentity)
        );
        assert_eq!(registry, before);
        assert_eq!(
            registry.register(binding(3, 4, 1, 1.0 / 510.0), Vec::new()),
            Err(RegistryError::AddressCollision { word: first.word() })
        );
        assert_eq!(registry, before);
        assert_eq!(
            registry.register(binding(3, 2, 2, 0.0), Vec::new()),
            Err(RegistryError::DuplicateDeviceId)
        );
        assert_eq!(registry, before);
        assert_eq!(
            registry.address(&first.identity()).unwrap().to_word(),
            first.word()
        );
    }

    #[test]
    fn registry_uses_core_ordinary_validity_without_erasing_reserved_bytes() {
        // Failing mutation: allow null/wildcard fields or mask accepted reserved bits.
        let mut registry = Registry::new();
        for theta in [0, 31] {
            assert_eq!(
                registry.register(binding(1, 2, theta, 0.0), Vec::new()),
                Err(RegistryError::InvalidAddress)
            );
        }
        let ordinary = binding(1, 2, 1, 0.0);
        registry.register(ordinary, Vec::new()).unwrap();
        assert_eq!(
            registry.address(&ordinary.identity()).unwrap().reserved(),
            7
        );
    }
}
