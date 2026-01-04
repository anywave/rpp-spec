# RPP Extended Addressing Specification
## Hardware-Testable Spec for Holographic Acceleration

**Version:** 2.1.0-draft
**Status:** Working Draft
**Target:** Software Emulation + FPGA/ASIC Implementation
**Repository:** github.com/anywave/rpp-spec

---

> **Ra-Canonical v2.0 Update:** This document describes extended precision formats.
> The core 32-bit format is now defined by Ra-Canonical v2.0 (see [RPP-CANONICAL-v2.md](RPP-CANONICAL-v2.md)).
> The legacy 28-bit core format described below is deprecated for new implementations.

---

## 1. Executive Summary

This specification defines a multi-layer addressing system for RPP:

| Layer | Bit Width | Purpose | Hardware Target |
|-------|-----------|---------|-----------------|
| **Ra-Canonical** | 32 bits | Core routing (θ/φ/h/r format) | FPGA registers, SPI, MRAM |
| **Legacy Core** | 28 bits | Routing, storage, consent (deprecated) | Legacy hardware |
| **Extended** | 64+ bits | Holographic precision | DSP, floating-point units |

The goal: **testable at every layer**, from Python emulation to Verilog synthesis.

---

## 2. Core Address Formats

### 2.0 Ra-Canonical Format (32-bit) — Current Standard

See [RPP-CANONICAL-v2.md](RPP-CANONICAL-v2.md) for the authoritative specification.

```
┌─────────────────────────────────────────────────────────────┐
│               RPP CANONICAL ADDRESS (32 bits)                │
├─────────┬─────────┬─────────┬──────────┬───────────────────┤
│    θ    │    φ    │    h    │    r     │   Reserved/CRC    │
│ (5 bits)│ (3 bits)│ (3 bits)│ (8 bits) │    (13 bits)      │
├─────────┼─────────┼─────────┼──────────┼───────────────────┤
│ [31:27] │ [26:24] │ [23:21] │ [20:13]  │      [12:0]       │
└─────────┴─────────┴─────────┴──────────┴───────────────────┘
```

### 2.1 Legacy Layout (28-bit) — Deprecated

> **DEPRECATED:** Use Ra-Canonical v2.0 for new implementations.

```
┌─────────────────────────────────────────────────────────────────┐
│                      28-BIT RPP CORE ADDRESS                     │
├────────┬────────────────┬────────────────┬──────────────────────┤
│ Shell  │     Theta      │      Phi       │      Harmonic        │
│ 2 bits │    9 bits      │    9 bits      │       8 bits         │
├────────┼────────────────┼────────────────┼──────────────────────┤
│ [27:26]│    [25:17]     │    [16:8]      │        [7:0]         │
│  0-3   │     0-511      │     0-511      │        0-255         │
└────────┴────────────────┴────────────────┴──────────────────────┘
```

### 2.2 Bit Masks and Shifts

| Field | Mask | Shift | C Macro |
|-------|------|-------|---------|
| Shell | `0x0C000000` | 26 | `RPP_SHELL_MASK` |
| Theta | `0x03FE0000` | 17 | `RPP_THETA_MASK` |
| Phi | `0x0001FF00` | 8 | `RPP_PHI_MASK` |
| Harmonic | `0x000000FF` | 0 | `RPP_HARMONIC_MASK` |

### 2.3 Hardware Alignment

The 28-bit format fits in a 32-bit register with 4 bits reserved:

```
┌────────┬────────────────────────────────────────────────────────┐
│Reserved│                  28-bit RPP Address                    │
│ [31:28]│                       [27:0]                           │
│  0000  │  Shell  │    Theta    │     Phi     │    Harmonic     │
└────────┴────────┴─────────────┴─────────────┴──────────────────┘
```

**Test:** Any 28-bit address fits in uint32_t with no data loss.

---

## 3. Extended Address Format (64-bit)

### 3.1 Purpose

The extended format provides:
- **Float-precision coordinates** for holographic intersection
- **Phase angle** for wave interference calculations
- **Backward compatibility** with 28-bit routing

