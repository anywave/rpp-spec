# RPP Mesh: Consent-Aware Overlay Network

> **⚠️ NOTICE:** This document uses legacy 28-bit addressing examples. The current canonical format is **Ra-Canonical v2.0 (32-bit)**: `[θ:5][φ:3][h:3][r:8][reserved:13]`. See `spec/RPP-CANONICAL-v2.md` for authoritative format. Mesh header structure remains valid; RPP address section should use 32-bit Ra-Canonical format.

## Overview

RPP Mesh is an optional deployment mode for AVACHATTER that provides consent-aware routing at the network level. Fragments carry RPP headers that mesh nodes inspect, enabling:

- **Geometric routing** by theta/phi sectors (functional affinity)
- **Consent enforcement** at relay nodes (drop before propagation)
- **Coherence-aware prioritization** (hot fragments route faster)
- **Fragment quarantine** without reaching destination

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │         RPP MESH OVERLAY            │
                    │                                     │
   ┌────────┐       │  ┌──────────┐      ┌──────────┐    │       ┌────────────┐
   │ Human  │       │  │  Ingress │      │  Sector  │    │       │   Portal   │
   │ Client │──────▶│  │   Node   │─────▶│  Router  │────│──────▶│   Hotel    │
   │        │       │  │          │      │  (θ=64)  │    │       │            │
   └────────┘       │  └──────────┘      └────┬─────┘    │       └────────────┘
       │            │                         │          │
       │            │                    ┌────▼─────┐    │
       │            │                    │ Consent  │    │
       │            │                    │   Gate   │    │
       │            │                    └────┬─────┘    │
       │            │                         │          │
       │            │         SUSPENDED? ─────┴────▶ DROP│
       │            │                                    │
       │            └────────────────────────────────────┘
       │
       └──── Biometric signals update consent state via HNC
```

## Node Types

### 1. Ingress Node
First point of contact for client traffic.

**Responsibilities:**
- Validate RPP header format
- Attach/verify soul signature
- Initial consent state check
- Route to appropriate sector router

**Config:**
```yaml
node_type: ingress
listen: 0.0.0.0:7700
upstream_sectors:
  - theta_range: [0, 127]
    endpoint: sector-0.mesh.local:7701
  - theta_range: [128, 255]
    endpoint: sector-1.mesh.local:7701
  - theta_range: [256, 383]
    endpoint: sector-2.mesh.local:7701
  - theta_range: [384, 511]
    endpoint: sector-3.mesh.local:7701
```

### 2. Sector Router
Routes packets within a theta sector range.

**Responsibilities:**
- Geometric routing by theta/phi
- Load balancing within sector
- Phi-based prioritization (grounded > ethereal)
- Shell-aware caching (shell=0 cached locally)

**Routing Logic:**
```python
def route_packet(packet: RPPPacket) -> Endpoint:
    shell, theta, phi, harmonic = decode_rpp_address(packet.address)
    
    # Find Portal Hosts registered for this theta range
    candidates = registry.get_hosts(theta_range=(theta - 16, theta + 16))
    
    # Prioritize by phi proximity (grounded affinity)
    candidates.sort(key=lambda h: abs(h.phi_center - phi))
    
    # Shell-based routing
    if shell == 0:
        # Hot data - route to nearest cached
        return candidates[0] if candidates[0].has_cache else candidates[1]
    elif shell == 3:
        # Archive - route to cold storage nodes
        return registry.get_archive_node(theta)
    
    return candidates[0]
```

### 3. Consent Gate
Enforces ACSP state at network level.

**Responsibilities:**
- Inspect consent_state header field
- DROP packets with SUSPENDED_CONSENT
- DELAY packets with DIMINISHED_CONSENT (requeue with backoff)
- PASS packets with FULL_CONSENT
- EMERGENCY_OVERRIDE triggers alert + freeze

**State Machine:**
```
┌─────────────────┐
│  FULL_CONSENT   │───────────────────────▶ PASS
└─────────────────┘

┌─────────────────┐      ┌─────────┐
│DIMINISHED_CONSENT│─────▶│  DELAY  │──(retry after backoff)──▶ RE-CHECK
└─────────────────┘      └─────────┘

┌─────────────────┐
│SUSPENDED_CONSENT│───────────────────────▶ DROP (log to SCL)
└─────────────────┘

