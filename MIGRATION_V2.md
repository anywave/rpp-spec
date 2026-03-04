# RPP Layer Translation Reference: Semantic Interface ↔ Transport/Resonance

**Status:** Active reference
**Date:** 2026-01-04
**Revised:** 2026-03-04

> **Framing Note:** This document was originally titled "Migration Guide" with the framing that
> v1.0 was being replaced by v2.0. That framing was incorrect. v1.0 and v2.0 are NOT competing
> versions — they are **complementary layers** of the same protocol stack, analogous to DNS names
> and IP addresses. Neither is deprecated. This document now describes the **translation** between
> the two layers. See [spec/ADDRESSING-LAYERS.md](spec/ADDRESSING-LAYERS.md) for full architecture.

---

## 1. Format Comparison

### Semantic Interface Layer (v1.0 - 28-bit)
```
┌─────────┬───────────┬───────────┬────────────┐
│  Shell  │   Theta   │    Phi    │  Harmonic  │
│ (2 bits)│  (9 bits) │  (9 bits) │  (8 bits)  │
├─────────┼───────────┼───────────┼────────────┤
│ [27:26] │  [25:17]  │  [16:8]   │   [7:0]    │
└─────────┴───────────┴───────────┴────────────┘
Total: 28 bits
Encoding: (shell << 26) | (theta << 17) | (phi << 8) | harmonic
```

### Transport/Resonance Layer (v2.0 - 32-bit)
```
┌─────────┬─────────┬─────────┬──────────┬───────────────────┐
│    θ    │    φ    │    h    │    r     │    Reserved/CRC   │
│ (5 bits)│ (3 bits)│ (3 bits)│ (8 bits) │    (13 bits)      │
├─────────┼─────────┼─────────┼──────────┼───────────────────┤
│ [31:27] │ [26:24] │ [23:21] │ [20:13]  │      [12:0]       │
└─────────┴─────────┴─────────┴──────────┴───────────────────┘
Total: 32 bits
```

---

## 2. Layer Field Correspondence

These fields are **not replacements** — they are representations of the same address at two
different layers of the protocol stack. The projection from semantic to transport is intentionally
lossy: the transport layer encodes resonance category, not exact semantic position.

| Semantic (v1.0) | Range | Transport (v2.0) | Range | Layer Projection |
|-----------------|-------|------------------|-------|-----------------|
| Shell (2 bits) | 0–3 | r / radius | 0–255 | Shell → normalized radius (shell/3) |
| Theta (9 bits) | 0–511 | θ (5 bits) | 1–27 | 512 semantic sectors → 27 Repitans |
| Phi (9 bits) | 0–511 | φ (3 bits) | 1–6 | 512-value consent spectrum → 6 RAC levels |
| Harmonic (8 bits) | 0–255 | h (3 bits) | 0–4 | 256 routing modes → 5 Omega tiers |
| — | — | Reserved (13 bits) | 0–8191 | CRC or routing hints |

**Note on Phi:** Phi's reduction from 9 bits (512 consent values) to 3 bits (6 RAC levels)
is a transport-layer approximation. The full consent spectrum is preserved in the semantic layer
and must not be discarded — the transport tier can only route at the granularity of RAC levels.
The resolver uses the semantic Phi value for fine-grained consent decisions.

---

## 3. Files to Update

