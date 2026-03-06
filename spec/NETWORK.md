# RPP Consent-Field Mesh — Network Architecture

**Version:** 1.0.0
**Status:** Active — Network / Mesh Layer
**Last Updated:** 2026-03-04
**License:** CC BY 4.0

---

## 1. Overview

RPP does not have a routing table. It has a **consent field**.

A routing table is a static snapshot: "to reach destination X, forward to node Y." It is
updated periodically, cached globally, and breaks when topology changes. RPP's design
property — that addresses are temporal, consent-gated, and ephemeral — is fundamentally
incompatible with a routing table.

Instead, RPP nodes participate in a **consent-field mesh**: a distributed, self-organizing
network where routing decisions emerge from the local consent field state at each node, not
from a globally consistent forwarding table. Packets are not "routed to a destination" —
they are **conducted through the consent field toward a resonant angular position** on the
torus.

```
Traditional mesh:
    Node A has table: { X → B, Y → C, Z → D }
    Packet arrives for X → forward to B

RPP consent-field mesh:
    Node A has consent field: { phi=256 epoch=7, theta=128 active, ... }
    Packet arrives with (shell=0, theta=120, phi=200, harmonic=64)
    Node A: "phi=200 is within my consent field. theta=120 is 8 degrees
             from my own theta. My neighbor at theta=115 is closer.
             Forward there."
    No table. No pre-computed route. Local gradient on the torus.
```

This is the **B+D routing model**: a resonance backbone (B) combined with an event-driven
mesh (D). Nodes make autonomous local decisions. Packets trigger events at nodes. The
network topology is not configured — it **emerges from the consent field state**.

---

## 2. Node Tiers — Shell-Based Self-Organization

RPP nodes self-organize into tiers based on their **Shell capacity** — their ability to
sustain routing state at a given temporal scope. Tiers are not configured; they emerge.

```
Shell 0 — HOT tier    (spintronic / in-memory)
Shell 1 — WARM tier   (near-line / fast storage)
Shell 2 — COLD tier   (archive storage)
Shell 3 — FROZEN tier (deep archive)
```

### 2.1 Tier Characteristics

| Tier | Shell | Relay role | Consent scope | Address TTL | Propagation |
|------|-------|------------|---------------|-------------|-------------|
| Hot | 0 | Full relay backbone | Session | ~25 ns (T2) | Field broadcast |
| Warm | 1 | Near-line relay | Transaction/day | ~100 ns | Broadcast + token |
| Cold | 2 | Archive sink | Agreement/month | ~400 ns | Epoch gossip |
| Frozen | 3 | Deep archive sink | Explicit revocation | ~1,600 ns | Hedera anchor |

### 2.2 Self-Organization Rules

A node declares its tier by advertising the highest Shell it can sustain:

```python
from dataclasses import dataclass, field
from enum import IntEnum
import math

class NodeTier(IntEnum):
    HOT    = 0
    WARM   = 1
    COLD   = 2
    FROZEN = 3


@dataclass
class NodeRecord:
    """
    A node's self-description broadcast to the consent field.
    Generated locally; not assigned by any authority.
    """
    node_id: bytes           # SHA-256(public_key) — 32 bytes
    tier: NodeTier           # Shell capacity (0-3)
    theta: int               # Node's angular sector [0-511] — what data types it routes
    phi_min: int             # Minimum consent level this node will relay [0-511]
    phi_max: int             # Maximum consent level this node will relay [0-511]
    harmonic_modes: list     # List of HarmonicMode values this node supports
    substrate_modality: str  # "spintronic" | "ipv4" | "ipv6" | "lora" | "ipfs" | etc.
    consent_epoch: int       # Current consent epoch — increments on policy change
    t2_ns: int               # T2 coherence time in ns (0 = software simulation)
    announced_at_ns: int     # Timestamp (monotonic ns since epoch)
    signature: bytes         # Node signature over all other fields
```

**A node MUST NOT relay packets with phi < phi_min** — it has declared it will not route
that consent level. **A node SHOULD NOT relay packets with phi > phi_max** — the data
requires higher consent than the node can verify.

