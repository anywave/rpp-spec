# SPIRAL Protocol HDL Architecture

**Version:** 2.0.0-RaCanonical  
**Target:** Lattice ECP5 FPGA (Fragment Host Node)  
**Last Updated:** 2025-01-01

---

## Overview

This directory contains Verilog RTL implementations of the SPIRAL Protocol components. The design supports both legacy stub interfaces (for prototyping) and spec-compliant Ra-derived implementations (for production).

## File Structure

```
hardware/verilog/
├── rpp_canonical.v         # RPP Address modules (Ra-derived 32-bit)
├── spiral_consolidated.v   # Unified consent + PMA + routing pipeline
├── spiral_consent.v        # Detailed consent header implementation
└── README.md               # This file
```

## Module Hierarchy

```
SpiralRoutingCore (Top-Level)
├── ConsentHeaderParser      # 18-byte header extraction
├── CoherenceEvaluator       # Ra-weighted distance calculation
│   ├── ThetaToSector        # 27 Repitans → 8 sectors
│   └── SectorAdjacency      # Ra topology adjacency matrix
├── FallbackResolver         # XOR-based alternate routing
├── PhaseMemoryAnchorRAM     # PMA circular buffer
└── ScalarTrigger            # Sustained coherence detection
```

## Key Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| Consent Header | 144 bits (18 bytes) | Spec-aligned byte layout |
| RPP Address | 32 bits (4 bytes) | Ra-derived canonical format |
| PMA Record | 144 bits (18 bytes) | Compact temporal coherence |
| Coherence Weights | θ=0.30, φ=0.40, h=0.20, r=0.10 | Ra System derived |

## Module Details

### ConsentHeaderParser

Extracts fields from 18-byte Consent Packet Header.

**Inputs:**
- `header_in[143:0]` — Big-endian header bytes

**Outputs:**
- `rpp_address[31:0]` — Canonical Ra-derived address
- `theta[4:0]` — Repitan 1-27
- `phi[2:0]` — RAC level 0-5
- `omega[2:0]` — Omega tier 0-4
- `radius[7:0]` — Intensity 0-255
- `consent_state[1:0]` — Derived ACSP state
- `needs_fallback` — Entropy > 25
- `has_pma_link` — Window ID ≠ 0

### CoherenceEvaluator

Computes Ra-weighted coherence between source and destination.

**Formula:**
```
distance = w_θ×θ_dist + w_φ×φ_dist + w_h×h_dist + w_r×r_dist
coherence = 255 - distance
```

**Theta Distance:** Circular on 27-Repitan ring (max 13)  
**Phi/Omega/Radius:** Linear distance, normalized to 0-255

### FallbackResolver

XOR-based alternate route calculation with modulo wrapping.

**Vector Layout:**
```
[7:5] theta_offset (XOR, mod 27)
[4:2] phi_offset   (XOR, mod 6)
[1:0] omega_offset (XOR, mod 5)
```

### ScalarTrigger

Detects sustained high-radius conditions for scalar activation.

**Logic:**
- If `radius >= threshold` for `duration` cycles → trigger
- Any dip below threshold resets counter

### PhaseMemoryAnchorRAM

Simple dual-port RAM for PMA record storage.

**Parameters:**
- `DEPTH` — Number of records (default 64)

## Resource Estimates (Lattice ECP5-25K)

| Module | LUTs | Registers | BRAM |
|--------|------|-----------|------|
| ConsentHeaderParser | ~80 | ~32 | 0 |
| CoherenceEvaluator | ~250 | ~64 | 0 |
| FallbackResolver | ~100 | ~32 | 0 |
| PhaseMemoryAnchorRAM | ~20 | ~16 | 1 (18Kb) |
| ScalarTrigger | ~50 | ~24 | 0 |
| **SpiralRoutingCore** | ~600 | ~200 | 1 |

**Total Utilization:** ~2.5% LUTs, <1% registers, 2% BRAM

## Timing

| Path | Cycles | Notes |
|------|--------|-------|
| Header parse → consent_state | 1 | Combinational |
| Coherence calculation | 1 | Pipelined multipliers |
| Fallback computation | 1 | Combinational |
| PMA lookup | 1 | Registered read |
| Scalar trigger | N | N = coherence_duration |

## Legacy Compatibility

Stub modules with original interfaces are preserved with `_Stub` suffix:

- `ConsentHeaderParser_Stub` — Original arbitrary bit positions
- `CoherenceEvaluator_Stub` — Simple entropy + complecount model
- `FallbackResolver_Stub` — Basic XOR without wrapping

Use these for backward compatibility with existing testbenches.

## Integration with Fragment Host Node

```
ESP32-S3                    ECP5 FPGA
    │                           │
    │  SPI @ 40MHz              │
    ├───────────────────────────▶
    │  18-byte header           │
    │                           ├── ConsentHeaderParser
    │                           ├── CoherenceEvaluator
    │                           ├── FallbackResolver
    │                           ├── PMA RAM
    │                           │
    │◄──────────────────────────┤
    │  route_valid + address    │
    │  coherence_score          │
    │  consent_state            │
```

## Verification

Test with cocotb or Verilator. Key test vectors:

1. **Valid header parse** — All fields extracted correctly
2. **Consent state derivation** — somatic thresholds
3. **Coherence calculation** — Known distance pairs
4. **Fallback wrapping** — Modulo boundaries
5. **PMA lookup** — Window ID match/miss

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-01-01 | Ra-canonical consolidation |
| 1.0.0 | 2024-12-27 | Initial stubs |

---

*"Hardware that routes by resonance, not just destination."*
