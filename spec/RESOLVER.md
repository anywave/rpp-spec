# RPP Resolver Architecture

**Version:** 2.1.0
**Status:** Active
**Last Updated:** 2026-03-04
**License:** CC BY 4.0

---

> **Two-Layer Architecture Note:** The Resolver operates across both RPP layers:
>
> - **Input:** Either v1.0 Semantic Interface addresses (Shell/Theta/Phi/Harmonic) or v2.0 Transport/Resonance addresses (θ/φ/h/r)
> - **Output:** A URI targeting **any communication modality** — not just traditional storage backends
>
> RPP sits above the transport layer. The resolver output is a URI that may point to IPv4/IPv6
> endpoints, spintronic lattice nodes, LoRaWAN devices, IPFS content hashes, quantum memory
> registers, or any future modality. Existing network infrastructure is incorporated naturally —
> IPv4/IPv6 are two modalities among many. See [ADDRESSING-LAYERS.md](ADDRESSING-LAYERS.md).

---

## 1. Overview

This document defines the **Resolver** — the component that translates RPP addresses into
communication endpoints. The Resolver is what makes RPP a **modality-agnostic bridge
architecture**: it routes to existing infrastructure without replacing it, and evolves as new
communication technologies emerge.

---

## 2. Bridge Model

### 2.1 Core Principle

RPP does not store data and does not own a transport. RPP **routes** to existing systems using
whatever communication modality is available.

```
┌──────────────────────────────────────────────────────────────┐
│                    RPP ADDRESS SPACE                          │
│                                                              │
│    v1.0: Shell/Theta/Phi/Harmonic  (semantic interface)      │
│    v2.0: θ/φ/h/r                   (transport/resonance)     │
│                                                              │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                        RESOLVER                              │
│                                                              │
│    Address → Modality selection → URI construction           │
│    Consent gating · Cache management · Audit logging         │
│    Modality discovery · Fallback negotiation                 │
│                                                              │
└──┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────────┘
   │      │      │      │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
 IPv4   IPv6   File    S3    Redis  Spin-  LoRa   IPFS /
                                   tronic  WAN   Quantum
                                   Node          (future)
```

The resolver output is always a **URI** — the scheme encodes the modality:

| Modality | URI Scheme | Example |
|----------|------------|---------|
| IPv4 (TCP/UDP) | `ipv4://` | `ipv4://192.168.1.10:8080/path` |
| IPv6 | `ipv6://` | `ipv6://[2001:db8::1]:8080/path` |
| Filesystem | `file://` | `file:///mnt/rpp-store/sector/path` |
| S3-compatible | `s3://` | `s3://bucket/prefix/sector/path` |
| Redis | `redis://` | `redis://host:6379/0/key` |
| Spintronic lattice | `spintronic://` | `spintronic://node-id/repitan/rac/addr` |
| LoRaWAN | `lora://` | `lora://network-server/devEUI/fport` |
| IPFS | `ipfs://` | `ipfs://bafybei.../path` |
| Quantum memory | `quantum://` | `quantum://register/qubit-range` |
| Bluetooth | `bt://` | `bt://device-addr/characteristic` |

### 2.2 What Resolvers Do

| Function | Description |
|----------|-------------|
| **Modality selection** | Choose appropriate transport for the address and context |
| **URI construction** | Build endpoint URI for the selected modality |
| **Consent gating** | Enforce consent/coherence requirements before routing |
| **Caching** | Manage hot data across shells (modality-aware) |
| **Logging** | Audit all resolution attempts with modality info |
| **Fallback negotiation** | Try alternate modalities when primary is unavailable |
| **Modality discovery** | Detect which transports are available in the current environment |

### 2.3 What Resolvers Do NOT Do

| Non-Function | Reason |
|--------------|--------|
| Store data | Backends/endpoints store data |
| Own a transport | Any modality is valid; resolver selects, not owns |
| Transform content | Adapters transform |
| Authenticate users | Identity layer handles |
| Persist state | External persistence |
| Lock in a protocol | The same RPP address resolves to different modalities as infrastructure evolves |

---

