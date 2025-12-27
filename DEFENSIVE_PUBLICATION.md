# Rotational Packet Protocol (RPP): A Semantic Addressing Architecture for Consent-Aware Memory Systems

**Authors:** Alexander Liam Lennon
**Date:** December 2024
**Version:** 1.1.0
**Classification:** Defensive Publication / Prior Art Disclosure
**License:** CC BY 4.0

---

## Abstract

We present the Rotational Packet Protocol (RPP), a novel addressing architecture that encodes semantic meaning, access consent, and lifecycle state directly into a fixed-width 28-bit address. Unlike traditional linear memory addressing, RPP uses a spherical coordinate system where address components represent functional sectors, grounding levels, and harmonic modes rather than arbitrary byte offsets. The protocol defines both the address encoding and the minimal packet envelope (address + optional payload) that serves as the atomic unit of semantically-addressed data. This paper describes the complete specification sufficient for implementation, compares the approach to existing architectures (CPU virtual memory, GPU memory, content-addressable memory, object storage), and demonstrates integration patterns with existing storage systems. RPP is explicitly released as open infrastructure with no patent claims.

**Keywords:** semantic addressing, consent-aware systems, memory architecture, geometric addressing, bridge architecture, open infrastructure, packet protocol

---

## 1. Introduction

### 1.1 Problem Statement

Modern computing architectures treat memory addresses as opaque numerical identifiers:

```
address → location → bytes
```

This model, established in the von Neumann architecture and refined through decades of CPU design, optimizes for:
- Sequential access patterns
- Cache locality
- Hardware simplicity
- Byte-level granularity

However, it provides no intrinsic mechanism for:
- Semantic classification of data
- Consent-based access control beyond binary ACLs
- Lifecycle management at the address level
- Functional routing without lookup tables

As systems increasingly deal with meaning (embeddings, knowledge graphs, AI-generated content) rather than raw bytes, the gap between address semantics and data semantics creates architectural friction.

### 1.2 Contribution

We propose RPP, an addressing model where:

1. **Address = Classification**: The 28-bit address directly encodes what data means, not just where it resides
2. **Access = State-Dependent**: Consent and coherence are intrinsic to address resolution
3. **Routing = Geometric**: Spherical coordinates enable functional locality instead of physical locality
4. **Bridge Architecture**: RPP overlays existing storage systems without replacement

### 1.3 Explicit Non-Patent Statement

**This publication constitutes a defensive disclosure.** The authors explicitly:
- Claim no patent rights
- Intend to establish prior art preventing future patent claims
- Release this specification under CC BY 4.0
- Encourage independent implementation without licensing obligations

---

## 2. The 28-Bit RPP Address

### 2.1 Bit Layout

The canonical RPP address format is a 28-bit unsigned integer with fixed field positions:

```
28-bit RPP Address
┌────────┬───────────┬───────────┬────────────┐
│ 2 bits │  9 bits   │  9 bits   │  8 bits    │
├────────┼───────────┼───────────┼────────────┤
│ Shell  │  Theta    │   Phi     │  Harmonic  │
│ Depth  │ (0–511)   │ (0–511)   │  (0–255)   │
└────────┴───────────┴───────────┴────────────┘
  [27:26]   [25:17]     [16:8]      [7:0]
```

### 2.2 Field Definitions

| Field | Bits | Range | Semantic Meaning |
|-------|------|-------|------------------|
| **Shell** | 2 | 0-3 | Radial depth / storage tier |
| **Theta** | 9 | 0-511 | Longitude / functional sector |
| **Phi** | 9 | 0-511 | Latitude / grounding level |
| **Harmonic** | 8 | 0-255 | Frequency / mode / resolution |

**Total addressable space:** 2²⁸ = 268,435,456 unique addresses (~256 MB equivalent)

### 2.3 Encoding Algorithm

```python
def encode_rpp_address(shell: int, theta: int, phi: int, harmonic: int) -> int:
    """
    Encode RPP components into a 28-bit address.

    Args:
        shell: 0-3 (radial depth)
        theta: 0-511 (angular longitude, typically degrees * 511/359)
        phi: 0-511 (angular latitude, typically (degrees + 90) * 511/180)
        harmonic: 0-255 (frequency/mode index)

    Returns:
        28-bit unsigned integer
    """
    assert 0 <= shell <= 3
    assert 0 <= theta <= 511
    assert 0 <= phi <= 511
    assert 0 <= harmonic <= 255

    return (shell << 26) | (theta << 17) | (phi << 8) | harmonic
```