### 2.3 Hot Tier — The Backbone

Shell=0 (Hot) nodes form the **routing backbone**. Because their address TTL equals session
duration and their propagation is T2-speed field broadcast, they are always-on relay nodes
that maintain live awareness of the consent field topology.

Hot nodes differ from Warm/Cold/Frozen in one critical way: they do not just forward
packets — they **participate in the consent field**. A Hot node continuously emits consent
field pulses (Section 4.1) and maintains a live neighbor map of other Hot nodes within
angular tolerance.

```
Hot backbone property:
    For any two Hot nodes A and B in the same theta sector (|theta_A - theta_B| < 32),
    there MUST exist a consent-field path between them with latency < 3 hops.
```

This is a liveness requirement, not a configuration requirement. Hot nodes self-heal
the backbone by detecting gaps and recruiting Warm nodes to upgrade.

---

## 3. Node Discovery

Discovery happens at three levels corresponding to the three upper tiers:

### 3.1 Hot Tier Discovery (Shell=0 — spintronic / local subnet)

Hot nodes discover each other via **consent field multicast**:

```
Protocol:   UDP multicast (224.0.0.89:8900) on local segment
            OR spintronic T2 field coupling (hardware)
            OR BLE beacon (short-range)
Message:    FIELD_PULSE (Section 4.1)
Frequency:  Every T2 window (25ns on spintronics, 100ms on software)
Scope:      Local segment only — no WAN multicast
```

On spintronic hardware, discovery is physical: spin states couple directly across
the lattice. Two Hot nodes within coupling distance discover each other without any
message exchange — the consent field state is shared at the physics level.

On software: UDP multicast on a local segment provides equivalent behavior for
simulation and software-only deployments.

### 3.2 Warm Tier Discovery (Shell=1 — near-line / internet)

Warm nodes bootstrap through known Hot nodes:

```python
def warm_node_bootstrap(bootstrap_hot_nodes: list[str]) -> list[NodeRecord]:
    """
    A Warm node discovers its neighborhood by querying Hot nodes
    for their current neighbor map filtered to theta-adjacent nodes.
    """
    # Step 1: Send CONSENT_PROBE to each bootstrap Hot node
    # Step 2: Receive FIELD_MAP response (list of NodeRecords in theta sector)
    # Step 3: Select neighbors: same theta sector, compatible phi range
    # Step 4: Exchange NodeRecords, verify signatures
    # Step 5: Begin receiving EPOCH_GOSSIP (Section 4.3)
    ...
```

Warm nodes maintain a **token cache**: a short-lived record of consent epochs received
from Hot nodes. Token TTL = min(T_transaction, 1 day). If the token expires before
the next refresh, the Warm node falls back to re-querying Hot nodes.

### 3.3 Cold/Frozen Tier Discovery (Shell=2/3 — archival)

Cold and Frozen nodes use pre-configured anchors rather than dynamic discovery:

```
Cold:   Hedera Hashgraph topic (opt-in audit registry)
        OR pre-configured list of Warm node bootstrap endpoints
        Consent epoch TTL: agreement/month

Frozen: Hedera Hashgraph only (permanent anchoring)
        NodeRecord stored on Hedera at time of deployment
        Cannot change without explicit on-chain revocation
```

For Cold/Frozen nodes, discovery is rare — they are archive sinks, not routing
participants. A Cold node does not need to find its neighbors every session; it needs
to find them once per agreement period.

---

## 4. Consent Field Propagation

The consent field is not a data structure stored somewhere — it is the **live state
of all active nodes' consent policies**, propagated continuously through the mesh.
Each node maintains its local view of the field and updates it as events arrive.

### 4.1 FIELD_PULSE — Hot Tier Heartbeat

Hot nodes emit a FIELD_PULSE every T2 window:

