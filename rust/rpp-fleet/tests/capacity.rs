//! Fixed fleet limits are checked before a registry operation can change owners.

#![cfg(feature = "alloc")]

use rpp_fleet::endpoint::{Endpoint, EndpointCapabilities, EndpointKind};
use rpp_fleet::identity::{AddressBinding, AssignmentPolicy, CanonicalFields, NodeIdentity};
use rpp_fleet::registry::{Registry, RegistryError};
use rpp_fleet::{MAX_ENDPOINTS_PER_NODE, MAX_NODES, MAX_URI_LEN};
use rpp_link::LinkReading;

fn identity(index: u8) -> NodeIdentity {
    let mut device = [0; 16];
    device[15] = index;
    NodeIdentity::new([0xa5; 16], device)
}

fn binding(index: u8) -> AddressBinding {
    AddressBinding::from_fields(
        identity(index),
        CanonicalFields {
            theta: i64::from(index),
            phi: 1,
            omega: 0,
            radius: 0.0,
            reserved: 0,
        },
        AssignmentPolicy::ExplicitCallerAssignmentV1,
    )
    .unwrap()
}

fn reading() -> LinkReading {
    LinkReading {
        latency_ms: 5,
        loss_ppm: 100,
        jitter_ms: 1,
        available: true,
        observed: 10,
    }
}

fn largest_valid_reading() -> LinkReading {
    LinkReading {
        latency_ms: u64::MAX - 1,
        loss_ppm: 1_000_000,
        jitter_ms: u64::MAX - 1,
        available: false,
        observed: u64::MAX,
    }
}

fn invalid_readings() -> [LinkReading; 3] {
    [
        LinkReading {
            loss_ppm: 1_000_001,
            ..reading()
        },
        LinkReading {
            latency_ms: u64::MAX,
            ..reading()
        },
        LinkReading {
            jitter_ms: u64::MAX,
            ..reading()
        },
    ]
}

fn endpoint(index: u32) -> Endpoint {
    Endpoint::new(
        index,
        EndpointKind::Lan,
        format!("lan://fixture-{index}"),
        reading(),
        EndpointCapabilities::default(),
    )
    .unwrap()
}

fn endpoints(count: usize) -> Vec<Endpoint> {
    (0..count).map(|index| endpoint(index as u32)).collect()
}

fn assert_binding_indices(registry: &Registry, binding: AddressBinding) {
    let node = registry.get(&binding.identity()).unwrap();
    assert_eq!(node.binding(), &binding);
    assert_eq!(registry.address(&binding.identity()), Ok(binding.address()));
    assert_eq!(
        registry.get_by_address(binding.word()).unwrap().identity(),
        binding.identity()
    );
    assert_eq!(
        registry
            .get_by_device_id(binding.identity().device_id())
            .unwrap()
            .identity(),
        binding.identity()
    );
}

/// Failing mutation: admit node 17, reject node 16, check duplicates before the full-node cap, or mutate an owner index on failure.
#[test]
fn exactly_sixteen_nodes_fit_and_seventeenth_rejection_preserves_all_registry_indices() {
    assert_eq!(MAX_NODES, 16);
    let mut registry = Registry::new();
    let mut accepted = Vec::new();
    for index in 1..=MAX_NODES {
        let assignment = binding(index as u8);
        registry.register(assignment, Vec::new()).unwrap();
        accepted.push(assignment);
    }
    assert_eq!(registry.len(), 16);
    let before = registry.clone();
    let seventeenth = binding(17);
    assert_eq!(
        registry.register(seventeenth, Vec::new()),
        Err(RegistryError::Capacity)
    );
    assert_eq!(registry, before);
    assert_eq!(
        registry.register(accepted[0], Vec::new()),
        Err(RegistryError::Capacity)
    );
    assert_eq!(registry, before);
    assert!(registry.get(&seventeenth.identity()).is_none());
    assert!(registry.get_by_address(seventeenth.word()).is_none());
    assert!(registry
        .get_by_device_id(seventeenth.identity().device_id())
        .is_none());
    for assignment in accepted {
        assert_binding_indices(&registry, assignment);
    }
}

/// Failing mutation: accept five endpoints, reject four, reserve owners before the endpoint cap, or truncate accepted URI metadata.
#[test]
fn registration_accepts_four_endpoints_and_five_is_an_atomic_capacity_error() {
    assert_eq!(MAX_ENDPOINTS_PER_NODE, 4);
    assert_eq!(MAX_URI_LEN, 192);
    let first = binding(1);
    let candidate = binding(2);
    let mut registry = Registry::new();
    let long_uri = format!("lan://{}", "x".repeat(MAX_URI_LEN - 6));
    assert_eq!(long_uri.len(), 192);
    let mut four = endpoints(MAX_ENDPOINTS_PER_NODE);
    four[3].uri = long_uri.clone();
    registry.register(first, four.clone()).unwrap();
    assert_eq!(
        registry.get(&first.identity()).unwrap().endpoints(),
        four.as_slice()
    );
    assert_eq!(
        registry.get(&first.identity()).unwrap().endpoints()[3].uri,
        long_uri
    );
    let before = registry.clone();
    assert_eq!(
        registry.register(candidate, endpoints(5)),
        Err(RegistryError::Capacity)
    );
    assert_eq!(registry, before);
    assert_eq!(
        registry.register(first, endpoints(5)),
        Err(RegistryError::Capacity)
    );
    assert_eq!(registry, before);
    assert!(registry.get(&candidate.identity()).is_none());
    assert!(registry.get_by_address(candidate.word()).is_none());
    assert!(registry
        .get_by_device_id(candidate.identity().device_id())
        .is_none());
    registry.register(candidate, endpoints(4)).unwrap();
    assert_binding_indices(&registry, first);
    assert_binding_indices(&registry, candidate);
}

