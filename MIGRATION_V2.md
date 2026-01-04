# Migration Guide: RPP v1.0 (28-bit) to Ra-Canonical v2.0 (32-bit)

**Status:** In Progress
**Date:** 2026-01-04

---

## 1. Format Comparison

### OLD Format (v1.0 - 28-bit)
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

### NEW Format (Ra-Canonical v2.0 - 32-bit)
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

## 2. Semantic Changes

| Old Field | Old Range | New Field | New Range | Mapping |
|-----------|-----------|-----------|-----------|---------|
| Shell (2 bits) | 0-3 | **Removed** | N/A | Storage tier now derived from context |
| Theta (9 bits) | 0-511 | θ (5 bits) | 1-27 | 27 Repitans from Ra System |
| Phi (9 bits) | 0-511 | φ (3 bits) | 1-6 | 6 RAC access levels |
| Harmonic (8 bits) | 0-255 | h (3 bits) | 0-4 | 5 Omega tiers (RED→BLUE) |
| N/A | N/A | r (8 bits) | 0-255 | Radius/intensity scalar |
| N/A | N/A | Reserved (13 bits) | 0-8191 | CRC or future use |

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
- [ ] reference/haskell/README.md
- [x] hardware/clash/RPP.hs (marked deprecated)
- [x] hardware/clash/RPP_Canonical.hs (NEW - Ra-Canonical v2.0)
- [x] hardware/clash/README.md (v2.0 notice, points to RPP_Canonical.hs)
- [ ] examples/*.py
- [ ] tests/*.py
- [ ] landing/index.html
- [ ] docs/index.html
- [ ] diagrams/*.svg
- [ ] diagrams/*.html
- [ ] paper/main.tex
- [ ] .github/workflows/ci.yml
- [ ] .github/ISSUE_TEMPLATE/*.yml

### silver-pancake (19 files)
- [x] README.md (32-bit Ra-Canonical reference)
- [x] docs/ROTATIONAL_PACKET_PROTOCOL.md (Ra-Canonical notice added)
- [x] docs/RPP_HARDWARE_ARCHITECTURE.md (Ra-Canonical notice added)
- [x] docs/RPP_LIFECYCLE_GUIDE.md (v2.0 notice added)
- [x] docs/END_TO_END_TUTORIAL.md (v2.0 notice added)
- [x] docs/DEMO_GUIDE.md (v2.0 notice added)
- [ ] docs/E2E_TEST_FIXES.md
- [x] docs/whitepapers/WHITEPAPER_06_FPGA_CONSENT_GATE.md (v2.0 notice added)
- [ ] hardware/phase_slot_register.v
- [ ] hardware/hdl/DEPRECATED.md
- [x] fpga/clash/RPP.hs (marked deprecated)
- [ ] fpga/simulations/rpp_hardware_sim.py
- [ ] fpga/constraints/arty_a7.xdc
- [x] holographic/virtual_hardware.py (deprecation notice added)
- [x] holographic/rpp_integration_proof.py (deprecation notice added)
- [ ] crypto/keys.py
- [ ] tests/test_virtual_hardware.py
- [ ] tests/test_rpp_api.py
- [ ] tests/test_emulation_firmware_alignment.py

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
