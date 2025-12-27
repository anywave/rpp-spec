# RPP Address - Haskell Reference Implementation

Pure Haskell reference implementation of RPP (Rotational Packet Protocol) addressing.

## Overview

This package provides encoding, decoding, and semantic interpretation of 28-bit RPP addresses in pure Haskell with no external dependencies beyond `base`.

## Installation

```bash
# With cabal
cabal build

# With stack
stack build
```

## Usage

```haskell
import RPPAddress

-- Encode an address from components
let addr = encode 0 45 128 64
-- Result: 5939264 (0x005A8040)

-- Decode an address to components
let (shell, theta, phi, harmonic) = decode 0x005A8040
-- Result: (0, 45, 128, 64)

-- Create structured RPPAddress with semantic interpretation
let rppAddr = fromComponents 1 96 192 128

-- Access semantic properties
sectorName rppAddr      -- "memory"
groundingLevel rppAddr  -- "transitional"
shellName rppAddr       -- "warm"

-- Convert to hex representation
toHex (raw rppAddr)     -- "0x04C0C080"
```

## Address Format

```
28-bit address: [Shell:2][Theta:9][Phi:9][Harmonic:8]

Bit Layout:
  27 26 | 25 24 23 22 21 20 19 18 17 | 16 15 14 13 12 11 10 9 8 | 7 6 5 4 3 2 1 0
  Shell |         Theta (9 bits)     |       Phi (9 bits)       |   Harmonic
```

## Semantic Interpretation

### Sectors (Theta 0-511)
| Range   | Sector    | Function              |
|---------|-----------|----------------------|
| 0-63    | gene      | Core identity        |
| 64-127  | memory    | Experiences          |
| 128-191 | witness   | Observations         |
| 192-255 | dream     | Speculation          |
| 256-319 | bridge    | Integration          |
| 320-383 | guardian  | Protection           |
| 384-447 | emergence | Discovery            |
| 448-511 | meta      | Self-reference       |

### Grounding Levels (Phi 0-511)
| Range   | Level        | Description          |
|---------|--------------|---------------------|
| 0-127   | grounded     | Physical/verified   |
| 128-255 | transitional | Behavioral          |
| 256-383 | abstract     | Conceptual          |
| 384-511 | ethereal     | Speculative         |

### Storage Tiers (Shell 0-3)
| Value | Tier   | Purpose              |
|-------|--------|---------------------|
| 0     | hot    | Immediate cache     |
| 1     | warm   | Working memory      |
| 2     | cold   | Persistent storage  |
| 3     | frozen | Archive             |

## Testing

```bash
# Run tests
cabal test

# Or use GHCi
ghci RPPAddress.hs
> runTests
```

## License

Apache-2.0 (see LICENSE in repository root)

## Related

- [RPP Specification](https://github.com/anywave/rpp-spec)
- [Python Reference Implementation](../python/)
- [Clash FPGA Implementation](../../hardware/clash/)
