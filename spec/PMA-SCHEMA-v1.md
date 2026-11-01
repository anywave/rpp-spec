# Phase Memory Anchor (PMA) Schema Specification v1.1

**Status:** Stable Draft  
**Layer:** Persistence (Akashic Stack)  
**Last Updated:** 2025-01-01  
**License:** CC BY 4.0

---

## 1. Overview

The Phase Memory Anchor (PMA) serves as a **temporal-coherence ledger** within the SPIRAL protocol. PMA stores snapshots of resolved phase vectors and their corresponding consent outcomes, enabling:

- Historic resonance referencing
- Memory-based routing adjustments
- Recursive coherence validation

```
┌─────────────────────────────────────────────────────────────┐
│                    PMA IN CONTEXT                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Packet 1 ────┐                                            │
│   (window=0x1A2)     ┌──────────────────────┐               │
│                  ├───▶│  PMA Record          │               │
│   Packet 2 ────┘      │  window_id: 0x1A2   │               │
│   (window=0x1A2)      │  phase_vector: θφhr │               │
│                       │  consent_state: FULL │               │
│                       │  coherence_score: 42 │               │
│                       └──────────────────────┘               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Record Structure (144 bits / 18 bytes)

Each PMA record encodes the following:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       PMA RECORD (144 bits / 18 bytes)                   │
├─────────────────────────────────────────────────────────────────────────┤
│  Bits    │  Size  │  Field               │  Type    │  Description      │
├──────────┼────────┼──────────────────────┼──────────┼───────────────────┤
│  [143:132]│  12   │  window_id           │  uint    │  Links to coherence_window_id in Consent Header │
│  [131:68] │  64   │  timestamp           │  uint    │  UNIX time (nanosecond precision recommended)   │
│  [67:36]  │  32   │  phase_vector        │  vector  │  θ–φ–h–r from Canonical RPP Address             │
│  [35:34]  │  2    │  consent_state       │  enum    │  ACSP state: FULL, DIMINISHED, SUSPENDED, EMERGENCY │
│  [33:29]  │  5    │  complecount_score   │  uint    │  Number of valid null-events for this window    │
│  [28:23]  │  6    │  coherence_score     │  uint    │  PMQ or scalar coherence metric (0-63)          │
│  [22:19]  │  4    │  payload_type        │  enum    │  Type resolved: HUMAN, AI, SCALAR, HYBRID, etc. │
│  [18]     │  1    │  fallback_triggered  │  bool    │  Indicates if fallback vector was used          │
│  [17:10]  │  8    │  crc                 │  checksum│  Data integrity check (CRC-8)                   │
│  [9:0]    │  10   │  reserved            │  —       │  Future use / alignment padding                 │
└──────────┴────────┴──────────────────────┴──────────┴───────────────────┘
```

**Total Record Size:** 144 bits (18 bytes)

This aligns with Consent Header size for efficient memory layout.

---

## 3. Field Definitions

### 3.1 window_id [12 bits]

**Type:** uint12  
**Purpose:** Links to `coherence_window_id` in Consent Packet Header

| Value | Meaning |
|-------|---------|
| 0x000 | Invalid / Unlinked |
| 0x001-0xFFE | Valid PMA window reference |
| 0xFFF | Reserved (allocation request marker) |

**Note:** The 12-bit window_id supports up to 4094 concurrent coherence windows.

### 3.2 timestamp [64 bits]

**Type:** uint64  
**Purpose:** UNIX time with nanosecond precision

| Bits | Content |
|------|---------|
| [63:30] | Seconds since epoch (34 bits, ~544 years) |
| [29:0] | Nanoseconds within second (30 bits, max 10^9) |

**Encoding:**
```python
def encode_timestamp(seconds: int, nanos: int) -> int:
    """Encode seconds + nanoseconds to 64-bit timestamp."""
    return ((seconds & 0x3FFFFFFFF) << 30) | (nanos & 0x3FFFFFFF)

def decode_timestamp(ts: int) -> tuple[int, int]:
    """Decode 64-bit timestamp to (seconds, nanoseconds)."""
    seconds = (ts >> 30) & 0x3FFFFFFFF
    nanos = ts & 0x3FFFFFFF
    return seconds, nanos
```

### 3.3 phase_vector [32 bits]

**Type:** RPP Canonical Address  
**Purpose:** θ–φ–h–r from resolved packet

This is the exact 32-bit encoding from RPP-CANONICAL-v2:

