# RPP Mesh

**Consent-Aware Overlay Network for RPP**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/anywave/rpp-spec/blob/master/LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/rpp-mesh.svg)](https://pypi.org/project/rpp-mesh/)

RPP Mesh extends the [Rotational Packet Protocol](https://pypi.org/project/rpp-protocol/) with network-level consent enforcement. Instead of checking consent only at the application layer, mesh nodes inspect RPP headers and enforce ACSP states at every hop.

---

## Installation

```bash
pip install rpp-mesh
```

For WebSocket support (consent streaming from HNC):
```bash
pip install rpp-mesh[websockets]
```

---

## Quick Start

```python
from rpp_mesh import (
    RPPMeshTransport,
    RPPMeshConfig,
    DeploymentConfig,
    DeploymentMode,
    load_config,
)

# Load production config
config = load_config("production")

# Or configure manually
config = DeploymentConfig(
    mode=DeploymentMode.RPP_MESH,
    rpp_mesh=RPPMeshConfig(
        ingress_nodes=["mesh.example.com:7700"],
        consent_update_endpoint="wss://hnc.example.com/consent",
    )
)

# Create transport
transport = RPPMeshTransport(config.rpp_mesh)

# Connect to mesh
await transport.connect()

# Send packet (consent enforced at network level)
response = await transport.send(
    rpp_address=0x0182801,  # shell=0, theta=12, phi=40, harmonic=1
    payload=b"fragment data"
)

await transport.disconnect()
```

---

## Architecture

```
┌────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌────────┐
│ Client │────▶│ Ingress │────▶│ Sector  │────▶│ Consent │────▶│ Portal │
│        │     │  Node   │     │ Router  │     │  Gate   │     │  Host  │
└────────┘     └─────────┘     └─────────┘     └─────────┘     └────────┘
                                    │               │
                              Routes by θ/φ    Enforces ACSP
```

### Node Types

| Node | Purpose |
|------|---------|
| **Ingress** | Entry point, validates headers, routes to sector |
| **Sector Router** | Geometric routing by theta/phi ranges |
| **Consent Gate** | Enforces ACSP: PASS/DELAY/DROP/FREEZE |
| **Portal Host** | Final destination, executes fragments |

---

## Consent States

| State | Action | Description |
|-------|--------|-------------|
| `FULL_CONSENT` | PASS | Packet forwarded immediately |
| `DIMINISHED_CONSENT` | DELAY | Held, re-checked after backoff |
| `SUSPENDED_CONSENT` | DROP | Dropped, logged to SCL |
| `EMERGENCY_OVERRIDE` | FREEZE | Alert HNC, quarantine |

---

## Mesh Header Format

16-byte header prepended to RPP packets:

```
┌───────┬───────┬───────────────┬─────────────────────────────┐
│ Ver   │ Flags │ Consent State │      Soul ID (16b)          │
│ (4b)  │ (4b)  │    (8b)       │                             │
├───────┴───────┴───────────────┴─────────────────────────────┤
│ Hop Count │  TTL  │ Coherence Hash │      Reserved          │
│   (8b)    │ (8b)  │     (16b)      │        (16b)           │
└───────────┴───────┴────────────────┴─────────────────────────┘
```

---

## Deployment Modes

```python
from rpp_mesh import DeploymentMode, load_config

# Development: Direct connection, no mesh
config = load_config("development")

# Staging: VPN tunnel
config = load_config("staging")

# Production: Full RPP Mesh
config = load_config("production")
```

---

## Requirements

- Python 3.9+
- [rpp-protocol](https://pypi.org/project/rpp-protocol/) >= 0.1.9
- Optional: [websockets](https://pypi.org/project/websockets/) for HNC consent streaming

---

## Documentation

- [Full Mesh Specification](https://github.com/anywave/rpp-spec/blob/master/spec/extensions/MESH.md)
- [RPP Core Protocol](https://github.com/anywave/rpp-spec)
- [PyPI: rpp-protocol](https://pypi.org/project/rpp-protocol/)

---

## License

Apache 2.0

---

## Citation

```
Lennon, A. L. (2025). RPP Mesh: Consent-Aware Overlay Network.
Extension to Rotational Packet Protocol (RPP).
https://github.com/anywave/rpp-spec
```
