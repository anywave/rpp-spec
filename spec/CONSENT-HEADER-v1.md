# SPIRAL Consent Packet Header Specification v1.0

**Status:** Draft  
**Layer:** System (wraps RPP Canonical Address)  
**Last Updated:** 2025-01-01  
**License:** CC BY 4.0

---

## 1. Overview

The Consent Packet Header is **not** part of the RPP address—it is a **system-layer envelope** that wraps an RPP address with consent state, integrity markers, and Phase Memory Anchor linkage.

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER SEPARATION                          │
├─────────────────────────────────────────────────────────────┤
│  SPIRAL Envelope    │ Signatures, Origin Hash, Fragment ID  │
├─────────────────────┼───────────────────────────────────────┤
│  Consent Header     │ Consent state, PMA link, Complecount  │  ← This spec
├─────────────────────┼───────────────────────────────────────┤
│  RPP Address        │ θ, φ, h, r (Ra-derived coordinates)   │  ← RPP-CANONICAL-v2
├─────────────────────┼───────────────────────────────────────┤
│  Payload            │ Application data                      │
└─────────────────────┴───────────────────────────────────────┘
```

---

## 2. Header Structure (144 bits / 18 bytes)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SPIRAL CONSENT PACKET HEADER                          │
│                          (144 bits / 18 bytes)                           │
├─────────────────────────────────────────────────────────────────────────┤
│  Byte 0-3:   RPP Canonical Address (32 bits)                            │
│  Byte 4-7:   Packet ID (32 bits)                                        │
│  Byte 8-9:   Origin Avatar Reference (16 bits)                          │
│  Byte 10:    Consent Fields (8 bits)                                    │
│  Byte 11:    Phase Entropy + Complecount (8 bits)                       │
│  Byte 12:    Temporal + Payload Type (8 bits)                           │
│  Byte 13:    Fallback Vector (8 bits)                                   │
│  Byte 14-15: Coherence Window ID (16 bits)                              │
│  Byte 16:    Target Phase Reference (8 bits)                            │
│  Byte 17:    Header CRC (8 bits)                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Field Definitions

### 3.1 RPP Canonical Address [Bytes 0-3, 32 bits]

**Type:** RPP Canonical Address v2.0  
**Contents:** Ra-derived θ/φ/h/r coordinates  
**Reference:** See RPP-CANONICAL-v2.md

```
┌─────────┬─────────┬─────────┬──────────┬───────────────────┐
│    θ    │    φ    │    h    │    r     │    Reserved       │
│ (5 bits)│ (3 bits)│ (3 bits)│ (8 bits) │    (13 bits)      │
└─────────┴─────────┴─────────┴──────────┴───────────────────┘
```

### 3.2 Packet ID [Bytes 4-7, 32 bits]

**Type:** uint32  
**Purpose:** Unique identifier for traceability and deduplication

| Bits | Field | Description |
|------|-------|-------------|
| [31:16] | Timestamp Hash | Upper 16 bits of millisecond timestamp hash |
| [15:0] | Sequence | Per-origin sequence counter |

### 3.3 Origin Avatar Reference [Bytes 8-9, 16 bits]

**Type:** uint16  
**Purpose:** Compressed reference to origin avatar (full hash stored elsewhere)

| Value | Meaning |
|-------|---------|
| 0x0000 | Self-reference (same origin as router context) |
| 0x0001-0xFFFE | Avatar reference index (lookup in registry) |
| 0xFFFF | Broadcast (no specific origin) |

### 3.4 Consent Fields [Byte 10, 8 bits]

```
┌───────────┬───────────┬─────────────┬────────────────┐
│ consent_v │ consent_s │ consent_a   │ temporal_lock  │
│  (1 bit)  │  (4 bits) │  (3 bits)   │    (1 bit)     │
└───────────┴───────────┴─────────────┴────────────────┘
  [7]         [6:3]       [2:1]          [0]
```

| Field | Bits | Description |
|-------|------|-------------|
| consent_verbal | [7] | Explicit verbal consent flag (1=yes) |
| consent_somatic | [6:3] | Body-aligned field score (0-15 → 0.0-1.0) |
| consent_ancestral | [2:1] | Lineage-verified inheritance layer (0-3) |
| temporal_lock | [0] | Prevents re-routing before phase shift |

**consent_somatic encoding:**
```python
def encode_consent_somatic(value: float) -> int:
    """Encode 0.0-1.0 to 4-bit field."""
    return min(15, max(0, round(value * 15)))

def decode_consent_somatic(bits: int) -> float:
    """Decode 4-bit field to 0.0-1.0."""
    return bits / 15.0