### 3.2 Extended Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      64-BIT RPP EXTENDED ADDRESS                         │
├────────┬──────────────┬──────────────┬──────────────┬───────────────────┤
│ Shell  │ Theta (fine) │  Phi (fine)  │   Harmonic   │   Phase Angle     │
│ 2 bits │   20 bits    │   20 bits    │   10 bits    │     12 bits       │
├────────┼──────────────┼──────────────┼──────────────┼───────────────────┤
│[63:62] │   [61:42]    │   [41:22]    │   [21:12]    │      [11:0]       │
│  0-3   │  0-1048575   │  0-1048575   │    0-1023    │      0-4095       │
└────────┴──────────────┴──────────────┴──────────────┴───────────────────┘
```

### 3.3 Resolution Comparison

| Field | Core (28-bit) | Extended (64-bit) | Improvement |
|-------|---------------|-------------------|-------------|
| Theta | 512 steps (0.703°/step) | 1,048,576 steps (0.000343°/step) | 2048× |
| Phi | 512 steps (0.703°/step) | 1,048,576 steps (0.000343°/step) | 2048× |
| Harmonic | 256 steps | 1024 steps | 4× |
| Phase | N/A | 4096 steps (0.088°/step) | New dimension |

### 3.4 Angular Precision

Extended resolution: **360° / 1,048,576 = 0.000343°** = **1.23 arcseconds**

For reference:
- Human eye resolution: ~60 arcseconds
- GPS accuracy: ~5 meters ≈ 0.00005° latitude
- RPP Extended: **1.23 arcseconds** (precision for holographic formation)

---

## 4. Coordinate Systems

### 4.1 Theta (Azimuthal Angle)

```
             θ = 0° / 360°
                  │
                  │   GENE
                  │   θ: 0-63
     META         │         MEMORY
    θ: 448-511    │        θ: 64-127
                  │
 ─────────────────┼─────────────────→ θ increases clockwise
                  │
    GUARDIAN      │        WITNESS
    θ: 320-383    │       θ: 128-191
                  │
                  │   DREAM
                  │  θ: 192-255
             θ = 180°
```

**Semantic Sectors (8):**

| Sector | Core Range | Extended Range | Semantic Meaning |
|--------|------------|----------------|------------------|
| GENE | 0-63 | 0-131071 | Identity, biometric |
| MEMORY | 64-127 | 131072-262143 | Historical records |
| WITNESS | 128-191 | 262144-393215 | Attestation, observation |
| DREAM | 192-255 | 393216-524287 | Creative, aspirational |
| BRIDGE | 256-319 | 524288-655359 | Shared, relational |
| GUARDIAN | 320-383 | 655360-786431 | Protective, safety |
| EMERGENCE | 384-447 | 786432-917503 | Transformational |
| META | 448-511 | 917504-1048575 | System, protocol |

### 4.2 Phi (Polar/Consent Angle)

```
                    φ = 511 (ETHEREAL)
                    North Pole
                    Strict consent
                         │
                         │
                    ╱────┴────╲
                  ╱  ETHEREAL   ╲     φ > 341
                ╱   (restricted)  ╲
              ╱─────────────────────╲
             │    TRANSITIONAL      │   170 < φ ≤ 341
             │    (verification)    │
              ╲─────────────────────╱
                ╲   (open access) ╱      φ ≤ 170
                  ╲  GROUNDED   ╱
                    ╲────┬────╱
                         │
                    φ = 0 (GROUNDED)
                    South Pole
                    Open access
