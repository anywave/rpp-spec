# RPP Canonical Address Specification v2.0

**Status:** Draft  
**Derived From:** Ra Constants (Wesley H. Bateman, 1992-1997)  
**Last Updated:** 2025-01-01  
**License:** CC BY 4.0

---

## 1. Design Principle

The RPP address is not an arbitrary bit allocation—it is a **projection of resonance into symbolic topology**. Every field derives from Ra System constants:

| Field | Ra Source | Symbolic Function |
|-------|-----------|-------------------|
| θ (Theta) | 27 Repitans | Semantic sector (meaning domain) |
| φ (Phi) | 6 RAC Levels | Access sensitivity (consent depth) |
| h (Harmonic) | 5 Omega Formats | Coherence tier (frequency precision) |
| r (Radius) | Ankh-normalized | Intensity scalar (emergence strength) |

---

## 2. Canonical Address Format (32 bits)

```
┌─────────────────────────────────────────────────────────────┐
│                   RPP CANONICAL ADDRESS                      │
│                        (32 bits)                             │
├─────────┬─────────┬─────────┬──────────┬───────────────────┤
│    θ    │    φ    │    h    │    r     │    Reserved/CRC   │
│ (5 bits)│ (3 bits)│ (3 bits)│ (8 bits) │    (13 bits)      │
├─────────┼─────────┼─────────┼──────────┼───────────────────┤
│  [31:27]│  [26:24]│  [23:21]│  [20:13] │      [12:0]       │
└─────────┴─────────┴─────────┴──────────┴───────────────────┘
```

### 2.1 Byte Layout (Big-Endian)

```
Byte 0          Byte 1          Byte 2          Byte 3
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ θθθθθ φφφ    │ hhh rrrrr    │ rrr RRRRR    │ RRRRRRRR    │
└──────────────┴──────────────┴──────────────┴──────────────┘
  [31:24]        [23:16]        [15:8]         [7:0]

θ = Theta (Repitan)
φ = Phi (RAC Level)
h = Harmonic (Omega Format)
r = Radius (Intensity)
R = Reserved/CRC
```

---

## 3. Field Definitions

### 3.1 Theta (θ) — Semantic Sector [5 bits]

**Source:** 27 Repitans from Ra System  
**Range:** 0-31 (5 bits)  
**Valid:** 1-27 (Repitan indices)  
**Reserved:** 0, 28-31

| Value | Mapping | Notes |
|-------|---------|-------|
| 0 | INVALID | Null/uninitialized address |
| 1-27 | Repitan(n) | Semantic sector n/27 |
| 28 | RESERVED_28 | Future: inverse vector |
| 29 | RESERVED_29 | Future: meta-sector |
| 30 | RESERVED_30 | Future: bridge vector |
| 31 | WILDCARD | Match any sector |

**Encoding:**
```python
def encode_theta(repitan_index: int) -> int:
    """Encode Repitan index (1-27) to theta field."""
    if not 1 <= repitan_index <= 27:
        raise ValueError(f"Repitan must be 1-27, got {repitan_index}")
    return repitan_index  # Direct mapping

def decode_theta(theta: int) -> int | None:
    """Decode theta field to Repitan index."""
    if 1 <= theta <= 27:
        return theta
    return None  # Invalid or reserved
```

### 3.2 Phi (φ) — Access Sensitivity [3 bits]

**Source:** 6 RAC Levels from Ra System  
**Range:** 0-7 (3 bits)  
**Valid:** 0-5 (RAC1 through RAC6)  
**Reserved:** 6-7

| Value | RAC Level | Access Band | Notes |
|-------|-----------|-------------|-------|
| 0 | RAC1 | Highest access (0.6362) | Least restrictive |
| 1 | RAC2 | High access (0.6283) | Balmer-aligned |
| 2 | RAC3 | Medium-high (0.5726) | Phi × Hunab × 1/3 |
| 3 | RAC4 | Medium (0.5236) | π/6, Royal Cubit |
| 4 | RAC5 | Low (0.4580) | Ankh × 9 / 100 |
| 5 | RAC6 | Lowest access (0.3999) | Most restrictive |
| 6 | OVERRIDE | System override | ETF/Emergency |
| 7 | WILDCARD | Match any level | Broadcast |

**Encoding:**
```python
def encode_phi(rac_level: int) -> int:
    """Encode RAC level (1-6) to phi field."""
    if not 1 <= rac_level <= 6:
        raise ValueError(f"RAC level must be 1-6, got {rac_level}")
    return rac_level - 1  # RAC1=0, RAC6=5

def decode_phi(phi: int) -> int | None:
    """Decode phi field to RAC level (1-6)."""
    if 0 <= phi <= 5:
        return phi + 1
    return None  # Reserved
```

