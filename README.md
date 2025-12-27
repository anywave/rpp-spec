# Rotational Packet Protocol (RPP)

**A Semantic Addressing Architecture for Consent-Aware Memory Systems**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Spec Version](https://img.shields.io/badge/Spec-v1.0.0-green.svg)](spec/SPEC.md)
[![arXiv Intent](https://img.shields.io/badge/arXiv-Defensive%20Publication-orange.svg)](ARXIV_INTENT.md)

> **Disambiguation:** This specification is unrelated to AMD ROCm Performance Primitives (rocPRIM), REAPER project files (.rpp), or any other technology sharing the "RPP" abbreviation.

---

## Abstract

The Rotational Packet Protocol (RPP) defines a semantic addressing architecture wherein meaning, access consent, and lifecycle state are encoded directly into a fixed-width 28-bit address. Unlike conventional linear memory addressing schemes that treat addresses as opaque location identifiers, RPP employs a spherical coordinate system where address components represent functional classification, grounding level, and harmonic mode.

This specification establishes RPP as open infrastructure designed for interoperability and auditability. The architecture functions as a semantic control plane that routes to existing storage systems rather than replacing them, enabling adoption without migration.

**Key Properties:**
- Deterministic encoding and decoding with hardware-software parity
- Consent-aware access gating intrinsic to address resolution
- Bridge architecture preserving existing storage investments
- Intentional openness enabling reproducibility and independent implementation

---

## Technical Overview

### Address Structure

RPP addresses are 28-bit unsigned integers with the following canonical structure:

```
┌────────────────────────────────────────────────────────────────┐
│                     28-BIT RPP ADDRESS                          │
├────────┬─────────────┬─────────────┬───────────────────────────┤
│ Shell  │    Theta    │     Phi     │         Harmonic          │
│ 2 bits │   9 bits    │   9 bits    │          8 bits           │
├────────┼─────────────┼─────────────┼───────────────────────────┤
│ [27:26]│   [25:17]   │   [16:8]    │          [7:0]            │
└────────┴─────────────┴─────────────┴───────────────────────────┘
```

### Field Definitions

| Field | Width | Range | Semantic Function |
|-------|-------|-------|-------------------|
| **Shell** | 2 bits | 0–3 | Radial depth encoding storage tier (hot→frozen) |
| **Theta** | 9 bits | 0–511 | Angular longitude encoding functional sector |
| **Phi** | 9 bits | 0–511 | Angular latitude encoding grounding level |
| **Harmonic** | 8 bits | 0–255 | Frequency index encoding resolution/mode |

**Total Address Space:** 2²⁸ = 268,435,456 unique addresses

### Encoding Function

```
encode(shell, theta, phi, harmonic) = (shell << 26) | (theta << 17) | (phi << 8) | harmonic
```

### Decoding Function

```
decode(address) = (
    (address >> 26) & 0x3,
    (address >> 17) & 0x1FF,
    (address >> 8) & 0x1FF,
    address & 0xFF
)
```

---

## Conformance Criteria

A conforming RPP implementation MUST:

1. **Encode deterministically:** Given identical inputs (shell, theta, phi, harmonic), always produce the identical 28-bit address
2. **Decode deterministically:** Given an identical address, always produce identical component values
3. **Satisfy roundtrip identity:** `decode(encode(s, t, p, h)) ≡ (s, t, p, h)` for all valid inputs
4. **Reject invalid inputs:** Addresses exceeding 0x0FFFFFFF or components exceeding their defined ranges must be rejected
5. **Preserve bit-level compatibility:** Implementations across languages and platforms must produce byte-identical results

See [spec/SPEC.md](spec/SPEC.md) for complete conformance requirements and test vectors.

---

## Integration Patterns

RPP functions as a **bridge architecture**, providing semantic routing to existing storage systems:

```
┌─────────────────────────────────────────────────────────────┐
│                    RPP Address Space                         │
│              (Semantic Classification)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Resolver Layer                          │
│         (Address → Backend Mapping + Consent Gating)        │
└───────┬─────────┬─────────┬─────────┬─────────┬────────────┘
        ▼         ▼         ▼         ▼         ▼
   [Filesystem] [Object   [Relational [Vector  [Key-Value
                 Store]    Database]   Database] Store]
```

**Integration requires no migration.** Existing storage systems continue to provide persistence, durability, and scale. RPP adds semantic routing, consent awareness, and lifecycle management.

---

## Documentation

### Core Specification
| Document | Description |
|----------|-------------|
| [spec/SPEC.md](spec/SPEC.md) | Canonical 28-bit addressing specification with formal definitions |
| [spec/PACKET.md](spec/PACKET.md) | Rotational packet format: address + optional payload envelope |
| [spec/SEMANTICS.md](spec/SEMANTICS.md) | Geometric meaning model, sector definitions, grounding interpretation |
| [spec/RESOLVER.md](spec/RESOLVER.md) | Bridge architecture, adapter interfaces, consent gating |

### Design and Rationale
| Document | Description |
|----------|-------------|
| [VISION.md](VISION.md) | Architectural principles and mission |
| [DESIGN_RATIONALE.md](DESIGN_RATIONALE.md) | Justification for each design decision |
| [NON_GOALS.md](NON_GOALS.md) | Explicit exclusions and scope boundaries |
| [RELATED_WORK.md](RELATED_WORK.md) | Academic context and prior art comparison |
| [ADVERSARIAL_ANALYSIS.md](ADVERSARIAL_ANALYSIS.md) | Counterexamples and comparison to existing standards |
| [IRREDUCIBILITY.md](IRREDUCIBILITY.md) | Proof that RPP is the minimum viable solution |
| [BOUNDARIES.md](BOUNDARIES.md) | Hard scope constraints—where RPP must stop |
| [MVP.md](MVP.md) | Minimum viable product specification |

### Governance and Process
| Document | Description |
|----------|-------------|
| [GOVERNANCE.md](GOVERNANCE.md) | Decision-making process and contribution guidelines |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute and cite this work |
| [VERSION_POLICY.md](VERSION_POLICY.md) | Stability guarantees and compatibility promises |
| [ARXIV_INTENT.md](ARXIV_INTENT.md) | Academic publication intent and citation format |

### Implementation
| Document | Description |
|----------|-------------|
| [reference/python/](reference/python/) | Canonical Python reference implementation |
| [reference/haskell/](reference/haskell/) | Pure Haskell reference implementation |
| [hardware/clash/](hardware/clash/) | Clash/FPGA hardware implementation |
| [examples/](examples/) | Usage examples and demonstrations |
| [tests/](tests/) | Pytest suite and official test vectors |

### Diagrams and Visualizations
| Document | Description |
|----------|-------------|
| [diagrams/address-structure.svg](diagrams/address-structure.svg) | 28-bit address field layout |
| [diagrams/bridge-architecture.svg](diagrams/bridge-architecture.svg) | Resolver and storage integration |
| [diagrams/sectors.svg](diagrams/sectors.svg) | Circular sector map (theta) |
| [diagrams/interactive-explorer.html](diagrams/interactive-explorer.html) | Interactive address explorer (open in browser) |

---

## Academic Intent

This specification is published as **defensive prior art** to establish public domain status and prevent patent enclosure. The work is intended for submission to arXiv (cs.OS or cs.DC) and Zenodo for DOI assignment.

**Preferred Citation:**
```
Lennon, A. L. (2024). Rotational Packet Protocol (RPP): A Semantic
Addressing Architecture for Consent-Aware Memory Systems. Version 1.0.0.
https://github.com/anywave/rpp-spec
```

See [ARXIV_INTENT.md](ARXIV_INTENT.md) for complete citation guidance and academic usage policy.

---

## Design Philosophy

RPP is designed for **openness and interoperability** rather than proprietary advantage:

- **Auditability:** All address semantics are transparent and deterministic
- **Reproducibility:** Reference implementations and test vectors enable independent verification
- **Interoperability:** Bridge architecture integrates with existing infrastructure
- **Non-enclosure:** Defensive publication prevents patent capture by any party

These properties align with academic values of transparency, reproducibility, and open inquiry.

---

## License

| Component | License |
|-----------|---------|
| Specification and Documentation | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Reference Implementation | [Apache 2.0](LICENSE) |
| Diagrams | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |

---

## Status

| Component | Status | Version |
|-----------|--------|---------|
| Core Specification | Stable | 1.0.0 |
| Python Reference | Complete | 1.0.0 |
| Haskell Reference | Complete | 1.0.0 |
| Clash/FPGA Hardware | Complete | 1.0.0 |
| Test Vectors | Complete | 1.0.0 |
| Defensive Publication | Ready for submission | — |

---

*Open infrastructure for semantic addressing. Designed for auditability, interoperability, and non-enclosure.*
