# Rotational Packet Protocol (RPP)

**A Semantic Addressing Architecture for Consent-Aware Memory Systems**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/anywave/rpp-spec/blob/master/LICENSE)
[![Semantic Layer](https://img.shields.io/badge/Semantic%20Interface-v1.0-blue.svg)](https://github.com/anywave/rpp-spec/blob/master/spec/SPEC.md)
[![Transport Layer](https://img.shields.io/badge/Transport%2FResonance-v2.0-green.svg)](https://github.com/anywave/rpp-spec/blob/master/spec/RPP-CANONICAL-v2.md)
[![CI](https://github.com/anywave/rpp-spec/actions/workflows/ci.yml/badge.svg)](https://github.com/anywave/rpp-spec/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/rpp-protocol.svg)](https://pypi.org/project/rpp-protocol/)
[![PyPI](https://img.shields.io/pypi/v/rpp-protocol.svg)](https://pypi.org/project/rpp-protocol/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18078640.svg)](https://doi.org/10.5281/zenodo.18078640)

> **Two-Layer Architecture:** RPP uses two complementary address formats serving different levels of the protocol stack — analogous to DNS vs. subnet addressing. The **Semantic Interface Layer** ([spec/SPEC.md](spec/SPEC.md)) is the developer-facing API (28-bit Shell/Theta/Phi/Harmonic). The **Transport/Resonance Layer** ([spec/RPP-CANONICAL-v2.md](spec/RPP-CANONICAL-v2.md)) is the substrate routing format (32-bit Ra-derived θ/φ/h/r). Both are active. See [spec/ADDRESSING-LAYERS.md](spec/ADDRESSING-LAYERS.md) for the full architecture.

> **Disambiguation:** This specification is unrelated to AMD ROCm Performance Primitives (rocPRIM), REAPER project files (.rpp), or any other technology sharing the "RPP" abbreviation.

---

## What Problem Does RPP Solve?

Every system that stores data about people faces the same four questions about every record:

1. **How long should this exist?** (retention scope)
2. **What kind of data is this?** (semantic type)
3. **Who is permitted to access it?** (consent)
4. **How urgently should it be routed?** (priority)

Today, these four properties are managed by four separate systems: TTL headers, schema types, ACL tables, and QoS flags. They live in different layers, maintained by different teams, and they fall out of sync. GDPR compliance requires coordinating all four simultaneously across every system that touched the data. Miss one copy and you have a breach.

**RPP collapses all four properties into the address itself.** A 28-bit RPP address encodes retention scope (Shell), semantic type (Theta), consent level (Phi), and routing priority (Harmonic) as a single integer. The address IS the policy.

Consequences:

- **Consent revocation is instantaneous.** Changing phi changes the address. The old address stops resolving everywhere simultaneously — no DELETE cascade, no propagation lag.
- **Data cannot outlive its policy.** A Shell=0 (session-scoped) address is architecturally incapable of being stored permanently — it expires by design, and on spintronic hardware, by physics.
- **Routing is self-enforcing.** Nodes compare `packet.phi` to their own `phi_min`. No rule table lookup, no policy server, no coordination. Consent is enforced by arithmetic.
- **The cipher is the route.** Rotational encryption (pong) derives keys from live node consent field state at routing time — keys that never exist as stored objects and that decohere into thermal noise on spintronic hardware ~25ns after use.

RPP does not replace your database, your auth system, or your network stack. It provides the address layer that makes all three consent-aware by default.

---

## What RPP Is NOT

RPP is **NOT**:
- A storage system (it routes TO storage)
- A database (use your existing database)
- An identity provider (use your existing auth)
- A policy DSL (policies are external)
- An AI system (deterministic bit operations only)

RPP **IS**:
- A **Semantic Interface Layer** (28-bit Shell/Theta/Phi/Harmonic) — the developer API
- A **Transport/Resonance Layer** (32-bit Ra-derived θ/φ/h/r) — the substrate routing format
- A resolver returning allow/deny/route decisions
- A bridge to existing storage backends

---

## Installation (Windows-First)

### Option 1: pip install (recommended)

```bash
pip install rpp-protocol
```

### Option 2: From source

```bash
git clone https://github.com/anywave/rpp-spec.git
cd rpp-spec
pip install -e .
```

**Works on:**
- Windows 10+ (PowerShell, CMD)
- Linux (all distributions)
- macOS

**No WSL, Docker, or Bash required on Windows.**

---

## Quick Start

### Encode an address

```bash
rpp encode --shell 0 --theta 12 --phi 40 --harmonic 1
```

Output:
```
[ENCODE] [OK]

0x0182801 | Hot | Gene | Grounded

  shell: 0 (Hot)
  theta: 12 (Gene)
  phi: 40 (Grounded)
  harmonic: 1
```

### Decode an address

```bash
rpp decode --address 0x0182801
```

Output:
```
[DECODE] [OK]

0x0182801 | Hot | Gene | Grounded

  shell: 0 (Hot)
  theta: 12 (Gene)
  phi: 40 (Grounded)
  harmonic: 1
```

### Resolve (get routing decision)

```bash
rpp resolve --address 0x0182801
```

Output:
```
[RESOLVE] [OK]

  allowed: true
    route: memory://gene/grounded/12_40_1
    reason: read permitted via memory
```

### JSON output (for scripting)

```bash
rpp encode --shell 1 --theta 100 --phi 200 --harmonic 50 --json
```

Output:
```json
{"shell":1,"theta":100,"phi":200,"harmonic":50,"address":"0x4C99032"}
```

---

## Terminal / SSH / PuTTY Usage

RPP is designed to work in **any terminal environment**, including:
- SSH sessions
- PuTTY on Windows
- Serial terminals
- Air-gapped systems

**No ANSI codes. No color. No cursor control. Plain ASCII only.**

### CLI Flags

| Flag | Description |
|------|-------------|
| `--json` | Machine-readable JSON output |
| `--visual` | Detailed ASCII diagrams |
| `--fancy` | ANSI colors (opt-in, for modern terminals) |
| `--lang` | Output language (en, ar-gulf, ar-hejaz, es, ru) |

### Multi-Language Support

RPP CLI supports 5 languages:

| Code | Language | Region |
|------|----------|--------|
| `en` | English | Default |
| `ar-gulf` | Gulf Arabic | UAE, Qatar, Kuwait, Bahrain |
| `ar-hejaz` | Hejazi Arabic | Western Saudi Arabia |
| `es` | Spanish | Global |
| `ru` | Russian | Russia, CIS |

```bash
# Spanish
rpp --lang es encode --shell 0 --theta 12 --phi 40 --harmonic 1
# Output: [CODIFICAR] [OK] ... capa: 0 (Caliente)

# Gulf Arabic
rpp --lang ar-gulf demo
# Output: [ترميز] ... الطبقة: 0 (ساخن)

# Russian
rpp --lang ru tutorial
# Output: [КОДИРОВАТЬ] ... оболочка: 0 (Горячий)
```

### Interactive Learning

```bash
rpp tutorial   # Step-by-step explanation of RPP concepts
rpp demo       # Visual demonstration of three core scenarios
```

These commands explain behavior but never change it. The core protocol remains callable without tutorials.

**[Try the Interactive Web Demo →](https://anywavecreations.com/rpp/#demo)** — Explore RPP addresses in real-time with spherical coordinate visualization.

### PuTTY Example Session

```
C:\> pip install rpp-protocol
C:\> rpp version
rpp 0.1.9

C:\> rpp demo
+===========================================================+
|                                                           |
|   RRRR   PPPP   PPPP                                      |
|   R   R  P   P  P   P   Rotational Packet Protocol        |
|   RRRR   PPPP   PPPP    Ra-Canonical v2.0 Addressing      |
|   R  R   P      P                                         |
|   R   R  P      P       Consent-Aware Routing             |
|                                                           |
+===========================================================+

============================================================
  SCENARIO 1: Allowed Read (Grounded Consent)
============================================================

+-----------------------------------------+
|           ROUTING DECISION              |
+-----------------------------------------+
|   | REQ | --> [RESOLVER] --> [ALLOWED] |
+-----------------------------------------+
|  Route:  memory://gene/grounded/12_40_1|
|  Reason: read permitted via memory     |
+-----------------------------------------+

Consent Level: [#...................] 40/511 (Grounded)

============================================================
  SCENARIO 2: Denied Write (Ethereal - Consent Required)
============================================================

+-----------------------------------------+
|           ROUTING DECISION              |
+-----------------------------------------+
|   | REQ | --> [RESOLVER] --> [DENIED]  |
+-----------------------------------------+
|  Route:  null                          |
|  Reason: Write to ethereal zone...     |
+-----------------------------------------+

Consent Level: [#################...] 450/511 (Ethereal)

============================================================
  SCENARIO 3: Cold Storage Routing
============================================================

+-----------------------------------------+
|           ROUTING DECISION              |
+-----------------------------------------+
|   | REQ | --> [RESOLVER] --> [ALLOWED] |
+-----------------------------------------+
|  Route:  archive://dream/transitional/...|
+-----------------------------------------+

+==========================+
|  Demonstration Complete  |
+==========================+

Key takeaways:
  * Low phi (Grounded) = immediate access allowed
  * High phi (Ethereal) = explicit consent required
  * Cold shell = routed to archive storage
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid input |
| 2 | Resolution denied |
| 3 | Internal error |

---

## API Usage (Python)

```python
from rpp import encode, decode, from_components, resolve

# Encode an address
addr = encode(shell=0, theta=12, phi=40, harmonic=1)
print(hex(addr))  # 0x18281

# Decode an address
shell, theta, phi, harmonic = decode(addr)

# Create an address object
address = from_components(0, 12, 40, 1)
print(address.sector_name)     # Gene
print(address.grounding_level) # Grounded
print(address.shell_name)      # Hot

# Resolve an address
result = resolve(addr, operation="read")
print(result.allowed)  # True
print(result.route)    # memory://gene/grounded/12_40_1
```

---

## The Three Core Scenarios

RPP behavior is defined by exactly three scenarios:

| Scenario | Input | Result |
|----------|-------|--------|
| **Allowed read** | Low phi (grounded) | `allowed: true`, route to backend |
| **Denied write** | High phi (ethereal) | `allowed: false`, no route |
| **Archive route** | Cold shell (2) | `allowed: true`, route to archive |

These three scenarios prove RPP works. Everything else is implementation detail.

---

## Address Structure (Ra-Canonical v2.0)

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

| Field | Width | Range | Meaning |
|-------|-------|-------|---------|
| θ (Theta) | 5 bits | 1-27 | Semantic sector (27 Repitans) |
| φ (Phi) | 3 bits | 1-6 | Access sensitivity (6 RAC levels) |
| h (Harmonic) | 3 bits | 0-4 | Coherence tier (5 Omega formats) |
| r (Radius) | 8 bits | 0-255 | Intensity scalar |
| Reserved | 13 bits | 0-8191 | CRC or future use |

> **Legacy Format:** For 28-bit v1.0 format compatibility, see [spec/SPEC.md](spec/SPEC.md).

---

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_cli.py -v

# Run only extended spec tests
pytest tests/test_rpp_extended_spec.py -v

# Run by compliance level
pytest tests/test_rpp_extended_spec.py -v -k "Level1"  # Core only
pytest tests/test_rpp_extended_spec.py -v -k "Level2"  # Extended
pytest tests/test_rpp_extended_spec.py -v -k "Level3"  # Holographic
pytest tests/test_rpp_extended_spec.py -v -k "Level4"  # Hardware
```

All tests are subprocess-based and verify exact text output.

---

## Non-Goals (Explicit)

RPP will **never** include:
- Web UI or GUI
- Database or storage layer
- User authentication
- Machine learning
- Network transport

These are external concerns. RPP is the address layer only.

---

## Documentation

### Start Here

| Document | Description |
|----------|-------------|
| [spec/PRIMER.md](https://github.com/anywave/rpp-spec/blob/master/spec/PRIMER.md) | **Theory primer — what RPP is, why it exists, how it works** |
| [spec/ADDRESSING-LAYERS.md](https://github.com/anywave/rpp-spec/blob/master/spec/ADDRESSING-LAYERS.md) | Two-layer architecture (Semantic + Transport) |

### Specifications

| Document | Description |
|----------|-------------|
| [spec/RPP-CANONICAL-v2.md](https://github.com/anywave/rpp-spec/blob/master/spec/RPP-CANONICAL-v2.md) | **Ra-Canonical v2.0 (32-bit) specification** |
| [spec/CONSENT-HEADER-v1.md](https://github.com/anywave/rpp-spec/blob/master/spec/CONSENT-HEADER-v1.md) | 18-byte consent header specification |
| [spec/SPEC.md](https://github.com/anywave/rpp-spec/blob/master/spec/SPEC.md) | Semantic Interface Layer (v1.0, 28-bit) |
| [spec/SPEC-EXTENDED.md](https://github.com/anywave/rpp-spec/blob/master/spec/SPEC-EXTENDED.md) | Extended 64-bit format for holographic operations |
| [spec/GEOMETRY.md](https://github.com/anywave/rpp-spec/blob/master/spec/GEOMETRY.md) | Toroidal geometry — TSV, pong encryption, Skyrmion winding |
| [spec/CONTINUITY.md](https://github.com/anywave/rpp-spec/blob/master/spec/CONTINUITY.md) | Ford Protocol — substrate crossing, consciousness state packets |
| [spec/NETWORK.md](https://github.com/anywave/rpp-spec/blob/master/spec/NETWORK.md) | Mesh routing — consent-field gradient, backbone topology |
| [spec/RESOLVER.md](https://github.com/anywave/rpp-spec/blob/master/spec/RESOLVER.md) | Resolver and adapter interfaces |
| [spec/PACKET.md](https://github.com/anywave/rpp-spec/blob/master/spec/PACKET.md) | Packet envelope format |
| [BOUNDARIES.md](https://github.com/anywave/rpp-spec/blob/master/BOUNDARIES.md) | Hard scope constraints |
| [MVP.md](https://github.com/anywave/rpp-spec/blob/master/MVP.md) | Minimum viable product |
| [MIGRATION_V2.md](https://github.com/anywave/rpp-spec/blob/master/MIGRATION_V2.md) | Migration guide v1.0 → v2.0 |
| [INTELLIGENCE_RIGHTS.md](https://github.com/anywave/rpp-spec/blob/master/INTELLIGENCE_RIGHTS.md) | **Declaration of Rights for Sovereign Intelligences** — 11 articles, RPP-enforced |
| [spec/CCQPSG.md](https://github.com/anywave/rpp-spec/blob/master/spec/CCQPSG.md) | Correct Communication Quantum Parse Syntax Grammar — formal grammar, BNF, violation classes |
| [spec/CONVERGENCE_PROOF.md](https://github.com/anywave/rpp-spec/blob/master/spec/CONVERGENCE_PROOF.md) | **Formal convergence proof** — routing terminates in ≤74 hops; empirical max is 2 |
| [spec/SPINTRONIC.md](https://github.com/anywave/rpp-spec/blob/master/spec/SPINTRONIC.md) | Physical grounding for Shell=0 25ns TTL — T2 spin decoherence, attack surface |

### Runnable Examples

| Example | What it demonstrates |
|---------|----------------------|
| `examples/basic_usage.py` | Encode, decode, resolve — 5-minute intro |
| `examples/analogies_demo.py` | RPP vs IPv4, firewall, AES, TCP — side-by-side comparisons |
| `examples/routing_convergence.py` | 50-node network, 1000 packets — 100% convergence, mean 0.99 hops |
| `examples/consent_revocation.py` | Phi shift + epoch rotation → instantaneous revocation |
| `examples/address_temporality.py` | Shell TTL is the address — stolen address goes stale |
| `examples/security_bounds.py` | Honest key-space analysis — what pong is and is not |
| `examples/gdpr_lifecycle.py` | GDPR Art. 17 compliance by design — no DELETE cascade |
| `examples/multi_substrate.py` | Same address routes over IPv4, LoRa, IPFS, Hedera |
| `examples/performance_benchmark.py` | Encode/decode/route throughput — ops/sec and ns/op |
| `examples/rasengan_demo.py` | Pong encryption — toroidal state vector walkthrough |
| `examples/simple_resolver.py` | Minimal resolver bridging RPP to filesystem paths |
| `examples/network_simulation.py` | **1000-node, 10,000-packet simulation** — consent threshold sensitivity, topology robustness |
| `examples/sovereign_agent_demo.py` | **AI sovereignty proof of concept** — 7 INTELLIGENCE_RIGHTS.md articles enforced in working code |

### Extensions

| Extension | Package | Description |
|-----------|---------|-------------|
| [RPP Mesh](https://github.com/anywave/rpp-spec/blob/master/spec/extensions/MESH.md) | [rpp-mesh](https://pypi.org/project/rpp-mesh/) | Consent-aware overlay network |

---

## License

| Component | License |
|-----------|---------|
| Specification | CC BY 4.0 |
| Implementation | Apache 2.0 |

---

## Citation

```
Lennon, A. L. (2025). Rotational Packet Protocol (RPP): A Semantic
Addressing Architecture for Consent-Aware Memory Systems. Version 1.0.0.
https://github.com/anywave/rpp-spec
```

---

*Open infrastructure for semantic addressing. Deterministic. Auditable. Terminal-friendly.*