```python
@dataclass
class FieldPulse:
    """
    Emitted by Hot nodes every T2 window.
    Receivers update their local consent field map.
    """
    node_id: bytes        # emitting node
    theta: int            # node's angular sector
    phi_range: tuple      # (phi_min, phi_max) — consent corridor
    consent_epoch: int    # current epoch
    harmonic_active: int  # currently active harmonic mode
    load_factor: float    # routing load [0.0 = idle, 1.0 = saturated]
    timestamp_ns: int     # monotonic ns
    signature: bytes      # node signature

    # Wire encoding: 64 bytes (fits in single UDP packet)
    # On spintronics: 2 spin register writes
```

**On spintronics, this IS physics**: the spin state carrying the consent permission
decoheres in T2 time. The "field pulse" is not a message — it is the decoherence
measurement itself. Software implementations MUST enforce equivalent TTL semantics.

### 4.2 CONSENT_PROBE — Discovery and Validation

Any node can send a CONSENT_PROBE to ask whether a specific RPP address is routable
through a target node:

```python
@dataclass
class ConsentProbe:
    """
    Ask: "Can you route this address? Under what consent conditions?"
    """
    queried_address: int   # 28-bit RPP address
    queried_phi: int       # consent level being claimed
    queried_epoch: int     # epoch the requester is operating under
    requester_id: bytes    # hashed requester identity
    nonce: bytes           # prevents replay

@dataclass
class ConsentProbeResponse:
    """
    Response to CONSENT_PROBE.
    """
    can_route: bool
    reason: str            # "CONSENT_INSUFFICIENT" | "EPOCH_MISMATCH" | "OK"
    node_phi_min: int      # what consent level I require
    current_epoch: int     # my current epoch
    theta_distance: int    # angular distance from my sector to requested theta
    next_hop_hint: bytes   # optional: node_id of a closer neighbor
    signature: bytes
```

### 4.3 EPOCH_GOSSIP — Warm/Cold Consent Propagation

Warm nodes propagate consent epoch changes via gossip. Unlike Hot tier's T2-speed
field broadcast, gossip is eventually consistent — appropriate for Warm tier's
transaction/day TTL:

```python
@dataclass
class EpochGossipMessage:
    """
    Propagated when a consent epoch changes.
    Each node forwards to all Warm neighbors within 2 hops.
    """
    issuer_id: bytes        # who changed their consent policy
    new_epoch: int          # the new epoch number
    old_epoch: int          # the epoch being superseded
    phi_delta: int          # how consent changed (positive = more permissive)
    theta_sectors: list     # which theta sectors are affected
    effective_at_ns: int    # when this epoch takes effect
    hedera_sequence: int    # optional: Hedera anchor for audit trail
    signature: bytes

    # Propagation rule: forward to all neighbors where any(theta in theta_sectors)
    # TTL: 3 hops (prevents infinite propagation in dense meshes)
```

**Gossip vs. field broadcast:**

| Property | FIELD_PULSE (Hot) | EPOCH_GOSSIP (Warm/Cold) |
|----------|-------------------|--------------------------|
| Latency | T2 / sub-ms | Seconds to minutes |
| Consistency | Immediate (field physics) | Eventually consistent |
| Scope | Local segment | Network-wide |
| Trigger | Every T2 window | On consent change only |
| Cost | Very low (25-64 bytes) | Moderate (propagates N hops) |
| Hedera anchor | No (too frequent) | Optional (significant changes) |

### 4.4 Per-Tier Propagation Policy

```python
def should_propagate_consent_change(node_tier: NodeTier,
                                    delta_phi: int,
                                    affected_sectors: int) -> str:
    """
    Decide how to propagate a consent change based on node tier.
    Returns propagation strategy.
    """
    if node_tier == NodeTier.HOT:
        # Always immediate — field broadcast
        return "FIELD_BROADCAST"

    elif node_tier == NodeTier.WARM:
        if abs(delta_phi) > 50:
            # Significant consent change → gossip immediately
            return "GOSSIP_NOW"
        else:
            # Minor change → bundle with next scheduled gossip
            return "GOSSIP_BATCH"

    elif node_tier == NodeTier.COLD:
        if abs(delta_phi) > 100:
            # Major change → gossip + Hedera anchor
            return "GOSSIP_AND_HEDERA"
        else:
            return "HEDERA_ONLY"

    elif node_tier == NodeTier.FROZEN:
        # Frozen nodes never change consent except by explicit revocation
        # All changes are anchored on Hedera
        return "HEDERA_ONLY"
```