## 3. Resolver Interface

### 3.1 Core Protocol

```python
from typing import Protocol, Optional
from dataclasses import dataclass, field
from enum import Enum

class ConsentState(Enum):
    FULL_CONSENT = "full"
    DIMINISHED_CONSENT = "diminished"
    SUSPENDED_CONSENT = "suspended"
    EMERGENCY_OVERRIDE = "emergency"

class TransportModality(Enum):
    """Communication modalities the resolver can target."""
    IPV4        = "ipv4"        # Traditional TCP/UDP over IPv4
    IPV6        = "ipv6"        # TCP/UDP over IPv6
    FILE        = "file"        # Local/NFS filesystem
    S3          = "s3"          # S3-compatible object storage
    REDIS       = "redis"       # In-memory key-value store
    SPINTRONIC  = "spintronic"  # Spin-lattice quantum-adjacent node
    LORAWAN     = "lora"        # Low-power wide-area IoT network
    IPFS        = "ipfs"        # Content-addressed distributed filesystem
    QUANTUM     = "quantum"     # Quantum memory register (future)
    BLUETOOTH   = "bt"          # Short-range BLE endpoint
    HEDERA      = "hedera"      # Hedera Hashgraph DLT (audit/registry)
    UNKNOWN     = "unknown"     # Modality not yet registered

@dataclass
class ResolvedLocation:
    """Result of resolving an RPP address."""
    modality: TransportModality  # How to reach this endpoint
    uri: str               # Full modality URI, e.g. "ipv4://10.0.0.1:9000/path"
    path: str              # Modality-internal path component
    content_type: str      # e.g., "application/json"
    cache_hint: str        # e.g., "hot", "warm", "cold"
    ttl_seconds: int       # Address TTL from Shell tier (0 = no caching)
    metadata: dict = field(default_factory=dict)  # Backend-specific extras

    # Legacy compat: derive backend name from modality
    @property
    def backend(self) -> str:
        return self.modality.value

@dataclass
class ResolutionError:
    """Error during resolution."""
    code: str              # e.g., "CONSENT_DENIED", "NOT_FOUND", "NO_MODALITY"
    message: str
    address: int
    consent_state: ConsentState
    tried_modalities: list[TransportModality] = field(default_factory=list)

class RPPResolver(Protocol):
    """Interface for RPP address resolution."""

    def resolve(
        self,
        address: int,
        consent_state: ConsentState,
        operation: str = "read",
        preferred_modalities: Optional[list[TransportModality]] = None,
    ) -> ResolvedLocation | ResolutionError:
        """
        Resolve an RPP address to a communication endpoint.

        Args:
            address: 28-bit v1.0 or 32-bit v2.0 RPP address
            consent_state: Current user consent/coherence state
            operation: "read", "write", "delete", "list"
            preferred_modalities: Ordered list of preferred transports.
                                  Resolver falls back down the list if
                                  primary is unavailable. If None, uses
                                  environment-default ordering.

        Returns:
            ResolvedLocation (with URI) on success, ResolutionError on failure
        """
        ...

    def reverse_resolve(
        self,
        uri: str,
    ) -> Optional[int]:
        """
        Find RPP address for an endpoint URI.

        Args:
            uri: Modality URI (any scheme)

        Returns:
            RPP address if mapped, None otherwise
        """
        ...

    def available_modalities(self) -> list[TransportModality]:
        """
        Return modalities the resolver can currently reach.
        Implementations probe their environment on startup/refresh.
        """
        ...
```

### 3.2 Extended Interface

```python
class ExtendedRPPResolver(RPPResolver):
    """Extended resolver with additional capabilities."""

    def list_addresses(
        self,
        theta_range: tuple[int, int],
        phi_range: tuple[int, int],
        shell: Optional[int] = None
    ) -> list[int]:
        """List all addresses in a region."""
        ...

    def migrate_shell(
        self,
        address: int,
        target_shell: int
    ) -> bool:
        """Move data to different shell (tier)."""
        ...

    def invalidate_cache(
        self,
        address: int
    ) -> bool:
        """Remove address from resolver cache."""
        ...
```

