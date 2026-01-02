"""
SPIRAL Consent Packet Header v2.0

System-layer envelope that wraps an RPP Canonical Address with
consent state, integrity markers, and Phase Memory Anchor linkage.

This is NOT part of the address—it is governance metadata that
rides on top of the Ra-derived routing vector.

v2.0: Updated to 5-state ACSP with ATTENTIVE intermediate state,
      φ-based thresholds, and multi-bit verbal signal strength.

Reference: CONSENT-HEADER-v1.md, SPIRAL-Architecture.md v2.2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Final, ClassVar
import struct
import time

from rpp.address_canonical import RPPAddress
from rpp.ra_constants import (
    PHI_THRESHOLD_4BIT,
    ATTENTIVE_THRESHOLD_4BIT,
    DIMINISHED_THRESHOLD_4BIT,
)


# =============================================================================
# Constants
# =============================================================================

HEADER_SIZE: Final[int] = 18  # bytes
HEADER_BITS: Final[int] = 144

# Field positions (byte offsets)
OFF_RPP_ADDRESS: Final[int] = 0     # 4 bytes
OFF_PACKET_ID: Final[int] = 4       # 4 bytes
OFF_ORIGIN_REF: Final[int] = 8      # 2 bytes
OFF_CONSENT: Final[int] = 10        # 1 byte
OFF_ENTROPY: Final[int] = 11        # 1 byte
OFF_TEMPORAL: Final[int] = 12       # 1 byte
OFF_FALLBACK: Final[int] = 13       # 1 byte
OFF_WINDOW_ID: Final[int] = 14      # 2 bytes
OFF_PHASE_REF: Final[int] = 16      # 1 byte
OFF_CRC: Final[int] = 17            # 1 byte


# =============================================================================
# Enumerations
# =============================================================================

class ConsentState(IntEnum):
    """
    5-state ACSP (Avatar Consent State Protocol).

    φ-based thresholds on 4-bit somatic consent (0-15):
        FULL_CONSENT: ≥ 10 (φ × 16 ≈ 9.89, rounded to 10)
        ATTENTIVE: 7-9 (early engagement zone)
        DIMINISHED_CONSENT: 6 ((1-φ) × 16 ≈ 6.11, rounded to 6)
        SUSPENDED_CONSENT: 0-5 (below 1-φ threshold)
        EMERGENCY_OVERRIDE: External trigger (ETF)
    """
    FULL_CONSENT = 0       # Full operation, all sectors accessible
    ATTENTIVE = 1          # Early engagement, preliminary routing
    DIMINISHED_CONSENT = 2 # Delayed/reconfirm required
    SUSPENDED_CONSENT = 3  # Blocked, minimal sectors
    EMERGENCY_OVERRIDE = 4 # Frozen (ETF), GUARDIAN lockdown


class AncestralConsent(IntEnum):
    """Ancestral consent inheritance levels."""
    NONE = 0       # No ancestral consent
    INHERITED = 1  # Lineage-verified
    DELEGATED = 2  # Granted by ancestor
    SOVEREIGN = 3  # Self-sovereign override


class PayloadType(IntEnum):
    """Payload origin/type indicator."""
    EMPTY = 0x0
    HUMAN = 0x1
    AI = 0x2
    SCALAR = 0x3
    HYBRID = 0x4
    FRAGMENT = 0x5
    COMMAND = 0x6
    QUERY = 0x7
    RESPONSE = 0x8
    HEARTBEAT = 0x9
    FREEZE = 0xA
    DISSOLVE = 0xB
    # 0xC-0xF reserved


# =============================================================================
# CRC-8 Implementation
# =============================================================================

def compute_crc8(data: bytes) -> int:
    """
    Compute CRC-8/CCITT over data.
    
    Polynomial: 0x07 (x^8 + x^2 + x + 1)
    """
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
            crc &= 0xFF
    return crc


# =============================================================================
# Standalone Consent Derivation
# =============================================================================

def derive_consent_state(
    consent_somatic_4bit: int,
    verbal_signal_strength: int = 0,
) -> ConsentState:
    """
    Derive 5-state ACSP consent state from raw signal values.

    This is a standalone function for use outside of ConsentPacketHeader.

    Args:
        consent_somatic_4bit: 4-bit somatic consent (0-15)
        verbal_signal_strength: Verbal signal strength (0-3)

    Returns:
        ConsentState enum value

    φ-based thresholds:
        - ≥ 10 (PHI_THRESHOLD): FULL_CONSENT
        - 7-9 (ATTENTIVE zone): ATTENTIVE
        - 6 (DIMINISHED boundary): verbal≥2 boosts to ATTENTIVE
        - 0-5 (below threshold): SUSPENDED_CONSENT
    """
    if consent_somatic_4bit >= PHI_THRESHOLD_4BIT:  # ≥ 10
        return ConsentState.FULL_CONSENT
    elif consent_somatic_4bit >= ATTENTIVE_THRESHOLD_4BIT:  # 7-9
        return ConsentState.ATTENTIVE
    elif consent_somatic_4bit >= DIMINISHED_THRESHOLD_4BIT:  # 6
        if verbal_signal_strength >= 2:
            return ConsentState.ATTENTIVE
        return ConsentState.DIMINISHED_CONSENT
    else:  # 0-5
        return ConsentState.SUSPENDED_CONSENT


# =============================================================================
# Consent Packet Header
# =============================================================================

@dataclass
class ConsentPacketHeader:
    """
    SPIRAL Consent Packet Header (18 bytes / 144 bits).
    
    Wraps an RPP Canonical Address with consent governance.
    
    Structure:
        Bytes 0-3:   RPP Canonical Address (32 bits)
        Bytes 4-7:   Packet ID (32 bits)
        Bytes 8-9:   Origin Avatar Reference (16 bits)
        Byte 10:     Consent Fields (8 bits)
        Byte 11:     Phase Entropy + Complecount (8 bits)
        Byte 12:     Temporal + Payload Type (8 bits)
        Byte 13:     Fallback Vector (8 bits)
        Bytes 14-15: Coherence Window ID (16 bits)
        Byte 16:     Target Phase Reference (8 bits)
        Byte 17:     Header CRC (8 bits)
    """
    
    # Core address (Ra-derived)
    rpp_address: RPPAddress
    
    # Identification
    packet_id: int = 0          # 32-bit unique ID
    origin_ref: int = 0         # 16-bit avatar reference
    
    # Consent fields (Byte 10)
    # v2.0: consent_somatic is now 4-bit int (0-15), verbal_signal_strength is 2-bit int (0-3)
    verbal_signal_strength: int = 3     # 2 bits (0-3): 0=none, 1=weak, 2=moderate, 3=strong
    consent_somatic_4bit: int = 15      # 4 bits (0-15): φ-scaled somatic consent
    consent_ancestral: AncestralConsent = AncestralConsent.NONE  # 2 bits
    temporal_lock: bool = False         # 1 bit (reserved)
    
    # Entropy fields (Byte 11)
    phase_entropy_index: int = 0        # 5 bits (0-31)
    complecount_trace: int = 0          # 3 bits (0-7)
    
    # Temporal/Payload (Byte 12)
    payload_type: PayloadType = PayloadType.EMPTY  # 4 bits
    
    # Routing
    fallback_vector: int = 0            # 8 bits
    coherence_window_id: int = 0        # 16 bits (PMA link)
    target_phase_ref: int = 0           # 8 bits
    
    # Computed on encode
    _crc: int = field(default=0, repr=False)
    
    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate header against SPIRAL rules (v2.0).

        Returns: (valid, list of error messages)
        """
        errors = []

        # V3: RPP address must be valid
        if not self.rpp_address.is_valid():
            errors.append("V3: RPP address is invalid")

        # C1: Low somatic consent (< 6) requires complecount > 0
        if self.consent_somatic_4bit < DIMINISHED_THRESHOLD_4BIT and self.complecount_trace == 0:
            errors.append(f"C1: consent_somatic_4bit < {DIMINISHED_THRESHOLD_4BIT} requires complecount_trace > 0")

        # Range checks
        if not 0 <= self.consent_somatic_4bit <= 15:
            errors.append(f"consent_somatic_4bit must be 0-15, got {self.consent_somatic_4bit}")

        if not 0 <= self.verbal_signal_strength <= 3:
            errors.append(f"verbal_signal_strength must be 0-3, got {self.verbal_signal_strength}")

        if not 0 <= self.phase_entropy_index <= 31:
            errors.append(f"phase_entropy_index must be 0-31, got {self.phase_entropy_index}")

        if not 0 <= self.complecount_trace <= 7:
            errors.append(f"complecount_trace must be 0-7, got {self.complecount_trace}")

        if not 0 <= self.fallback_vector <= 255:
            errors.append(f"fallback_vector must be 0-255, got {self.fallback_vector}")

        return len(errors) == 0, errors
    
    # -------------------------------------------------------------------------
    # Consent State Derivation
    # -------------------------------------------------------------------------
    
    def derive_consent_state(self) -> ConsentState:
        """
        Derive 5-state ACSP consent state from header fields.

        φ-based thresholds on 4-bit somatic consent:
            - ≥ 10 (PHI_THRESHOLD): FULL_CONSENT
            - 7-9 (ATTENTIVE zone): ATTENTIVE
            - 6 (DIMINISHED boundary): verbal can boost to ATTENTIVE
            - 0-5 (below threshold): SUSPENDED_CONSENT

        Verbal signal strength (0-3) can boost consent:
            - At somatic=6, verbal≥2 boosts to ATTENTIVE
        """
        somatic = self.consent_somatic_4bit
        verbal = self.verbal_signal_strength

        if somatic >= PHI_THRESHOLD_4BIT:  # ≥ 10
            return ConsentState.FULL_CONSENT
        elif somatic >= ATTENTIVE_THRESHOLD_4BIT:  # 7-9
            return ConsentState.ATTENTIVE
        elif somatic >= DIMINISHED_THRESHOLD_4BIT:  # 6
            # Verbal boost: strong verbal signal can elevate to ATTENTIVE
            if verbal >= 2:
                return ConsentState.ATTENTIVE
            return ConsentState.DIMINISHED_CONSENT
        else:  # 0-5
            return ConsentState.SUSPENDED_CONSENT
    
    @property
    def consent_state(self) -> ConsentState:
        """Get current consent state."""
        return self.derive_consent_state()
    
    @property
    def needs_fallback(self) -> bool:
        """Check if fallback routing should be activated."""
        return self.phase_entropy_index > 25
    
    @property
    def has_pma_link(self) -> bool:
        """Check if linked to a Phase Memory Anchor."""
        return self.coherence_window_id != 0
    
    # -------------------------------------------------------------------------
    # Encoding
    # -------------------------------------------------------------------------
    
    def _encode_consent_byte(self) -> int:
        """
        Encode consent fields to Byte 10.

        v2.0 Layout:
            [7:6] verbal_signal_strength (2 bits, 0-3)
            [5:2] consent_somatic_4bit (4 bits, 0-15)
            [1:0] consent_ancestral (2 bits)

        Note: temporal_lock moved to reserved bits in temporal byte.
        """
        verbal_bits = (min(3, max(0, self.verbal_signal_strength)) & 0x03) << 6
        somatic_bits = (min(15, max(0, self.consent_somatic_4bit)) & 0x0F) << 2
        ancestral_bits = (self.consent_ancestral.value & 0x03)

        return verbal_bits | somatic_bits | ancestral_bits
    
    def _encode_entropy_byte(self) -> int:
        """
        Encode entropy fields to Byte 11.
        
        Layout:
            [7:3] phase_entropy_index (5 bits)
            [2:0] complecount_trace (3 bits)
        """
        entropy_bits = (self.phase_entropy_index & 0x1F) << 3
        complecount_bits = self.complecount_trace & 0x07
        
        return entropy_bits | complecount_bits
    
    def _encode_temporal_byte(self) -> int:
        """
        Encode temporal/payload fields to Byte 12.

        v2.0 Layout:
            [7]   temporal_lock
            [6:4] reserved
            [3:0] payload_type
        """
        temporal_bit = (1 if self.temporal_lock else 0) << 7
        return temporal_bit | (self.payload_type.value & 0x0F)
    
    def to_bytes(self) -> bytes:
        """
        Encode header to 18 bytes.
        
        Computes CRC over bytes 0-16.
        """
        # Build header without CRC
        header = bytearray(HEADER_SIZE)
        
        # Bytes 0-3: RPP Address
        header[0:4] = self.rpp_address.to_bytes()
        
        # Bytes 4-7: Packet ID
        struct.pack_into('>I', header, OFF_PACKET_ID, self.packet_id & 0xFFFFFFFF)
        
        # Bytes 8-9: Origin Reference
        struct.pack_into('>H', header, OFF_ORIGIN_REF, self.origin_ref & 0xFFFF)
        
        # Byte 10: Consent fields
        header[OFF_CONSENT] = self._encode_consent_byte()
        
        # Byte 11: Entropy + Complecount
        header[OFF_ENTROPY] = self._encode_entropy_byte()
        
        # Byte 12: Temporal + Payload Type
        header[OFF_TEMPORAL] = self._encode_temporal_byte()
        
        # Byte 13: Fallback Vector
        header[OFF_FALLBACK] = self.fallback_vector & 0xFF
        
        # Bytes 14-15: Coherence Window ID
        struct.pack_into('>H', header, OFF_WINDOW_ID, self.coherence_window_id & 0xFFFF)
        
        # Byte 16: Target Phase Reference
        header[OFF_PHASE_REF] = self.target_phase_ref & 0xFF
        
        # Byte 17: CRC over bytes 0-16
        header[OFF_CRC] = compute_crc8(header[:17])
        
        return bytes(header)
    
    # -------------------------------------------------------------------------
    # Decoding
    # -------------------------------------------------------------------------
    
    @classmethod
    def _decode_consent_byte(cls, byte: int) -> tuple[int, int, AncestralConsent]:
        """
        Decode Byte 10 consent fields (v2.0 layout).

        Returns:
            (verbal_signal_strength, consent_somatic_4bit, consent_ancestral)
        """
        verbal_signal_strength = (byte >> 6) & 0x03
        consent_somatic_4bit = (byte >> 2) & 0x0F
        consent_ancestral = AncestralConsent(byte & 0x03)

        return verbal_signal_strength, consent_somatic_4bit, consent_ancestral
    
    @classmethod
    def _decode_entropy_byte(cls, byte: int) -> tuple[int, int]:
        """Decode Byte 11 entropy fields."""
        phase_entropy_index = (byte >> 3) & 0x1F
        complecount_trace = byte & 0x07
        
        return phase_entropy_index, complecount_trace
    
    @classmethod
    def from_bytes(cls, data: bytes) -> ConsentPacketHeader:
        """
        Decode header from 18 bytes.
        
        Raises ValueError if CRC mismatch.
        """
        if len(data) != HEADER_SIZE:
            raise ValueError(f"Expected {HEADER_SIZE} bytes, got {len(data)}")
        
        # Verify CRC
        computed_crc = compute_crc8(data[:17])
        stored_crc = data[OFF_CRC]
        if computed_crc != stored_crc:
            raise ValueError(f"CRC mismatch: computed {computed_crc:02X}, stored {stored_crc:02X}")
        
        # Decode fields
        rpp_address = RPPAddress.from_bytes(data[OFF_RPP_ADDRESS:OFF_RPP_ADDRESS+4])
        packet_id = struct.unpack_from('>I', data, OFF_PACKET_ID)[0]
        origin_ref = struct.unpack_from('>H', data, OFF_ORIGIN_REF)[0]
        
        verbal_signal_strength, consent_somatic_4bit, consent_ancestral = \
            cls._decode_consent_byte(data[OFF_CONSENT])

        phase_entropy_index, complecount_trace = \
            cls._decode_entropy_byte(data[OFF_ENTROPY])

        # Decode temporal byte (v2.0: includes temporal_lock)
        temporal_byte = data[OFF_TEMPORAL]
        temporal_lock = bool((temporal_byte >> 7) & 0x01)
        payload_type = PayloadType(temporal_byte & 0x0F)

        fallback_vector = data[OFF_FALLBACK]
        coherence_window_id = struct.unpack_from('>H', data, OFF_WINDOW_ID)[0]
        target_phase_ref = data[OFF_PHASE_REF]

        return cls(
            rpp_address=rpp_address,
            packet_id=packet_id,
            origin_ref=origin_ref,
            verbal_signal_strength=verbal_signal_strength,
            consent_somatic_4bit=consent_somatic_4bit,
            consent_ancestral=consent_ancestral,
            temporal_lock=temporal_lock,
            phase_entropy_index=phase_entropy_index,
            complecount_trace=complecount_trace,
            payload_type=payload_type,
            fallback_vector=fallback_vector,
            coherence_window_id=coherence_window_id,
            target_phase_ref=target_phase_ref,
            _crc=stored_crc
        )
    
    # -------------------------------------------------------------------------
    # CRC Validation
    # -------------------------------------------------------------------------
    
    def validate_crc(self, data: bytes) -> bool:
        """Validate CRC of encoded data."""
        if len(data) != HEADER_SIZE:
            return False
        computed = compute_crc8(data[:17])
        return computed == data[OFF_CRC]
    
    # -------------------------------------------------------------------------
    # Factory Methods
    # -------------------------------------------------------------------------
    
    @classmethod
    def create(
        cls,
        rpp_address: RPPAddress,
        *,
        origin_ref: int = 0,
        consent_somatic_4bit: int = 15,
        verbal_signal_strength: int = 3,
        payload_type: PayloadType = PayloadType.HUMAN,
        coherence_window_id: int = 0,
    ) -> ConsentPacketHeader:
        """
        Create a header with auto-generated packet ID.

        Args:
            rpp_address: The Ra-derived routing address
            origin_ref: Avatar reference (0 = self)
            consent_somatic_4bit: 4-bit somatic consent (0-15)
            verbal_signal_strength: Verbal signal strength (0-3)
            payload_type: Type of payload
            coherence_window_id: PMA link (0 = none)

        Returns:
            ConsentPacketHeader with generated packet_id
        """
        # Generate packet ID from timestamp + counter
        timestamp_hash = int(time.time() * 1000) & 0xFFFF0000
        sequence = cls._get_next_sequence() & 0xFFFF
        packet_id = timestamp_hash | sequence

        return cls(
            rpp_address=rpp_address,
            packet_id=packet_id,
            origin_ref=origin_ref,
            verbal_signal_strength=verbal_signal_strength,
            consent_somatic_4bit=consent_somatic_4bit,
            payload_type=payload_type,
            coherence_window_id=coherence_window_id,
        )
    
    # Sequence counter for packet IDs
    _sequence_counter: ClassVar[int] = 0
    
    @classmethod
    def _get_next_sequence(cls) -> int:
        """Get next sequence number for packet ID."""
        cls._sequence_counter = (cls._sequence_counter + 1) & 0xFFFF
        return cls._sequence_counter
    
    # -------------------------------------------------------------------------
    # Fallback Address
    # -------------------------------------------------------------------------
    
    def compute_fallback_address(self) -> RPPAddress:
        """
        Compute fallback address using stored vector.
        
        Should be called when needs_fallback is True.
        """
        from rpp.address_canonical import compute_fallback
        return compute_fallback(self.rpp_address, self.fallback_vector)
    
    # -------------------------------------------------------------------------
    # String Representations
    # -------------------------------------------------------------------------
    
    def __str__(self) -> str:
        state = self.consent_state.name
        return (
            f"ConsentHeader(addr={self.rpp_address.to_hex()}, "
            f"state={state}, somatic={self.consent_somatic_4bit}/15, "
            f"verbal={self.verbal_signal_strength}/3, "
            f"window={self.coherence_window_id:04X})"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            'rpp_address': self.rpp_address.to_hex(),
            'packet_id': f"0x{self.packet_id:08X}",
            'origin_ref': f"0x{self.origin_ref:04X}",
            'consent_state': self.consent_state.name,
            'verbal_signal_strength': self.verbal_signal_strength,
            'consent_somatic_4bit': self.consent_somatic_4bit,
            'consent_ancestral': self.consent_ancestral.name,
            'temporal_lock': self.temporal_lock,
            'phase_entropy_index': self.phase_entropy_index,
            'complecount_trace': self.complecount_trace,
            'payload_type': self.payload_type.name,
            'fallback_vector': f"0x{self.fallback_vector:02X}",
            'coherence_window_id': f"0x{self.coherence_window_id:04X}",
            'target_phase_ref': f"0x{self.target_phase_ref:02X}",
            'needs_fallback': self.needs_fallback,
            'has_pma_link': self.has_pma_link,
        }