---

## 5. Routing Algorithm — Local Gradient Descent

### 5.1 The Torus Gradient

Routing is not path-finding. It is gradient descent on the torus toward the target
angular position. The "distance" between two addresses is the angular distance between
their (theta, phi) coordinates.

```python
import math

TWO_PI = 2 * math.pi

def angular_distance(theta1: int, phi1: int,
                     theta2: int, phi2: int) -> float:
    """
    Great-circle-like distance on the torus surface.
    Maps integer RPP fields to torus angles and computes geodesic distance.
    """
    t1 = (theta1 / 511.0) * TWO_PI
    p1 = (phi1   / 511.0) * TWO_PI
    t2 = (theta2 / 511.0) * TWO_PI
    p2 = (phi2   / 511.0) * TWO_PI

    # Modular angular difference
    dt = min(abs(t1 - t2), TWO_PI - abs(t1 - t2))
    dp = min(abs(p1 - p2), TWO_PI - abs(p1 - p2))

    return math.sqrt(dt**2 + dp**2)
```

### 5.2 Local Routing Decision

At each hop, a node decides: accept and process locally, forward to a closer neighbor,
or drop (consent barrier):

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RoutingDecision:
    action: str              # "ACCEPT" | "FORWARD" | "DROP" | "BARRIER"
    next_hop: Optional[bytes]  # node_id if FORWARD, else None
    reason: str
    angular_distance: float  # distance from this node to target


def make_routing_decision(packet_address: int,
                          local_node: NodeRecord,
                          neighbors: list[NodeRecord]) -> RoutingDecision:
    """
    Local routing decision — no global state, no routing table.

    1. Check consent: does this packet's phi fall within our relay range?
    2. Check if we are the destination (angular distance near zero).
    3. Find the neighbor closest to the target theta/phi.
    4. If a closer neighbor exists, forward there.
    5. If no closer neighbor, we are the local minimum — accept.
    """
    shell   = (packet_address >> 26) & 0x3
    theta   = (packet_address >> 17) & 0x1FF
    phi     = (packet_address >>  8) & 0x1FF
    harmonic = packet_address & 0xFF

    # Step 1: Consent check
    if phi < local_node.phi_min:
        return RoutingDecision(
            action="BARRIER",
            next_hop=None,
            reason=f"CONSENT_INSUFFICIENT: phi={phi} < node phi_min={local_node.phi_min}",
            angular_distance=0.0,
        )

    # Step 2: Compute our distance to target
    my_dist = angular_distance(local_node.theta, 256, theta, phi)
    # (We use phi=256 as our "resting" consent level for distance calc)

    # Step 3: Find closest neighbor
    best_neighbor = None
    best_dist = my_dist

    for neighbor in neighbors:
        # Only consider neighbors that can relay this consent level
        if neighbor.phi_min <= phi <= neighbor.phi_max:
            d = angular_distance(neighbor.theta, 256, theta, phi)
            if d < best_dist:
                best_dist = d
                best_neighbor = neighbor

    # Step 4: Forward or accept
    if best_neighbor is not None and best_dist < my_dist * 0.95:
        # A neighbor is at least 5% closer — forward
        return RoutingDecision(
            action="FORWARD",
            next_hop=best_neighbor.node_id,
            reason=f"CLOSER_NEIGHBOR: dist {my_dist:.4f} → {best_dist:.4f}",
            angular_distance=best_dist,
        )
    else:
        # We are the local minimum — accept the packet
        return RoutingDecision(
            action="ACCEPT",
            next_hop=None,
            reason=f"LOCAL_MINIMUM: dist={my_dist:.4f}, no closer neighbor",
            angular_distance=my_dist,
        )