---

## 4. Resolution Algorithm

### 4.1 Standard Resolution Flow

```
INPUT: address, consent_state, operation

1. VALIDATE address (32-bit Ra-Canonical range)
2. DECODE address → (theta, phi, harmonic, radius)
3. CHECK consent_requirements(theta, phi) vs consent_state
   - If insufficient → RETURN ConsentDenied
4. LOOKUP backend_mapping(shell, theta)
5. CONSTRUCT path from (theta, phi, harmonic)
6. VERIFY backend availability
   - If unavailable → TRY fallback or RETURN BackendError
7. RETURN ResolvedLocation
```

### 4.2 Pseudocode

```python
def resolve(address: int, consent: ConsentState, operation: str) -> Result:
    # Step 1: Validate
    if not (0x08000000 <= address <= 0xFFFFFFFF):
        return ResolutionError("INVALID_ADDRESS", "Address out of range")

    # Step 2: Decode (Ra-Canonical v2.0)
    theta, phi, harmonic, radius = decode_rpp_address(address)

    # Step 3: Consent check
    required_consent = get_consent_requirement(theta, phi, operation)
    if not consent_sufficient(consent, required_consent):
        return ResolutionError("CONSENT_DENIED",
            f"Operation requires {required_consent}, have {consent}")

    # Step 4: Backend lookup
    backend = get_backend_for_shell(shell)
    if backend is None:
        return ResolutionError("NO_BACKEND", f"No backend for shell {shell}")

    # Step 5: Path construction
    sector = get_sector_name(theta)
    grounding = get_grounding_level(phi)
    path = f"{sector}/{grounding}/{theta}_{phi}_{harmonic}"

    # Step 6: Availability check
    if not backend.is_available():
        fallback = get_fallback_backend(shell)
        if fallback and fallback.is_available():
            backend = fallback
        else:
            return ResolutionError("BACKEND_UNAVAILABLE", "Backend offline")

    # Step 7: Return result
    return ResolvedLocation(
        backend=backend.name,
        path=path,
        content_type=infer_content_type(harmonic),
        cache_hint=shell_to_cache_hint(shell),
        metadata={"address": address, "decoded": (shell, theta, phi, harmonic)}
    )
```

---

## 5. Transport Modalities

### 5.1 Modality-Agnostic Design

RPP is a **protocol**, not a pipeline. It does not impose a fixed route or a fixed transport —
the same RPP address may simultaneously or sequentially resolve across multiple modalities
depending on the network topology, available infrastructure, and consent state at resolution time.

```
                  RPP ADDRESS (temporal)
                         │
                         │  resolve()
                         ▼
              ┌──────────────────────┐
              │   Modality Selector  │
              │                      │
              │  1. probe environment │
              │  2. rank by Shell TTL │
              │  3. check consent    │
              │  4. select + fallback │
              └──────────┬───────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    ipv4://...    spintronic://...   lora://...
     (exists)      (preferred)      (fallback)
```

### 5.2 Current Modality Registry

| Modality | URI Scheme | Shell Affinity | Use Case |
|----------|------------|----------------|----------|
| IPv4 | `ipv4://host:port/path` | 0–1 | Standard internet, existing infrastructure |
| IPv6 | `ipv6://[addr]:port/path` | 0–1 | Next-gen internet, larger address space |
| Filesystem | `file:///path` | 1–2 | Local edge, on-device storage |
| S3-compatible | `s3://bucket/key` | 2–3 | Cold object storage |
| Redis | `redis://host:port/db/key` | 0 | Hot in-memory (session-duration TTL) |
| Spintronic | `spintronic://node/repitan/rac/addr` | 0 | Physics-enforced TTL via T2 decoherence |
| LoRaWAN | `lora://netserver/devEUI/fport` | 1–2 | Low-power, long-range IoT mesh |
| IPFS | `ipfs://CID/path` | 2–3 | Content-addressed, distributed |
| Hedera | `hedera://topic-id/sequence` | 2–3 | Hashgraph DLT (audit registry, opt-in) |
| Bluetooth | `bt://device/characteristic` | 0 | Proximity/local peer |
| Quantum | `quantum://register/range` | 0 | Register-level quantum memory (future) |