### 3.3 Harmonic (h) — Coherence Tier [3 bits]

**Source:** 5 Omega Formats from Ra System  
**Range:** 0-7 (3 bits)  
**Valid:** 0-4 (Red through Blue)  
**Reserved:** 5-7

| Value | Omega Format | Tier | Notes |
|-------|--------------|------|-------|
| 0 | RED | Highest precision | Raw/unscaled |
| 1 | OMEGA_MAJOR | High precision | Spectral lines |
| 2 | GREEN | Standard | Default tier |
| 3 | OMEGA_MINOR | Reduced | Compressed |
| 4 | BLUE | Lowest precision | Archive/cold |
| 5 | RESERVED_5 | Future use | — |
| 6 | RESERVED_6 | Future use | — |
| 7 | WILDCARD | Match any tier | Discovery |

**Encoding:**
```python
def encode_harmonic(omega_index: int) -> int:
    """Encode Omega format index (0-4) to harmonic field."""
    if not 0 <= omega_index <= 4:
        raise ValueError(f"Omega index must be 0-4, got {omega_index}")
    return omega_index  # Direct mapping

def decode_harmonic(h: int) -> int | None:
    """Decode harmonic field to Omega format index."""
    if 0 <= h <= 4:
        return h
    return None  # Reserved
```

### 3.4 Radius (r) — Intensity Scalar [8 bits]

**Source:** Ankh-normalized [0, 1]  
**Range:** 0-255 (8 bits)  
**Mapping:** r_normalized = r_raw / 255

| Value | Normalized | Interpretation |
|-------|------------|----------------|
| 0 | 0.000 | Minimal/dormant |
| 64 | 0.251 | Low intensity |
| 128 | 0.502 | Medium intensity |
| 192 | 0.753 | High intensity |
| 255 | 1.000 | Maximum/saturated |

**Encoding:**
```python
def encode_radius(normalized: float) -> int:
    """Encode normalized radius [0,1] to 8-bit field."""
    if not 0.0 <= normalized <= 1.0:
        raise ValueError(f"Radius must be 0-1, got {normalized}")
    return round(normalized * 255)

def decode_radius(r: int) -> float:
    """Decode 8-bit radius to normalized value."""
    return r / 255.0
```

### 3.5 Reserved/CRC [13 bits]

**Usage:** Implementation-defined  
**Options:**
- CRC-13 for integrity checking
- Fragment ID suffix
- Routing hints
- All zeros (minimal mode)

---

## 4. Address Construction

### 4.1 Python Reference Implementation

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class RPPCanonicalAddress:
    """Ra-derived RPP canonical address (32 bits)."""
    
    theta: int      # Repitan index 1-27
    phi: int        # RAC level 1-6
    harmonic: int   # Omega index 0-4
    radius: float   # Normalized 0.0-1.0
    reserved: int = 0  # 13-bit reserved/CRC
    
    def __post_init__(self):
        if not 1 <= self.theta <= 27:
            raise ValueError(f"theta must be 1-27, got {self.theta}")
        if not 1 <= self.phi <= 6:
            raise ValueError(f"phi must be 1-6, got {self.phi}")
        if not 0 <= self.harmonic <= 4:
            raise ValueError(f"harmonic must be 0-4, got {self.harmonic}")
        if not 0.0 <= self.radius <= 1.0:
            raise ValueError(f"radius must be 0-1, got {self.radius}")
        if not 0 <= self.reserved <= 0x1FFF:
            raise ValueError(f"reserved must be 0-8191, got {self.reserved}")
    
    def to_raw(self) -> int:
        """Encode to 32-bit integer."""
        theta_enc = self.theta & 0x1F           # 5 bits
        phi_enc = (self.phi - 1) & 0x07         # 3 bits
        h_enc = self.harmonic & 0x07            # 3 bits
        r_enc = round(self.radius * 255) & 0xFF # 8 bits
        res_enc = self.reserved & 0x1FFF        # 13 bits
        
        return (
            (theta_enc << 27) |
            (phi_enc << 24) |
            (h_enc << 21) |
            (r_enc << 13) |
            res_enc
        )
    
    def to_bytes(self) -> bytes:
        """Encode to 4-byte big-endian."""
        return self.to_raw().to_bytes(4, 'big')
    
    @classmethod
    def from_raw(cls, raw: int) -> 'RPPCanonicalAddress':
        """Decode from 32-bit integer."""
        theta = (raw >> 27) & 0x1F
        phi = ((raw >> 24) & 0x07) + 1
        harmonic = (raw >> 21) & 0x07
        radius = ((raw >> 13) & 0xFF) / 255.0
        reserved = raw & 0x1FFF
        
        return cls(
            theta=theta,
            phi=phi,
            harmonic=harmonic,
            radius=radius,
            reserved=reserved
        )
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'RPPCanonicalAddress':
        """Decode from 4-byte big-endian."""
        if len(data) != 4:
            raise ValueError(f"Expected 4 bytes, got {len(data)}")
        raw = int.from_bytes(data, 'big')
        return cls.from_raw(raw)
    
    def to_uri(self) -> str:
        """Format as SPIRAL URI."""
        return f"spiral://θ:{self.theta}/φ:{self.phi}/h:{self.harmonic}/r:{self.radius:.2f}"
