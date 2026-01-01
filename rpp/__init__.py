"""
RPP - Rotational Packet Protocol

A 28-bit semantic addressing system for consent-aware routing.

RPP IS:
- A deterministic 28-bit semantic address
- A resolver that returns allow / deny / route
- A bridge to existing storage backends

RPP IS NOT:
- A storage system
- A database
- An identity provider
- A policy DSL
- An AI system
"""

__version__ = "0.2.0"

from rpp.address import (
    RPPAddress,
    encode,
    decode,
    from_components,
    from_raw,
    is_valid_address,
    parse_address,
    MAX_ADDRESS,
    MAX_SHELL,
    MAX_THETA,
    MAX_PHI,
    MAX_HARMONIC,
)

from rpp.resolver import (
    RPPResolver,
    ResolveResult,
    resolve,
)

from rpp.packet import (
    RPPPacket,
    PayloadType,
    create_packet,
    parse_packet,
    parse_framed_packet,
    is_valid_packet,
    create_hash_packet,
    create_pointer_packet,
    create_framed_packet,
    extract_framed_content,
)

from rpp.extended import (
    RPPExtendedAddress,
    encode_extended,
    decode_extended,
    from_extended_components,
    from_extended_raw,
    from_core_address,
    degrees_to_theta,
    degrees_to_phi,
    degrees_to_phase,
    phase_interference,
    MAX_THETA_FINE,
    MAX_PHI_FINE,
    MAX_HARMONIC_EXT,
    MAX_PHASE,
)

from rpp.consent import (
    ConsentState,
    ConsentContext,
    ConsentCheck,
    Sector,
    GroundingZone,
    check_consent,
    create_consent_context,
)

__all__ = [
    # Version
    "__version__",
    # Core Address (28-bit)
    "RPPAddress",
    "encode",
    "decode",
    "from_components",
    "from_raw",
    "is_valid_address",
    "parse_address",
    "MAX_ADDRESS",
    "MAX_SHELL",
    "MAX_THETA",
    "MAX_PHI",
    "MAX_HARMONIC",
    # Resolver
    "RPPResolver",
    "ResolveResult",
    "resolve",
    # Packet
    "RPPPacket",
    "PayloadType",
    "create_packet",
    "parse_packet",
    "parse_framed_packet",
    "is_valid_packet",
    "create_hash_packet",
    "create_pointer_packet",
    "create_framed_packet",
    "extract_framed_content",
    # Extended Address (64-bit)
    "RPPExtendedAddress",
    "encode_extended",
    "decode_extended",
    "from_extended_components",
    "from_extended_raw",
    "from_core_address",
    "degrees_to_theta",
    "degrees_to_phi",
    "degrees_to_phase",
    "phase_interference",
    "MAX_THETA_FINE",
    "MAX_PHI_FINE",
    "MAX_HARMONIC_EXT",
    "MAX_PHASE",
    # Consent
    "ConsentState",
    "ConsentContext",
    "ConsentCheck",
    "Sector",
    "GroundingZone",
    "check_consent",
    "create_consent_context",
]
