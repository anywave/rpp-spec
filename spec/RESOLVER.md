# RPP Resolver Architecture

**Version:** 1.0.0
**Status:** Canonical
**Last Updated:** 2024-12-27
**License:** CC BY 4.0

---

## 1. Overview

This document defines the **Resolver** — the component that translates RPP addresses into backend storage locations. The Resolver is what makes RPP a **bridge architecture** rather than a replacement architecture.

---

## 2. Bridge Model

### 2.1 Core Principle

RPP does not store data. RPP **routes** data to existing storage systems.

```
┌─────────────────────────────────────────────────────────────┐
│                    RPP ADDRESS SPACE                         │
│                                                             │
│    [28-bit semantic coordinates]                            │
│                                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                       RESOLVER                              │
│                                                             │
│    Address → Backend mapping                                │
│    Consent gating                                           │
│    Cache management                                         │
│                                                             │
└───────┬─────────┬─────────┬─────────┬─────────┬────────────┘
        │         │         │         │         │
        ▼         ▼         ▼         ▼         ▼
    ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
    │ File │  │  S3  │  │ SQL  │  │Vector│  │Redis │
    │System│  │      │  │  DB  │  │  DB  │  │      │
    └──────┘  └──────┘  └──────┘  └──────┘  └──────┘
```

### 2.2 What Resolvers Do

| Function | Description |
|----------|-------------|
| **Mapping** | Translate RPP address → backend path |
| **Gating** | Enforce consent/coherence requirements |
| **Caching** | Manage hot data across shells |
| **Logging** | Audit all access attempts |
| **Failover** | Handle backend unavailability |

### 2.3 What Resolvers Do NOT Do

| Non-Function | Reason |
|--------------|--------|
| Store data | Backends store data |
| Transform content | Adapters transform |
| Authenticate users | Identity layer handles |
| Persist state | External persistence |

---

## 3. Resolver Interface

### 3.1 Core Protocol

```python
from typing import Protocol, Optional
from dataclasses import dataclass
from enum import Enum

class ConsentState(Enum):
    FULL_CONSENT = "full"
    DIMINISHED_CONSENT = "diminished"
    SUSPENDED_CONSENT = "suspended"
    EMERGENCY_OVERRIDE = "emergency"

@dataclass
class ResolvedLocation:
    """Result of resolving an RPP address."""
    backend: str           # e.g., "s3", "filesystem", "postgres"
    path: str              # e.g., "bucket/key" or "/path/to/file"
    content_type: str      # e.g., "application/json"
    cache_hint: str        # e.g., "hot", "warm", "cold"
    metadata: dict         # Additional backend-specific data

@dataclass
class ResolutionError:
    """Error during resolution."""
    code: str              # e.g., "CONSENT_DENIED", "NOT_FOUND"
    message: str
    address: int
    consent_state: ConsentState

class RPPResolver(Protocol):
    """Interface for RPP address resolution."""

    def resolve(
        self,
        address: int,
        consent_state: ConsentState,
        operation: str = "read"
    ) -> ResolvedLocation | ResolutionError:
        """
        Resolve an RPP address to a storage location.

        Args:
            address: 28-bit RPP address
            consent_state: Current user consent/coherence state
            operation: "read", "write", "delete", "list"

        Returns:
            ResolvedLocation on success, ResolutionError on failure
        """
        ...

    def reverse_resolve(
        self,
        backend: str,
        path: str
    ) -> Optional[int]:
        """
        Find RPP address for a backend location.

        Args:
            backend: Backend identifier
            path: Backend-specific path

        Returns:
            RPP address if mapped, None otherwise
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

1. VALIDATE address (28-bit range)
2. DECODE address → (shell, theta, phi, harmonic)
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
    if not (0 <= address <= 0x0FFFFFFF):
        return ResolutionError("INVALID_ADDRESS", "Address out of range")

    # Step 2: Decode
    shell, theta, phi, harmonic = decode_rpp_address(address)

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

## 5. Consent Gating

### 5.1 Consent Requirements by Sector

| Theta Range | Sector | Read | Write | Delete |
|-------------|--------|------|-------|--------|
| 0-63 | Gene | FULL | FULL | EMERGENCY |
| 64-127 | Memory | DIMINISHED | FULL | FULL |
| 128-191 | Witness | DIMINISHED | DIMINISHED | SUSPENDED |
| 192-255 | Dream | DIMINISHED | DIMINISHED | DIMINISHED |
| 256-319 | Bridge | DIMINISHED | DIMINISHED | DIMINISHED |
| 320-383 | Guardian | FULL | FULL | EMERGENCY |
| 384-447 | Emergence | FULL | FULL | FULL |
| 448-511 | Meta | NONE | EMERGENCY | EMERGENCY |

### 5.2 Consent Requirements by Grounding

| Phi Range | Grounding | Additional Requirement |
|-----------|-----------|------------------------|
| 0-127 | Grounded | +1 consent level for writes |
| 128-255 | Transitional | Standard requirements |
| 256-383 | Abstract | Standard requirements |
| 384-511 | Ethereal | -1 consent level allowed |

### 5.3 Consent Comparison

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

## 6. Backend Adapters

### 6.1 Adapter Interface

```python
class BackendAdapter(Protocol):
    """Interface for storage backend adapters."""

    name: str

    def read(self, path: str) -> bytes:
        """Read data from backend."""
        ...

    def write(self, path: str, data: bytes) -> bool:
        """Write data to backend."""
        ...

    def delete(self, path: str) -> bool:
        """Delete data from backend."""
        ...

    def exists(self, path: str) -> bool:
        """Check if path exists."""
        ...

    def is_available(self) -> bool:
        """Check backend availability."""
        ...
