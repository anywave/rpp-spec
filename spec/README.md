# RPP Specification Directory

This directory contains the complete specification for the Recursive Packet Protocol (RPP),
a consent-aware addressing system aligned with SPIRAL architecture.

---

## Two-Layer Architecture

RPP operates as two complementary, coexisting layers — analogous to how DNS and subnet
addressing both exist in TCP/IP without one replacing the other. See
[ADDRESSING-LAYERS.md](ADDRESSING-LAYERS.md) for the full architecture.

```
┌─────────────────────────────────────────────────────────┐
│          APPLICATION / DEVELOPER LAYER                  │
│                                                         │
│   RPP Semantic Interface (v1.0)                         │
│   28-bit  ·  Shell / Theta / Phi / Harmonic             │
│   Human-meaningful: storage tier, type, consent, mode   │
├─────────────────────────────────────────────────────────┤
│          TRANSLATION / RESOLVER LAYER                   │
│                                                         │
│   v1.0 ──── encodes ───► v2.0 transport address         │
│   (like DNS name  ──────► IP address)                   │
├─────────────────────────────────────────────────────────┤
│          TRANSPORT / RESONANCE LAYER                    │
│                                                         │
│   RPP Ra-Canonical (v2.0)                               │
│   32-bit  ·  θ / φ / h / r / reserved                  │
│   Ra-derived: Repitan, RAC level, Omega, radius         │
└─────────────────────────────────────────────────────────┘
```

Neither layer is deprecated. They serve different levels of the protocol stack.

---

## Specification Index

### Semantic Interface Layer (v1.0) — Developer-Facing

| Document | Version | Status | Description |
|----------|---------|--------|-------------|
| [SPEC.md](SPEC.md) | 1.0 | **Active** | Semantic Interface Layer — 28-bit Shell/Theta/Phi/Harmonic |
| [SPEC-EXTENDED.md](SPEC-EXTENDED.md) | 1.1 | Active | Extended field definitions and edge cases |
| [SEMANTICS.md](SEMANTICS.md) | 1.0 | Active | Sector and grounding-level semantic definitions |
| [PACKET.md](PACKET.md) | 1.0 | Active | Packet framing for v1.0 semantic addresses |

### Transport / Resonance Layer (v2.0) — Substrate-Facing

| Document | Version | Status | Description |
|----------|---------|--------|-------------|
| [RPP-CANONICAL-v2.md](RPP-CANONICAL-v2.md) | 2.0 | **Active** | Transport/Resonance Layer — 32-bit Ra-derived address format |
| [CONSENT-HEADER-v1.md](CONSENT-HEADER-v1.md) | 1.0 | Draft | System-layer envelope wrapping RPP address |
| [PMA-SCHEMA-v1.md](PMA-SCHEMA-v1.md) | 1.0 | Draft | Phase Memory Anchor persistence schema |
| [ROUTING-FLOW-v1.md](ROUTING-FLOW-v1.md) | 1.0 | Draft | Complete resolver routing decision flow |

### Architecture and Cross-Layer Documents

| Document | Version | Status | Description |
|----------|---------|--------|-------------|
| [ADDRESSING-LAYERS.md](ADDRESSING-LAYERS.md) | 1.0 | **Active** | Two-layer architecture — the definitive reference |
| [RESOLVER.md](RESOLVER.md) | 2.1 | Active | Resolver protocol spanning both layers (updated) |
| [GEOMETRY.md](GEOMETRY.md) | 1.0 | Active | Toroidal state vector and rotational encryption |
| [CONTINUITY.md](CONTINUITY.md) | 1.0 | Active | Consciousness routing layer — the Ford Protocol |
| [NETWORK.md](NETWORK.md) | 1.0 | Active | Consent-field mesh network architecture |
| [DEPLOYABLE.md](DEPLOYABLE.md) | 1.0 | Active | Real-world deployment guide (without spintronic hardware) |

---

## Field Reference

### v1.0 Semantic Interface Fields

| Field | Bits | Range | Meaning |
|-------|------|-------|---------|
| Shell | 2 | 0–3 | Storage proximity: Hot → Warm → Cold → Frozen |
| Theta | 9 | 0–511 | Data type sector (continuous azimuthal angle) |
| Phi | 9 | 0–511 | Consent level (continuous polar spectrum) |
| Harmonic | 8 | 0–255 | Routing mode / frequency tier |

