# RPP Addressing Specification

**Version:** 1.0.0
**Status:** Canonical
**Last Updated:** 2024-12-27
**License:** CC BY 4.0

---

## 1. Overview

This document defines the canonical 28-bit RPP (Rotational Packet Protocol) addressing format. All conforming implementations MUST adhere to this specification.

---

## 2. Address Format

### 2.1 Bit Layout

```
┌─────────────────────────────────────────────────────────────┐
│                    28-BIT RPP ADDRESS                        │
├────────┬────────────┬────────────┬──────────────────────────┤
│ Shell  │   Theta    │    Phi     │        Harmonic          │
│ 2 bits │  9 bits    │  9 bits    │        8 bits            │
├────────┼────────────┼────────────┼──────────────────────────┤
│ [27:26]│  [25:17]   │  [16:8]    │         [7:0]            │
└────────┴────────────┴────────────┴──────────────────────────┘
```

### 2.2 Field Specifications

| Field | Bits | Position | Range | Type |
|-------|------|----------|-------|------|
| Shell | 2 | 27:26 | 0-3 | Unsigned |
| Theta | 9 | 25:17 | 0-511 | Unsigned |
| Phi | 9 | 16:8 | 0-511 | Unsigned |
| Harmonic | 8 | 7:0 | 0-255 | Unsigned |

**Total Width:** 28 bits (unsigned integer)
**Address Space:** 2²⁸ = 268,435,456 unique addresses

### 2.3 Bit Masks

| Field | Mask | Shift |
|-------|------|-------|
| Shell | 0x0C000000 | 26 |
| Theta | 0x03FE0000 | 17 |
| Phi | 0x0001FF00 | 8 |
| Harmonic | 0x000000FF | 0 |

### 2.4 Reserved Bits (28-31)

When RPP addresses are stored or transported in wider containers (e.g., 32-bit or 64-bit words):

1. **Bits 28-31 MUST be zero** for any valid canonical RPP address
2. **Addresses with non-zero bits 28-31 MUST NOT be interpreted** as valid RPP addresses
3. **These bits are reserved** for potential future extension
4. **Implementations MUST validate** that bits 28-31 are zero before interpreting an address

**Rationale:** This reservation allows future specification versions to extend the address space if needed, while maintaining backward compatibility with existing implementations that properly validate.

```
32-bit container:
┌────────────────┬─────────────────────────────────────────────┐
│   Reserved     │              28-bit RPP Address              │
│   (MUST = 0)   │  Shell | Theta | Phi | Harmonic              │
├────────────────┼────────────────────────────────────────────┤
│   [31:28]      │               [27:0]                        │
└────────────────┴────────────────────────────────────────────┘
```

---

## 3. Encoding

### 3.1 Algorithm

```
address = (shell << 26) | (theta << 17) | (phi << 8) | harmonic
```

### 3.2 Pseudocode

```
FUNCTION encode(shell, theta, phi, harmonic) -> address:
    ASSERT 0 <= shell <= 3
    ASSERT 0 <= theta <= 511
    ASSERT 0 <= phi <= 511
    ASSERT 0 <= harmonic <= 255

    address = 0
    address = address OR (shell SHIFT_LEFT 26)
    address = address OR (theta SHIFT_LEFT 17)
    address = address OR (phi SHIFT_LEFT 8)
    address = address OR harmonic

    RETURN address
```

### 3.3 Reference Implementation (Python)

```python
def encode_rpp_address(shell: int, theta: int, phi: int, harmonic: int) -> int:
    """
    Encode RPP components into a 28-bit address.

    Args:
        shell: Radial depth (0-3)
        theta: Angular longitude (0-511)
        phi: Angular latitude (0-511)
        harmonic: Frequency/mode (0-255)

    Returns:
        28-bit unsigned integer

    Raises:
        ValueError: If any component out of range
    """
    if not (0 <= shell <= 3):
        raise ValueError(f"Shell must be 0-3, got {shell}")
    if not (0 <= theta <= 511):
        raise ValueError(f"Theta must be 0-511, got {theta}")
    if not (0 <= phi <= 511):
        raise ValueError(f"Phi must be 0-511, got {phi}")
    if not (0 <= harmonic <= 255):
        raise ValueError(f"Harmonic must be 0-255, got {harmonic}")

    return (shell << 26) | (theta << 17) | (phi << 8) | harmonic
```

