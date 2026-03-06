"""
RPP - Rotational Packet Protocol

Two-layer addressing and routing implementation.

Layers:
    Semantic Interface (v1.0): address, resolver — Shell/Theta/Phi/Harmonic
    Transport/Resonance (v2.0): address_canonical — Ra-derived θ/φ/h/r

Geometry & Routing:
    geometry:   Toroidal State Vector, Rasengan/Skyrmion encryption
    continuity: Ford Protocol, ConsciousnessStatePacket
    network:    Consent-field mesh, node tiers, routing algorithm

See spec/ADDRESSING-LAYERS.md for the full two-layer architecture.
"""

from rpp.address_canonical import (
    RPPAddress,
    ThetaSector,
    RACBand,
    OmegaTier,
    create_address,
    create_from_sector,
    address_distance,
    coherence,
    same_sector,
    adjacent_sectors,
    compute_fallback,
    verify_roundtrip,
    verify_ra_alignment,
)

from rpp.consent_header import (
    ConsentPacketHeader,
    ConsentState,
    AncestralConsent,
    PayloadType,
    SpiralPacket,
    HEADER_SIZE,
)

from rpp.pma import (
    PMARecord,
    PMABuffer,
    PMAStore,
    ConsentState as PMAConsentState,  # Re-exported from pma
    PayloadType as PMAPayloadType,    # Re-exported from pma
    encode_coherence,
    decode_coherence,
    encode_timestamp,
    decode_timestamp,
    PMA_RECORD_SIZE,
)

from rpp.address import encode, decode, from_components
from rpp.resolver import resolve, ResolveResult

from rpp.geometry import (
    TorusPoint,
    ToroidalStateVector,
    SkyrmionStateVector,
    TopologicalCollapseError,
    HarmonicMode as GeometryHarmonicMode,
    HARMONIC_OMEGA,
    antipodal,
    build_tsv,
    apply_rotation,
    apply_skyrmion_rotation,
    derive_rotation_key,
    derive_skyrmion_key,
    encrypt_volley,
    decrypt_volleys,
    encrypt_skyrmion_volley,
    decrypt_skyrmion_volleys,
    verify_self_coherence,
    angular_drift_from_origin,
    to_skyrmion,
)

from rpp.continuity import (
    HarmonicMode as ContinuityHarmonicMode,
    FordPhase,
    RecoveryLevel,
    LiminalState,
    ConsciousnessStatePacket,
    csp_from_rpp,
    compute_liminal_timeout,
    ford_crossing_phases,
    continuity_hash,
)

from rpp.network import (
    NodeTier,
    NodeRecord,
    RoutingDecision,
    FieldPulse,
    angular_distance,
    make_routing_decision,
    rank_next_hops,
    harmonic_to_tier_preference,
    detect_backbone_gaps,
)

from rpp.ccqpsg import (
    verify_ccqpsg_compliance,
    CCQPSGViolation,
    VIOLATION_CLASSES,
    bidirectional_check,
    routing_decision_compliant,
)

from rpp.memory_bridge import (
    RPPMemoryBridge,
    THETA_MEMORY,
    THETA_WITNESS,
    THETA_PROJECT,
    PERSISTENT_SHELLS,
)

__version__ = "2.1.0"
__author__ = "Anywave Creations"

__all__ = [
    # Address
    "RPPAddress",
    "ThetaSector",
    "RACBand",
    "OmegaTier",
    "create_address",
    "create_from_sector",
    "address_distance",
    "coherence",
    "same_sector",
    "adjacent_sectors",
    "compute_fallback",
    "verify_roundtrip",
    "verify_ra_alignment",
    # Consent Header
    "ConsentPacketHeader",
    "ConsentState",
    "AncestralConsent",
    "PayloadType",
    "SpiralPacket",
    "HEADER_SIZE",
    # PMA
    "PMARecord",
    "PMABuffer",
    "PMAStore",
    "PMAConsentState",
    "PMAPayloadType",
    "encode_coherence",
    "decode_coherence",
    "encode_timestamp",
    "decode_timestamp",
    "PMA_RECORD_SIZE",
    # Address (Semantic Interface v1.0)
    "encode",
    "decode",
    "from_components",
    # Resolver
    "resolve",
    "ResolveResult",
    # Geometry
    "TorusPoint",
    "ToroidalStateVector",
    "SkyrmionStateVector",
    "TopologicalCollapseError",
    "GeometryHarmonicMode",
    "HARMONIC_OMEGA",
    "antipodal",
    "build_tsv",
    "apply_rotation",
    "apply_skyrmion_rotation",
    "derive_rotation_key",
    "derive_skyrmion_key",
    "encrypt_volley",
    "decrypt_volleys",
    "encrypt_skyrmion_volley",
    "decrypt_skyrmion_volleys",
    "verify_self_coherence",
    "angular_drift_from_origin",
    "to_skyrmion",
    # Continuity (Ford Protocol)
    "ContinuityHarmonicMode",
    "FordPhase",
    "RecoveryLevel",
    "LiminalState",
    "ConsciousnessStatePacket",
    "csp_from_rpp",
    "compute_liminal_timeout",
    "ford_crossing_phases",
    "continuity_hash",
    # Network (Consent-Field Mesh)
    "NodeTier",
    "NodeRecord",
    "RoutingDecision",
    "FieldPulse",
    "angular_distance",
    "make_routing_decision",
    "rank_next_hops",
    "harmonic_to_tier_preference",
    "detect_backbone_gaps",
    # CCQPSG (Correct Communication Quantum Parse Syntax Grammar)
    "verify_ccqpsg_compliance",
    "CCQPSGViolation",
    "VIOLATION_CLASSES",
    "bidirectional_check",
    "routing_decision_compliant",
    # Memory Bridge (cross-session persistence)
    "RPPMemoryBridge",
    "THETA_MEMORY",
    "THETA_WITNESS",
    "THETA_PROJECT",
    "PERSISTENT_SHELLS",
]
