# Rotational Packet Specification

**Version:** 1.0.0
**Status:** Canonical
**Last Updated:** 2024-12-27
**License:** CC BY 4.0

---

## 1. Overview

This document defines the **Rotational Packet** — the minimal envelope that combines an RPP address with an optional payload. A rotational packet is the atomic unit of semantically-addressed data.

> **The Clean Rule:** A rotational packet is simply a small envelope with a structured address and an optional payload. That's it.

---

## 2. Packet Structure

### 2.1 Minimal Format

```
┌─────────────────────────────────────────────────────────────┐
│                    ROTATIONAL PACKET                         │
├──────────────────────┬──────────────────────────────────────┤
│     RPP Address      │           Payload (Optional)          │
│      (4 bytes)       │           (0 to N bytes)              │
├──────────────────────┼──────────────────────────────────────┤
│       [31:0]         │              [N:32]                   │
└──────────────────────┴──────────────────────────────────────┘
```

### 2.2 Field Definitions

| Field | Size | Required | Description |
|-------|------|----------|-------------|
| **Address** | 4 bytes | YES | 28-bit RPP address in bits [27:0], bits [31:28] reserved (must be zero) |
| **Payload** | 0-N bytes | NO | Optional data, pointer, hash, or content |

### 2.3 Minimum Packet Size

- **Minimum:** 4 bytes (address only, no payload)
- **Maximum:** Implementation-defined (address + payload)

---

## 3. Address Field

### 3.1 Layout

The first 4 bytes contain the RPP address:

```
Byte 0       Byte 1       Byte 2       Byte 3
┌──────────┬──────────┬──────────┬──────────┐
│ Reserved │          │          │          │
│ + Shell  │  Theta   │   Phi    │ Harmonic │
│ + Theta  │  + Phi   │  + Harm  │          │
└──────────┴──────────┴──────────┴──────────┘
  [31:24]    [23:16]    [15:8]      [7:0]
```

### 3.2 Bit Mapping

| Bits | Field | Description |
|------|-------|-------------|
| [31:28] | Reserved | MUST be zero |
| [27:26] | Shell | Storage tier (0-3) |
| [25:17] | Theta | Functional sector (0-511) |
| [16:8] | Phi | Grounding level (0-511) |
| [7:0] | Harmonic | Mode/resolution (0-255) |

### 3.3 Byte Order

Addresses are stored in **big-endian** (network byte order):
- Byte 0: Most significant (reserved + shell + theta high bits)
- Byte 3: Least significant (harmonic)

---

## 4. Payload Field

### 4.1 Payload Types

The payload is opaque to the packet format. Common payload types include:

| Type | Size | Description |
|------|------|-------------|
| Empty | 0 bytes | Address-only packet (routing, query) |
| Pointer | 4-8 bytes | Reference to external storage |
| Hash | 32 bytes | Content-addressable reference (SHA-256) |
| Inline | Variable | Small data embedded directly |
| Framed | Variable | Length-prefixed content |

### 4.2 Empty Payload

A packet with no payload is valid. Use cases:
- Address existence query
- Routing probe
- Consent check
- Cache invalidation

```python
# Empty packet (address only)
packet = bytes([0x05, 0xA4, 0x08, 0x80])  # Just the 28-bit address
```

### 4.3 Pointer Payload

A pointer references data stored elsewhere:

```
┌──────────────────────┬─────────────────────────────────────┐
│     RPP Address      │           Backend Pointer            │
│      (4 bytes)       │            (8 bytes)                 │
└──────────────────────┴─────────────────────────────────────┘
```

### 4.4 Hash Payload

A content hash for integrity verification:

```
┌──────────────────────┬─────────────────────────────────────┐
│     RPP Address      │           SHA-256 Hash               │
│      (4 bytes)       │            (32 bytes)                │
└──────────────────────┴─────────────────────────────────────┘
```

### 4.5 Inline Payload

Small data embedded directly in the packet:

```
┌──────────────────────┬─────────────────────────────────────┐
│     RPP Address      │           Inline Data                │
│      (4 bytes)       │          (1-256 bytes)               │
└──────────────────────┴─────────────────────────────────────┘
```

### 4.6 Framed Payload

Length-prefixed for variable content:

```
┌──────────────────────┬────────────┬────────────────────────┐
│     RPP Address      │   Length   │        Content         │
│      (4 bytes)       │ (4 bytes)  │      (N bytes)         │
└──────────────────────┴────────────┴────────────────────────┘
```

---

## 5. Packet Operations

### 5.1 Create Packet

```python
def create_packet(address: int, payload: bytes = b"") -> bytes:
    """
    Create a rotational packet from address and optional payload.

    Args:
        address: 28-bit RPP address
        payload: Optional payload bytes

    Returns:
        Packet bytes (address + payload)
    """
    if not (0 <= address <= 0x0FFFFFFF):
        raise ValueError("Address must be 28-bit")

    # Big-endian address (4 bytes)
    addr_bytes = address.to_bytes(4, byteorder='big')

    return addr_bytes + payload
```