### rpp-spec (~50 files)
- [x] README.md
- [x] DESIGN_RATIONALE.md
- [x] DEFENSIVE_PUBLICATION.md (v2.0 notice added)
- [x] MVP.md
- [x] VISION.md
- [x] VERSION_POLICY.md
- [x] CONTRIBUTING.md
- [x] ARXIV_INTENT.md
- [x] pyproject.toml (version 2.0.0)
- [x] spec/SPEC.md (marked deprecated)
- [x] spec/PACKET.md
- [x] spec/RPP-CANONICAL-v2.md (marked canonical)
- [x] spec/RESOLVER.md
- [x] spec/SPEC-EXTENDED.md
- [x] spec/extensions/MESH.md (v2.0 notice added)
- [x] rpp/address.py (deprecation warning added)
- [x] rpp/cli.py (deprecation notice added)
- [x] rpp/packet.py (deprecation warning added)
- [x] rpp/resolver.py (deprecation warning added)
- [x] rpp/visual.py (deprecation notice added)
- [x] rpp/i18n.py (deprecation notice added)
- [x] rpp/extended.py (deprecation notice added)
- [x] reference/python/rpp_address.py (deprecation warning added)
- [x] reference/haskell/RPPAddress.hs (deprecation notice added)
- [x] reference/haskell/README.md (deprecation notice added)
- [x] hardware/clash/RPP.hs (marked deprecated)
- [x] hardware/clash/RPP_Canonical.hs (NEW - Ra-Canonical v2.0)
- [x] hardware/clash/README.md (v2.0 notice, points to RPP_Canonical.hs)
- [x] examples/*.py (deprecation notices added)
- [x] tests/test_address.py, test_extended.py (deprecation notices added)
- [x] landing/index.html (meta description updated)
- [x] docs/index.html (meta description updated)
- [x] diagrams/README.md (v2.0 notice added)
- [x] diagrams/interactive-explorer.html (deprecation notice added)
- [x] paper/main.tex (v2.0 deprecation notice added)
- [x] .github/workflows/ci.yml (v2.0 notice added)
- [x] .github/workflows/mesh-ci.yml (v2.0 notice added)
- [x] .github/ISSUE_TEMPLATE/rpp-collaboration.yml (updated to v2.0)
- [x] .github/ISSUE_TEMPLATE/rpp-collaboration.md (updated to v2.0)

### silver-pancake (19 files)
- [x] README.md (32-bit Ra-Canonical reference)
- [x] docs/ROTATIONAL_PACKET_PROTOCOL.md (Ra-Canonical notice added)
- [x] docs/RPP_HARDWARE_ARCHITECTURE.md (Ra-Canonical notice added)
- [x] docs/RPP_LIFECYCLE_GUIDE.md (v2.0 notice added)
- [x] docs/END_TO_END_TUTORIAL.md (v2.0 notice added)
- [x] docs/DEMO_GUIDE.md (v2.0 notice added)
- [x] docs/E2E_TEST_FIXES.md (v2.0 notice added)
- [x] docs/whitepapers/WHITEPAPER_06_FPGA_CONSENT_GATE.md (v2.0 notice added)
- [x] hardware/phase_slot_register.v (deprecation notice added)
- [x] hardware/hdl/DEPRECATED.md (already has v2.0 info)
- [x] fpga/clash/RPP.hs (marked deprecated)
- [x] fpga/simulations/rpp_hardware_sim.py (deprecation notice added)
- [x] fpga/constraints/arty_a7.xdc (v2.0 deprecation notice added)
- [x] holographic/virtual_hardware.py (deprecation notice added)
- [x] holographic/rpp_integration_proof.py (deprecation notice added)
- [x] crypto/keys.py (N/A - generic crypto module, not RPP format specific)
- [x] tests/test_virtual_hardware.py (deprecation notice added)
- [x] tests/test_rpp_api.py (deprecation notice added)
- [x] tests/test_emulation_firmware_alignment.py (deprecation notice added)
- [x] docs/E2E_TEST_FIXES.md (v2.0 notice added)

---

## 4. Code Migration Patterns

### Python: Old encode/decode
```python
# OLD
def encode(shell, theta, phi, harmonic):
    return (shell << 26) | (theta << 17) | (phi << 8) | harmonic

def decode(address):
    shell = (address >> 26) & 0x03
    theta = (address >> 17) & 0x1FF
    phi = (address >> 8) & 0x1FF
    harmonic = address & 0xFF
    return (shell, theta, phi, harmonic)
```

```python
# NEW (use rpp.address_canonical)
from rpp.address_canonical import RPPAddress, create_from_sector, ThetaSector

# Create from semantic sector
addr = create_from_sector(ThetaSector.MEMORY, phi=3, omega=2, radius=0.75)

# Or direct
addr = RPPAddress(theta=10, phi=3, omega=2, radius=0.75)

# Encode/decode
raw = addr.to_raw()  # 32-bit integer
addr2 = RPPAddress.from_raw(raw)
```

### Verilog: Bit widths
```verilog
// OLD
input [1:0] shell;    // 2 bits
input [8:0] theta;    // 9 bits
input [8:0] phi;      // 9 bits
input [7:0] harmonic; // 8 bits

// NEW (Ra-Canonical)
input [4:0] theta;    // 5 bits (1-27 Repitans)
input [2:0] phi;      // 3 bits (1-6 RAC levels)
input [2:0] omega;    // 3 bits (0-4 Omega tiers)
input [7:0] radius;   // 8 bits (0-255 intensity)
input [12:0] reserved; // 13 bits (CRC/future)
```

---

## 5. Reference Documents

- `spec/RPP-CANONICAL-v2.md` - Authoritative address format
- `spec/CONSENT-HEADER-v1.md` - 18-byte header specification
- `rpp/address_canonical.py` - Python reference implementation
- `rpp/consent_header.py` - Header implementation
- `hardware/verilog/rpp_canonical.v` - HDL reference

---

## 6. Validation

After migration, verify:
1. All tests pass with new format
2. Round-trip encode/decode works
3. Header CRC validation works
4. Consent state derivation is correct
5. PMA storage aligns with spec

---

*Migration in progress. Track updates via git commits.*