```

**Consent Zones:**

| Zone | Core Range | Extended Range | Access Level |
|------|------------|----------------|--------------|
| GROUNDED | 0-170 | 0-349524 | Open, no verification |
| TRANSITIONAL | 171-341 | 349525-699049 | Consent verification |
| ETHEREAL | 342-511 | 699050-1048575 | Strict, real-time consent |

### 4.3 Shell (Radial/Storage Tier)

| Shell | Value | Name | Access Latency | Use Case |
|-------|-------|------|----------------|----------|
| 0 | `00` | HOT | <10ns | Active, real-time |
| 1 | `01` | WARM | <100ns | Recent, frequent access |
| 2 | `10` | COLD | <1ms | Archival, occasional |
| 3 | `11` | FROZEN | >1ms | Deep archive, compliance |

### 4.4 Phase Angle (Extended Only)

The phase angle encodes **temporal alignment** for holographic interference:

| Phase | Interference | Effect |
|-------|--------------|--------|
| 0° | Constructive | Maximum file stability |
| 90° | Quadrature | Partial interference |
| 180° | Destructive | Cancellation |
| 270° | Quadrature | Partial interference |

**Test:** Two packets at same (θ, φ) with phase=0° produce 2× amplitude.  
**Test:** Two packets at same (θ, φ) with phase=180° produce 0 amplitude.

---

## 5. Encoding/Decoding

### 5.1 Core Address (28-bit)

#### Encode

```c
uint32_t rpp_encode_core(uint8_t shell, uint16_t theta, 
                         uint16_t phi, uint8_t harmonic) {
    assert(shell <= 3);
    assert(theta <= 511);
    assert(phi <= 511);
    assert(harmonic <= 255);
    
    return ((uint32_t)shell << 26) |
           ((uint32_t)theta << 17) |
           ((uint32_t)phi << 8) |
           (uint32_t)harmonic;
}
```

#### Decode

```c
void rpp_decode_core(uint32_t addr, uint8_t *shell, uint16_t *theta,
                     uint16_t *phi, uint8_t *harmonic) {
    *shell    = (addr >> 26) & 0x3;
    *theta    = (addr >> 17) & 0x1FF;
    *phi      = (addr >> 8) & 0x1FF;
    *harmonic = addr & 0xFF;
}
```

### 5.2 Extended Address (64-bit)

#### Encode

```c
uint64_t rpp_encode_extended(uint8_t shell, uint32_t theta_fine,
                              uint32_t phi_fine, uint16_t harmonic,
                              uint16_t phase) {
    assert(shell <= 3);
    assert(theta_fine <= 1048575);
    assert(phi_fine <= 1048575);
    assert(harmonic <= 1023);
    assert(phase <= 4095);
    
    return ((uint64_t)shell << 62) |
           ((uint64_t)theta_fine << 42) |
           ((uint64_t)phi_fine << 22) |
           ((uint64_t)harmonic << 12) |
           (uint64_t)phase;
}
```

#### Core from Extended (Truncation)

```c
uint32_t rpp_extended_to_core(uint64_t extended) {
    uint8_t shell = (extended >> 62) & 0x3;
    // Truncate theta_fine (20 bits) to theta (9 bits)
    uint16_t theta = ((extended >> 42) & 0xFFFFF) >> 11;  // Top 9 bits
    // Truncate phi_fine (20 bits) to phi (9 bits)
    uint16_t phi = ((extended >> 22) & 0xFFFFF) >> 11;
    // Truncate harmonic (10 bits) to 8 bits
    uint8_t harmonic = ((extended >> 12) & 0x3FF) >> 2;
    
    return rpp_encode_core(shell, theta, phi, harmonic);
}
```

---

## 6. Wire Format

### 6.1 Packet Structure

```
┌────────────────────────────────────────────────────────────────────────┐
│                        RPP PACKET (variable length)                     │
├────────┬────────┬──────────────┬──────────────────────────────────────┤
│ Flags  │ Core   │  Extended    │            Payload                   │
│ 1 byte │4 bytes │ 0 or 8 bytes │         Variable                     │
├────────┼────────┼──────────────┼──────────────────────────────────────┤
│[F:8]   │[C:32]  │  [E:64]      │            [P:n]                     │
└────────┴────────┴──────────────┴──────────────────────────────────────┘

Flags byte:
  [7]    : Has extended address (1 = yes)
  [6]    : Has phase angle (1 = yes)
  [5:4]  : Reserved
  [3:0]  : Payload type
```

### 6.2 Minimum Packet Sizes

| Configuration | Size | Use Case |
|---------------|------|----------|
| Core only | 5 bytes | Routing, simple storage |
| Core + Extended | 13 bytes | Holographic operations |
| Full header (no payload) | 13 bytes | Maximum addressing precision |

---

## 7. Hardware Interface

### 7.1 SPI Command Set

Aligned with `task_fpga.c` firmware:

| Command | Opcode | Description |
|---------|--------|-------------|
| NOP | 0x00 | No operation |
| READ_STATUS | 0x01 | Read FPGA status register |
| WRITE_CACHE | 0x10 | Write to angular cache |
| READ_CACHE | 0x11 | Read from angular cache |
| INVALIDATE | 0x12 | Invalidate cache line |
| COHERENCE_CHK | 0x20 | Check coherence at address |
| CONSENT_GATE | 0x21 | Verify consent state |
| GLYPH_DETECT | 0x30 | Detect glyph storm pattern |
| EMERGENCE_TRIG | 0x31 | Trigger holographic emergence |
| SET_SKIP_PATTERN | 0x40 | Configure skip pattern |
| GET_SKIP_ANGLE | 0x41 | Get next skip angle |

### 7.2 Memory Timing

Aligned with `virtual_hardware.py` emulation:

| Operation | STT-MRAM | Emulation |
|-----------|----------|-----------|
| Read | 35ns | `read_latency_ns` |
| Write | 50ns | `write_latency_ns` |
| Bus clock | 25ns (40MHz) | `bus_clock_ns` |

### 7.3 Angular Resolution Targets

| Target | Theta Bits | Phi Bits | Total Address Bits |
|--------|------------|----------|-------------------|
| Minimum viable | 9 | 9 | 28 |
| Standard | 12 | 12 | 34 |
| High precision | 16 | 16 | 42 |
| Holographic | 20 | 20 | 64 |

---

## 8. Symbolic Coherence Overlay (SCO)

> **Historical Note:** The original "Holographic Files" architecture (wave interference,
> phase angles, extended precision) was deprecated December 2025 in favor of Symbolic
> Coherence Overlay. See `docs/architecture-decisions/SCO_ANALYSIS_SUMMARY.md` for
> rationale. Legacy components preserved in `legacy/` namespace.

### 8.1 Purpose

SCO serves as the **emergence arbiter** for AVACHATTER, unifying:
- **ACSP** (biometric consent and coherence)
- **RPP** (semantic addressing: θ sectors, φ sensitivity)
- **Fragment Storage** (content-addressed data packets)

SCO determines *how* and *whether* memory constructs emerge:

```
FULL → PARTIAL → WITHHELD
```

based on harmonic alignment between user-state and fragment-state.

### 8.2 Inputs

All inputs are modeled as `FieldVector`:

```python
@dataclass
class FieldVector:
    source: str              # acsp | rpp | attestation | intent
    theta: int               # semantic sector (9-bit, ~0.7° granularity)
    phi: int                 # access sensitivity (9-bit)
    coherence_score: float   # 0.0–1.0
    timestamp: datetime
    content_hash: Optional[str]  # for fragment references