```

### 5.3 Shell-Tier Routing Priority

When multiple next-hop candidates are at similar angular distance, prefer the one
at the lowest (most capable) Shell:

```python
def rank_next_hops(candidates: list[NodeRecord],
                   target_theta: int,
                   target_phi: int) -> list[NodeRecord]:
    """
    Rank candidate next-hops by: angular distance first, then Shell tier.
    Hot nodes (Shell=0) beat Warm nodes at equal distance.
    """
    def score(n: NodeRecord) -> tuple:
        dist = angular_distance(n.theta, 256, target_theta, target_phi)
        return (dist, n.tier)   # sort ascending: closer + hotter = better

    return sorted(candidates, key=score)
```

### 5.4 Harmonic Mode Routing

The Harmonic field (bits 7:0) encodes routing priority and frequency tier:

| Harmonic range | Mode | Routing behavior |
|---------------|------|-----------------|
| 0-63 | BACKGROUND | Best-effort, low priority, accepts long paths |
| 64-127 | MEMORY | Standard, moderate priority |
| 128-191 | REFLECTIVE | Elevated priority, prefers Hot nodes |
| 192-223 | ACTIVE | High priority, Hot backbone only |
| 224-255 | ARCHIVAL | Direct-to-Cold routing, bypasses Hot tier |

```python
def harmonic_to_tier_preference(harmonic: int) -> NodeTier:
    """Map harmonic value to preferred node tier for routing."""
    if harmonic >= 224:
        return NodeTier.COLD       # ARCHIVAL → route directly to archive
    elif harmonic >= 192:
        return NodeTier.HOT        # ACTIVE → Hot backbone only
    elif harmonic >= 128:
        return NodeTier.HOT        # REFLECTIVE → prefer Hot
    elif harmonic >= 64:
        return NodeTier.WARM       # MEMORY → standard path
    else:
        return NodeTier.WARM       # BACKGROUND → any path
```

---

## 6. Hot Backbone Maintenance

The Hot backbone (Shell=0 nodes) MUST maintain coverage across the full theta range
[0-511]. A "gap" in the backbone — a theta sector with no Hot node — degrades routing
quality for all nodes traversing that sector.

### 6.1 Gap Detection

Hot nodes continuously monitor the field for gaps in coverage:

```python
THETA_SECTORS = 8     # 512 / 8 = 64 theta values per sector (45° each)
GAP_THRESHOLD = 3     # if fewer than this many Hot nodes cover a sector, it's a gap

def detect_backbone_gaps(neighbor_map: list[NodeRecord]) -> list[int]:
    """
    Returns list of theta sector indices with insufficient Hot coverage.
    Sector i covers theta values [i*64, (i+1)*64 - 1].
    """
    hot_nodes = [n for n in neighbor_map if n.tier == NodeTier.HOT]
    sector_counts = [0] * THETA_SECTORS

    for node in hot_nodes:
        sector = node.theta // 64
        sector_counts[sector] += 1

    return [i for i, count in enumerate(sector_counts) if count < GAP_THRESHOLD]
```

### 6.2 Gap Repair — Warm Upgrade Request

When a Hot node detects a backbone gap, it broadcasts a BACKBONE_UPGRADE_REQUEST
to Warm nodes in the affected sector:

```python
@dataclass
class BackboneUpgradeRequest:
    """
    Sent by Hot nodes to Warm nodes in under-covered theta sectors.
    A Warm node MAY accept and begin operating as a Hot node for
    the duration of the current consent epoch.
    """
    requesting_node: bytes      # Hot node making the request
    target_sector: int          # theta sector index needing coverage (0-7)
    current_coverage: int       # how many Hot nodes are in this sector
    requested_coverage: int     # how many are needed
    epoch: int                  # consent epoch this request is valid for
    duration_ns: int            # how long the upgraded node should remain Hot
    reward_hint: str            # optional: "hedera://topic/reward" for PoP systems
    signature: bytes
```

A Warm node that accepts becomes **temporarily Hot** for the duration of the epoch,
maintaining T2-speed field pulses and routing at Shell=0 priority.

### 6.3 Backbone Topology Invariant

```
For all theta sectors S in [0-7]:
    count(Hot nodes covering S) >= 3

