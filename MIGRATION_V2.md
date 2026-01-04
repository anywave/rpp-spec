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
- [ ] README.md
- [ ] DESIGN_RATIONALE.md
- [ ] DEFENSIVE_PUBLICATION.md
- [ ] MVP.md
- [ ] VISION.md
- [ ] VERSION_POLICY.md
- [ ] CONTRIBUTING.md
- [ ] ARXIV_INTENT.md
- [ ] pyproject.toml
- [ ] spec/SPEC.md
- [ ] spec/PACKET.md
- [ ] spec/RESOLVER.md
- [ ] spec/SPEC-EXTENDED.md
- [ ] spec/extensions/MESH.md
- [ ] rpp/address.py
- [ ] rpp/cli.py
- [ ] rpp/packet.py
- [ ] rpp/resolver.py
- [ ] rpp/visual.py
- [ ] rpp/i18n.py
- [ ] rpp/extended.py
- [ ] reference/python/rpp_address.py
- [ ] reference/haskell/RPPAddress.hs
- [ ] reference/haskell/README.md
- [ ] hardware/clash/RPP.hs
- [ ] hardware/clash/README.md
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
- [ ] README.md
- [ ] docs/ROTATIONAL_PACKET_PROTOCOL.md
- [ ] docs/RPP_HARDWARE_ARCHITECTURE.md
- [ ] docs/RPP_LIFECYCLE_GUIDE.md
- [ ] docs/END_TO_END_TUTORIAL.md
- [ ] docs/DEMO_GUIDE.md
- [ ] docs/E2E_TEST_FIXES.md
- [ ] docs/whitepapers/WHITEPAPER_06_FPGA_CONSENT_GATE.md
- [ ] hardware/phase_slot_register.v
- [ ] hardware/hdl/DEPRECATED.md
- [ ] fpga/clash/RPP.hs
- [ ] fpga/simulations/rpp_hardware_sim.py
- [ ] fpga/constraints/arty_a7.xdc
- [ ] holographic/virtual_hardware.py
- [ ] holographic/rpp_integration_proof.py
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
