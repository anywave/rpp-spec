//! Identity inputs are opaque host data; explicit assignments confer no authority.

use core::fmt::{self, Write};
use rpp_core::canonical::CanonicalError;
use rpp_fleet::identity::{
    derive, AddressBinding, AssignmentError, AssignmentPolicy, CanonicalFields, NodeIdentity,
};

const POLICY: AssignmentPolicy = AssignmentPolicy::ExplicitCallerAssignmentV1;

fn fields(theta: i64, radius: f64, reserved: i64) -> CanonicalFields {
    CanonicalFields {
        theta,
        phi: 3,
        omega: 2,
        radius,
        reserved,
    }
}

fn identity(lender: u8, device: u8) -> NodeIdentity {
    NodeIdentity::new([lender; 16], [device; 16])
}

/// Failing mutations: hash identity into a default address, ignore the lender or device, or alter encoding.
#[test]
fn explicit_assignment_is_repeatable_unassigned_without_binding_and_checks_full_identity() {
    let identity = identity(17, 29);
    let assigned = AddressBinding::from_fields(identity, fields(14, 0.5, 17), POLICY).unwrap();
    assert_eq!(assigned.word(), 0x7250_0011);
    assert_eq!(assigned.policy(), POLICY);
    assert_eq!(POLICY.as_str(), "explicit-caller-assignment-v1");
    for _ in 0..3 {
        assert_eq!(derive(&identity, Some(&assigned)), Ok(assigned.address()));
        assert_eq!(derive(&identity, None), Err(AssignmentError::Unassigned));
    }
    let different_lender = NodeIdentity::new([18; 16], [29; 16]);
    let different_device = NodeIdentity::new([17; 16], [30; 16]);
    for other in [different_lender, different_device] {
        assert_eq!(
            derive(&other, Some(&assigned)),
            Err(AssignmentError::IdentityMismatch)
        );
    }
}

struct LabelBuffer {
    bytes: [u8; 64],
    used: usize,
}

impl LabelBuffer {
    fn new() -> Self {
        Self {
            bytes: [0; 64],
            used: 0,
        }
    }
}

impl Write for LabelBuffer {
    fn write_str(&mut self, value: &str) -> fmt::Result {
        let end = self.used.checked_add(value.len()).ok_or(fmt::Error)?;
        if end > self.bytes.len() {
            return Err(fmt::Error);
        }
        self.bytes[self.used..end].copy_from_slice(value.as_bytes());
        self.used = end;
        Ok(())
    }
}

/// Failing mutations: truncate, reorder, hash, zero-pad away, or skip any of the 32 opaque input bytes.
#[test]
fn opaque_full_identity_preserves_16_plus_16_bytes_and_64_hex_without_alloc() {
    let lender = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15];
    let device = [
        0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe,
        0xff,
    ];
    let identity = NodeIdentity::new(lender, device);
    assert_eq!(identity.lender_key_id(), &lender);
    assert_eq!(identity.device_id(), &device);
    let mut label = LabelBuffer::new();
    identity.write_label(&mut label).unwrap();
    assert_eq!(label.used, 64);
    assert_eq!(
        &label.bytes,
        b"000102030405060708090a0b0c0d0e0ff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff"
    );
    let mut display = LabelBuffer::new();
    write!(&mut display, "{identity}").unwrap();
    assert_eq!(display.bytes, label.bytes);
    assert_eq!(display.used, 64);
    for index in 0..16 {
        let mut changed_lender = lender;
        changed_lender[index] ^= 0x80;
        let mut changed_device = device;
        changed_device[index] ^= 0x80;
        assert_ne!(identity, NodeIdentity::new(changed_lender, device));
        assert_ne!(identity, NodeIdentity::new(lender, changed_device));
    }
    let opaque_zero = NodeIdentity::new([0; 16], [0; 16]);
    assert_eq!(opaque_zero.lender_key_id(), &[0; 16]);
    assert_eq!(opaque_zero.device_id(), &[0; 16]);
}