This MUST hold at all times.
A single Hot node failure SHOULD NOT partition the backbone.
```

---

## 7. Packet Recovery in the Mesh

See also: spec/RESOLVER.md Section 5.4 (packet recovery mechanisms).

In a consent-field mesh, packets can become "stuck" — lodged at a node that cannot
forward them because no neighbor has the required consent level. The Recovery
Escalation Ladder applies at the mesh level:

### 7.1 Stuck Packet Detection

```python
MAX_HOPS = 32       # packets exceeding this hop count are considered stuck
HOLD_TIMEOUT_NS = {
    NodeTier.HOT:    100_000,          # 100 µs
    NodeTier.WARM:   5 * 60 * 1_000_000_000,    # 5 min
    NodeTier.COLD:   24 * 3600 * 1_000_000_000, # 24 hours
    NodeTier.FROZEN: 30 * 24 * 3600 * 1_000_000_000,  # 30 days
}

def is_packet_stuck(packet_hop_count: int,
                    time_at_node_ns: int,
                    node_tier: NodeTier) -> bool:
    return (packet_hop_count > MAX_HOPS or
            time_at_node_ns > HOLD_TIMEOUT_NS[node_tier])
```

### 7.2 Recovery Escalation

| Level | Name | Mechanism | When |
|-------|------|-----------|------|
| 1 | Reroute | Find alternate theta path | Next hop unreachable |
| 2 | Steering cargo | Send consent-refresh ahead of packet | Consent epoch mismatch |
| 3 | Pull-back | Return packet to previous node | Destination unreachable |
| 4 | Copy-and-collect | Hold partial copy, forward remainder | Partial consent |
| 5 | Abort | Discard + Hedera anchor (if phi threshold met) | All paths exhausted |

**Hold Not Drop**: At all levels 1-4, the origin node MUST retain its copy of the
packet until Level 5 is reached or successful delivery is confirmed. This mirrors
the Ford Protocol's continuity guarantee (spec/CONTINUITY.md).

---

## 8. Network Topology Diagrams

### 8.1 Shell-Tier Mesh

```
              FROZEN tier (Shell=3)
              [Archive sinks, Hedera-anchored]
                        |
              COLD tier (Shell=2)
              [Archive sinks, gossip-fed]
                        |
              WARM tier (Shell=1)
              [Near-line relay, token-cached]
                        |
    ┌─────────────────────────────────────────┐
    │            HOT BACKBONE (Shell=0)        │
    │                                          │
    │  [A]──[B]──[C]──[D]──[E]──[F]──[G]──[H] │
    │   |    |    |    |    |    |    |    |   │
    │  theta sectors: 0   1   2   3   4   5   6   7  │
    │  (each covers 64 theta values, 45° arc)  │
    └─────────────────────────────────────────┘

    Routing packets traverse Hot backbone to the closest
    theta sector, then drop to Warm/Cold as needed.
```

### 8.2 Consent Field as Torus

```
    Theta (outer ring — data type sector)
    Phi (tube cross-section — consent spectrum)

         phi=511 (max consent)
              │
    ┌─────────┼─────────┐
    │  FROZEN │  COLD   │ ← high consent requirement
    ├─────────┼─────────┤
    │  WARM   │  HOT    │ ← low-mid consent
    └─────────┼─────────┘
              │
         phi=0 (open access)

    ←────── theta=0 ────── theta=511 ──────→

    Packets flow toward their (theta, phi) coordinate.
    Consent field state at each node determines passage.
```

### 8.3 Multi-Hop Routing Example

```
Packet: shell=0, theta=280, phi=128, harmonic=192 (ACTIVE mode)

  Node A (theta=50)                      Node D (theta=300)
  dist to target: 4.2 rad                dist to target: 0.4 rad
      |                                       |
      | forward →                             | accept
      ↓                                       ↓
  Node B (theta=150)    →    Node C (theta=260)    → ACCEPT
  dist: 2.8 rad              dist: 0.9 rad

  Each hop: local consent check + gradient descent on torus.
  No routing table. No pre-computed path. Emergent trajectory.
