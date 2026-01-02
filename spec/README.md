# RPP Specification Directory

This directory contains the complete specification for the Recursive Packet Protocol (RPP), derived from Ra Constants and aligned with SPIRAL architecture.

## Specification Hierarchy

### Core Specifications (Ra-Derived)

| Document | Version | Status | Description |
|----------|---------|--------|-------------|
| [RPP-CANONICAL-v2.md](RPP-CANONICAL-v2.md) | 2.0 | **Finalized** | Canonical RPP address format derived from Ra Constants |
| [CONSENT-HEADER-v1.md](CONSENT-HEADER-v1.md) | 1.0 | Draft | System-layer envelope wrapping RPP address |
| [PMA-SCHEMA-v1.md](PMA-SCHEMA-v1.md) | 1.0 | Draft | Phase Memory Anchor persistence schema |
| [ROUTING-FLOW-v1.md](ROUTING-FLOW-v1.md) | 1.0 | Draft | Complete resolver routing decision flow |

### Legacy Specifications (Superseded)

| Document | Status | Notes |
|----------|--------|-------|
| [PACKET.md](PACKET.md) | Superseded | Original 28-bit format, replaced by RPP-CANONICAL-v2 |
| [RESOLVER.md](RESOLVER.md) | Active | Backend resolver protocol (still valid) |
| [SECTOR.md](SECTOR.md) | Active | Sector definitions (compatible) |

### Architecture Documents

| Document | Description |
|----------|-------------|
| [SPIRAL-Architecture.md](../SPIRAL-Architecture.md) | Full SPIRAL packet format (208+ bytes) |

## Ra Constants Integration

The canonical RPP address format is derived directly from Ra System constants:

| RPP Field | Ra Source | Bit Width | Range |
|-----------|-----------|-----------|-------|
| θ (Theta) | 27 Repitans | 5 bits | 1-27 (0, 28-31 reserved) |
| φ (Phi) | 6 RAC Levels | 3 bits | 0-5 (6-7 reserved) |
| h (Omega) | 5 Omega Formats | 3 bits | 0-4 (5-7 reserved) |
| r (Radius) | Ankh-normalized | 8 bits | 0-255 (0.0-1.0) |
| Reserved | — | 13 bits | CRC or future |

**Total: 32 bits (4 bytes)**

## Packet Type Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    PACKET TYPE HIERARCHY                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  RPP Compact          4 bytes     Ra-derived address only    │
│       │                                                      │
│       └──▶ SPIRAL Routing Frame                              │
│                      22 bytes     Consent Header + RPP       │
│                 │                                            │
│                 └──▶ SPIRAL Envelope                         │
│                            208+ bytes   Full packet + sigs   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Status

### Python (`rpp/`)

| Module | Status | Description |
|--------|--------|-------------|
| `address_canonical.py` | ✅ Complete | Canonical address with full Ra integration |
| `consent_header.py` | ✅ Complete | Consent header encoding/decoding |
| `pma.py` | ✅ Complete | Phase Memory Anchor storage |
| `packet.py` | ⚠️ Legacy | Original packet utilities |

### Verilog (`hardware/verilog/`)

| Module | Status | Description |
|--------|--------|-------------|
| `rpp_canonical.v` | ✅ Complete | Ra-derived address encoder/decoder/coherence |

### Tests (`tests/`)

| Test Suite | Status | Coverage |
|------------|--------|----------|
| `test_address_canonical.py` | ✅ Complete | Full Ra alignment validation |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0-RaCanonical | 2025-01-01 | Canonical format derived from Ra Constants |
| v0.9-Legacy | 2024-12-27 | Original 28-bit format (superseded) |

## Integration Points

The canonical RPP address integrates with:

- **SPIRAL Resolver**: Required for all route calculations
- **Consent Packet Header**: Overlay consistency validation
- **Phase Memory Anchor**: Address reference anchoring
- **Cymatics Engine**: Tone generation via θ-φ-h vector
- **Fragment Mesh (DTFM)**: Coherence-based routing

## Symbolic Note

> *"This is not an address. It is a phase vector."*
> 
> It encodes positional resonance across the Ra topology, treated as harmonic origin from which coherence can be measured.

---

*RPP v1.0-RaCanonical — Anywave Creations*