### 5.2 Parse Packet

```python
def parse_packet(packet: bytes) -> tuple[int, bytes]:
    """
    Parse a rotational packet into address and payload.

    Args:
        packet: Packet bytes (minimum 4 bytes)

    Returns:
        (address, payload) tuple
    """
    if len(packet) < 4:
        raise ValueError("Packet too short (minimum 4 bytes)")

    # Extract address (first 4 bytes, big-endian)
    address = int.from_bytes(packet[:4], byteorder='big')

    # Validate reserved bits
    if address > 0x0FFFFFFF:
        raise ValueError("Reserved bits must be zero")

    # Extract payload (remaining bytes)
    payload = packet[4:]

    return (address, payload)
```

### 5.3 Validate Packet

```python
def is_valid_packet(packet: bytes) -> bool:
    """Check if bytes form a valid rotational packet."""
    if len(packet) < 4:
        return False

    address = int.from_bytes(packet[:4], byteorder='big')
    return address <= 0x0FFFFFFF  # Reserved bits must be zero
```

---

## 6. Wire Format

### 6.1 Transmission

When transmitted over network or stored:

```
┌────────┬────────┬────────┬────────┬────────────────────────┐
│ Byte 0 │ Byte 1 │ Byte 2 │ Byte 3 │ Bytes 4..N (payload)   │
├────────┼────────┼────────┼────────┼────────────────────────┤
│  0x05  │  0xA4  │  0x08  │  0x80  │ [optional payload]     │
└────────┴────────┴────────┴────────┴────────────────────────┘
```

### 6.2 Example Packets

| Description | Address | Payload | Hex |
|-------------|---------|---------|-----|
| Empty (query) | 0x05A4080 | None | `05 A4 08 80` |
| With pointer | 0x05A4080 | 8-byte ref | `05 A4 08 80 [8 bytes]` |
| With hash | 0x05A4080 | SHA-256 | `05 A4 08 80 [32 bytes]` |
| Inline data | 0x05A4080 | "hello" | `05 A4 08 80 68 65 6C 6C 6F` |

---

## 7. Invariants

### 7.1 Packet Invariants

A valid rotational packet MUST:

1. Be at least 4 bytes long
2. Have bits [31:28] set to zero in the address field
3. Contain a valid 28-bit RPP address in bits [27:0]

### 7.2 Address-Payload Independence

The packet format imposes no relationship between address semantics and payload content. The address describes *how the packet should be treated*, not *what the payload contains*.

---

## 8. What Packets Are NOT

Per BOUNDARIES.md, packets are NOT:

| Non-Function | Reason |
|--------------|--------|
| Storage containers | Packets route TO storage |
| Encrypted blobs | Encryption is transport-layer |
| Self-describing | Address provides semantics |
| Signed | Signatures are application-layer |

Packets are **envelopes**, not **safes**.

---

## 9. Relationship to RPP Address

```
┌─────────────────────────────────────────────────────────────┐
│                    SPECIFICATION LAYERS                      │
├─────────────────────────────────────────────────────────────┤
│  PACKET.md (this document)                                  │
│  "Envelope format: address + optional payload"              │
├─────────────────────────────────────────────────────────────┤
│  SPEC.md                                                    │
│  "28-bit address encoding: shell + theta + phi + harmonic"  │
├─────────────────────────────────────────────────────────────┤
│  SEMANTICS.md                                               │
│  "What address components mean: sectors, grounding, tiers"  │
├─────────────────────────────────────────────────────────────┤
│  RESOLVER.md                                                │
│  "How addresses route to storage backends"                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Examples

### 10.1 Minimal Packet (Address Only)

```python
from rpp_address import encode

# Create address: Hot cache, Memory sector, Transitional, Standard
address = encode(shell=0, theta=96, phi=192, harmonic=128)

# Create minimal packet
packet = address.to_bytes(4, 'big')
# Result: b'\x04\xc0\xc0\x80' (4 bytes)
```

### 10.2 Packet with Inline Data

```python
# Create packet with inline JSON payload
address = encode(shell=1, theta=100, phi=200, harmonic=64)
payload = b'{"user": "alice", "action": "login"}'

packet = address.to_bytes(4, 'big') + payload
# Result: 4 + 36 = 40 bytes
```

### 10.3 Packet with Content Hash

```python
import hashlib

# Content stored elsewhere
content = b"Large document content..."
content_hash = hashlib.sha256(content).digest()

# Packet contains address + hash reference
address = encode(shell=2, theta=160, phi=96, harmonic=128)
packet = address.to_bytes(4, 'big') + content_hash
# Result: 4 + 32 = 36 bytes
```

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-27 | Initial packet specification |

---

## 12. Conformance

A conforming packet implementation MUST:

1. Correctly serialize addresses in big-endian format
2. Validate reserved bits are zero on parse
3. Handle empty payloads (address-only packets)
4. Preserve payload bytes without modification

---

*The packet is the envelope. The address is the label. The payload is optional.*