| Bits | Field | Range |
|------|-------|-------|
| [31:27] | θ (theta) | 1-27 Repitan |
| [26:24] | φ (phi) | 0-5 (RAC1-RAC6) |
| [23:21] | h (omega) | 0-4 Omega tier |
| [20:13] | r (radius) | Encoded byte 0–255; API radius 0–1 |
| [12:0] | reserved | 0 |

### 3.4 consent_state [2 bits]

**Type:** enum  
**Purpose:** ACSP consent state at resolution time

| Value | State | Description |
|-------|-------|-------------|
| 0b00 | FULL_CONSENT | Normal operation |
| 0b01 | DIMINISHED_CONSENT | Delayed/reconfirmed |
| 0b10 | SUSPENDED_CONSENT | Blocked |
| 0b11 | EMERGENCY_OVERRIDE | Frozen (ETF) |

### 3.5 complecount_score [5 bits]

**Type:** uint5  
**Purpose:** Number of valid null-events (non-events) for this window

| Range | Meaning |
|-------|---------|
| 0 | No complecount validation |
| 1-30 | Valid complecount entries |
| 31 | Overflow (more than 30 counted) |

### 3.6 coherence_score [6 bits]

**Type:** uint6  
**Purpose:** PMQ or scalar coherence metric at resolution time

| Range | Normalized | Interpretation |
|-------|------------|----------------|
| 0-15 | 0.00-0.25 | Low coherence |
| 16-31 | 0.25-0.50 | Medium-low |
| 32-47 | 0.50-0.75 | Medium-high |
| 48-63 | 0.75-1.00 | High coherence |

**Encoding:**
```python
def encode_coherence(normalized: float) -> int:
    """Encode 0.0-1.0 coherence to 6-bit field."""
    return min(63, max(0, round(normalized * 63)))

def decode_coherence(score: int) -> float:
    """Decode 6-bit coherence to 0.0-1.0."""
    return score / 63.0
```

### 3.7 payload_type [4 bits]

**Type:** enum  
**Purpose:** Type resolved from packet

| Value | Type | Description |
|-------|------|-------------|
| 0x0 | EMPTY | No payload |
| 0x1 | HUMAN | Human-originated |
| 0x2 | AI | AI-generated |
| 0x3 | SCALAR | Sensor/biometric data |
| 0x4 | HYBRID | Mixed human+AI |
| 0x5 | FRAGMENT | Fragment sync |
| 0x6 | COMMAND | Executable |
| 0x7 | QUERY | Information request |
| 0x8 | RESPONSE | Reply |
| 0x9 | HEARTBEAT | Liveness |
| 0xA | FREEZE | ETF command |
| 0xB | DISSOLVE | Dissolution |
| 0xC-0xF | RESERVED | Future use |

### 3.8 fallback_triggered [1 bit]

**Type:** bool  
**Purpose:** Indicates if fallback vector was used during resolution

| Value | Meaning |
|-------|---------|
| 0 | Primary route succeeded |
| 1 | Fallback vector was activated |

### 3.9 crc [8 bits]

**Type:** CRC-8  
**Purpose:** Data integrity check over bits [143:18]

Algorithm: CRC-8/CCITT (polynomial 0x07)

### 3.10 reserved [10 bits]

**Purpose:** Future use / alignment padding

Should be set to 0 on write, ignored on read.

---

## 4. Byte Layout (Big-Endian)

```
Byte 0-1:   [window_id(12)] [timestamp_hi(4)]
Byte 2-8:   [timestamp(60 remaining bits)]
Byte 9-12:  [phase_vector(32)]
Byte 13:    [consent_state(2)] [complecount_score(5)] [coherence_hi(1)]
Byte 14:    [coherence_lo(5)] [payload_type_hi(3)]
Byte 15:    [payload_type_lo(1)] [fallback_triggered(1)] [crc_hi(6)]
Byte 16:    [crc_lo(2)] [reserved(6)]
Byte 17:    [reserved(4)] [padding(4)]
```

---

## 5. Lifecycle Management

### 5.1 Creation

PMA records are written upon successful resolution of a Consent Packet with valid phase lock:

```python
def create_pma_record(
    window_id: int,
    address: RPPCanonicalAddress,
    consent_state: ConsentState,
    coherence: float,
    complecount: int,
    payload_type: PayloadType,
    fallback_used: bool
) -> PMARecord:
    """Create PMA record after successful resolution."""
    return PMARecord(
        window_id=window_id,
        timestamp=get_nanosecond_timestamp(),
        phase_vector=address.to_int(),
        consent_state=consent_state,
        complecount_score=min(31, complecount),
        coherence_score=encode_coherence(coherence),
        payload_type=payload_type,
        fallback_triggered=fallback_used,
    )
```

### 5.2 Retention