```

### 6.2 Example: Filesystem Adapter

```python
import os
from pathlib import Path

class FilesystemAdapter:
    name = "filesystem"

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

### 6.3 Example: S3 Adapter

```python
import boto3

class S3Adapter:
    name = "s3"

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

## 7. Shell-to-Backend Mapping

### 7.1 Default Mapping

```python
DEFAULT_SHELL_MAPPING = {
    0: "redis",       # Hot: In-memory cache
    1: "filesystem",  # Warm: Local SSD
    2: "s3",          # Cold: Object storage
    3: "glacier",     # Frozen: Archive
}
```

### 7.2 Configurable Mapping

```yaml
# resolver_config.yaml
shell_mapping:
  0:
    primary: redis
    fallback: filesystem
  1:
    primary: filesystem
    fallback: s3
  2:
    primary: s3
    fallback: filesystem
  3:
    primary: glacier
    fallback: s3
```

---

## 8. Caching

### 8.1 Cache Layers

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

### 8.2 Cache Policy by Shell

| Shell | Cache TTL | Eviction Policy |
|-------|-----------|-----------------|
| 0 | 60s | LRU |
| 1 | 300s | LRU |
| 2 | 3600s | LFU |
| 3 | None | Manual only |

---

## 9. Error Handling

### 9.1 Error Codes

| Code | Meaning | Recommended Action |
|------|---------|-------------------|
| INVALID_ADDRESS | Address out of 28-bit range | Reject |
| CONSENT_DENIED | Insufficient consent | Request elevation |
| BACKEND_UNAVAILABLE | Storage offline | Retry with fallback |
| NOT_FOUND | Address not mapped | Return empty |
| PERMISSION_DENIED | Backend rejected | Audit and alert |
| TIMEOUT | Operation took too long | Retry with backoff |

### 9.2 Graceful Degradation

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

## 10. Audit Logging

### 10.1 Required Log Fields

| Field | Description |
|-------|-------------|
| timestamp | ISO 8601 timestamp |
| address | 28-bit RPP address (hex) |
| operation | read/write/delete/list |
| consent_state | Current consent level |
| result | success/error code |
| backend | Resolved backend |
| path | Resolved path |
| latency_ms | Resolution time |

### 10.2 Example Log Entry

```json
{
  "timestamp": "2024-12-27T15:30:45.123Z",
  "address": "0x05A7880",
  "operation": "read",
  "consent_state": "full",
  "result": "success",
  "backend": "s3",
  "path": "gene/grounded/45_120_128",
  "latency_ms": 12
}
```

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-27 | Initial resolver specification |

---

*This document is released under CC BY 4.0. Attribution required.*