---

## 4. Decoding

### 4.1 Algorithm

```
shell    = (address >> 26) & 0x3
theta    = (address >> 17) & 0x1FF
phi      = (address >> 8) & 0x1FF
harmonic = address & 0xFF
```

### 4.2 Pseudocode

```
FUNCTION decode(address) -> (shell, theta, phi, harmonic):
    ASSERT 0 <= address <= 0x0FFFFFFF

    shell    = (address SHIFT_RIGHT 26) AND 0x3
    theta    = (address SHIFT_RIGHT 17) AND 0x1FF
    phi      = (address SHIFT_RIGHT 8) AND 0x1FF
    harmonic = address AND 0xFF

    RETURN (shell, theta, phi, harmonic)
```

### 4.3 Reference Implementation (Python)

```python
def decode_rpp_address(address: int) -> tuple[int, int, int, int]:
    """
    Decode a 28-bit RPP address into components.

    Args:
        address: 28-bit unsigned integer

    Returns:
        Tuple of (shell, theta, phi, harmonic)

    Raises:
        ValueError: If address exceeds 28 bits
    """
    if not (0 <= address <= 0x0FFFFFFF):
        raise ValueError(f"Address must be 0-0x0FFFFFFF, got {hex(address)}")

    shell = (address >> 26) & 0x3
    theta = (address >> 17) & 0x1FF
    phi = (address >> 8) & 0x1FF
    harmonic = address & 0xFF

    return (shell, theta, phi, harmonic)
```

---

## 5. Invariants

### 5.1 Address Invariants

The following MUST always be true:

1. **Bounded Range:** `0 <= address <= 0x0FFFFFFF`
2. **Deterministic Encoding:** `encode(decode(x)) == x` for all valid `x`
3. **Deterministic Decoding:** `decode(encode(s,t,p,h)) == (s,t,p,h)` for all valid inputs
4. **No Reserved Bits:** Bits 28-31 are unused and MUST be zero

### 5.2 Component Invariants

| Component | Invariant |
|-----------|-----------|
| Shell | Always 0-3 (2-bit unsigned) |
| Theta | Always 0-511 (9-bit unsigned) |
| Phi | Always 0-511 (9-bit unsigned) |
| Harmonic | Always 0-255 (8-bit unsigned) |

---

## 6. Angular Conversions

### 6.1 Theta (Longitude)

To convert degrees (0-359) to 9-bit theta:

```python
def degrees_to_theta(degrees: float) -> int:
    """Convert 0-359 degrees to 0-511 theta."""
    normalized = degrees % 360
    return int(normalized * 511 / 359)

def theta_to_degrees(theta: int) -> float:
    """Convert 0-511 theta to 0-359 degrees."""
    return theta * 359 / 511
```

### 6.2 Phi (Latitude)

To convert degrees (-90 to +90) to 9-bit phi:

```python
def latitude_to_phi(latitude: float) -> int:
    """Convert -90 to +90 latitude to 0-511 phi."""
    normalized = latitude + 90  # 0-180
    return int(normalized * 511 / 180)

def phi_to_latitude(phi: int) -> float:
    """Convert 0-511 phi to -90 to +90 latitude."""
    return (phi * 180 / 511) - 90
```

---

## 7. Test Vectors

### 7.1 Boundary Cases