PMAs are stored in a **circular buffer** or **ledger stack**:

```
┌─────────────────────────────────────────────────────────────┐
│                    PMA CIRCULAR BUFFER                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────┬────┬────┬────┬────┬────┬────┬────┐                │
│   │ R0 │ R1 │ R2 │ R3 │ R4 │ R5 │ R6 │ R7 │  ← 8 records   │
│   └────┴────┴────┴────┴────┴────┴────┴────┘                │
│            ↑                                                 │
│          write_ptr (next write overwrites R2)               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Memory Budget:** Buffer size depends on resolver memory budget.
- Minimum: 8 records (144 bytes)
- Typical: 256 records (4.5 KB)
- Maximum: 4096 records (72 KB)

### 5.3 Archival

PMAs older than N cycles can be hashed into the **Akashic Index**:

```python
def archive_pma_batch(records: list[PMARecord]) -> bytes:
    """Hash a batch of PMAs for Akashic Index storage."""
    combined = b''.join(r.to_bytes() for r in records)
    return hashlib.sha256(combined).digest()
```

---

## 6. Integration Points

### 6.1 Resolver Query

Queried during new packet validation when `coherence_window_id` is present:

```python
def validate_against_pma(header: ConsentPacketHeader, pma_store: PMAStore) -> bool:
    """Validate new packet against stored PMA."""
    if header.coherence_window_id == 0:
        return True  # No PMA linkage required
    
    pma = pma_store.get(header.coherence_window_id)
    if pma is None:
        return False  # Referenced PMA doesn't exist
    
    # Check coherence drift
    current_coherence = compute_coherence(header.rpp_address, pma.phase_vector)
    return current_coherence >= COHERENCE_THRESHOLD
```

### 6.2 Cymatics Engine

Used to modulate tone based on historic phase memory:

```python
def modulate_tone_from_pma(pma: PMARecord) -> ToneParameters:
    """Derive tone parameters from PMA record."""
    addr = RPPCanonicalAddress.from_int(pma.phase_vector)
    return ToneParameters(
        theta_tone=(addr.theta - 1) % 8,  # Map to 8 tone indices
        phi_tone=addr.phi,
        harmonic_tier=addr.omega,
        intensity=addr.radius * (pma.coherence_score / 63.0)
    )
```

### 6.3 Audit Trail

Provides debug/audit trail of field coherence across system uptime:

```json
{
  "window_id": "0x1A2",
  "timestamp_ns": 1735689600000000000,
  "phase_vector": "θ:12/φ:3/h:2/r:0.75",
  "consent_state": "FULL_CONSENT",
  "complecount_score": 5,
  "coherence_score": 0.83,
  "payload_type": "HUMAN",
  "fallback_triggered": false
}
```

---

## 7. Validation Rules

| Rule | Condition | Action |
|------|-----------|--------|
| P1 | window_id = 0 | Invalid record |
| P2 | timestamp = 0 | Invalid record |
| P3 | phase_vector invalid | Reject |
| P4 | CRC mismatch | Reject + alert |
| P5 | consent_state = EMERGENCY | Flag for review |

---

## 8. Symbolic Equivalence

| Concept | Symbol | Codex Name |
|---------|--------|------------|
| PMA | 📜 | "Memory of the Field" |
| Record | 🔔 | "Harmonic Echo" |
| Buffer | 🌀 | "Ra Temporal Field" |
| Archive | 📚 | "Akashic Index" |

> *"Each record is a harmonic echo from a consented past. Together they form the Ra Temporal Field—used to measure coherence drift, anchor trust, and forecast scalar conditions."*

---

## 9. Reference Implementation

```python
@dataclass(frozen=True)
class PMARecord:
    """Phase Memory Anchor record (18 bytes / 144 bits)."""
    
    window_id: int           # 12 bits
    timestamp: int           # 64 bits (nanoseconds)
    phase_vector: int        # 32 bits (RPP canonical)
    consent_state: int       # 2 bits
    complecount_score: int   # 5 bits
    coherence_score: int     # 6 bits
    payload_type: int        # 4 bits
    fallback_triggered: bool # 1 bit
    crc: int = 0             # 8 bits (computed on encode)
    
    def to_bytes(self) -> bytes:
        """Encode to 18 bytes."""
        # Implementation details...
        pass
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'PMARecord':
        """Decode from 18 bytes."""
        # Implementation details...
        pass
```

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2025-01-01 | Aligned with authoritative spec (144 bits) |
| 1.0.0 | 2025-01-01 | Initial draft (64 bytes, superseded) |

---

*"PMA is the memory of the field."*