**Key:** Modalities are additive. IPv4 and IPv6 are incorporated naturally — they are two entries
in the registry. As new modalities emerge (optical, acoustic, future quantum transports), they are
added to this table. No RPP address changes when a new modality is added.

### 5.3 Hedera Hashgraph Registry (Opt-In)

Routing events MAY be recorded on Hedera Hashgraph for audit purposes. This is **not required**
for RPP routing — it is an optional trace layer, analogous to signature-required vs. regular mail.

```
Not all packets require a signature.
Not all routing events require a ledger trace.
Hedera recording is consent-gated: only if phi > PHI_LEDGER_THRESHOLD.
```

When enabled, the resolver emits a secondary resolution to `hedera://`:

```python
# Audit record written to Hedera topic
HEDERA_TOPIC = "hedera://0.0.XXXXX/sequence"

audit_payload = {
    "rpp_address": hex(address),
    "modality": resolved.modality.value,
    "uri_hash": sha256(resolved.uri),  # URI hashed, not exposed
    "consent_state": consent_state.value,
    "timestamp_ns": time.time_ns(),
    "shell": shell,
    "ttl_seconds": resolved.ttl_seconds,
}
```

The URI itself is hashed before Hedera recording — the ledger proves routing happened without
revealing the endpoint. This preserves the consent-aware routing property at the audit layer.

### 5.4 Packet Recovery

When a temporal address expires (T2 decoherence or Shell TTL expiry) before delivery, the
packet is not simply lost — recovery can be attempted via **cargo packets**:

```
Primary route: spintronic://nodeA → packet expires mid-route (T2 decay)

Recovery options:
  1. STEERING: Send a new consent-refresh packet ahead of the original
     → re-establishes T2 on the downstream lattice sites
     → original packet resumes route

  2. PULL-BACK: Send a recall signal to upstream nodes
     → upstream copies re-route via alternate modality (e.g., IPv6)
     → delivers to original destination via new path

  3. COPY-AND-COLLECT: If packet reached a coherence gate, a partial
     copy may be held at the gate boundary until consent is refreshed
     → gate releases copy on new consent signal
```

These mechanisms are analogous to postal recovery: re-routing a lost letter, returning to sender,
or holding at the post office pending pickup. The protocol is not linear — multiple paths and
recovery signals may coexist in the network simultaneously.

---

## 6. Consent Gating

### 6.1 Consent Requirements by Sector (Ra-Canonical v2.0)

| Theta (Repitan) | Sector | Read | Write | Delete |
|-----------------|--------|------|-------|--------|
| 1-4 | Foundation | FULL | FULL | EMERGENCY |
| 5-9 | Structure | DIMINISHED | FULL | FULL |
| 10-14 | Process | DIMINISHED | DIMINISHED | SUSPENDED |
| 15-18 | Connection | DIMINISHED | DIMINISHED | DIMINISHED |
| 19-22 | Expression | DIMINISHED | DIMINISHED | DIMINISHED |
| 23-25 | Integration | FULL | FULL | EMERGENCY |
| 26-27 | Transcendence | FULL | FULL | FULL |

### 6.2 Consent Requirements by RAC Level (Ra-Canonical v2.0)

| Phi (RAC) | Level | Additional Requirement |
|-----------|-------|------------------------|
| 1 (RAC1) | Highest access | Standard requirements |
| 2 (RAC2) | High access | Standard requirements |
| 3 (RAC3) | Medium-high | +1 consent for sensitive ops |
| 4 (RAC4) | Medium | +1 consent level for writes |
| 5 (RAC5) | Low | +2 consent level for writes |
| 6 (RAC6) | Lowest access | Full consent required |

### 6.3 Consent Comparison

```python
CONSENT_LEVELS = {
    ConsentState.SUSPENDED_CONSENT: 0,
    ConsentState.DIMINISHED_CONSENT: 1,
    ConsentState.FULL_CONSENT: 2,
    ConsentState.EMERGENCY_OVERRIDE: 3,
}

def consent_sufficient(current: ConsentState, required: ConsentState) -> bool:
    return CONSENT_LEVELS[current] >= CONSENT_LEVELS[required]
```