/// Failing mutations: silently clamp/default invalid fields or replace core half-even quantization.
#[test]
fn explicit_fields_reject_invalid_values_instead_of_defaulting_and_use_core_quantization() {
    let identity = identity(1, 2);
    let ordinary = fields(1, 0.0, 0);
    for invalid in [
        CanonicalFields {
            theta: -1,
            ..ordinary
        },
        CanonicalFields {
            theta: 32,
            ..ordinary
        },
        CanonicalFields { phi: 0, ..ordinary },
        CanonicalFields { phi: 9, ..ordinary },
        CanonicalFields {
            omega: -1,
            ..ordinary
        },
        CanonicalFields {
            omega: 8,
            ..ordinary
        },
        CanonicalFields {
            radius: f64::NAN,
            ..ordinary
        },
        CanonicalFields {
            radius: f64::INFINITY,
            ..ordinary
        },
        CanonicalFields {
            radius: f64::NEG_INFINITY,
            ..ordinary
        },
        CanonicalFields {
            radius: -0.01,
            ..ordinary
        },
        CanonicalFields {
            radius: 1.01,
            ..ordinary
        },
        CanonicalFields {
            reserved: -1,
            ..ordinary
        },
        CanonicalFields {
            reserved: 8192,
            ..ordinary
        },
    ] {
        assert!(matches!(
            AddressBinding::from_fields(identity, invalid, POLICY),
            Err(AssignmentError::Canonical(_))
        ));
    }
    assert_eq!(
        AddressBinding::from_fields(
            identity,
            CanonicalFields {
                radius: f64::NAN,
                ..ordinary
            },
            POLICY,
        ),
        Err(AssignmentError::Canonical(CanonicalError::RadiusOutOfRange))
    );
    for (radius, encoded) in [(1.0 / 510.0, 0), (5.0 / 510.0, 2), (0.5, 128)] {
        let binding =
            AddressBinding::from_fields(identity, CanonicalFields { radius, ..ordinary }, POLICY)
                .unwrap();
        assert_eq!((binding.word() >> 13) & 255, encoded);
    }
}

#[cfg(feature = "alloc")]
mod registry {
    use super::*;
    use rpp_fleet::endpoint::{Endpoint, EndpointCapabilities, EndpointKind};
    use rpp_fleet::registry::{Registry, RegistryError};
    use rpp_link::LinkReading;

    fn reading(latency: u64, observed: u64) -> LinkReading {
        LinkReading {
            latency_ms: latency,
            loss_ppm: 100,
            jitter_ms: 2,
            available: true,
            observed,
        }
    }

    fn endpoint(id: u32, latency: u64) -> Endpoint {
        Endpoint::new(
            id,
            EndpointKind::Lan,
            format!("lan://fixture-{id}"),
            reading(latency, 10),
            EndpointCapabilities {
                tunnel_verified: false,
                reviewed_adapter: false,
                observation_verified: false,
                control_capable: false,
                failure_domain: 0,
            },
        )
        .unwrap()
    }

    fn binding(lender: u8, device: u8, theta: i64, radius: f64, reserved: i64) -> AddressBinding {
        AddressBinding::from_fields(
            identity(lender, device),
            fields(theta, radius, reserved),
            POLICY,
        )
        .unwrap()
    }

    /// Failing mutation: overwrite a full identity or reserve the rejected replacement's new word.
    #[test]
    fn duplicate_full_identity_is_rejected_without_changing_assignment_or_indices() {
        let first = binding(1, 2, 1, 0.0, 1);
        let replacement = binding(1, 2, 2, 1.0, 2);
        let mut registry = Registry::new();
        registry.register(first, vec![endpoint(10, 10)]).unwrap();
        let before = registry.clone();
        assert_eq!(
            registry.register(replacement, vec![endpoint(20, 20)]),
            Err(RegistryError::DuplicateIdentity)
        );
        assert_eq!(registry, before);
        assert_eq!(registry.address(&first.identity()), Ok(first.address()));
        assert!(registry.get_by_address(replacement.word()).is_none());
        let other = binding(3, 4, 2, 1.0, 2);
        registry.register(other, vec![endpoint(20, 20)]).unwrap();
        assert_eq!(registry.len(), 2);
    }

