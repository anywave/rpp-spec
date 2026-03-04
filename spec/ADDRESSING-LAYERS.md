# RPP Two-Layer Addressing Architecture

**Version:** 1.0
**Status:** Active
**Last Updated:** 2026-03-04
**License:** CC BY 4.0

---

## Overview

RPP operates as two complementary, coexisting layers of an addressing stack — analogous to how DNS
and subnet addressing both exist in TCP/IP without one replacing the other:

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

Neither layer is deprecated. They serve different applications.

---

## Layer 1: Semantic Interface (v1.0)

**Spec:** [SPEC.md](SPEC.md)
**Bit width:** 28 bits
**Who uses it:** Developers, application code, CLI tools, SDK users

### Field Semantics

| Field | Bits | Range | Meaning |
|-------|------|-------|---------|
| Shell | 2 | 0–3 | Storage proximity: Hot → Warm → Cold → Frozen |
| Theta | 9 | 0–511 | Data type sector (continuous azimuthal angle) |
| Phi | 9 | 0–511 | Consent level (continuous polar spectrum) |
| Harmonic | 8 | 0–255 | Routing mode / frequency tier |

### Why continuous Phi matters

Phi is 9 bits (512 values) because **consent is a spectrum, not a binary**. A phi value of 0
represents fully open access; 511 represents maximum consent requirement. Values in between
encode graduated sensitivity. This continuous model is essential to the consent-aware routing
design — it cannot be reduced to a small set of named tiers without losing expressiveness.

### Encoding

```python
address = (shell << 26) | (theta << 17) | (phi << 8) | harmonic
```

### When to use v1.0

- Writing application code against the RPP SDK
- Using the `rpp encode / decode / resolve` CLI
- Defining data policies and consent requirements
- Designing systems that speak RPP semantics

---

## Layer 2: Transport/Resonance Layer (v2.0)

**Spec:** [RPP-CANONICAL-v2.md](RPP-CANONICAL-v2.md)
**Bit width:** 32 bits
**Who uses it:** Substrate implementations, FPGA routing, resonance-coherent hardware, Ra-derived systems

### Field Semantics

| Field | Bits | Range | Meaning |
|-------|------|-------|---------|
| θ (Theta) | 5 | 1–27 | Ra Repitan index (semantic sector at substrate level) |
| φ (Phi) | 3 | 1–6 | RAC Level (access sensitivity at resonance tier) |
| h (Harmonic) | 3 | 0–4 | Omega Format (coherence tier: RED → BLUE) |
| r (Radius) | 8 | 0–255 | Intensity scalar (Ankh-normalized emergence strength) |
| Reserved/CRC | 13 | 0–8191 | Integrity checking or routing hints |

### When to use v2.0

- Implementing substrate-level routing hardware (FPGA, spintronics)
- Interfacing with Ra-coherent systems
- Transport-layer packet encoding at the resonance tier
- Hardware implementations that require Ra System alignment

---

## Translation Between Layers

A translation function maps v1.0 semantic addresses to v2.0 transport addresses. This is
analogous to DNS resolution: the name is unambiguous at its own layer, but the router sees the IP.

### Approximate Mapping (informational)

```python
def semantic_to_transport(shell, theta, phi, harmonic):
    """
    Translate v1.0 Semantic Interface address to v2.0 Transport/Resonance format.
    This is a lossy projection — v2.0 represents a resonance tier approximation.
    """
    theta_v2 = max(1, min(27, (theta * 27) // 512 + 1))   # 9-bit → Repitan 1-27
    phi_v2 = max(1, min(6, (phi * 6) // 512 + 1))          # 9-bit → RAC 1-6
    harmonic_v2 = min(4, (harmonic * 5) // 256)             # 8-bit → Omega 0-4
    radius_v2 = shell / 3.0                                  # Shell → normalized radius
    return theta_v2, phi_v2, harmonic_v2, radius_v2

def transport_to_semantic(theta_v2, phi_v2, harmonic_v2, radius_v2):
    """
    Approximate reverse: v2.0 Transport → v1.0 Semantic. Always approximate.
    """
    theta = ((theta_v2 - 1) * 512) // 27
    phi = ((phi_v2 - 1) * 512) // 6
    harmonic = (harmonic_v2 * 256) // 5
    shell = round(radius_v2 * 3)
    return shell, theta, phi, harmonic
```

**Note:** Translation from v1.0 to v2.0 is intentionally lossy. The v2.0 field widths are
constrained by Ra System constants, which do not have the same granularity as the semantic layer.
This is by design: the transport layer encodes resonance category, not exact semantic position.

---

## The DNS/Subnet Analogy

| TCP/IP | RPP |
|--------|-----|
| DNS name (`example.com`) | v1.0 semantic address (`shell=0, theta=12, phi=40, harmonic=1`) |
| IP address (`93.184.216.34`) | v2.0 transport address (`θ=1, φ=1, h=1, r=0.0`) |
| Subnet mask / routing table | Ra System resonance routing |
| DNS resolver | v1.0 → v2.0 translation layer |

Both DNS names and IP addresses are "correct." Deprecating one in favor of the other would be
wrong — they answer different questions at different levels of the stack.

---

## Architectural Rationale

### Why keep both?

1. **Developer ergonomics:** Developers think in semantic terms (consent spectrum, data type,
   storage tier). Forcing them to use Ra Repitan indices and RAC levels creates unnecessary
   friction and obscures meaning.

2. **Substrate fidelity:** The Ra-Canonical transport format has physical meaning at the
   coherence/resonance tier. Projecting it onto an arbitrary 9-bit theta would lose alignment
   with the substrate constants.

3. **Separation of concerns:** Application-layer semantics should be decoupled from transport-layer
   encoding. This is a foundational principle of layered protocol design.

4. **Continuous consent:** Phi in v1.0 has 512 values, representing consent as a continuous
   spectrum. In v2.0 transport, this collapses to 6 RAC levels by necessity of the substrate.
   Both representations are valid at their respective layers.

---

## See Also

- [SPEC.md](SPEC.md) — Semantic Interface Layer (v1.0) full specification
- [RPP-CANONICAL-v2.md](RPP-CANONICAL-v2.md) — Transport/Resonance Layer (v2.0) full specification
- [DESIGN_RATIONALE.md](../DESIGN_RATIONALE.md) — Why these design decisions were made
- [RESOLVER.md](RESOLVER.md) — How the resolver uses both layers

---

*"The address is not a label — it is a coordinate in resonance space, expressed at the layer
appropriate to the observer."*