---

## 7. Modality Adapters

### 7.1 Adapter Interface

```python
class ModalityAdapter(Protocol):
    """Interface for transport modality adapters."""

    modality: TransportModality

    def build_uri(self, path: str, address_components: dict) -> str:
        """Construct the full modality URI for a resolved path."""
        ...

    def read(self, uri: str) -> bytes:
        """Read data via this modality."""
        ...

    def write(self, uri: str, data: bytes) -> bool:
        """Write data via this modality."""
        ...

    def delete(self, uri: str) -> bool:
        """Delete data via this modality."""
        ...

    def exists(self, uri: str) -> bool:
        """Check if URI is reachable."""
        ...

    def is_available(self) -> bool:
        """Check if this modality is reachable in the current environment."""
        ...
```

### 7.2 Example: Filesystem Adapter

```python
import os
from pathlib import Path

class FilesystemAdapter:
    modality = TransportModality.FILE

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def read(self, path: str) -> bytes:
        full_path = self.base_path / path
        return full_path.read_bytes()

    def write(self, path: str, data: bytes) -> bool:
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return True

    def delete(self, path: str) -> bool:
        full_path = self.base_path / path
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def exists(self, path: str) -> bool:
        return (self.base_path / path).exists()

    def is_available(self) -> bool:
        return self.base_path.exists()
```

### 7.3 Example: S3 Adapter

```python
import boto3

class S3Adapter:
    modality = TransportModality.S3

    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket = bucket
        self.prefix = prefix
        self.client = boto3.client('s3')

    def read(self, path: str) -> bytes:
        key = f"{self.prefix}{path}" if self.prefix else path
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response['Body'].read()

    def write(self, path: str, data: bytes) -> bool:
        key = f"{self.prefix}{path}" if self.prefix else path
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return True

    def delete(self, path: str) -> bool:
        key = f"{self.prefix}{path}" if self.prefix else path
        self.client.delete_object(Bucket=self.bucket, Key=key)
        return True

    def exists(self, path: str) -> bool:
        try:
            key = f"{self.prefix}{path}" if self.prefix else path
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except:
            return False

    def is_available(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except:
            return False
```

---

## 8. Shell-to-Modality Mapping

### 8.1 Default Mapping

```python
# Default modality preference order per Shell tier.
# First available modality in the list is selected.
DEFAULT_SHELL_MODALITIES = {
    0: [TransportModality.SPINTRONIC, TransportModality.REDIS,
        TransportModality.IPV6, TransportModality.IPV4],      # Hot: TTL = session
    1: [TransportModality.IPV4, TransportModality.IPV6,
        TransportModality.FILE, TransportModality.LORAWAN],    # Warm: TTL = day
    2: [TransportModality.S3, TransportModality.IPFS,
        TransportModality.FILE],                                # Cold: TTL = month
    3: [TransportModality.IPFS, TransportModality.S3,
        TransportModality.HEDERA],                             # Frozen: Until revocation
}
```

The resolver probes `available_modalities()` on startup, then selects the first match per shell.
On a standard cloud server, Spintronic and LoRaWAN are unavailable → Shell 0 falls through to
Redis → IPv6 → IPv4. On spintronic hardware, Spintronic is selected first. No code changes needed.

### 8.2 Configurable Mapping

```yaml
# resolver_config.yaml
shell_modalities:
  0:
    preferred: [spintronic, redis, ipv6, ipv4]
    fallback: [file]
    ttl_seconds: 0       # Session-duration; no explicit TTL (Shell enforces)
  1:
    preferred: [ipv4, ipv6, file, lora]
    fallback: [s3]
    ttl_seconds: 86400   # 1 day
  2:
    preferred: [s3, ipfs, file]
    fallback: [s3]
    ttl_seconds: 2592000 # 30 days
  3:
    preferred: [ipfs, s3, hedera]
    fallback: [s3]
    ttl_seconds: -1      # Until explicit revocation

# Hedera audit topic (opt-in; only records if phi > phi_ledger_threshold)
hedera:
  enabled: false
  topic_id: "0.0.XXXXX"
  phi_ledger_threshold: 400   # Only record routing for phi > 400/511
  hash_uri: true              # Hash the endpoint URI before recording
```