    /// Failing mutation: scope device ownership by lender or overwrite the original control-device owner.
    #[test]
    fn same_device_id_across_different_lenders_is_globally_rejected_atomically() {
        let first = binding(1, 9, 1, 0.0, 0);
        let same_device = binding(2, 9, 2, 0.0, 0);
        let mut registry = Registry::new();
        registry.register(first, vec![endpoint(10, 10)]).unwrap();
        let before = registry.clone();
        assert_eq!(
            registry.register(same_device, vec![endpoint(20, 20)]),
            Err(RegistryError::DuplicateDeviceId)
        );
        assert_eq!(registry, before);
        assert!(registry.get(&same_device.identity()).is_none());
        assert!(registry.get_by_address(same_device.word()).is_none());
        assert_eq!(
            registry
                .get_by_device_id(first.identity().device_id())
                .unwrap()
                .identity(),
            first.identity()
        );
    }

    /// Failing mutation: compare floating-point address fields instead of the global encoded word.
    #[test]
    fn radius_quantization_aliases_cannot_claim_the_same_global_address_word() {
        let first = binding(1, 2, 14, 0.5, 5);
        let alias = binding(3, 4, 14, 0.5001, 5);
        assert_ne!(first.address(), alias.address());
        assert_eq!(first.word(), alias.word());
        let mut registry = Registry::new();
        registry.register(first, Vec::new()).unwrap();
        let before = registry.clone();
        assert_eq!(
            registry.register(alias, Vec::new()),
            Err(RegistryError::AddressCollision { word: first.word() })
        );
        assert_eq!(registry, before);
        assert_eq!(
            registry.get_by_address(first.word()).unwrap().identity(),
            first.identity()
        );
        let different_reserved_bits = binding(3, 4, 14, 0.5001, 6);
        registry
            .register(different_reserved_bits, Vec::new())
            .unwrap();
        assert_eq!(registry.len(), 2);
    }

    /// Failing mutation: admit null/reserved profile states or erase an ordinary address's low 13 bits.
    #[test]
    fn registry_rejects_reserved_profiles_while_preserving_ordinary_reserved_bits() {
        let ordinary = fields(1, 0.0, 0);
        let mut registry = Registry::new();
        for invalid_profile in [
            CanonicalFields {
                theta: 0,
                ..ordinary
            },
            CanonicalFields {
                theta: 28,
                ..ordinary
            },
            CanonicalFields {
                theta: 31,
                ..ordinary
            },
            CanonicalFields { phi: 7, ..ordinary },
            CanonicalFields { phi: 8, ..ordinary },
            CanonicalFields {
                omega: 5,
                ..ordinary
            },
            CanonicalFields {
                omega: 7,
                ..ordinary
            },
        ] {
            let invalid =
                AddressBinding::from_fields(identity(1, 2), invalid_profile, POLICY).unwrap();
            assert_eq!(
                registry.register(invalid, Vec::new()),
                Err(RegistryError::InvalidAddress)
            );
            assert!(registry.is_empty());
        }
        let valid = AddressBinding::from_fields(
            identity(1, 2),
            CanonicalFields {
                theta: 27,
                phi: 6,
                omega: 4,
                radius: 1.0,
                reserved: 8191,
            },
            POLICY,
        )
        .unwrap();
        registry.register(valid, Vec::new()).unwrap();
        let stored = registry.get(&valid.identity()).unwrap();
        assert_eq!(stored.address().reserved(), 8191);
        assert_eq!(stored.binding(), &valid);
        assert_eq!(stored.address().to_word(), valid.word());
        assert_eq!(
            registry.get_by_address(valid.word()).unwrap().identity(),
            valid.identity()
        );
    }