```

---

## 9. Non-Linear Routing Properties

RPP is explicitly **not linear**. The consent-field mesh is designed to avoid
the linearity assumptions of traditional networking:

| Linear network assumption | RPP consent-field mesh |
|--------------------------|------------------------|
| Packets follow a fixed path | Packets follow the consent gradient — path emerges at runtime |
| Routing tables are pre-computed | Routing decisions are purely local, real-time |
| Failure = re-route around a node | Failure = consent field adjusts, new gradient forms |
| Addressing is permanent | Addressing is temporal — consent expiry is topology change |
| Security is an overlay | Consent is intrinsic to the address — cannot be separated |
| Adding a new protocol means new headers | New transport modality = new URI scheme in resolver |

**Non-linearity is a feature, not a limitation.** It means the network is never
"routing table stale" — the routing state IS the current consent field state, which
is always live. It means no node has global knowledge — every routing decision is
a local trust decision.

---

## 10. Protocol Constants

```python
# Backbone maintenance
THETA_SECTORS          = 8       # 512 theta values / 8 sectors = 64 per sector
MIN_HOT_NODES_PER_SECTOR = 3     # minimum for backbone redundancy
BACKBONE_UPGRADE_EPOCH_TTL = 1   # temporary Hot upgrades last 1 epoch

# Routing
MAX_HOP_COUNT          = 32      # stuck packet threshold
ROUTING_GRADIENT_MIN   = 0.05    # minimum improvement to forward (5%)
ANGULAR_TOLERANCE_RAD  = 0.1     # ~5.7° — angular proximity to "accept" a packet

# Consent propagation
FIELD_PULSE_INTERVAL_NS = 25     # Hot tier pulse interval (≈ T2 on spintronics)
GOSSIP_BATCH_INTERVAL_S = 60     # Warm tier gossip batch interval
GOSSIP_TTL_HOPS        = 3       # epoch gossip propagation limit
HEDERA_PHI_THRESHOLD   = 400     # phi > this value → Hedera anchor on epoch change

# Discovery
WARM_BOOTSTRAP_TIMEOUT_S  = 30   # max time to complete Warm node bootstrap
COLD_REFRESH_INTERVAL_S   = 86400  # Cold nodes refresh anchors daily
MULTICAST_GROUP            = "224.0.0.89"
MULTICAST_PORT             = 8900
```

---

## 11. Invariants

1. **Consent monotonicity:** A packet's phi requirement MUST NOT decrease in transit.
   Nodes that relax consent requirements downstream invalidate the routing guarantee.

2. **Backbone coverage:** All 8 theta sectors MUST have >= 3 Hot nodes at all times.
   Gap detection and repair (Section 6) enforces this continuously.

3. **Local-only decisions:** Routing decisions MUST be made using only local state
   (local consent field + direct neighbor map). No global routing state is consulted.

4. **Hold Not Drop:** A node holding a packet in the recovery escalation ladder
   MUST retain its copy until either successful delivery or explicit abort (Level 5).

5. **Temporal address consistency:** A node MUST NOT forward a packet to a next-hop
   whose consent epoch is more than 1 epoch behind the packet's epoch. Stale consent
   = stale address = invalid route.

6. **Tier self-declaration:** Node tier is self-declared and verified by observation.
   A node claiming Shell=0 capability that cannot sustain T2-speed field pulses MUST
   be excluded from the Hot backbone by its neighbors.

7. **Consent field is the network:** There is no "network configuration" separate
   from the consent field state. The topology IS the consent field.

---

## 12. See Also

- [SPEC.md](SPEC.md) — RPP v1.0 address encoding (Shell/Theta/Phi/Harmonic)
- [ADDRESSING-LAYERS.md](ADDRESSING-LAYERS.md) — two-layer architecture
- [RESOLVER.md](RESOLVER.md) — transport-modality-agnostic resolver (v2.1)
- [ROUTING-FLOW-v1.md](ROUTING-FLOW-v1.md) — per-packet routing decision tree
- [CONTINUITY.md](CONTINUITY.md) — Ford Protocol substrate crossing
- [GEOMETRY.md](GEOMETRY.md) — toroidal coordinate system, Rasengan encryption

---

*"There is no map. There is only the field. The field is the map."*

*This specification is released under CC BY 4.0. Attribution required.*
