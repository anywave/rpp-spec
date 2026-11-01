#![allow(dead_code)]

use rpp_control::{
    decode, ControlFrame, ControlKind, NodeId, Signature, VerifiedControlFrame, Verifier,
    HEADER_LEN,
};
use rpp_core::{canonical::CanonicalAddress, overlay::Auth};
use rpp_fleet::{
    endpoint::{Endpoint, EndpointCapabilities, EndpointKind},
    identity::{AddressBinding, AssignmentPolicy, NodeIdentity},
    registry::Registry,
    resolver::FleetResolver,
};
use rpp_link::LinkReading;

pub fn source() -> NodeIdentity {
    NodeIdentity::new([0x11; 16], [1; 16])
}

pub fn target() -> NodeIdentity {
    NodeIdentity::new([0x22; 16], [2; 16])
}

pub fn reading(latency_ms: u64, observed: u64) -> LinkReading {
    LinkReading {
        latency_ms,
        loss_ppm: 0,
        jitter_ms: 0,
        available: true,
        observed,
    }
}

pub fn endpoint(id: u32, kind: EndpointKind, latency: u64, tick: u64) -> Endpoint {
    Endpoint::new(
        id,
        kind,
        if kind == EndpointKind::Ble {
            "bt://fixture/control"
        } else {
            "ipv4://192.0.2.1:9000/rpp"
        },
        reading(latency, tick),
        EndpointCapabilities {
            tunnel_verified: true,
            reviewed_adapter: false,
            observation_verified: true,
            control_capable: true,
            failure_domain: if kind == EndpointKind::Ble { 2 } else { 1 },
        },
    )
    .unwrap()
}

pub fn binding(identity: NodeIdentity, theta: i64) -> AddressBinding {
    AddressBinding::new(
        identity,
        CanonicalAddress::new(theta, 1, 0, 0.0, 0).unwrap(),
        AssignmentPolicy::ExplicitCallerAssignmentV1,
    )
}

pub fn registry(endpoints: Vec<Endpoint>) -> Registry {
    let mut result = Registry::new();
    result.register(binding(source(), 1), Vec::new()).unwrap();
    result.register(binding(target(), 2), endpoints).unwrap();
    result
}

pub fn resolver(registry: &mut Registry) -> FleetResolver<'_> {
    FleetResolver::new(
        registry,
        source(),
        Auth::fixture(&source().label(), true),
        &[source(), target()],
        &[(source(), target()), (target(), source())],
    )
}

/// Exact literal fixture recognition; this performs no cryptography.
struct LiteralVerifier {
    header: [u8; HEADER_LEN],
    signature: Signature,
}

impl Verifier for LiteralVerifier {
    fn verify(&self, sender: &NodeId, header: &[u8; HEADER_LEN], signature: &Signature) -> bool {
        header == &self.header
            && signature == &self.signature
            && sender.as_slice() == &self.header[16..32]
    }
}

pub fn verified(sequence: u64) -> VerifiedControlFrame {
    let signature = [0xa5; 64];
    let frame = ControlFrame::new(
        ControlKind::Stop,
        sequence,
        *source().device_id(),
        *target().device_id(),
        signature,
    );
    decode(
        &frame.encode(),
        target().device_id(),
        &LiteralVerifier {
            header: frame.header(),
            signature,
        },
    )
    .unwrap()
}