```

| Source | Input Type | Example |
|--------|-----------|---------|
| ACSP | coherence score, consent state | 0.62, `DIMINISHED_CONSENT` |
| RPP | semantic location (θ), sensitivity (φ) | θ=44, φ=160 |
| Attestations | trust-weighted confirmations | verified claims |
| Intent | semantic targeting & request scope | "recall event from Aug 14" |

### 8.3 Decision Thresholds

| State | Alignment Range | Result |
|-------|----------------|--------|
| FULL EMERGENCE | ≥ 0.70 | Assemble and return full memory construct |
| PARTIAL EMERGENCE | 0.40–0.69 | Modal or symbolic access |
| WITHHELD | < 0.40 | Stability warning; no reveal |

**Consent state from ACSP can override:**
- `SUSPENDED` or `EMERGENCY` → Auto-withhold regardless of score

### 8.4 Emergence States

**FULL**: All required fragments align → assemble complete memory

**PARTIAL**: Insufficient alignment → SCO selects safe subsets:
- Modal Reduction (audio only, text summary)
- Symbolic Rendering (metaphor card)
- Stability Preview (UX cue)

**WITHHELD**: No synthesis. The system reflects state without exposing content.

---

## 9. Test Vectors

### 9.1 Core Address Tests

| Test | Shell | Theta | Phi | Harmonic | Expected (hex) |
|------|-------|-------|-----|----------|----------------|
| All zeros | 0 | 0 | 0 | 0 | 0x00000000 |
| All max | 3 | 511 | 511 | 255 | 0x0FFFFFFF |
| Shell only | 3 | 0 | 0 | 0 | 0x0C000000 |
| Theta only | 0 | 511 | 0 | 0 | 0x03FE0000 |
| Phi only | 0 | 0 | 511 | 0 | 0x0001FF00 |
| Harmonic only | 0 | 0 | 0 | 255 | 0x000000FF |
| Example 1 | 0 | 12 | 40 | 1 | 0x00182801 |

### 9.2 Roundtrip Tests

```python
def test_roundtrip():
    for shell in range(4):
        for theta in [0, 255, 511]:
            for phi in [0, 255, 511]:
                for harmonic in [0, 127, 255]:
                    addr = encode(shell, theta, phi, harmonic)
                    s, t, p, h = decode(addr)
                    assert (s, t, p, h) == (shell, theta, phi, harmonic)
