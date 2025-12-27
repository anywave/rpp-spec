# Rotational Packet Protocol (RPP)

**A Semantic Addressing Architecture for Consent-Aware Memory Systems**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Spec Version](https://img.shields.io/badge/Spec-v1.0.0-green.svg)](spec/SPEC.md)
[![CI](https://github.com/anywave/rpp-spec/workflows/CI/badge.svg)](https://github.com/anywave/rpp-spec/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> **Disambiguation:** This specification is unrelated to AMD ROCm Performance Primitives (rocPRIM), REAPER project files (.rpp), or any other technology sharing the "RPP" abbreviation.

---

## What Problem Does RPP Solve?

RPP provides semantic addressing for consent-aware systems. Instead of opaque memory locations, RPP addresses encode meaning: what kind of data, how accessible, and where to route it. The resolver returns simple decisions: **allow**, **deny**, or **route**.

---

## What RPP Is NOT

RPP is **NOT**:
- A storage system (it routes TO storage)
- A database (use your existing database)
- An identity provider (use your existing auth)
- A policy DSL (policies are external)
- An AI system (deterministic bit operations only)

RPP **IS**:
- A deterministic 28-bit semantic address
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
address: 0x0018281
shell: 0 (Hot)
theta: 12 (Gene)
phi: 40 (Grounded)
harmonic: 1
```

### Decode an address

```bash
rpp decode --address 0x0018281
```

### Resolve (get routing decision)

```bash
rpp resolve --address 0x0018281
```

Output:
```
allowed: true
route: memory://gene/grounded/12_40_1
reason: read permitted via memory
```

### JSON output (for scripting)

```bash
rpp encode --shell 1 --theta 100 --phi 200 --harmonic 50 --json
```

---

## Terminal / SSH / PuTTY Usage

RPP is designed to work in **any terminal environment**, including:
- SSH sessions
- PuTTY on Windows
- Serial terminals
- Air-gapped systems

**No ANSI codes. No color. No cursor control. Plain text only.**

### PuTTY Example Session

```
C:\> pip install rpp-protocol
C:\> rpp version
rpp 0.1.0

C:\> rpp demo
RPP Demonstration
=================

Scenario 1: Allowed read (low phi)
----------------------------------------
Address: 0x0018281
allowed: true
route: memory://gene/grounded/12_40_1
reason: read permitted via memory

Scenario 2: Denied write (high phi)
----------------------------------------
Address: 0x0C8E140
allowed: false
route: null
reason: Write to ethereal zone (phi=450) requires explicit consent

Scenario 3: Routed to archive (cold shell)
----------------------------------------
Address: 0x8640020
allowed: true
route: archive://witness/transitional/200_128_32
reason: read permitted via archive

Demonstration complete.
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

## Address Structure

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

| Field | Width | Range | Meaning |
|-------|-------|-------|---------|
| Shell | 2 bits | 0-3 | Storage tier (hot → frozen) |
| Theta | 9 bits | 0-511 | Functional sector |
| Phi | 9 bits | 0-511 | Grounding level (access control) |
| Harmonic | 8 bits | 0-255 | Resolution/mode |

---

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_cli.py -v
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

| Document | Description |
|----------|-------------|
| [spec/SPEC.md](spec/SPEC.md) | 28-bit addressing specification |
| [spec/RESOLVER.md](spec/RESOLVER.md) | Resolver and adapter interfaces |
| [spec/PACKET.md](spec/PACKET.md) | Packet envelope format |
| [BOUNDARIES.md](BOUNDARIES.md) | Hard scope constraints |
| [MVP.md](MVP.md) | Minimum viable product |

---

## License

| Component | License |
|-----------|---------|
| Specification | CC BY 4.0 |
| Implementation | Apache 2.0 |

---

## Citation

```
Lennon, A. L. (2024). Rotational Packet Protocol (RPP): A Semantic
Addressing Architecture for Consent-Aware Memory Systems. Version 1.0.0.
https://github.com/anywave/rpp-spec
```

---

*Open infrastructure for semantic addressing. Deterministic. Auditable. Terminal-friendly.*