┌─────────────────┐      ┌─────────┐
│EMERGENCY_OVERRIDE│─────▶│  FREEZE │──(alert HNC)──▶ QUARANTINE
└─────────────────┘      └─────────┘
```

### 4. Portal Host (Destination)
Final destination running LLM endpoint.

**Responsibilities:**
- Fragment execution
- Response generation
- Coherence proof attachment
- Reverse path through mesh

## Packet Format (Mesh Extension)

Standard RPP packet with mesh header prepended:

```
┌────────────────────────────────────────────────────────────────┐
│                      RPP MESH HEADER (16 bytes)                │
├────────────────────────────────────────────────────────────────┤
│  0       1       2       3       4       5       6       7     │
│ ┌───────┬───────┬───────────────┬─────────────────────────────┐│
│ │ Ver   │ Flags │ Consent State │      Soul ID (truncated)    ││
│ │ (4b)  │ (4b)  │    (8b)       │          (16b)              ││
│ └───────┴───────┴───────────────┴─────────────────────────────┘│
│  8       9      10      11      12      13      14      15     │
│ ┌───────────────┬───────────────┬───────────────┬─────────────┐│
│ │   Hop Count   │  TTL (sector) │ Coherence Hash│  Reserved   ││
│ │    (8b)       │     (8b)      │    (16b)      │    (16b)    ││
│ └───────────────┴───────────────┴───────────────┴─────────────┘│
├────────────────────────────────────────────────────────────────┤
│                    RPP ADDRESS (4 bytes)                       │
│ ┌─────────┬─────────────────┬─────────────────┬───────────────┐│
│ │  Shell  │      Theta      │       Phi       │   Harmonic    ││
│ │  (2b)   │      (9b)       │      (9b)       │     (8b)      ││
│ └─────────┴─────────────────┴─────────────────┴───────────────┘│
├────────────────────────────────────────────────────────────────┤
│                    PAYLOAD (variable)                          │
│                    Fragment data, prompts, responses           │
└────────────────────────────────────────────────────────────────┘
```

### Header Fields

| Field | Bits | Description |
|-------|------|-------------|
| Version | 4 | Mesh protocol version (current: 1) |
| Flags | 4 | `0x1`=encrypted, `0x2`=compressed, `0x4`=priority |
| Consent State | 8 | ACSP state: `0x00`=FULL, `0x01`=DIMINISHED, `0x02`=SUSPENDED, `0xFF`=EMERGENCY |
| Soul ID | 16 | Truncated hash of verified human identity |
| Hop Count | 8 | Incremented at each mesh node |
| TTL | 8 | Decremented on sector boundary crossing |
| Coherence Hash | 16 | Short proof fragment is in-sync with soul |
| Reserved | 16 | Future use (must be zero) |

## Consent State Propagation

Consent state updates flow from HNC to mesh nodes:

```
┌─────────┐    biometric     ┌─────────┐    ACSP state    ┌─────────┐
│  HRDA   │────────────────▶ │   HNC   │ ────────────────▶│  Mesh   │
│ signals │                  │ consent │                  │  Nodes  │
└─────────┘                  │  calc   │                  └─────────┘
                             └─────────┘
                                  │
                                  ▼
                             ┌─────────┐
                             │   SCL   │ (audit log)
                             └─────────┘
```

**Update Protocol:**
1. HNC calculates new consent state from biometrics
2. HNC signs state change with soul key
3. Broadcast to mesh nodes via gossip protocol
4. Nodes update local consent cache (TTL: 30s)
5. Stale cache = re-query HNC before routing decision

## Deployment Topologies

### Minimal (Development)
```
┌──────────┐     ┌───────────────────────┐     ┌──────────┐
│  Client  │────▶│  All-in-One Node      │────▶│  Portal  │
└──────────┘     │  (ingress+gate+router)│     │  Host    │
                 └───────────────────────┘     └──────────┘
```
Single node runs all mesh functions. Good for local testing.

### Standard (Production)
```
                        ┌─────────────┐
               ┌───────▶│ Sector 0-127│───────┐
               │        └─────────────┘       │
┌────────┐  ┌──┴───┐    ┌─────────────┐    ┌──▼───┐  ┌────────┐
│ Client │─▶│Ingress│───▶│Sector 128-255│───▶│ Gate │─▶│ Portal │
└────────┘  └──┬───┘    └─────────────┘    └──▲───┘  └────────┘
               │        ┌─────────────┐       │
               └───────▶│Sector 256+  │───────┘
                        └─────────────┘
```
Separate sector routers, shared consent gate.

### High Availability (Enterprise)
```
┌──────────────────────────────────────────────────────────────┐
│                        REGION A                              │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐      │
│  │Ingress-A│   │Router-A1│   │Router-A2│   │ Gate-A  │      │
│  └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘      │
│       └─────────────┴─────────────┴─────────────┘           │
└──────────────────────────────┬───────────────────────────────┘
                               │ Cross-region sync
┌──────────────────────────────▼───────────────────────────────┐
│                        REGION B                              │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐      │
│  │Ingress-B│   │Router-B1│   │Router-B2│   │ Gate-B  │      │
│  └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘      │
│       └─────────────┴─────────────┴─────────────┘           │
└──────────────────────────────────────────────────────────────┘
```

## Integration with AVACHATTER

### Configuration Flag
```python
# avachatter_config.py

