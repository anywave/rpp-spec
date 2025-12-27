# Version Policy and Stability Guarantees

**Document Version:** 1.0.0
**Last Updated:** 2024-12-27
**License:** CC BY 4.0

---

## Purpose

This document defines the versioning scheme, stability guarantees, and compatibility promises for the RPP specification. Implementers and users can rely on these commitments when building on RPP.

---

## Version Format

RPP uses Semantic Versioning 2.0.0:

```
MAJOR.MINOR.PATCH
```

| Component | Meaning | Example |
|-----------|---------|---------|
| MAJOR | Breaking changes | 1.0.0 → 2.0.0 |
| MINOR | Backward-compatible additions | 1.0.0 → 1.1.0 |
| PATCH | Backward-compatible fixes | 1.0.0 → 1.0.1 |

---

## Current Version

**RPP Specification Version:** 1.0.0
**Status:** Stable
**Release Date:** 2024-12-27

---

## Stability Guarantees

### What v1.0.0 Guarantees

The following are **immutable** for all 1.x.x versions:

#### Address Format
| Guarantee | Value |
|-----------|-------|
| Total address width | 28 bits |
| Shell field position | Bits 27:26 |
| Shell field width | 2 bits |
| Theta field position | Bits 25:17 |
| Theta field width | 9 bits |
| Phi field position | Bits 16:8 |
| Phi field width | 9 bits |
| Harmonic field position | Bits 7:0 |
| Harmonic field width | 8 bits |

#### Encoding/Decoding
| Guarantee | Formula |
|-----------|---------|
| Encoding | `(shell << 26) \| (theta << 17) \| (phi << 8) \| harmonic` |
| Shell decoding | `(address >> 26) & 0x3` |
| Theta decoding | `(address >> 17) & 0x1FF` |
| Phi decoding | `(address >> 8) & 0x1FF` |
| Harmonic decoding | `address & 0xFF` |

#### Value Ranges
| Field | Minimum | Maximum |
|-------|---------|---------|
| Shell | 0 | 3 |
| Theta | 0 | 511 |
| Phi | 0 | 511 |
| Harmonic | 0 | 255 |
| Address | 0x0000000 | 0x0FFFFFFF |

#### Test Vectors

All test vectors in `tests/test_vectors.json` version 1.0.0 will produce identical results in all 1.x.x implementations.

### What May Change in 1.x.x

| Change Type | Permitted | Requires |
|-------------|-----------|----------|
| New test vectors | Yes | Must not contradict existing |
| Clarified documentation | Yes | Must not change meaning |
| Additional examples | Yes | Must be consistent |
| New optional features | Yes | Must not affect core behavior |
| Bug fixes | Yes | Must fix toward spec intent |

---

## Compatibility Definitions

### Backward Compatible

A change is **backward compatible** if:

1. All valid 1.0.0 addresses remain valid
2. All valid 1.0.0 encodings produce the same addresses
3. All valid 1.0.0 decodings produce the same components
4. All 1.0.0 test vectors pass unchanged

### Forward Compatible

A change is **forward compatible** if:

1. An older implementation can ignore new features
2. An older implementation produces correct results for core operations
3. New features are clearly identified as additions

### Breaking Change

A change is **breaking** if:

1. Valid addresses become invalid (or vice versa)
2. Encoding/decoding results change
3. Field positions or widths change
4. Existing test vectors fail

---

## Version Lifecycle

### Development Phase

- Version: 0.x.x
- Stability: None guaranteed
- Status: RPP has completed this phase

### Stable Phase (Current)

- Version: 1.x.x
- Stability: Guarantees above apply
- Duration: Indefinite (minimum 5 years)

### Evolution Phase

- Version: 2.x.x (if ever)
- Trigger: Fundamental limitations requiring breaking changes
- Process: 6-month deprecation, migration guide, parallel support

---

## Deprecation Policy

### For Minor Features

1. Mark as deprecated in documentation
2. Maintain for at least 2 minor versions
3. Remove in subsequent minor version with notice

### For Specification Elements

1. **6-month advance notice** before any breaking change
2. **Migration guide** published before change takes effect
3. **Parallel version support** for transition period
4. **Sunset date** clearly communicated

---

## Extension Guidelines

### Compatible Extensions

Extensions that do not conflict with the core specification:

- Additional sector definitions within unassigned ranges
- Application-specific harmonic interpretations
- Additional resolver behaviors

**May use:** Same version number with extension identifier
**Example:** "RPP 1.0.0 + MyExtension 1.0"

### Incompatible Extensions

Extensions that modify core behavior:

- Different field widths
- Different encoding formulas
- Conflicting sector definitions

**Must use:** Different specification name
**Example:** "Extended RPP" or "RPP-variant"

---

## Implementation Compliance

### Conformance Levels

| Level | Requirements |
|-------|--------------|
| **Core** | Encode/decode per spec, pass all test vectors |
| **Standard** | Core + sector interpretation + consent gating |
| **Full** | Standard + resolver + lifecycle management |

### Claiming Compliance

Implementations may claim:

```
"Implements RPP 1.0.0 Core"
"Implements RPP 1.0.0 Standard"
"Implements RPP 1.0.0 Full"
```

### Compliance Verification

1. Run official test vectors
2. Verify roundtrip identity
3. Test boundary conditions
4. Document any deviations

---

## Support Timeline

### Version 1.0.0

| Milestone | Commitment |
|-----------|------------|
| Release | 2024-12-27 |
| Minimum support | 2029-12-27 (5 years) |
| Security fixes | Throughout support period |
| Clarifications | Throughout support period |

### If Version 2.0.0 Released

| Phase | Duration |
|-------|----------|
| 2.0.0 release | — |
| Parallel 1.x support | 2 years minimum |
| 1.x security-only | 1 year additional |
| 1.x end-of-life | Announced 6 months ahead |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-27 | Initial stable release |

---

## Promises to Implementers

We commit to:

1. **No surprise breaking changes** — Always announced with deprecation period
2. **Clear communication** — All changes documented in release notes
3. **Test vector stability** — Existing tests never invalidated
4. **Long support windows** — Minimum 5 years for major versions
5. **Migration support** — Guides provided for any breaking changes

---

## Questions

For versioning questions:
- Open an issue with `versioning` label
- Reference this document

---

*Stability enables trust. Trust enables adoption.*