---

## 9. Caching

### 9.1 Cache Layers

```
┌─────────────────────────────────────────┐
│           Resolver Cache                │
│     (Address → ResolvedLocation)        │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           Content Cache                 │
│     (Address → Data, by shell)          │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           Backend Storage               │
│     (Authoritative data)                │
└─────────────────────────────────────────┘
```

### 9.2 Cache Policy by Shell

| Shell | Cache TTL | Eviction Policy |
|-------|-----------|-----------------|
| 0 | 60s | LRU |
| 1 | 300s | LRU |
| 2 | 3600s | LFU |
| 3 | None | Manual only |

---

## 10. Error Handling

### 10.1 Error Codes

| Code | Meaning | Recommended Action |
|------|---------|-------------------|
| INVALID_ADDRESS | Address outside valid range | Reject |
| CONSENT_DENIED | Insufficient consent | Request elevation |
| NO_MODALITY | No available modality for this shell/env | Check env or retry |
| MODALITY_UNAVAILABLE | Selected modality offline | Fallback to next modality |
| NOT_FOUND | Address not mapped | Return empty |
| PERMISSION_DENIED | Modality/backend rejected | Audit and alert |
| ADDRESS_EXPIRED | Shell TTL exceeded (address is stale) | Re-resolve at point of access |
| TIMEOUT | Operation took too long | Retry with backoff |

### 10.2 Graceful Degradation

```python
def resolve_with_degradation(address: int, consent: ConsentState) -> Result:
    # Try primary resolution
    result = resolve(address, consent, "read")

    if isinstance(result, ResolutionError):
        if result.code == "BACKEND_UNAVAILABLE":
            # Try lower shell (colder storage)
            shell, theta, phi, harmonic = decode_rpp_address(address)
            if shell < 3:
                degraded_address = encode_rpp_address(shell + 1, theta, phi, harmonic)
                return resolve(degraded_address, consent, "read")

        if result.code == "NOT_FOUND":
            # Check if data exists at different harmonic
            shell, theta, phi, harmonic = decode_rpp_address(address)
            for alt_harmonic in [128, 64, 0]:  # Try standard, then lower
                if alt_harmonic != harmonic:
                    alt_address = encode_rpp_address(shell, theta, phi, alt_harmonic)
                    alt_result = resolve(alt_address, consent, "read")
                    if not isinstance(alt_result, ResolutionError):
                        alt_result.metadata["degraded_from"] = address
                        return alt_result

    return result
```

---

## 11. Audit Logging

### 11.1 Required Log Fields

| Field | Description |
|-------|-------------|
| timestamp | ISO 8601 timestamp |
| address | RPP address (hex), v1.0 or v2.0 |
| operation | read/write/delete/list |
| consent_state | Current consent level |
| result | success/error code |
| modality | Selected transport modality |
| uri_hash | SHA-256 of resolved URI (endpoint not logged in plaintext) |
| latency_ms | Resolution time |
| hedera_seq | Hedera sequence number if recorded (optional) |

### 11.2 Example Log Entry

```json
{
  "timestamp": "2026-03-04T15:30:45.123Z",
  "address": "0x05A7880",
  "operation": "read",
  "consent_state": "full",
  "result": "success",
  "modality": "ipv4",
  "uri_hash": "a3f8c2...",
  "latency_ms": 12,
  "hedera_seq": null
}
```

---

## 12. Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | 2026-03-04 | Transport-modality-agnostic design; TransportModality enum; Hedera opt-in registry; packet recovery; modality-aware shell mapping |
| 2.0.0 | 2026-01-04 | Ra-Canonical v2.0 address format |
| 1.0.0 | 2024-12-27 | Initial resolver specification (v1.0 28-bit) |

---

*This document is released under CC BY 4.0. Attribution required.*