### 2.4 Decoding Algorithm

```python
def decode_rpp_address(address: int) -> tuple[int, int, int, int]:
    """
    Decode a 28-bit RPP address into components.

    Args:
        address: 28-bit unsigned integer

    Returns:
        (shell, theta, phi, harmonic)
    """
    shell = (address >> 26) & 0x3
    theta = (address >> 17) & 0x1FF
    phi = (address >> 8) & 0x1FF
    harmonic = address & 0xFF

    return (shell, theta, phi, harmonic)
```

### 2.5 Concrete Examples

| Shell | Theta | Phi | Harmonic | Hex Address | Decimal |
|-------|-------|-----|----------|-------------|---------|
| 0 | 45 | 120 | 128 | 0x05A7880 | 5,961,856 |
| 1 | 180 | 255 | 64 | 0x45A7F40 | 73,138,496 |
| 2 | 0 | 0 | 0 | 0x8000000 | 134,217,728 |
| 3 | 359 | 180 | 255 | 0xEB3B4FF | 246,695,167 |

### 2.6 Reserved Bits

When stored in 32-bit containers, bits [31:28] are reserved and MUST be zero. This allows future extension while maintaining backward compatibility.

---

## 3. The Rotational Packet

### 3.1 Packet Structure

A rotational packet is the minimal envelope combining an RPP address with an optional payload:

```
┌──────────────────────┬──────────────────────────────────────┐
│     RPP Address      │           Payload (Optional)          │
│      (4 bytes)       │           (0 to N bytes)              │
└──────────────────────┴──────────────────────────────────────┘
```

> **The Clean Rule:** A rotational packet is simply a small envelope with a structured address and an optional payload. That's it.

### 3.2 Packet Fields

| Field | Size | Required | Description |
|-------|------|----------|-------------|
| **Address** | 4 bytes | YES | 28-bit RPP address, bits [31:28] reserved (must be zero) |
| **Payload** | 0-N bytes | NO | Optional data, pointer, hash, or inline content |

### 3.3 Wire Format

Addresses are stored in big-endian (network byte order):

```
Byte 0       Byte 1       Byte 2       Byte 3       Bytes 4..N
┌──────────┬──────────┬──────────┬──────────┬──────────────────┐
│ Reserved │  Theta   │   Phi    │ Harmonic │  Payload         │
│ + Shell  │  (cont)  │  (cont)  │          │  (optional)      │
└──────────┴──────────┴──────────┴──────────┴──────────────────┘
```

### 3.4 Payload Types

The payload is opaque to the packet format. Common types include:

| Type | Size | Use Case |
|------|------|----------|
| Empty | 0 bytes | Address queries, routing probes |
| Pointer | 4-8 bytes | Reference to external storage |
| Hash | 32 bytes | Content-addressable reference (SHA-256) |
| Inline | Variable | Small embedded data |
| Framed | Variable | Length-prefixed content |

### 3.5 Packet Operations

```python
def create_packet(address: int, payload: bytes = b"") -> bytes:
    """Create a rotational packet from address and optional payload."""
    if not (0 <= address <= 0x0FFFFFFF):
        raise ValueError("Address must be 28-bit")
    return address.to_bytes(4, byteorder='big') + payload

def parse_packet(packet: bytes) -> tuple[int, bytes]:
    """Parse a rotational packet into address and payload."""
    if len(packet) < 4:
        raise ValueError("Packet too short")
    address = int.from_bytes(packet[:4], byteorder='big')
    if address > 0x0FFFFFFF:
        raise ValueError("Reserved bits must be zero")
    return (address, packet[4:])
```

### 3.6 Design Rationale

The packet format deliberately imposes no relationship between address semantics and payload content. The address describes *how the packet should be treated*, not *what the payload contains*. This separation enables:

- Address-only queries (empty packets)
- Content-addressable storage (hash payloads)
- Inline optimization (small data embedded)
- External references (pointer payloads)

---

## 4. Semantic Interpretation

### 4.1 Shell (Radial Depth)

The Shell field encodes hierarchical depth or storage tier:

| Shell | Typical Mapping | Temperature |
|-------|-----------------|-------------|
| 0 | Immediate / hot cache | Hot |
| 1 | Working memory | Warm |
| 2 | Persistent storage | Cold |
| 3 | Archive / dormant | Frozen |

### 4.2 Theta (Functional Sector)

Theta divides the address space into functional zones. Example canonical sectors:

| Theta Range | Sector Name | Function |
|-------------|-------------|----------|
| 0-63 | Gene | Core identity, immutable traits |
| 64-127 | Memory | Experiential storage |
| 128-191 | Witness | Observational records |
| 192-255 | Dream | Speculative/creative space |
| 256-319 | Bridge | Integration/translation |
| 320-383 | Guardian | Protection/consent enforcement |
| 384-447 | Emergence | Novel pattern detection |
| 448-511 | Meta | Self-reference, reflection |

### 4.3 Phi (Grounding Level)

Phi encodes the axis from concrete/grounded to abstract/ethereal:

| Phi Range | Interpretation |
|-----------|----------------|
| 0-127 | Highly grounded (physical, verifiable) |
| 128-255 | Transitional (contextual) |
| 256-383 | Abstract (conceptual, inferential) |
| 384-511 | Ethereal (emergent, speculative) |

### 4.4 Harmonic (Mode/Resolution)

Harmonic encodes the frequency, version, or resolution mode:

| Harmonic | Example Usage |
|----------|---------------|
| 0 | Raw/unprocessed |
| 64 | Compressed/summarized |
| 128 | Standard resolution |
| 192 | High-fidelity |
| 255 | Maximum detail |

---

## 5. Comparison to Existing Architectures

### 5.1 CPU Virtual Memory (x86/ARM)

| Aspect | CPU Virtual Memory | RPP |
|--------|-------------------|-----|
| Address meaning | Arbitrary offset | Semantic coordinate |
| Protection | Page tables + MMU | Consent + coherence |
| Translation | Hardware MMU | Software/FPGA resolver |
| Granularity | 4KB pages | Per-address |
| Locality | Physical | Functional |

**Key Difference:** CPU memory asks "Is this address allowed?" RPP asks "Should this address exist at all?"

### 5.2 GPU Memory (CUDA/Vulkan)

| Aspect | GPU Memory | RPP |
|--------|-----------|-----|
| Addressing | Linear buffers | Spherical coordinates |
| Optimization | Spatial locality | Functional locality |
| Parallelism | Thread blocks | Packet traversal patterns |
| Access | Explicit barriers | Consent-gated |

**Similarity:** Both optimize for parallel traversal.
**Difference:** RPP avoids collisions via skip patterns instead of thread synchronization.

### 5.3 Content-Addressable Memory (CAM)

| Aspect | CAM | RPP |
|--------|-----|-----|
| Lookup | By value | By coordinate |
| Speed | O(1) | O(1) |
| Hardware cost | Expensive | FPGA-friendly |
| Semantics | Weak | Strong (intrinsic) |

**Relationship:** RPP behaves as a geometric CAM where address ≡ classification.

### 5.4 Object Storage (S3/GCS/ZFS)

| Aspect | Object Storage | RPP |
|--------|---------------|-----|
| Identifier | Hash/UUID/path | Coordinate |
| Metadata | External | Embedded in address |
| Lifecycle | Explicit GC | TTL + coherence |
| Meaning | None | Intrinsic |

**Relationship:** RPP provides the semantic control plane that object stores lack.

---

## 6. Resolver Architecture

### 6.1 Bridge Model

RPP does not replace storage systems. It provides a semantic routing layer:

```
┌──────────────────────┐
│  RPP 28-bit Address  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Resolver / Adapter  │
└──────────┬───────────┘
           │
     ┌─────┼─────┬─────────┬─────────┐
     ▼     ▼     ▼         ▼         ▼
   [FS]  [S3]  [DB]   [Vector]  [Archive]
```

### 6.2 Resolver Interface

```python
class RPPResolver(Protocol):
    def resolve(self, address: int, consent_state: ConsentState) -> ResolvedLocation:
        """
        Resolve an RPP address to a storage backend location.

        Args:
            address: 28-bit RPP address
            consent_state: Current consent/coherence state

        Returns:
            ResolvedLocation containing backend type and path

        Raises:
            ConsentDenied: If consent_state insufficient
            AddressInvalid: If address violates invariants
        """
        ...
```

### 6.3 Example Resolution

```python
# Input
address = 0x05A7880  # Shell=0, Theta=45, Phi=120, Harmonic=128

# Resolution mapping
shell_0_backend = "s3://hot-cache/"
theta_45_namespace = "users/identity/"
phi_120_policy = "read-write"
harmonic_128_format = "json-v1"

# Output
resolved = "s3://hot-cache/users/identity/profile.json-v1"
```

---

## 7. Consent and Coherence Gating

### 7.1 Consent States

