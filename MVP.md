# RPP Minimum Viable Product (MVP)

**Version:** 1.0.0
**Author:** Alexander Liam Lennon
**Last Updated:** 2024-12-27
**License:** CC BY 4.0

---

## Purpose

This document defines the **smallest possible MVP** that proves the RPP thesis. If this MVP works, the core idea is validated. Everything else is optional.

---

## Goal of MVP

> **Prove that a shared, interpretable label reduces duplicated decision logic and improves consistency without replacing anything.**

---

## MVP Must Include Only 4 Components

| Component | Description |
|-----------|-------------|
| 1. Address struct | Fixed fields, encode/decode |
| 2. Resolver | allow/deny + route |
| 3. Adapters | Minimum 2 backends |
| 4. Test vectors | Deterministic validation |

**That's it.**

No coherence pipeline. No twin. No emergence. No hardware.

---

## MVP Spec (Minimal)

### A. Address Format

28-bit address with minimal semantics:

| Field | Bits | Range | Meaning |
|-------|------|-------|---------|
| Shell | 2 | 0-3 | Tier (hot/warm/cold/archive) or lifecycle class |
| Theta | 9 | 0-511 | Domain bucket |
| Phi | 9 | 0-511 | Sensitivity/grounding band |
| Harmonic | 8 | 0-255 | Mode/version |

```
encode(shell, theta, phi, harmonic) = (shell << 26) | (theta << 17) | (phi << 8) | harmonic
```

### B. Resolver Output

A resolver returns a tiny decision:

```json
{
  "allowed": true,
  "route": "s3://bucket-a/path",
  "reason": "phi band requires elevated consent"
}
```

**That's the entire output contract.**

### C. Backend Adapters (Minimum Two)

| Adapter | Purpose |
|---------|---------|
| Local filesystem | File-based storage |
| In-memory store | Testing without cloud |

You can do in-memory for MVP to avoid cloud dependencies.

---

## MVP Demo Scenario

**Scenario:** "One label, consistent behavior across two systems"

### Flow

1. A user requests an operation on an object
2. Two different services both call `resolve(address, context)`
3. Both enforce the same decision without duplicating rules

### Three Cases to Demonstrate

| Case | Address Profile | Expected Outcome |
|------|-----------------|------------------|
| 1 | Low phi (grounded) | ✅ Allowed read |
| 2 | High phi (ethereal) | ❌ Denied write |
| 3 | Cold shell | 🔄 Routed to archive |

**If you can show those 3 cases, you proved the thesis.**

---

## MVP Repo Layout

```
rpp-mvp/
├── README.md
├── SPEC.md
├── src/
│   ├── address.py       # or address.rs, address.hs
│   ├── resolver.py
│   └── adapters/
│       ├── fs.py
│       └── memstore.py
├── tests/
│   ├── test_vectors.json
│   └── test_parity.py
└── examples/
    └── demo_cli.py
```

---

## MVP Build Checklist

### Address

- [ ] Address struct defined (fixed fields)
- [ ] `encode()` → 28-bit int
- [ ] `decode()` → struct
- [ ] Deterministic test vectors (JSON)

### Resolver

- [ ] Resolver function implemented
- [ ] Inputs: `address` + `context`
- [ ] Outputs: `allowed` + `route` + `reason`

### Adapters

- [ ] Filesystem adapter
- [ ] In-memory store adapter

### Demo

- [ ] CLI demo runs in < 2 minutes
- [ ] Shows all 3 cases

---

## MVP Success Criteria (Binary)

MVP is **"real"** if:

| Criterion | Met? |
|-----------|------|
| Two separate modules/services call the resolver | ☐ |
| No duplicated policy logic exists outside resolver | ☐ |
| Behavior is identical for the same address+context | ☐ |
| Developers can add a new domain bucket without editing 10 places | ☐ |

**All four must be true. Partial credit doesn't count.**

---

## The "Stop Line" for MVP (Hard Rule)

If you find yourself adding any of these, **you are leaving MVP scope**:

| Feature | Status |
|---------|--------|
| User accounts | ❌ OUT |
| Biometrics | ❌ OUT |
| ML inference | ❌ OUT |
| Embeddings | ❌ OUT |
| Distributed consensus | ❌ OUT |
| Persistence layers beyond pointers | ❌ OUT |
| Policy DSL | ❌ OUT |
| Ontologies | ❌ OUT |

**MVP proves the core without them.**

---

## Pseudocode: Complete MVP

```python
# address.py
def encode(shell, theta, phi, harmonic):
    return (shell << 26) | (theta << 17) | (phi << 8) | harmonic

def decode(address):
    return (
        (address >> 26) & 0x3,
        (address >> 17) & 0x1FF,
        (address >> 8) & 0x1FF,
        address & 0xFF
    )

# resolver.py
def resolve(address, context):
    shell, theta, phi, harmonic = decode(address)

    # Simple rules (no DSL, just fixed logic)
    if phi > 384 and context.get("consent") != "full":
        return {"allowed": False, "route": None, "reason": "ethereal band requires full consent"}

    if shell >= 2:
        return {"allowed": True, "route": "archive://cold", "reason": "cold tier"}

    return {"allowed": True, "route": "local://hot", "reason": "default"}

# demo_cli.py
if __name__ == "__main__":
    # Case 1: Low phi, allowed
    addr1 = encode(0, 100, 64, 128)
    print(resolve(addr1, {}))  # allowed

    # Case 2: High phi, denied
    addr2 = encode(0, 100, 448, 128)
    print(resolve(addr2, {}))  # denied

    # Case 3: Cold shell, routed
    addr3 = encode(2, 100, 64, 128)
    print(resolve(addr3, {}))  # routed to archive
```

**That's the entire MVP in ~40 lines.**

---

## What MVP Proves

If MVP works, it proves:

1. **Shared labels reduce duplication** — One resolver, many callers
2. **Addresses carry meaning** — No external lookup required
3. **Decisions are consistent** — Same input = same output
4. **Adoption is incremental** — Works in one service, day one

---

## What MVP Does NOT Prove

MVP does not prove:

- Scale (that's infrastructure)
- Security (that's complementary)
- Adoption (that's marketing)
- Completeness (that's impossible)

**MVP proves the core. Everything else is extension.**

---

## Timeline

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1. Address spec | `encode()`, `decode()`, test vectors | ✅ Complete |
| 2. Resolver | `resolve()` with 3 cases | ✅ Complete |
| 3. Demo | CLI showing all cases | 🔄 In progress |
| 4. Validation | Two services, one resolver | ☐ Pending |

---

## Architecture Layer Model

```
┌─────────────────────────────────────────────────────────────┐
│           [ RPP Address + Semantics ]                        │
│               ↑ MUST be simple & universal                   │
│               ↑ THIS IS ALL RPP DEFINES                      │
├─────────────────────────────────────────────────────────────┤
│           [ Optional Packet Payload ]                        │
│               May exist or not                               │
│               RPP doesn't care what's inside                 │
├─────────────────────────────────────────────────────────────┤
│           [ Storage / Transport Layer ]                      │
│               FS, S3, memory, holographic, etc.              │
│               RPP routes TO this, doesn't provide it         │
└─────────────────────────────────────────────────────────────┘
```

**RPP occupies exactly one layer.** Everything above and below is someone else's problem.

---

*"If it can't be proven small, it can't be trusted large."*
