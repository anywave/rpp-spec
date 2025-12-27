# RPP Clash/FPGA Implementation

Hardware implementation of RPP using [Clash](https://clash-lang.org/), a functional hardware description language that compiles Haskell to synthesizable Verilog/VHDL.

## Overview

This implementation demonstrates how RPP's spherical coordinate addressing can be realized in hardware for:

- High-speed memory controllers
- Network interface cards
- Embedded consent-gating systems
- MRAM/FPGA hybrid architectures

## Key Features

| Feature | Description |
|---------|-------------|
| Phase-encoded addressing | 9-bit theta, 8-bit phi coordinate system |
| TRB zone detection | Real-time zone classification from coordinates |
| Fibonacci skip patterns | Golden-angle based memory traversal |
| Consent gating | Hardware-level access control based on coherence |
| Coherence monitoring | Continuous consent state evaluation |

## Hardware Targets

Tested synthesis targets:
- **Xilinx 7-series**: Artix-7, Kintex-7
- **Intel FPGA**: Cyclone V, Arria 10
- **Lattice**: ECP5

## Building

### Prerequisites

```bash
# Install GHCup (Haskell toolchain manager)
curl --proto '=https' --tlsv1.2 -sSf https://get-ghcup.haskell.org | sh

# Install Clash
cabal update
cabal install clash-ghc
```

### Generate HDL

```bash
# Generate Verilog
clash --verilog RPP.hs

# Generate VHDL
clash --vhdl RPP.hs

# Interactive simulation
clash -i. --interactive RPP.hs
```

### Output Files

After synthesis, find generated HDL in:
- `verilog/RPP/rpp_controller.v` - Verilog output
- `vhdl/RPP/rpp_controller.vhdl` - VHDL output

## Architecture

```
                    +-----------------+
  query_theta ----->|                 |-----> mem_addr
  query_phi ------->|  RPP Controller |-----> mem_read
  coherence ------->|                 |-----> access_granted
  packet_valid ---->|   (Mealy FSM)   |-----> trb_zone
  packet_theta ---->|                 |-----> consent_state
  packet_phi ------>|                 |-----> skip_angle
                    +-----------------+
                          ^   ^
                          |   |
                        clk   rst
```

## Type Definitions

### Core Types
```haskell
type Theta = Unsigned 9   -- Angular position (0-511)
type Phi = Unsigned 8     -- Elevation (0-255)
type Coherence = Unsigned 8
type MemAddr = Unsigned 17
```

### TRB Zones
```haskell
data TRBZone
  = NoZone        -- Outside defined zones
  | GeneMap       -- theta 0-90, equatorial
  | MemoryLattice -- theta 90-180
  | WitnessField  -- theta 180-270
  | Integration   -- theta 270-360, north
  | Grounding     -- full theta, south pole
```

### Consent States
```haskell
data ConsentState
  = FullConsent       -- Coherence >= 0.7
  | DiminishedConsent -- Coherence >= 0.4
  | SuspendedConsent  -- Coherence >= 0.2
  | EmergencyOverride -- Coherence < 0.2
```

## Memory Mapping

Angular coordinates map to linear memory addresses:

```
Address = theta * 181 + phi

For 360x181 memory (65,160 locations):
  - theta 0-359 (uses 9 bits, but limited to 360 values)
  - phi 0-180 (uses 8 bits, but limited to 181 values)
```

## Testbench

The module includes a built-in testbench:

```haskell
-- Run in GHCi
> :l RPP.hs
> sampleN 10 testBench
```

Expected output verifies TRB zone detection:
- theta=45, phi=90 -> GeneMap
- theta=135, phi=90 -> MemoryLattice
- theta=225, phi=90 -> WitnessField
- theta=315, phi=150 -> Integration

## Integration Notes

### Clock Domain
- Default: 100 MHz system clock
- All signals synchronous to single clock domain

### Reset
- Active-high synchronous reset
- Returns controller to initial state

### Timing
- Single-cycle memory address generation
- TRB zone detection: combinational
- Consent state update: registered

## Resource Utilization (Artix-7)

| Resource | Usage |
|----------|-------|
| LUTs     | ~450  |
| FFs      | ~320  |
| BRAMs    | 0     |
| DSPs     | 0     |

## License

Apache-2.0 (see LICENSE in repository root)

## Related

- [RPP Specification](https://github.com/anywave/rpp-spec)
- [Haskell Reference Implementation](../../reference/haskell/)
- [Clash Documentation](https://clash-lang.org/documentation/)