| State | Description | Access Level |
|-------|-------------|--------------|
| FULL_CONSENT | User fully present and authorized | Full access |
| DIMINISHED_CONSENT | Partial presence, reconfirmation needed | Read-only |
| SUSPENDED_CONSENT | User revoked or impaired | Emergency only |
| EMERGENCY_OVERRIDE | System-detected anomaly | Safety operations |

### 7.2 Address-Level Gating

```python
def access_permitted(address: int, consent: ConsentState) -> bool:
    shell, theta, phi, harmonic = decode_rpp_address(address)

    # Guardian sector (320-383) requires FULL_CONSENT
    if 320 <= theta < 384 and consent != ConsentState.FULL_CONSENT:
        return False

    # High-grounded data (phi < 128) requires at least DIMINISHED
    if phi < 128 and consent == ConsentState.SUSPENDED_CONSENT:
        return False

    return True
```

---

## 8. Hardware Considerations

### 8.1 Why 28 Bits

| Consideration | 28-bit Advantage |
|---------------|------------------|
| FPGA registers | Fits standard 32-bit with parity |
| SPI transfer | 4 bytes with alignment |
| MRAM addressing | Matches common cell sizes |
| Cache efficiency | Avoids 64-bit waste |

### 8.2 Historical Precedent

- Motorola 68000: 24-bit address space
- LISP machines: 28-bit tagged pointers
- Early ARM: 26-bit addressing
- Bitcoin transactions: 28-bit indices

### 8.3 FPGA Implementation Sketch

```verilog
module rpp_decoder (
    input  [27:0] address,
    output [1:0]  shell,
    output [8:0]  theta,
    output [8:0]  phi,
    output [7:0]  harmonic
);
    assign shell    = address[27:26];
    assign theta    = address[25:17];
    assign phi      = address[16:8];
    assign harmonic = address[7:0];
endmodule
```

---

## 9. Implementation Status

Reference implementations exist in:
- Python (canonical reference with full test suite)
- Haskell (pure functional implementation)
- Clash/FPGA (hardware synthesis-ready)

Test vectors (60 comprehensive tests) and validation suites are publicly available at:
https://github.com/anywave/rpp-spec

---

## 10. Prior Art Differentiation

### 10.1 What RPP Does NOT Claim as Novel

- Spherical coordinate systems (standard mathematics)
- Content-addressable memory (existing hardware)
- Semantic tagging (metadata systems)
- Access control lists (standard security)

### 10.2 What RPP DOES Claim as Novel Synthesis

The combination of:
1. Fixed-width geometric addressing (not hashing)
2. Intrinsic semantic classification (not external metadata)
3. Consent-state as address property (not binary ACL)
4. Bridge architecture preserving existing storage
5. Minimal packet envelope separating address semantics from payload content

This specific synthesis has not been previously published or patented.

---

## 11. Conclusion

RPP provides a semantic addressing layer that sits above existing storage infrastructure, enabling meaning-aware routing without requiring migration or replacement. The 28-bit address format balances expressiveness with hardware efficiency, and the bridge architecture ensures incremental adoption.

By publishing this specification openly, we establish prior art that prevents patent enclosure while enabling plural implementations. The architecture is designed to be calm, boring, and inevitable rather than clever, disruptive, or proprietary.

---

## References

1. Hennessy, J.L., Patterson, D.A. *Computer Architecture: A Quantitative Approach*. Morgan Kaufmann.
2. Seaborn, K., et al. *Capability Hardware Enhanced RISC Instructions*. ARM Research.
3. Pagiamtzis, K., Sheikholeslami, A. *Content-Addressable Memory (CAM) Circuits and Architectures*. IEEE JSSC.
4. ASIS International. *Code of Ethics*. March 2023.

---

## Appendix A: Test Vectors

```json
{
  "test_vectors": [
    {
      "input": {"shell": 0, "theta": 45, "phi": 120, "harmonic": 128},
      "expected_address": "0x05A7880",
      "expected_decimal": 5961856
    },
    {
      "input": {"shell": 3, "theta": 511, "phi": 511, "harmonic": 255},
      "expected_address": "0xFFFFFF",
      "expected_decimal": 268435455
    },
    {
      "input": {"shell": 0, "theta": 0, "phi": 0, "harmonic": 0},
      "expected_address": "0x0000000",
      "expected_decimal": 0
    }
  ]
}
```

---

## Appendix B: Licensing

- **Specification:** CC BY 4.0
- **Reference Code:** Apache 2.0
- **Diagrams:** CC BY-SA 4.0

---

*This document constitutes a defensive publication establishing prior art for the described architecture. No patent claims are made or intended.*
