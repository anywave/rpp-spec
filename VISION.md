# RPP Vision & Intent

**Version:** 1.0.0
**Status:** Canonical
**License:** CC BY 4.0

---

## Mission

RPP (Rotational Packet Protocol) is an open semantic addressing architecture that encodes **meaning, consent, and lifecycle directly into the address itself**.

Traditional memory and storage systems ask: *"Where do I put this?"*
RPP asks: *"Where does this belong?"*

---

## One-Sentence Summary

> RPP turns storage from "where bytes live" into "how meaning flows" — without breaking what already works.

---

## Core Principles

### 1. Meaning at the Address Level

Every RPP address is a **28-bit coordinate** encoding:
- **Shell** (2 bits): Radial depth / storage tier
- **Theta** (9 bits): Functional sector (what it does)
- **Phi** (9 bits): Elevation / grounding level
- **Harmonic** (8 bits): Resolution / mode / version

No lookup tables required. The address **is** the classification.

### 2. Bridge Architecture, Not Replacement

RPP is a **semantic control plane**, not a data plane.

- Existing filesystems, databases, and object stores remain
- RPP adds routing, consent, and lifecycle awareness
- Zero-migration integration path
- Storage stays dumb and durable; RPP stays smart and light

### 3. Consent and Coherence as First-Class Citizens

Access is not binary (allowed/denied). It is:
- **State-aware**: Depends on current coherence level
- **Consent-gated**: Revocable, contextual, non-transferable
- **Graceful**: Degrades rather than crashes

### 4. Hardware-Software Parity

The 28-bit address format is designed for:
- FPGA register packing
- SPI transfer efficiency
- MRAM addressability
- Deterministic routing

Software emulation and hardware execution produce identical results.

---

## What RPP Is NOT

| Non-Goal | Explanation |
|----------|-------------|
| A new filesystem | RPP overlays existing storage |
| A database | RPP routes to databases, not replaces them |
| A blockchain | No consensus mechanism, no distributed ledger |
| An AI model | RPP routes AI outputs, not generates them |
| A security product | RPP enables consent; it is not a firewall |
| Patentable | This architecture is intentionally open and unpatentable |

---

## Ethical Stance

RPP is designed around:

| Principle | Implementation |
|-----------|----------------|
| **Consent** | Access requires explicit, revocable authorization |
| **Agency** | Users control their meaning space |
| **Non-coercion** | No punitive mechanisms; only reflection |
| **Transparency** | Address semantics are fully auditable |
| **Openness** | The architecture is public and unenclosable |

This is not a marketing position. It is an architectural invariant.

---

## Why Open Source

We explicitly reject patent protection because:

1. **Prior-art defense**: Public specification prevents later enclosure
2. **Adoption speed**: Open infrastructure spreads faster than proprietary
3. **Philosophical coherence**: A consent-based system cannot be coercively owned
4. **Plural futures**: Multiple implementations strengthen the standard

Open source is not charity. It is strategy aligned with values.

---

## Success Criteria

RPP succeeds when:

- [ ] The 28-bit addressing spec is stable and widely understood
- [ ] Multiple independent implementations exist
- [ ] Integration with existing systems requires no migration
- [ ] The architecture can outlive its original authors
- [ ] No single entity can capture or enclose the standard

---

## Governance Philosophy

- **Steward, not owner**: Maintainers hold the center of gravity
- **Calm over clever**: Boring stability beats exciting fragmentation
- **Explicit over implicit**: All decisions documented
- **Forkable**: If governance fails, the spec survives

---

## Document References

| Document | Purpose |
|----------|---------|
| [SPEC.md](spec/SPEC.md) | Canonical 28-bit addressing specification |
| [SEMANTICS.md](spec/SEMANTICS.md) | Meaning model and geometric interpretation |
| [RESOLVER.md](spec/RESOLVER.md) | Bridge/adapter architecture |
| [GOVERNANCE.md](GOVERNANCE.md) | Decision-making process |
| [LICENSE](LICENSE) | Apache 2.0 (code) / CC BY 4.0 (docs) |

---

*This document is intentionally brief. Clarity is the goal.*
