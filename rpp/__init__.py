"""
RPP - Recursive Packet Protocol

Ra-derived address and routing implementation for SPIRAL systems.

Modules:
    address_canonical: RPP Canonical Address v1.0-RaCanonical
    consent_header: SPIRAL Consent Packet Header v1.0
    pma: Phase Memory Anchor v1.1 (18-byte compact format)

Version: 1.1.0-RaCanonical
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

__version__ = "1.1.0-RaCanonical"
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
]
