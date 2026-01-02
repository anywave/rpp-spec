"""
Phase Memory Anchor (PMA) v1.1

Temporal-coherence ledger within the SPIRAL protocol.
PMA stores snapshots of resolved phase vectors and their consent outcomes.

Record Size: 144 bits (18 bytes) - aligned with Consent Header

Reference: PMA-SCHEMA-v1.md (v1.1)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Final, Optional
import struct
import time

from rpp.address_canonical import RPPAddress


# =============================================================================
# Constants
# =============================================================================

PMA_RECORD_SIZE: Final[int] = 18  # bytes
PMA_RECORD_BITS: Final[int] = 144

# Window ID limits (12 bits)
WINDOW_ID_MAX: Final[int] = 0xFFE
WINDOW_ID_INVALID: Final[int] = 0x000
WINDOW_ID_ALLOCATE: Final[int] = 0xFFF


# =============================================================================
# Enumerations (matching Consent Header)
# =============================================================================

class ConsentState(IntEnum):
    """ACSP consent state (2 bits)."""
    FULL_CONSENT = 0b00
    DIMINISHED_CONSENT = 0b01
    SUSPENDED_CONSENT = 0b10
    EMERGENCY_OVERRIDE = 0b11


class PayloadType(IntEnum):
    """Payload type indicator (4 bits)."""
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


# =============================================================================
# Timestamp Utilities
# =============================================================================

def encode_timestamp(seconds: int, nanos: int = 0) -> int:
    """
    Encode seconds + nanoseconds to 64-bit timestamp.
    
    Layout:
        [63:30] seconds (34 bits, ~544 years)
        [29:0]  nanoseconds (30 bits, 0-999999999)
    """
    return ((seconds & 0x3FFFFFFFF) << 30) | (nanos & 0x3FFFFFFF)


def decode_timestamp(ts: int) -> tuple[int, int]:
    """Decode 64-bit timestamp to (seconds, nanoseconds)."""
    seconds = (ts >> 30) & 0x3FFFFFFFF
    nanos = ts & 0x3FFFFFFF
    return seconds, nanos


def get_nanosecond_timestamp() -> int:
    """Get current time as 64-bit nanosecond timestamp."""
    t = time.time()
    seconds = int(t)
    nanos = int((t - seconds) * 1_000_000_000)
    return encode_timestamp(seconds, nanos)


# =============================================================================
# Coherence Encoding
# =============================================================================

def encode_coherence(normalized: float) -> int:
    """Encode 0.0-1.0 coherence to 6-bit field (0-63)."""
    return min(63, max(0, round(normalized * 63)))


def decode_coherence(score: int) -> float:
    """Decode 6-bit coherence (0-63) to 0.0-1.0."""
    return score / 63.0


# =============================================================================
# CRC-8 Implementation
# =============================================================================

def compute_crc8(data: bytes) -> int:
    """Compute CRC-8/CCITT over data (polynomial 0x07)."""
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
# PMA Record (18 bytes / 144 bits)
# =============================================================================

@dataclass(frozen=True)
class PMARecord:
    """
    Phase Memory Anchor record (18 bytes / 144 bits).
    
    Structure:
        window_id:          12 bits - Links to coherence_window_id
        timestamp:          64 bits - UNIX time (nanosecond precision)
        phase_vector:       32 bits - θ–φ–h–r from Canonical RPP Address
        consent_state:       2 bits - ACSP state at resolution
        complecount_score:   5 bits - Valid null-events count (0-31)
        coherence_score:     6 bits - PMQ/scalar coherence (0-63)
        payload_type:        4 bits - Type resolved
        fallback_triggered:  1 bit  - Fallback vector was used
        crc:                 8 bits - Data integrity check
        reserved:           10 bits - Future use
    """
    
    window_id: int           # 12 bits (0-4094, 0=invalid, 4095=allocate)
    timestamp: int           # 64 bits (nanosecond timestamp)
    phase_vector: int        # 32 bits (RPP canonical address)
    consent_state: ConsentState  # 2 bits
    complecount_score: int   # 5 bits (0-31)
    coherence_score: int     # 6 bits (0-63)
    payload_type: PayloadType    # 4 bits
    fallback_triggered: bool # 1 bit
    
    def __post_init__(self):
        """Validate field ranges."""
        if not 0 <= self.window_id <= 0xFFF:
            raise ValueError(f"window_id must be 0-4095, got {self.window_id}")
        if not 0 <= self.complecount_score <= 31:
            raise ValueError(f"complecount_score must be 0-31, got {self.complecount_score}")
        if not 0 <= self.coherence_score <= 63:
            raise ValueError(f"coherence_score must be 0-63, got {self.coherence_score}")
    
    # -------------------------------------------------------------------------
    # Accessors
    # -------------------------------------------------------------------------
    
    @property
    def is_valid(self) -> bool:
        """Check if record is valid."""
        return self.window_id != WINDOW_ID_INVALID and self.timestamp != 0
    
    @property
    def coherence_normalized(self) -> float:
        """Get coherence as 0.0-1.0."""
        return decode_coherence(self.coherence_score)
    
    def get_address(self) -> RPPAddress:
        """Get phase vector as RPP address."""
        return RPPAddress.from_int(self.phase_vector)
    
    def get_timestamp_parts(self) -> tuple[int, int]:
        """Get timestamp as (seconds, nanoseconds)."""
        return decode_timestamp(self.timestamp)
    
    # -------------------------------------------------------------------------
    # Encoding (18 bytes)
    # -------------------------------------------------------------------------
    
    def to_bytes(self) -> bytes:
        """
        Encode to 18 bytes (144 bits).
        
        Bit layout (big-endian):
            Byte 0:    [window_id_hi(8)]
            Byte 1:    [window_id_lo(4)] [timestamp_hi(4)]
            Byte 2-8:  [timestamp(60 bits)]
            Byte 9-12: [phase_vector(32)]
            Byte 13:   [consent_state(2)] [complecount_score(5)] [coherence_hi(1)]
            Byte 14:   [coherence_lo(5)] [payload_type_hi(3)]
            Byte 15:   [payload_type_lo(1)] [fallback(1)] [reserved(6)]
            Byte 16:   [reserved(8)]
            Byte 17:   [crc(8)]
        """
        data = bytearray(PMA_RECORD_SIZE)
        
        # Bytes 0-1: window_id (12 bits) + timestamp_hi (4 bits)
        wid = self.window_id & 0xFFF
        ts_hi = (self.timestamp >> 60) & 0x0F
        data[0] = (wid >> 4) & 0xFF
        data[1] = ((wid & 0x0F) << 4) | ts_hi
        
        # Bytes 2-8: timestamp remaining (60 bits = 7.5 bytes)
        ts_remaining = self.timestamp & 0x0FFFFFFFFFFFFFFF
        for i in range(7):
            data[2 + i] = (ts_remaining >> (52 - i * 8)) & 0xFF
        data[8] = (ts_remaining & 0x0F) << 4  # Lower 4 bits in upper nibble of byte 8
        
        # Bytes 9-12: phase_vector (32 bits)
        struct.pack_into('>I', data, 9, self.phase_vector & 0xFFFFFFFF)
        
        # Byte 13: consent_state(2) + complecount_score(5) + coherence_hi(1)
        consent_bits = (self.consent_state.value & 0x03) << 6
        comple_bits = (self.complecount_score & 0x1F) << 1
        coh_hi = (self.coherence_score >> 5) & 0x01
        data[13] = consent_bits | comple_bits | coh_hi
        
        # Byte 14: coherence_lo(5) + payload_type_hi(3)
        coh_lo = (self.coherence_score & 0x1F) << 3
        pt_hi = (self.payload_type.value >> 1) & 0x07
        data[14] = coh_lo | pt_hi
        
        # Byte 15: payload_type_lo(1) + fallback(1) + reserved(6)
        pt_lo = (self.payload_type.value & 0x01) << 7
        fb = (1 if self.fallback_triggered else 0) << 6
        data[15] = pt_lo | fb
        
        # Byte 16: reserved
        data[16] = 0x00
        
        # Byte 17: CRC over bytes 0-16
        data[17] = compute_crc8(data[:17])
        
        return bytes(data)
    
    # -------------------------------------------------------------------------
    # Decoding
    # -------------------------------------------------------------------------
    
    @classmethod
    def from_bytes(cls, data: bytes) -> PMARecord:
        """
        Decode from 18 bytes.
        
        Raises ValueError if CRC mismatch.
        """
        if len(data) != PMA_RECORD_SIZE:
            raise ValueError(f"Expected {PMA_RECORD_SIZE} bytes, got {len(data)}")
        
        # Verify CRC
        computed_crc = compute_crc8(data[:17])
        stored_crc = data[17]
        if computed_crc != stored_crc:
            raise ValueError(f"CRC mismatch: computed {computed_crc:02X}, stored {stored_crc:02X}")
        
        # Decode window_id (12 bits)
        window_id = (data[0] << 4) | ((data[1] >> 4) & 0x0F)
        
        # Decode timestamp (64 bits)
        ts_hi = data[1] & 0x0F
        ts_remaining = 0
        for i in range(7):
            ts_remaining = (ts_remaining << 8) | data[2 + i]
        ts_remaining = (ts_remaining << 4) | ((data[8] >> 4) & 0x0F)
        timestamp = (ts_hi << 60) | ts_remaining
        
        # Decode phase_vector (32 bits)
        phase_vector = struct.unpack_from('>I', data, 9)[0]
        
        # Decode byte 13
        consent_state = ConsentState((data[13] >> 6) & 0x03)
        complecount_score = (data[13] >> 1) & 0x1F
        coh_hi = data[13] & 0x01
        
        # Decode byte 14
        coh_lo = (data[14] >> 3) & 0x1F
        coherence_score = (coh_hi << 5) | coh_lo
        pt_hi = data[14] & 0x07
        
        # Decode byte 15
        pt_lo = (data[15] >> 7) & 0x01
        payload_type = PayloadType((pt_hi << 1) | pt_lo)
        fallback_triggered = bool((data[15] >> 6) & 0x01)
        
        return cls(
            window_id=window_id,
            timestamp=timestamp,
            phase_vector=phase_vector,
            consent_state=consent_state,
            complecount_score=complecount_score,
            coherence_score=coherence_score,
            payload_type=payload_type,
            fallback_triggered=fallback_triggered,
        )
    
    # -------------------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------------------
    
    @classmethod
    def create(
        cls,
        window_id: int,
        address: RPPAddress,
        consent_state: ConsentState,
        coherence: float,
        complecount: int = 0,
        payload_type: PayloadType = PayloadType.HUMAN,
        fallback_used: bool = False,
    ) -> PMARecord:
        """
        Create PMA record after successful resolution.
        
        Args:
            window_id: Coherence window ID from header
            address: Resolved RPP address
            consent_state: ACSP state at resolution
            coherence: Coherence score 0.0-1.0
            complecount: Number of null-events (0-31)
            payload_type: Payload type from header
            fallback_used: Whether fallback vector was activated
        
        Returns:
            New PMARecord with current timestamp
        """
        return cls(
            window_id=window_id,
            timestamp=get_nanosecond_timestamp(),
            phase_vector=address.to_int(),
            consent_state=consent_state,
            complecount_score=min(31, complecount),
            coherence_score=encode_coherence(coherence),
            payload_type=payload_type,
            fallback_triggered=fallback_used,
        )
    
    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------
    
    def __str__(self) -> str:
        addr = self.get_address()
        return (
            f"PMA(wid=0x{self.window_id:03X}, "
            f"θ={addr.theta}, coherence={self.coherence_normalized:.2f}, "
            f"state={self.consent_state.name})"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        secs, nanos = self.get_timestamp_parts()
        return {
            'window_id': f"0x{self.window_id:03X}",
            'timestamp_s': secs,
            'timestamp_ns': nanos,
            'phase_vector': self.get_address().to_hex(),
            'consent_state': self.consent_state.name,
            'complecount_score': self.complecount_score,
            'coherence_score': self.coherence_normalized,
            'payload_type': self.payload_type.name,
            'fallback_triggered': self.fallback_triggered,
        }


# =============================================================================
# PMA Circular Buffer
# =============================================================================

class PMABuffer:
    """
    Circular buffer for PMA records.
    
    Used by resolver for retention and lookup.
    """
    
    def __init__(self, capacity: int = 256):
        """
        Initialize buffer with given capacity.
        
        Args:
            capacity: Number of records (8-4096)
        """
        if not 8 <= capacity <= 4096:
            raise ValueError(f"Capacity must be 8-4096, got {capacity}")
        
        self._capacity = capacity
        self._buffer: list[Optional[PMARecord]] = [None] * capacity
        self._write_ptr = 0
        self._count = 0
        self._index: dict[int, int] = {}  # window_id → buffer position
    
    @property
    def capacity(self) -> int:
        """Buffer capacity in records."""
        return self._capacity
    
    @property
    def count(self) -> int:
        """Number of valid records."""
        return self._count
    
    @property
    def memory_bytes(self) -> int:
        """Memory usage in bytes."""
        return self._capacity * PMA_RECORD_SIZE
    
    def write(self, record: PMARecord) -> int:
        """
        Write record to buffer.
        
        Args:
            record: PMA record to write
        
        Returns:
            Buffer position where record was written
        """
        pos = self._write_ptr
        
        # Remove old record from index if being overwritten
        old_record = self._buffer[pos]
        if old_record is not None:
            if old_record.window_id in self._index:
                del self._index[old_record.window_id]
        else:
            self._count += 1
        
        # Write new record
        self._buffer[pos] = record
        self._index[record.window_id] = pos
        
        # Advance write pointer
        self._write_ptr = (self._write_ptr + 1) % self._capacity
        
        return pos
    
    def get(self, window_id: int) -> Optional[PMARecord]:
        """
        Get record by window_id.
        
        Args:
            window_id: Window ID to look up
        
        Returns:
            PMARecord or None if not found
        """
        pos = self._index.get(window_id)
        if pos is None:
            return None
        return self._buffer[pos]
    
    def get_latest(self, n: int = 10) -> list[PMARecord]:
        """
        Get N most recent records.
        
        Args:
            n: Number of records to return
        
        Returns:
            List of records (newest first)
        """
        result = []
        pos = (self._write_ptr - 1) % self._capacity
        
        for _ in range(min(n, self._count)):
            record = self._buffer[pos]
            if record is not None:
                result.append(record)
            pos = (pos - 1) % self._capacity
        
        return result
    
    def archive_batch(self, n: int = 100) -> tuple[bytes, int]:
        """
        Archive N oldest records as hash.
        
        Args:
            n: Number of records to archive
        
        Returns:
            (SHA-256 hash, count archived)
        """
        import hashlib
        
        # Get oldest records
        oldest_pos = (self._write_ptr - self._count) % self._capacity
        records_data = []
        
        for i in range(min(n, self._count)):
            pos = (oldest_pos + i) % self._capacity
            record = self._buffer[pos]
            if record is not None:
                records_data.append(record.to_bytes())
        
        if not records_data:
            return b'\x00' * 32, 0
        
        combined = b''.join(records_data)
        hash_bytes = hashlib.sha256(combined).digest()
        
        return hash_bytes, len(records_data)
    
    def clear(self) -> None:
        """Clear all records."""
        self._buffer = [None] * self._capacity
        self._write_ptr = 0
        self._count = 0
        self._index.clear()


# =============================================================================
# PMA Store (Window-Based)
# =============================================================================

class PMAStore:
    """
    Window-based PMA storage with circular buffer backend.
    
    Provides allocate/get/put interface for coherence windows.
    """
    
    def __init__(self, buffer_capacity: int = 256):
        self._buffer = PMABuffer(buffer_capacity)
        self._next_window_id = 1
    
    def allocate(self) -> int:
        """
        Allocate new window ID.
        
        Returns:
            New window ID (1-4094)
        """
        wid = self._next_window_id
        self._next_window_id = (self._next_window_id % WINDOW_ID_MAX) + 1
        return wid
    
    def record(
        self,
        window_id: int,
        address: RPPAddress,
        consent_state: ConsentState,
        coherence: float,
        **kwargs
    ) -> PMARecord:
        """
        Create and store PMA record.
        
        Returns:
            The created PMARecord
        """
        record = PMARecord.create(
            window_id=window_id,
            address=address,
            consent_state=consent_state,
            coherence=coherence,
            **kwargs
        )
        self._buffer.write(record)
        return record
    
    def get(self, window_id: int) -> Optional[PMARecord]:
        """Get record by window ID."""
        return self._buffer.get(window_id)
    
    def get_recent(self, n: int = 10) -> list[PMARecord]:
        """Get N most recent records."""
        return self._buffer.get_latest(n)
    
    @property
    def count(self) -> int:
        """Number of records in store."""
        return self._buffer.count


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    from rpp.address_canonical import create_from_sector, ThetaSector
    
    print("Phase Memory Anchor (PMA) v1.1")
    print("=" * 60)
    print(f"Record size: {PMA_RECORD_SIZE} bytes ({PMA_RECORD_BITS} bits)")
    
    # Create test address
    addr = create_from_sector(ThetaSector.MEMORY, phi=3, omega=2, radius=0.75)
    print(f"\nTest address: {addr}")
    
    # Create PMA record
    record = PMARecord.create(
        window_id=0x1A2,
        address=addr,
        consent_state=ConsentState.FULL_CONSENT,
        coherence=0.85,
        complecount=5,
        payload_type=PayloadType.HUMAN,
        fallback_used=False,
    )
    
    print(f"\nCreated: {record}")
    print(f"  Coherence: {record.coherence_normalized:.3f}")
    secs, nanos = record.get_timestamp_parts()
    print(f"  Timestamp: {secs}s + {nanos}ns")
    
    # Encode/decode roundtrip
    encoded = record.to_bytes()
    print(f"\nEncoded ({len(encoded)} bytes): {encoded.hex()}")
    
    decoded = PMARecord.from_bytes(encoded)
    print(f"Decoded: {decoded}")
    
    # Verify fields match
    assert decoded.window_id == record.window_id
    assert decoded.phase_vector == record.phase_vector
    assert decoded.consent_state == record.consent_state
    assert decoded.complecount_score == record.complecount_score
    assert decoded.coherence_score == record.coherence_score
    assert decoded.payload_type == record.payload_type
    assert decoded.fallback_triggered == record.fallback_triggered
    print("✓ Roundtrip verification passed")
    
    # Test buffer
    print("\n--- PMA Buffer Test ---")
    buffer = PMABuffer(capacity=8)
    print(f"Buffer capacity: {buffer.capacity} records ({buffer.memory_bytes} bytes)")
    
    # Write some records
    for i in range(5):
        addr = create_from_sector(ThetaSector.MEMORY, phi=3, omega=i % 5, radius=0.5 + i * 0.1)
        rec = PMARecord.create(
            window_id=0x100 + i,
            address=addr,
            consent_state=ConsentState.FULL_CONSENT,
            coherence=0.7 + i * 0.05,
        )
        buffer.write(rec)
    
    print(f"Records written: {buffer.count}")
    
    # Lookup
    rec = buffer.get(0x102)
    print(f"Lookup 0x102: {rec}")
    
    # Recent
    recent = buffer.get_latest(3)
    print(f"Recent 3: {[r.window_id for r in recent]}")
    
    # Dict output
    print("\nRecord as dict:")
    for k, v in record.to_dict().items():
        print(f"  {k}: {v}")