    /// Failing mutation: insert indices before endpoint validation or accept duplicate/invalid endpoint metadata.
    #[test]
    fn failed_registration_with_invalid_endpoints_leaves_all_owners_unchanged() {
        let existing = binding(1, 2, 1, 0.0, 0);
        let candidate = binding(3, 4, 2, 0.0, 0);
        let mut registry = Registry::new();
        registry.register(existing, vec![endpoint(10, 10)]).unwrap();
        let before = registry.clone();
        let mut invalid_uri = endpoint(20, 20);
        invalid_uri.uri.clear();
        let mut invalid_reading = endpoint(20, 20);
        invalid_reading.last_reading.loss_ppm = 1_000_001;
        for invalid in [vec![invalid_uri], vec![invalid_reading]] {
            assert_eq!(
                registry.register(candidate, invalid),
                Err(RegistryError::InvalidEndpoint)
            );
            assert_eq!(registry, before);
        }
        assert_eq!(
            registry.register(candidate, vec![endpoint(20, 20), endpoint(20, 30)]),
            Err(RegistryError::DuplicateEndpointId)
        );
        assert_eq!(registry, before);
        assert!(registry.get(&candidate.identity()).is_none());
        assert!(registry
            .get_by_device_id(candidate.identity().device_id())
            .is_none());
        assert!(registry.get_by_address(candidate.word()).is_none());
        registry
            .register(candidate, vec![endpoint(20, 20)])
            .unwrap();
        assert_eq!(registry.len(), 2);
    }

    /// Failing mutation: reject cross-node endpoint-ID reuse or accept duplicates inside one node.
    #[test]
    fn endpoint_ids_are_per_node_and_duplicate_errors_preserve_both_nodes() {
        let first = binding(1, 2, 1, 0.0, 0);
        let second = binding(3, 4, 2, 0.0, 0);
        let third = binding(5, 6, 3, 0.0, 0);
        let mut registry = Registry::new();
        registry.register(first, vec![endpoint(10, 10)]).unwrap();
        registry.register(second, vec![endpoint(10, 20)]).unwrap();
        let before = registry.clone();
        assert_eq!(
            registry.register(third, vec![endpoint(10, 30), endpoint(10, 40)]),
            Err(RegistryError::DuplicateEndpointId)
        );
        assert_eq!(registry, before);
        assert_eq!(
            registry
                .replace_endpoints(&second.identity(), vec![endpoint(10, 30), endpoint(10, 40)]),
            Err(RegistryError::DuplicateEndpointId)
        );
        assert_eq!(registry, before);
        registry
            .replace_endpoints(&second.identity(), vec![endpoint(10, 25), endpoint(20, 30)])
            .unwrap();
        assert_eq!(
            registry.get(&first.identity()).unwrap().endpoints()[0],
            endpoint(10, 10)
        );
        assert_eq!(registry.address(&second.identity()), Ok(second.address()));
        registry
            .replace_endpoints(&second.identity(), vec![endpoint(20, 35)])
            .unwrap();
        registry.register(third, vec![endpoint(10, 40)]).unwrap();
        assert_eq!(
            registry.get(&third.identity()).unwrap().endpoints()[0].id,
            10
        );
        assert_eq!(registry.len(), 3);
    }