/// Failing mutation: install five replacement endpoints before rejecting, reject exactly four, or change any binding/owner index.
#[test]
fn replacement_accepts_four_endpoints_and_five_keeps_the_entire_registry_unchanged() {
    let first = binding(1);
    let second = binding(2);
    let mut registry = Registry::new();
    registry.register(first, endpoints(1)).unwrap();
    registry.register(second, endpoints(1)).unwrap();
    let four = endpoints(4);
    registry
        .replace_endpoints(&first.identity(), four.clone())
        .unwrap();
    assert_eq!(
        registry.get(&first.identity()).unwrap().endpoints(),
        four.as_slice()
    );
    let before = registry.clone();
    assert_eq!(
        registry.replace_endpoints(&first.identity(), endpoints(5)),
        Err(RegistryError::Capacity)
    );
    assert_eq!(registry, before);
    assert_eq!(
        registry.replace_endpoints(&identity(17), endpoints(5)),
        Err(RegistryError::Capacity)
    );
    assert_eq!(registry, before);
    assert_binding_indices(&registry, first);
    assert_binding_indices(&registry, second);
    assert_eq!(
        registry.get(&second.identity()).unwrap().endpoints(),
        endpoints(1).as_slice()
    );
    registry
        .replace_endpoints(&first.identity(), endpoints(1))
        .unwrap();
    assert_binding_indices(&registry, first);
}

/// Failing mutation: trust a public Endpoint literal's loss/latency/jitter or reserve any registry owner before validating it.
#[test]
fn invalid_literal_readings_cannot_enter_through_initial_registration() {
    let first = binding(1);
    let candidate = binding(2);
    let mut registry = Registry::new();
    registry.register(first, endpoints(1)).unwrap();
    let before = registry.clone();
    for invalid in invalid_readings() {
        let mut literal = endpoint(0);
        literal.last_reading = invalid;
        assert_eq!(
            registry.register(candidate, vec![literal]),
            Err(RegistryError::InvalidEndpoint)
        );
        assert_eq!(registry, before);
    }
    let mut valid = endpoint(0);
    valid.last_reading = largest_valid_reading();
    registry.register(candidate, vec![valid.clone()]).unwrap();
    assert_eq!(
        registry.get(&candidate.identity()).unwrap().endpoints(),
        &[valid]
    );
    assert_binding_indices(&registry, candidate);
}

/// Failing mutation: replace old endpoints before checking literal loss/latency/jitter or change identity/address on a failed replacement.
#[test]
fn invalid_literal_readings_cannot_replace_existing_endpoints() {
    let assignment = binding(1);
    let mut registry = Registry::new();
    registry.register(assignment, endpoints(2)).unwrap();
    let before = registry.clone();
    for invalid in invalid_readings() {
        let mut literal = endpoint(0);
        literal.last_reading = invalid;
        assert_eq!(
            registry.replace_endpoints(&assignment.identity(), vec![literal]),
            Err(RegistryError::InvalidEndpoint)
        );
        assert_eq!(registry, before);
    }
    let mut valid = endpoint(0);
    valid.last_reading = largest_valid_reading();
    registry
        .replace_endpoints(&assignment.identity(), vec![valid.clone()])
        .unwrap();
    assert_eq!(
        registry.get(&assignment.identity()).unwrap().endpoints(),
        &[valid]
    );
    assert_binding_indices(&registry, assignment);
}

/// Failing mutation: accept invalid loss/latency/jitter on direct updates or change another endpoint/binding when rejecting an update.
#[test]
fn invalid_literal_reading_updates_are_atomic_and_valid_boundary_readings_are_preserved() {
    let assignment = binding(1);
    let mut registry = Registry::new();
    registry.register(assignment, endpoints(2)).unwrap();
    let before = registry.clone();
    for invalid in invalid_readings() {
        assert_eq!(
            registry.update_reading(&assignment.identity(), 0, invalid),
            Err(RegistryError::InvalidReading)
        );
        assert_eq!(registry, before);
    }
    registry
        .update_reading(&assignment.identity(), 0, largest_valid_reading())
        .unwrap();
    let node = registry.get(&assignment.identity()).unwrap();
    assert_eq!(node.endpoints()[0].last_reading, largest_valid_reading());
    assert_eq!(node.endpoints()[1], endpoint(1));
    assert_binding_indices(&registry, assignment);
}