```

### 9.3 Extended Precision Tests

| Test | Theta (float) | Extended Value | Core Truncation |
|------|---------------|----------------|-----------------|
| Zero | 0.0° | 0 | 0 |
| Half step | 0.000171° | 1 | 0 |
| One core step | 0.703125° | 2048 | 1 |
| Max | 359.999657° | 1048575 | 511 |

### 9.4 Phase Interference Tests

| Packet A Phase | Packet B Phase | Expected Amplitude |
|----------------|----------------|-------------------|
| 0° | 0° | 2.0 (constructive) |
| 0° | 180° | 0.0 (destructive) |
| 0° | 90° | 1.414 (quadrature) |
| 45° | 45° | 2.0 (constructive) |

---

## 10. Verilog Integration

### 10.1 Module Interface

From `rpp_top.v`:

```verilog
module rpp_top #(
    parameter DATA_WIDTH = 64,
    parameter ADDR_WIDTH = 32,
    parameter NUM_PORTS = 4
)(
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [ADDR_WIDTH-1:0]    host_addr,    // 32-bit (28 used)
    input  wire [8:0]               pkt_theta,    // 9-bit theta
    input  wire [8:0]               pkt_phi,      // 9-bit phi
    input  wire [7:0]               pkt_harmonic, // 8-bit harmonic
    input  wire [1:0]               pkt_shell,    // 2-bit shell
    ...
);
```

### 10.2 Skip Pattern Generator

From `skip_pattern_generator`:

```verilog
localparam PATTERN_FIBONACCI = 4'h1;
localparam [8:0] GOLDEN_ANGLE = 9'd138;  // 137.5° rounded
```

**Test:** Fibonacci pattern generates 137.5° increments.

### 10.3 Angular Address Translator

```verilog
module angular_address_translator (
    input  wire [31:0] linear_addr,
    output wire [1:0]  shell,
    output wire [8:0]  theta,
    output wire [8:0]  phi,
    output wire [7:0]  harmonic,
    output wire [1:0]  quadrant
);
    assign shell    = linear_addr[27:26];
    assign theta    = linear_addr[25:17];
    assign phi      = linear_addr[16:8];
    assign harmonic = linear_addr[7:0];
    assign quadrant = theta[8:7];  // Top 2 bits = quadrant
endmodule
```

---

## 11. Compliance Levels

### Level 1: Core Only (Minimum)
- 28-bit addressing
- Encode/decode roundtrip
- Shell/Theta/Phi/Harmonic extraction
- **Test suite:** `test_rpp_core.py`

### Level 2: Extended Addressing
- 64-bit addressing
- Core truncation from extended
- Phase angle support
- **Test suite:** `test_rpp_extended.py`

### Level 3: Holographic Operations
- Intersection detection
- Emergence triggering
- Stability tracking
- **Test suite:** `test_holographic.py`

### Level 4: Hardware Emulation
- Virtual MRAM timing
- SPI command interface
- Skip pattern generation
- **Test suite:** `test_hardware_simulation.py`

### Level 5: RTL Synthesis
- Verilog module synthesis
- Timing closure
- FPGA deployment
- **Test suite:** `rpp_tb.v` (testbench)

---

## 12. Appendix: Conversion Formulas

### Degrees to Core Value

```python
def degrees_to_core_theta(degrees: float) -> int:
    """Convert 0-360° to 0-511 core theta."""
    return int((degrees / 360.0) * 512) % 512

def degrees_to_core_phi(degrees: float) -> int:
    """Convert -90° to +90° to 0-511 core phi (0 = grounded)."""
    # Map -90..+90 to 0..511
    normalized = (degrees + 90) / 180.0  # 0..1
    return int(normalized * 512) % 512
```

### Core Value to Degrees

```python
def core_theta_to_degrees(theta: int) -> float:
    """Convert 0-511 core theta to 0-360°."""
    return (theta / 512.0) * 360.0

def core_phi_to_degrees(phi: int) -> float:
    """Convert 0-511 core phi to -90° to +90°."""
    return (phi / 512.0) * 180.0 - 90.0
```

### Extended to Float

```python
def extended_theta_to_degrees(theta_fine: int) -> float:
    """Convert 20-bit theta to 0-360° with full precision."""
    return (theta_fine / 1048576.0) * 360.0

def extended_phi_to_degrees(phi_fine: int) -> float:
    """Convert 20-bit phi to -90° to +90° with full precision."""
    return (phi_fine / 1048576.0) * 180.0 - 90.0
```

---

## 13. References

- `rpp-spec/spec/RPP-CANONICAL-v2.md` - Core 32-bit Ra-Canonical specification (current)
- `rpp-spec/spec/SPEC.md` - Legacy 28-bit specification (deprecated)
- `holographic/hardware_simulation.py` - Physics emulation
- `holographic/virtual_hardware.py` - FPGA/MRAM emulation
- `holographic/intersection_engine.py` - Holographic file formation
- `hardware/rpp_top.v` - Top-level Verilog module
- `hardware/phase_slot_register.v` - Angular memory interface
- `tests/test_hardware_simulation.py` - Hardware test suite
- `tests/test_emulation_firmware_alignment.py` - Firmware alignment tests

---

**Document Status:** Draft for review  
**Next Steps:**
1. Implement Python reference library with extended addressing
2. Add test vectors to CI pipeline
3. Update Verilog modules for 64-bit extended support
4. Validate holographic emergence with extended precision