```

**consent_ancestral values:**
| Value | Meaning |
|-------|---------|
| 0 | NONE - No ancestral consent |
| 1 | INHERITED - Lineage-verified |
| 2 | DELEGATED - Granted by ancestor |
| 3 | SOVEREIGN - Self-sovereign override |

### 3.5 Phase Entropy + Complecount [Byte 11, 8 bits]

```
┌────────────────────┬───────────────────┐
│ phase_entropy_idx  │ complecount_trace │
│     (5 bits)       │     (3 bits)      │
└────────────────────┴───────────────────┘
      [7:3]                [2:0]
```

| Field | Bits | Range | Description |
|-------|------|-------|-------------|
| phase_entropy_index | [7:3] | 0-31 | Historical coherence volatility measure |
| complecount_trace | [2:0] | 0-7 | Number of non-events tracked (complecounting) |

**Validation Rules:**
- If consent_somatic < 0.3 (bits < 5), complecount_trace MUST be > 0
- phase_entropy_index > 25 activates fallback_vector routing

### 3.6 Temporal + Payload Type [Byte 12, 8 bits]

```
┌────────────────┬──────────────────┐
│  reserved_t    │   payload_type   │
│   (4 bits)     │     (4 bits)     │
└────────────────┴──────────────────┘
     [7:4]             [3:0]
```

| Field | Bits | Description |
|-------|------|-------------|
| reserved_t | [7:4] | Reserved for temporal extensions |
| payload_type | [3:0] | Payload origin/type indicator |

**payload_type values:**
| Value | Type | Description |
|-------|------|-------------|
| 0x0 | EMPTY | No payload |
| 0x1 | HUMAN | Human-originated content |
| 0x2 | AI | AI-generated content |
| 0x3 | SCALAR | Scalar/sensor data |
| 0x4 | HYBRID | Mixed human+AI |
| 0x5 | FRAGMENT | Fragment sync data |
| 0x6 | COMMAND | Executable instruction |
| 0x7 | QUERY | Information request |
| 0x8 | RESPONSE | Reply to query |
| 0x9 | HEARTBEAT | Liveness probe |
| 0xA | FREEZE | ETF freeze command |
| 0xB | DISSOLVE | Fragment dissolution |
| 0xC-0xF | RESERVED | Future use |

### 3.7 Fallback Vector [Byte 13, 8 bits]

**Type:** uint8  
**Purpose:** XOR-derived alternate route vector for degraded routing

```
┌────────────┬────────────┬────────────┐
│  alt_theta │  alt_phi   │ alt_harm   │
│  (3 bits)  │  (3 bits)  │  (2 bits)  │
└────────────┴────────────┴────────────┘
    [7:5]       [4:2]        [1:0]
```

| Field | Bits | Description |
|-------|------|-------------|
| alt_theta | [7:5] | Theta sector offset (0-7, XOR with primary) |
| alt_phi | [4:2] | Phi level offset (0-7, XOR with primary) |
| alt_harm | [1:0] | Harmonic offset (0-3, XOR with primary) |

**Activation:** Fallback vector activates when:
- phase_entropy_index > 25
- Primary route returns BLOCKED or UNAVAILABLE
- Coherence score below threshold

**Fallback address computation:**
```python
def compute_fallback(primary: RPPCanonicalAddress, fallback_vec: int) -> RPPCanonicalAddress:
    alt_theta = (fallback_vec >> 5) & 0x07
    alt_phi = (fallback_vec >> 2) & 0x07
    alt_harm = fallback_vec & 0x03
    
    new_theta = ((primary.theta - 1) ^ alt_theta) % 27 + 1
    new_phi = ((primary.phi - 1) ^ alt_phi) % 6 + 1
    new_harm = (primary.harmonic ^ alt_harm) % 5
    
    return RPPCanonicalAddress(
        theta=new_theta,
        phi=new_phi,
        harmonic=new_harm,
        radius=primary.radius
    )
```

### 3.8 Coherence Window ID [Bytes 14-15, 16 bits]

**Type:** uint16  
**Purpose:** Links to Phase Memory Anchor (PMA) batch

| Value | Meaning |
|-------|---------|
| 0x0000 | No PMA linkage (stateless packet) |
| 0x0001-0xFFFE | PMA window identifier |
| 0xFFFF | New window request (allocate on arrival) |

**PMA Integration:**
- coherence_window_id references a PMA batch for multi-window validation
- Packets with same window_id share coherence context
- Window lifecycle managed by Akashic Stack

### 3.9 Target Phase Reference [Byte 16, 8 bits]

**Type:** uint8  
**Purpose:** Harmonic vector for phase matching at destination

```
┌────────────┬────────────┬────────────┐
│ phase_θ    │ phase_φ    │ phase_h    │
│  (3 bits)  │  (3 bits)  │  (2 bits)  │
└────────────┴────────────┴────────────┘
    [7:5]       [4:2]        [1:0]
