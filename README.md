# RPP - Rotational Packet Protocol

**Semantic Addressing for Consent-Aware Systems**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Spec Version](https://img.shields.io/badge/Spec-v1.0.0-green.svg)](spec/SPEC.md)

---

## What is RPP?

RPP (Rotational Packet Protocol) is an open **semantic addressing architecture** that encodes meaning, consent, and lifecycle directly into a 28-bit address.

```
Traditional: address → location → bytes
RPP:         address → meaning → behavior
```

**RPP is not:**
- A new filesystem (it overlays existing storage)
- A database (it routes to databases)
- A blockchain (no consensus mechanism)
- Patentable (intentionally open)

**RPP is:**
- A semantic control plane
- A bridge architecture
- Hardware-software unified
- Consent-aware by design

---

## Quick Start

```python
from rpp_address import encode, decode, from_components

# Create an address
addr = from_components(
    shell=0,      # Hot cache
    theta=45,     # Identity sector
    phi=128,      # Transitional grounding
    harmonic=64   # Summary resolution
)

print(addr)
# RPP(0, 45, 128, 64) = 0x05A8040

print(addr.sector_name)      # "Gene"
print(addr.grounding_level)  # "Transitional"
print(addr.shell_name)       # "Hot"
```

---

## 28-Bit Address Format

```
┌────────┬───────────┬───────────┬────────────┐
│ Shell  │   Theta   │    Phi    │  Harmonic  │
│ 2 bits │  9 bits   │  9 bits   │  8 bits    │
├────────┼───────────┼───────────┼────────────┤
│ Depth  │ Function  │ Grounding │   Mode     │
└────────┴───────────┴───────────┴────────────┘
```

| Field | Meaning | Example |
|-------|---------|---------|
| **Shell** | Storage tier (hot→frozen) | 0=cache, 3=archive |
| **Theta** | Functional sector | Gene, Memory, Guardian... |
| **Phi** | Grounding level | Physical → Abstract |
| **Harmonic** | Resolution/version | Raw → Full fidelity |

---

## Documentation

| Document | Description |
|----------|-------------|
| [VISION.md](VISION.md) | Mission and principles |
| [NON_GOALS.md](NON_GOALS.md) | What RPP explicitly does NOT do |
| [DESIGN_RATIONALE.md](DESIGN_RATIONALE.md) | Why every design decision was made |
| [spec/SPEC.md](spec/SPEC.md) | Canonical 28-bit addressing spec |
| [spec/SEMANTICS.md](spec/SEMANTICS.md) | Meaning model, sectors, grounding |
| [spec/RESOLVER.md](spec/RESOLVER.md) | Bridge architecture, adapters |
| [GOVERNANCE.md](GOVERNANCE.md) | Project governance |
| [DEFENSIVE_PUBLICATION.md](DEFENSIVE_PUBLICATION.md) | Prior art / arXiv paper |

---

## Why Open Source?

We explicitly reject patents because:

1. **Prior art**: Public spec prevents future enclosure
2. **Adoption**: Open infrastructure spreads faster
3. **Philosophy**: Consent-based systems can't be coercively owned
4. **Resilience**: Multiple implementations strengthen the standard

---

## Bridge Architecture

RPP doesn't replace storage — it **routes** to existing systems:

```
┌─────────────────────────────────────────────┐
│           RPP Address Space                 │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│              Resolver                       │
└───────┬─────────┬─────────┬─────────┬───────┘
        ▼         ▼         ▼         ▼
    [FileSystem] [S3]    [Database] [Redis]
```

Zero migration. Semantic routing on top of existing infrastructure.

---

## Test Vectors

Validate your implementation:

```json
{
  "input": {"shell": 0, "theta": 45, "phi": 120, "harmonic": 128},
  "expected": {"hex": "0x05B7880", "decimal": 5961856}
}
```

Full test suite: [tests/test_vectors.json](tests/test_vectors.json)

---

## Contributing

1. Read [GOVERNANCE.md](GOVERNANCE.md)
2. Sign-off commits (DCO)
3. Follow existing patterns
4. Include tests for code

---

## License

- **Code**: Apache 2.0
- **Documentation**: CC BY 4.0
- **Diagrams**: CC BY-SA 4.0

---

## Status

| Component | Status |
|-----------|--------|
| Spec | ✅ v1.0.0 |
| Python reference | ✅ Complete |
| Test vectors | ✅ Complete |
| Defensive publication | ✅ Ready |

---

*Open infrastructure for semantic addressing. Not patentable. Not enclosable.*