DEPLOYMENT_MODE = "rpp_mesh"  # Options: "direct", "vpn", "rpp_mesh"

RPP_MESH_CONFIG = {
    "ingress_nodes": [
        "mesh-ingress-1.avachatter.net:7700",
        "mesh-ingress-2.avachatter.net:7700",
    ],
    "consent_update_endpoint": "wss://hnc.avachatter.net/consent-stream",
    "soul_key_path": "/etc/avachatter/soul.key",
    "fallback_mode": "direct",  # If mesh unreachable
}
```

### Client Integration
```python
class AVACHATTERClient:
    def __init__(self, config):
        self.mode = config.DEPLOYMENT_MODE
        
        if self.mode == "rpp_mesh":
            self.transport = RPPMeshTransport(config.RPP_MESH_CONFIG)
        elif self.mode == "vpn":
            self.transport = VPNTransport(config.VPN_CONFIG)
        else:
            self.transport = DirectTransport(config.PORTAL_HOSTS)
    
    async def send_fragment(self, fragment: Fragment, consent_state: ConsentState):
        packet = RPPPacket(
            address=fragment.rpp_address,
            consent_state=consent_state,
            soul_id=self.soul_id_truncated,
            payload=fragment.serialize()
        )
        
        if self.mode == "rpp_mesh":
            # Mesh handles routing by theta sector
            return await self.transport.send(packet)
        else:
            # Direct/VPN: we pick the endpoint
            endpoint = self.resolver.resolve(fragment.rpp_address)
            return await self.transport.send(packet, endpoint)
```

## Security Considerations

### Threat: Consent State Spoofing
**Attack:** Malicious client sets FULL_CONSENT when actually SUSPENDED
**Mitigation:** 
- Consent state must be signed by HNC
- Mesh nodes verify signature against known HNC public key
- Stale signatures (>30s) trigger re-verification

### Threat: Soul ID Collision
**Attack:** Attacker guesses truncated soul ID
**Mitigation:**
- 16-bit truncation is for routing only, not auth
- Full soul verification happens at Portal Host
- Coherence hash provides additional binding

### Threat: Mesh Node Compromise
**Attack:** Attacker controls a sector router
**Mitigation:**
- Payload encrypted end-to-end (client ↔ portal)
- Mesh sees headers only
- Consent state tampering detected by signature verification
- SCL audit log detects anomalous routing patterns

### Threat: Replay Attack
**Attack:** Attacker replays old packets
**Mitigation:**
- Hop count + TTL create implicit nonce
- Coherence hash changes with fragment state
- Portal Host tracks recent packet hashes

## Performance Characteristics

| Metric | Direct | VPN | RPP Mesh |
|--------|--------|-----|----------|
| Latency overhead | 0ms | +5-20ms | +10-30ms |
| Bandwidth overhead | 0% | +5-10% | +2-5% (header only) |
| Consent enforcement | Application | Application | Network |
| Routing intelligence | None | None | Geometric |
| Failover | Manual | VPN provider | Automatic sector reroute |

## Future Extensions

### 1. Hardware Consent Gates
FPGA-based consent verification for line-rate enforcement:
```
┌─────────────────────────────────────────┐
│  Lattice ECP5 Consent Gate              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ Parse   │─▶│ Verify  │─▶│ Route/  │  │
│  │ Header  │  │ Sig     │  │ Drop    │  │
│  └─────────┘  └─────────┘  └─────────┘  │
│       10 Gbps line rate                 │
└─────────────────────────────────────────┘
```

### 2. Sector-Aware DNS
DNS returns different IPs based on theta sector:
```
; Query for theta=64
_rpp._tcp.portal.avachatter.net. IN SRV 10 0 7700 portal-sector0.avachatter.net.

; Query for theta=320
_rpp._tcp.portal.avachatter.net. IN SRV 10 0 7700 portal-guardian.avachatter.net.
```

### 3. Cross-Mesh Peering
Multiple AVACHATTER deployments interconnect:
```
┌─────────────────┐         ┌─────────────────┐
│  Mesh A         │◄───────▶│  Mesh B         │
│  (Enterprise 1) │  Peering│  (Enterprise 2) │
└─────────────────┘         └─────────────────┘
```
Enables fragment migration between organizations with consent preservation.

---

## Summary

RPP Mesh provides:
1. **Consent at the network edge** - Bad actors stopped before reaching portals
2. **Geometric routing** - Fragments find functionally-appropriate hosts
3. **Graceful degradation** - Falls back to direct mode if mesh unavailable
4. **Audit trail** - All routing decisions logged to SCL

It's an optional deployment mode. AVACHATTER works without it, but organizations wanting defense-in-depth consent enforcement can enable it.