```

Used by Cymatics Engine for tone pattern matching.

### 3.10 Header CRC [Byte 17, 8 bits]

**Type:** uint8  
**Algorithm:** CRC-8/CCITT (polynomial 0x07)  
**Scope:** Bytes 0-16 (all preceding header fields)

```python
def compute_header_crc(header_bytes: bytes) -> int:
    """Compute CRC-8 over header bytes 0-16."""
    crc = 0x00
    for byte in header_bytes[:17]:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
            crc &= 0xFF
    return crc
```

---

## 4. Validation Rules

### 4.1 Structural Validation

| Rule | Condition | Action on Failure |
|------|-----------|-------------------|
| V1 | Header length = 18 bytes | Reject packet |
| V2 | CRC matches computed | Reject packet |
| V3 | RPP address valid (θ∈1-27, φ∈1-6, h∈0-4) | Reject packet |
| V4 | payload_type ∈ valid set | Reject packet |

### 4.2 Consent Validation

| Rule | Condition | Action on Failure |
|------|-----------|-------------------|
| C1 | consent_somatic < 0.3 → complecount_trace > 0 | Delay + reconfirm |
| C2 | consent_verbal = 0 AND consent_somatic < 0.5 | Route with caution |
| C3 | temporal_lock = 1 AND phase_shifted | Block until unlock |

### 4.3 Routing Validation

| Rule | Condition | Action on Failure |
|------|-----------|-------------------|
| R1 | phase_entropy_index > 25 | Activate fallback vector |
| R2 | coherence_window_id ≠ 0 → PMA exists | Queue for PMA resolution |

---

## 5. Integration Points

### 5.1 SPIRAL Resolver

```python
def resolve_with_consent_header(header: ConsentPacketHeader) -> RouteResult:
    # 1. Validate header structure
    if not header.validate_crc():
        return RouteResult.INVALID_HEADER
    
    # 2. Extract RPP address
    rpp_addr = header.rpp_address
    
    # 3. Check consent state
    consent_state = derive_consent_state(header)
    if consent_state == ConsentState.SUSPENDED:
        return RouteResult.BLOCKED
    
    # 4. Check phase entropy for fallback
    if header.phase_entropy_index > 25:
        fallback_addr = compute_fallback(rpp_addr, header.fallback_vector)
        # Try fallback route
    
    # 5. Link to PMA if present
    if header.coherence_window_id != 0:
        pma = akashic_stack.get_pma(header.coherence_window_id)
        # Validate against PMA context
    
    # 6. Route via standard resolver
    return spiral_resolver.resolve(rpp_addr, consent_state)
```

### 5.2 Cymatics Engine

The target_phase_ref field is parsed by the Cymatics Engine for tone pattern matching:

```python
def match_tone_pattern(header: ConsentPacketHeader) -> ToneMatch:
    phase_ref = header.target_phase_ref
    theta_tone = (phase_ref >> 5) & 0x07
    phi_tone = (phase_ref >> 2) & 0x07
    harm_tone = phase_ref & 0x03
    
    return cymatics_engine.find_resonance(theta_tone, phi_tone, harm_tone)
```

### 5.3 SCL Logging

All consent headers are logged to the Semantic Consent Ledger:

```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "packet_id": "0x12345678",
  "rpp_address": "θ:12/φ:3/h:2/r:0.75",
  "consent_somatic": 0.73,
  "consent_verbal": true,
  "complecount_trace": 2,
  "phase_entropy_index": 18,
  "coherence_window_id": "0x1A2B",
  "route_result": "DELIVERED"
}
```

---

## 6. Symbolic Mapping

| Field | Symbol | Codex Name |
|-------|--------|------------|
| Consent Header | 📜 | "Avatar's vibrational passport" |
| consent_verbal | 🗣️ | "Spoken yes" |
| consent_somatic | 🫀 | "Body's truth" |
| consent_ancestral | 👁️‍🗨️ | "Lineage witness" |
| complecount_trace | 🤫 | "The unbroken no" |
| fallback_vector | 🔀 | "Alternate path" |
| coherence_window_id | 🪟 | "Memory anchor" |

---

## 7. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-01 | Initial specification |

---

---

## See Also

- [DEPLOYABLE.md](DEPLOYABLE.md) — GDPR/HIPAA/IoT deployment context governing consent level requirements
- [NETWORK.md](NETWORK.md) — How consent fields propagate and are enforced across the consent-field mesh

*"This is not metadata. This is consent made coherent."*