    /// Failing mutation: overwrite old endpoints before validating all replacements or reassign identity/address.
    #[test]
    fn invalid_endpoint_replacements_preserve_the_full_existing_record() {
        let binding = binding(1, 2, 1, 0.5, 17);
        let mut registry = Registry::new();
        registry
            .register(binding, vec![endpoint(10, 10), endpoint(20, 20)])
            .unwrap();
        let before = registry.clone();
        assert_eq!(
            registry.replace_endpoints(
                &binding.identity(),
                vec![endpoint(30, 30), endpoint(30, 40)]
            ),
            Err(RegistryError::DuplicateEndpointId)
        );
        assert_eq!(registry, before);
        let mut invalid = endpoint(30, 30);
        invalid.uri.clear();
        assert_eq!(
            registry.replace_endpoints(&binding.identity(), vec![invalid]),
            Err(RegistryError::InvalidEndpoint)
        );
        assert_eq!(registry, before);
        assert_eq!(
            registry.replace_endpoints(&identity(8, 9), Vec::new()),
            Err(RegistryError::UnknownIdentity)
        );
        assert_eq!(registry, before);
        registry
            .replace_endpoints(&binding.identity(), vec![endpoint(30, 30)])
            .unwrap();
        let node = registry.get(&binding.identity()).unwrap();
        assert_eq!(node.binding(), &binding);
        assert_eq!(node.identity(), binding.identity());
        assert_eq!(node.device_id(), binding.identity().device_id());
        assert_eq!(node.endpoints(), &[endpoint(30, 30)]);
    }

    /// Failing mutation: change an address on reading update, update another endpoint, or accept invalid loss.
    #[test]
    fn reading_updates_change_only_the_named_endpoint_and_never_the_assignment() {
        let first = binding(1, 2, 1, 0.5, 17);
        let second = binding(3, 4, 2, 0.0, 0);
        let mut registry = Registry::new();
        registry
            .register(first, vec![endpoint(10, 10), endpoint(20, 20)])
            .unwrap();
        registry.register(second, vec![endpoint(10, 30)]).unwrap();
        let changed = LinkReading {
            available: false,
            loss_ppm: 1_000_000,
            ..reading(75, 99)
        };
        registry
            .update_reading(&first.identity(), 10, changed)
            .unwrap();
        let node = registry.get(&first.identity()).unwrap();
        assert_eq!(node.endpoints()[0].last_reading, changed);
        assert_eq!(node.endpoints()[1], endpoint(20, 20));
        assert_eq!(
            registry.get(&second.identity()).unwrap().endpoints()[0],
            endpoint(10, 30)
        );
        assert_eq!(node.binding(), &first);
        assert_eq!(registry.address(&first.identity()), Ok(first.address()));
        let before_errors = registry.clone();
        assert_eq!(
            registry.update_reading(
                &first.identity(),
                10,
                LinkReading {
                    loss_ppm: 1_000_001,
                    ..changed
                }
            ),
            Err(RegistryError::InvalidReading)
        );
        assert_eq!(registry, before_errors);
        assert_eq!(
            registry.update_reading(&first.identity(), 999, changed),
            Err(RegistryError::UnknownEndpoint)
        );
        assert_eq!(registry, before_errors);
        assert_eq!(
            registry.update_reading(&identity(8, 9), 10, changed),
            Err(RegistryError::UnknownIdentity)
        );
        assert_eq!(registry, before_errors);
    }

    /// Failing mutation: iterate by insertion order or by a truncated/encoded identity key.
    #[test]
    fn registry_iteration_is_deterministic_over_the_complete_identity() {
        let entries = [
            binding(2, 1, 1, 0.0, 0),
            binding(1, 3, 2, 0.0, 0),
            binding(1, 2, 3, 0.0, 0),
        ];
        let mut forward = Registry::new();
        let mut reverse = Registry::new();
        for binding in entries {
            forward.register(binding, Vec::new()).unwrap();
        }
        for binding in entries.into_iter().rev() {
            reverse.register(binding, Vec::new()).unwrap();
        }
        let expected = vec![
            entries[2].identity(),
            entries[1].identity(),
            entries[0].identity(),
        ];
        assert_eq!(
            forward
                .iter()
                .map(|(identity, _)| *identity)
                .collect::<Vec<_>>(),
            expected
        );
        assert_eq!(
            reverse
                .iter()
                .map(|(identity, _)| *identity)
                .collect::<Vec<_>>(),
            expected
        );
        for binding in entries {
            assert_eq!(forward.address(&binding.identity()), Ok(binding.address()));
            assert_eq!(reverse.address(&binding.identity()), Ok(binding.address()));
        }
    }
}