# =============================================================================
# SPIRAL Packet (Header + Payload)
# =============================================================================

@dataclass
class SpiralPacket:
    """
    Complete SPIRAL packet with header and payload.
    
    Structure:
        - Header: 18 bytes (ConsentPacketHeader)
        - Payload: 0-65517 bytes (limited to keep total under 64KB)
    """
    
    header: ConsentPacketHeader
    payload: bytes = b''
    
    MAX_PAYLOAD: ClassVar[int] = 65517  # 65535 - 18
    
    def __post_init__(self):
        if len(self.payload) > self.MAX_PAYLOAD:
            raise ValueError(f"Payload too large: {len(self.payload)} > {self.MAX_PAYLOAD}")
    
    def to_bytes(self) -> bytes:
        """Encode complete packet."""
        return self.header.to_bytes() + self.payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> SpiralPacket:
        """Decode complete packet."""
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Packet too short: {len(data)} < {HEADER_SIZE}")
        
        header = ConsentPacketHeader.from_bytes(data[:HEADER_SIZE])
        payload = data[HEADER_SIZE:]
        
        return cls(header=header, payload=payload)
    
    @property
    def total_size(self) -> int:
        """Total packet size in bytes."""
        return HEADER_SIZE + len(self.payload)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    from rpp.address_canonical import ThetaSector, create_from_sector

    print("SPIRAL Consent Packet Header v2.0 (5-State ACSP)")
    print("=" * 60)

    # Create a test address
    addr = create_from_sector(ThetaSector.MEMORY, phi=3, omega=2, radius=0.75)
    print(f"\nRPP Address: {addr}")

    # Create consent header with 5-state ACSP
    header = ConsentPacketHeader.create(
        rpp_address=addr,
        origin_ref=0x0042,
        consent_somatic_4bit=13,  # High consent (above φ threshold of 10)
        verbal_signal_strength=3,  # Strong verbal
        payload_type=PayloadType.HUMAN,
        coherence_window_id=0x1A2B,
    )
    
    print(f"\nHeader: {header}")
    print(f"Consent State: {header.consent_state.name}")
    print(f"Needs Fallback: {header.needs_fallback}")
    print(f"Has PMA Link: {header.has_pma_link}")
    
    # Encode and decode
    encoded = header.to_bytes()
    print(f"\nEncoded ({len(encoded)} bytes): {encoded.hex()}")
    
    decoded = ConsentPacketHeader.from_bytes(encoded)
    print(f"Decoded: {decoded}")
    
    # Validate
    valid, errors = decoded.validate()
    print(f"\nValid: {valid}")
    if errors:
        for e in errors:
            print(f"  Error: {e}")
    
    # Full packet
    packet = SpiralPacket(
        header=header,
        payload=b'Hello, SPIRAL!'
    )
    print(f"\nPacket size: {packet.total_size} bytes")
    
    # Dict representation
    print("\nHeader dict:")
    for k, v in header.to_dict().items():
        print(f"  {k}: {v}")