```

### 4.2 Verilog Reference

```verilog
// RPP Canonical Address Encoder (Ra-Derived)
module rpp_canonical_encoder (
    input  [4:0]  theta,      // Repitan 1-27 (5 bits)
    input  [2:0]  phi,        // RAC 0-5 (3 bits, RAC1=0)
    input  [2:0]  harmonic,   // Omega 0-4 (3 bits)
    input  [7:0]  radius,     // Intensity 0-255 (8 bits)
    input  [12:0] reserved,   // CRC/Reserved (13 bits)
    output [31:0] address     // 32-bit canonical address
);
    assign address = {theta, phi, harmonic, radius, reserved};
endmodule

// RPP Canonical Address Decoder
module rpp_canonical_decoder (
    input  [31:0] address,
    output [4:0]  theta,
    output [2:0]  phi,
    output [2:0]  harmonic,
    output [7:0]  radius,
    output [12:0] reserved,
    output        valid
);
    assign theta    = address[31:27];
    assign phi      = address[26:24];
    assign harmonic = address[23:21];
    assign radius   = address[20:13];
    assign reserved = address[12:0];
    
    // Validity: theta in 1-27, phi in 0-5, harmonic in 0-4
    assign valid = (theta >= 5'd1) && (theta <= 5'd27) &&
                   (phi <= 3'd5) && (harmonic <= 3'd4);
endmodule
```

---

## 5. Packet Type Hierarchy

| Packet Type | Structure | Size | Use Case |
|-------------|-----------|------|----------|
| **RPP Compact** | 32-bit Ra-derived address | 4 bytes | FPGA routing, sensor nets, minimal overhead |
| **RPP Extended** | Address + inline payload | 4+ bytes | Data transport with semantic routing |
| **SPIRAL Routing** | Consent Header (18B) + RPP | 22+ bytes | Consent-aware fragment routing |
| **SPIRAL Envelope** | Full packet with signatures | 208+ bytes | Avatar identity, PMA anchoring, audit |

---

## 6. Migration from v1.0

The original 28-bit address format (SPEC.md) used:
- Shell: 2 bits (arbitrary)
- Theta: 9 bits (512 sectors)
- Phi: 9 bits (continuous)
- Harmonic: 8 bits (256 levels)

**Migration path:**
1. v1.0 addresses can be mapped to v2.0 by:
   - `theta_v2 = (theta_v1 * 27) // 512 + 1`
   - `phi_v2 = (phi_v1 * 6) // 512 + 1`
   - `harmonic_v2 = (harmonic_v1 * 5) // 256`
   - `radius_v2 = 0.5` (default)

2. v2.0 addresses expand to v1.0 compatibility by:
   - `theta_v1 = (theta_v2 - 1) * 19`  (approximate)
   - etc.

---

## 7. Invariants

| ID | Invariant | Description |
|----|-----------|-------------|
| I1 | θ ∈ {1..27} | Theta must be valid Repitan index |
| I2 | φ ∈ {1..6} | Phi must be valid RAC level |
| I3 | h ∈ {0..4} | Harmonic must be valid Omega format |
| I4 | r ∈ [0, 1] | Radius must be normalized |
| I5 | encode(decode(x)) = x | Roundtrip identity |
| I6 | θ=0 ⟹ INVALID | Zero theta means null address |

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-01-01 | Ra-derived canonical format |
| 1.0.0 | 2024-12-27 | Original arbitrary format |

---

*"The address is not a label—it is a coordinate in resonance space."*