**Total: 28 bits**

### v2.0 Transport/Resonance Fields (Ra-Derived)

| Field | Bits | Range | Ra Source |
|-------|------|-------|-----------|
| θ (Theta) | 5 | 1–27 | 27 Repitans |
| φ (Phi) | 3 | 0–5 | 6 RAC Levels |
| h (Harmonic) | 3 | 0–4 | 5 Omega Formats |
| r (Radius) | 8 | 0–255 | Ankh-normalized |
| Reserved/CRC | 13 | — | Integrity / routing hints |

**Total: 32 bits**

---

## Packet Type Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    PACKET TYPE HIERARCHY                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  RPP v1.0 Address     4 bytes     Semantic (28-bit)          │
│       │                                                      │
│       └──▶ [resolver] RPP v2.0 Address                       │
│                        4 bytes     Transport/Resonance       │
│                   │                                          │
│                   └──▶ SPIRAL Routing Frame                  │
│                              22 bytes   Consent Header + RPP │
│                         │                                    │
│                         └──▶ SPIRAL Envelope                 │
│                                    208+ bytes   Full packet  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Status

### Python (`rpp/`)

| Module | Status | Description |
|--------|--------|-------------|
| `address.py` | ✅ Complete | v1.0 Semantic Interface address (Shell/Theta/Phi/Harmonic) |
| `address_canonical.py` | ✅ Complete | v2.0 Transport address with full Ra integration |
| `consent_header.py` | ✅ Complete | Consent header encoding/decoding |
| `pma.py` | ✅ Complete | Phase Memory Anchor storage |
| `resolver.py` | ✅ Complete | Cross-layer resolver (v1.0 → v2.0 translation) |
| `packet.py` | ✅ Complete | Packet framing utilities |
| `mesh.py` | 🔄 In Progress | Consent-field mesh (see NETWORK.md) |
| `coherence.py` | 🔄 In Progress | Toroidal geometry and rotational encoding (see GEOMETRY.md) |
| `transitions.py` | 🔄 In Progress | Continuity/Ford Protocol routing (see CONTINUITY.md) |
| `sector_router.py` | ✅ Complete | Sector classification and routing |
| `ra_constants.py` | ✅ Complete | Ra System constants |
| `consent.py` | ✅ Complete | Consent field utilities |

### Verilog (`hardware/verilog/`)

| Module | Status | Description |
|--------|--------|-------------|
| `rpp_canonical.v` | ✅ Complete | v2.0 Ra-derived address encoder/decoder/coherence |

### Tests (`tests/`)

| Test Suite | Status | Coverage |
|------------|--------|----------|
| `test_address_canonical.py` | ✅ Complete | Full Ra alignment validation |

---

## Integration Points

RPP addresses integrate with:

- **SPIRAL Resolver**: v1.0 → v2.0 translation for all route calculations
- **Consent Packet Header**: Overlay consistency validation (v2.0 transport layer)
- **Phase Memory Anchor**: Address reference anchoring
- **Cymatics Engine**: Tone generation via θ-φ-h vector (v2.0)
- **Fragment Mesh (DTFM)**: Coherence-based routing (NETWORK.md)
- **Ford Protocol**: Session continuity across address recycling (CONTINUITY.md)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v2.0 Transport Layer | 2025-01-01 | Ra-Canonical format added as Transport/Resonance Layer |
| v1.0 Semantic Layer | 2024-12-27 | Original 28-bit Semantic Interface Layer (still active) |
| ADDRESSING-LAYERS.md | 2026-03-04 | Two-layer architecture formally documented |
| GEOMETRY / CONTINUITY / NETWORK | 2026-03-04 | New spec documents for geometry, continuity, mesh layers |
| RESOLVER v2.1 | 2026-03-04 | Resolver updated to handle cross-layer translation |
| DEPLOYABLE v1.0 | 2026-03-04 | Deployment guide for real-world (non-spintronic) use |

---

## Symbolic Note

> *"The address is not a label — it is a coordinate in resonance space, expressed at the layer
> appropriate to the observer."*

---

*RPP Specification — Anywave Creations*