| Test Case | Shell | Theta | Phi | Harmonic | Address (Hex) | Address (Dec) |
|-----------|-------|-------|-----|----------|---------------|---------------|
| Minimum | 0 | 0 | 0 | 0 | 0x0000000 | 0 |
| Maximum | 3 | 511 | 511 | 255 | 0xFFFFFFF | 268,435,455 |
| Shell max | 3 | 0 | 0 | 0 | 0xC000000 | 201,326,592 |
| Theta max | 0 | 511 | 0 | 0 | 0x3FE0000 | 66,846,720 |
| Phi max | 0 | 0 | 511 | 0 | 0x001FF00 | 130,816 |
| Harmonic max | 0 | 0 | 0 | 255 | 0x00000FF | 255 |

### 7.2 Representative Cases

| Description | Shell | Theta | Phi | Harmonic | Address (Hex) |
|-------------|-------|-------|-----|----------|---------------|
| Hot cache, identity sector | 0 | 45 | 256 | 128 | 0x05B0080 |
| Warm memory, standard | 1 | 100 | 255 | 64 | 0x44CFF40 |
| Cold archive, grounded | 2 | 200 | 50 | 32 | 0x86433220 |
| Frozen meta, abstract | 3 | 450 | 400 | 200 | 0xF8590C8 |

### 7.3 Roundtrip Verification

```python
# All test cases MUST pass roundtrip
test_cases = [
    (0, 0, 0, 0),
    (3, 511, 511, 255),
    (1, 256, 256, 128),
    (2, 100, 400, 50),
]

for shell, theta, phi, harmonic in test_cases:
    encoded = encode_rpp_address(shell, theta, phi, harmonic)
    decoded = decode_rpp_address(encoded)
    assert decoded == (shell, theta, phi, harmonic), f"Roundtrip failed for {(shell, theta, phi, harmonic)}"
```

---

## 8. Hardware Considerations

### 8.1 Register Packing

The 28-bit address fits in a 32-bit register with 4 bits spare:

```
┌────────────┬────────────────────────────────┐
│  4 unused  │        28-bit RPP address      │
│   [31:28]  │            [27:0]              │
└────────────┴────────────────────────────────┘
```

The upper 4 bits MAY be used for:
- Parity bits
- Protocol version
- Error correction
- Application-specific flags

### 8.2 SPI Transfer

For SPI transmission, addresses are sent MSB-first in 4 bytes:

```
Byte 0: [31:24] - Upper 4 bits (unused) + Shell + Theta[8:6]
Byte 1: [23:16] - Theta[5:0] + Phi[8:6]
Byte 2: [15:8]  - Phi[5:0] + Harmonic[7:6]
Byte 3: [7:0]   - Harmonic[5:0] + padding
```

### 8.3 Verilog Module

```verilog
module rpp_address_decoder (
    input  wire [27:0] address,
    output wire [1:0]  shell,
    output wire [8:0]  theta,
    output wire [8:0]  phi,
    output wire [7:0]  harmonic
);
    assign shell    = address[27:26];
    assign theta    = address[25:17];
    assign phi      = address[16:8];
    assign harmonic = address[7:0];
endmodule

module rpp_address_encoder (
    input  wire [1:0]  shell,
    input  wire [8:0]  theta,
    input  wire [8:0]  phi,
    input  wire [7:0]  harmonic,
    output wire [27:0] address
);
    assign address = {shell, theta, phi, harmonic};
endmodule
```

---

## 9. Error Handling

### 9.1 Invalid Addresses

| Error Condition | Response |
|-----------------|----------|
| Address > 0x0FFFFFFF | Reject with INVALID_ADDRESS |
| Encoding overflow | Clamp to maximum or reject |
| Decoding non-28-bit | Mask upper bits or reject |

### 9.2 Recommended Behavior

```python
def validate_address(address: int) -> bool:
    """Return True if address is valid 28-bit RPP address."""
    return 0 <= address <= 0x0FFFFFFF
```

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-27 | Initial specification |

---

## 11. Conformance

An implementation is conforming if it:

1. Correctly encodes all valid component combinations
2. Correctly decodes all valid addresses
3. Passes all test vectors in Section 7
4. Rejects or handles invalid inputs per Section 9

---

*This specification is released under CC BY 4.0. Attribution required.*
