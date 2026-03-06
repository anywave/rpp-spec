"""
RPP Consent-Field Mesh — Network Architecture (v1.0)

Implements the consent-field mesh node and routing types defined in spec/NETWORK.md.

Routing in RPP is not table-based. Packets are conducted through the consent field
toward a resonant angular position on the torus. All routing decisions are purely
local — only local_node and direct neighbors are consulted.

This module is pure Python with no external dependencies (stdlib only: math,
dataclasses, enum, typing).
"""

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NodeTier(IntEnum):
    """
    Node tier derived from Shell capacity.

    Tiers are self-declared and emerge from a node's ability to sustain routing
    state at a given temporal scope. Shell=0 (Hot) nodes form the routing backbone.
    """
    HOT    = 0
    WARM   = 1
    COLD   = 2
    FROZEN = 3


# ---------------------------------------------------------------------------
# Protocol Constants (spec/NETWORK.md Section 10)
# ---------------------------------------------------------------------------

# Backbone maintenance
THETA_SECTORS              = 8    # 512 theta values / 8 sectors = 64 per sector
MIN_HOT_NODES_PER_SECTOR   = 3    # minimum for backbone redundancy
BACKBONE_UPGRADE_EPOCH_TTL = 1    # temporary Hot upgrades last 1 epoch

# Routing
MAX_HOP_COUNT              = 32   # stuck packet threshold
ROUTING_GRADIENT_MIN       = 0.05 # minimum improvement to forward (5%)
ANGULAR_TOLERANCE_RAD      = 0.1  # ~5.7° — angular proximity to "accept" a packet

# Consent propagation
FIELD_PULSE_INTERVAL_NS    = 25   # Hot tier pulse interval (≈ T2 on spintronics)
GOSSIP_BATCH_INTERVAL_S    = 60   # Warm tier gossip batch interval
GOSSIP_TTL_HOPS            = 3    # epoch gossip propagation limit
HEDERA_PHI_THRESHOLD       = 400  # phi > this value → Hedera anchor on epoch change

# Discovery
WARM_BOOTSTRAP_TIMEOUT_S   = 30       # max time to complete Warm node bootstrap
COLD_REFRESH_INTERVAL_S    = 86400    # Cold nodes refresh anchors daily
MULTICAST_GROUP            = "224.0.0.89"
MULTICAST_PORT             = 8900

# Stuck-packet hold timeouts keyed by NodeTier
HOLD_TIMEOUT_NS: dict = {
    NodeTier.HOT:    100_000,                    # 100 µs
    NodeTier.WARM:   5 * 60 * 1_000_000_000,     # 5 min
    NodeTier.COLD:   24 * 3600 * 1_000_000_000,  # 24 hours
    NodeTier.FROZEN: 30 * 24 * 3600 * 1_000_000_000,  # 30 days
}

# Internal — gap detection threshold (same value as MIN_HOT_NODES_PER_SECTOR)
_GAP_THRESHOLD = MIN_HOT_NODES_PER_SECTOR

# Torus math helper
_TWO_PI = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Data Classes — Node Self-Description
# ---------------------------------------------------------------------------

@dataclass
class NodeRecord:
    """
    A node's self-description broadcast to the consent field.

    Generated locally; not assigned by any authority. The node_id is the
    SHA-256 hash of the node's public key (32 bytes). Fields are ordered
    with no-default fields first.

    Consent relay policy:
      - MUST NOT relay packets with phi < phi_min.
      - SHOULD NOT relay packets with phi > phi_max.
    """
    node_id:            bytes   # SHA-256(public_key) — 32 bytes
    tier:               NodeTier
    theta:              int     # angular sector [0-511] — data type this node routes
    phi_min:            int     # minimum consent level this node will relay [0-511]
    phi_max:            int     # maximum consent level this node will relay [0-511]
    harmonic_modes:     list    # list of HarmonicMode values this node supports
    substrate_modality: str     # "spintronic" | "ipv4" | "ipv6" | "lora" | "ipfs" | ...
    consent_epoch:      int     # current consent epoch — increments on policy change
    t2_ns:              int     # T2 coherence time in ns (0 = software simulation)
    announced_at_ns:    int     # timestamp (monotonic ns since epoch)
    signature:          bytes   # node signature over all other fields


# ---------------------------------------------------------------------------
# Data Classes — Routing
# ---------------------------------------------------------------------------

@dataclass
class RoutingDecision:
    """
    Result of make_routing_decision().

    action values:
      "ACCEPT"  — this node is the local minimum; consume the packet.
      "FORWARD" — a closer neighbor exists; relay there.
      "DROP"    — packet should be discarded (not currently returned, reserved).
      "BARRIER" — consent gate: phi below this node's phi_min.
    """
    action:           str            # "ACCEPT" | "FORWARD" | "DROP" | "BARRIER"
    next_hop:         Optional[bytes]  # node_id if FORWARD, else None
    reason:           str
    angular_distance: float          # distance from this node to target


# ---------------------------------------------------------------------------
# Data Classes — Consent Field Messages
# ---------------------------------------------------------------------------

@dataclass
class FieldPulse:
    """
    Emitted by Hot nodes every T2 window (FIELD_PULSE heartbeat).

    Receivers update their local consent field map.
    Wire encoding: 64 bytes — fits in a single UDP packet.
    On spintronics: 2 spin register writes.
    """
    node_id:         bytes   # emitting node
    theta:           int     # node's angular sector
    phi_range:       tuple   # (phi_min, phi_max) — consent corridor
    consent_epoch:   int     # current epoch
    harmonic_active: int     # currently active harmonic mode
    load_factor:     float   # routing load [0.0 = idle, 1.0 = saturated]
    timestamp_ns:    int     # monotonic ns
    signature:       bytes   # node signature


@dataclass
class ConsentProbe:
    """
    Ask: "Can you route this address? Under what consent conditions?"

    Any node can send a CONSENT_PROBE to ask whether a specific RPP address
    is routable through a target node.
    """
    queried_address: int    # 28-bit RPP address
    queried_phi:     int    # consent level being claimed
    queried_epoch:   int    # epoch the requester is operating under
    requester_id:    bytes  # hashed requester identity
    nonce:           bytes  # prevents replay


@dataclass
class ConsentProbeResponse:
    """
    Response to CONSENT_PROBE.
    """
    can_route:       bool
    reason:          str    # "CONSENT_INSUFFICIENT" | "EPOCH_MISMATCH" | "OK"
    node_phi_min:    int    # what consent level I require
    current_epoch:   int    # my current epoch
    theta_distance:  int    # angular distance from my sector to requested theta
    next_hop_hint:   bytes  # optional: node_id of a closer neighbor
    signature:       bytes


@dataclass
class EpochGossipMessage:
    """
    Propagated when a consent epoch changes (EPOCH_GOSSIP).

    Each node forwards to all Warm neighbors within 2 hops.
    TTL: 3 hops (prevents infinite propagation in dense meshes).
    Propagation rule: forward to all neighbors where any(theta in theta_sectors).
    """
    issuer_id:        bytes  # who changed their consent policy
    new_epoch:        int    # the new epoch number
    old_epoch:        int    # the epoch being superseded
    phi_delta:        int    # how consent changed (positive = more permissive)
    theta_sectors:    list   # which theta sectors are affected
    effective_at_ns:  int    # when this epoch takes effect
    hedera_sequence:  int    # optional: Hedera anchor for audit trail
    signature:        bytes


@dataclass
class BackboneUpgradeRequest:
    """
    Sent by Hot nodes to Warm nodes in under-covered theta sectors.

    A Warm node MAY accept and begin operating as a Hot node for the duration
    of the current consent epoch.
    """
    requesting_node:    bytes  # Hot node making the request
    target_sector:      int    # theta sector index needing coverage (0-7)
    current_coverage:   int    # how many Hot nodes are in this sector
    requested_coverage: int    # how many are needed
    epoch:              int    # consent epoch this request is valid for
    duration_ns:        int    # how long the upgraded node should remain Hot
    reward_hint:        str    # optional: "hedera://topic/reward" for PoP systems
    signature:          bytes


# ---------------------------------------------------------------------------
# Torus Geometry
# ---------------------------------------------------------------------------

def angular_distance(theta1: int, phi1: int, theta2: int, phi2: int) -> float:
    """
    Great-circle-like distance on the torus surface.

    Maps integer RPP fields to torus angles and computes geodesic distance.
    Both theta and phi are integers in [0, 511]; the function normalises them
    to [0, 2π) before computing the modular angular difference on each axis.

    Args:
        theta1: First point theta component [0-511]
        phi1:   First point phi component   [0-511]
        theta2: Second point theta component [0-511]
        phi2:   Second point phi component   [0-511]

    Returns:
        Non-negative float representing the Euclidean distance in angle space
        on the torus surface.
    """
    t1 = (theta1 / 511.0) * _TWO_PI
    p1 = (phi1   / 511.0) * _TWO_PI
    t2 = (theta2 / 511.0) * _TWO_PI
    p2 = (phi2   / 511.0) * _TWO_PI

    # Modular angular difference (shortest arc on each circle)
    dt = min(abs(t1 - t2), _TWO_PI - abs(t1 - t2))
    dp = min(abs(p1 - p2), _TWO_PI - abs(p1 - p2))

    return math.sqrt(dt ** 2 + dp ** 2)


# ---------------------------------------------------------------------------
# Routing Functions
# ---------------------------------------------------------------------------

def make_routing_decision(
    packet_address: int,
    local_node: NodeRecord,
    neighbors: List[NodeRecord],
) -> RoutingDecision:
    """
    Local routing decision — no global state, no routing table.

    Decodes the 28-bit RPP address internally (shell, theta, phi, harmonic).
    Decision logic:

      1. Consent check: drop to BARRIER if phi < local node's phi_min.
      2. Compute this node's angular distance to the target (theta, phi).
      3. Find the neighbor closest to target that can relay the consent level.
      4. If a neighbor is at least ROUTING_GRADIENT_MIN (5%) closer, FORWARD there.
      5. Otherwise we are the local minimum — ACCEPT the packet.

    Args:
        packet_address: 28-bit RPP address integer.
        local_node:     This node's NodeRecord.
        neighbors:      Direct neighbor NodeRecords visible to this node.

    Returns:
        RoutingDecision describing the action to take.
    """
    # Decode 28-bit address
    shell    = (packet_address >> 26) & 0x3
    theta    = (packet_address >> 17) & 0x1FF
    phi      = (packet_address >>  8) & 0x1FF
    harmonic =  packet_address        & 0xFF

    # Step 1: Consent gate
    if phi < local_node.phi_min:
        return RoutingDecision(
            action="BARRIER",
            next_hop=None,
            reason=f"CONSENT_INSUFFICIENT: phi={phi} < node phi_min={local_node.phi_min}",
            angular_distance=0.0,
        )

    # Step 2: Our distance to target
    # phi=256 is the node's "resting" consent level for the distance calculation
    my_dist = angular_distance(local_node.theta, 256, theta, phi)

    # Step 3: Find the closest eligible neighbor
    best_neighbor: Optional[NodeRecord] = None
    best_dist = my_dist

    for neighbor in neighbors:
        if neighbor.phi_min <= phi <= neighbor.phi_max:
            d = angular_distance(neighbor.theta, 256, theta, phi)
            if d < best_dist:
                best_dist = d
                best_neighbor = neighbor

    # Step 4: Forward if a meaningfully closer neighbor exists (>= 5% improvement)
    if best_neighbor is not None and best_dist < my_dist * (1.0 - ROUTING_GRADIENT_MIN):
        return RoutingDecision(
            action="FORWARD",
            next_hop=best_neighbor.node_id,
            reason=f"CLOSER_NEIGHBOR: dist {my_dist:.4f} -> {best_dist:.4f}",
            angular_distance=best_dist,
        )

    # Step 5: Local minimum — accept
    return RoutingDecision(
        action="ACCEPT",
        next_hop=None,
        reason=f"LOCAL_MINIMUM: dist={my_dist:.4f}, no closer neighbor",
        angular_distance=my_dist,
    )


def rank_next_hops(
    candidates: List[NodeRecord],
    target_theta: int,
    target_phi: int,
) -> List[NodeRecord]:
    """
    Rank candidate next-hops by angular distance first, then Shell tier.

    Hot nodes (Shell=0) beat Warm nodes at equal angular distance. The result
    is sorted ascending: closer + hotter = earlier in the list.

    Args:
        candidates:   NodeRecords to rank.
        target_theta: Target theta coordinate [0-511].
        target_phi:   Target phi coordinate   [0-511].

    Returns:
        Sorted list of NodeRecords (best candidate first).
    """
    def _score(n: NodeRecord) -> tuple:
        dist = angular_distance(n.theta, 256, target_theta, target_phi)
        return (dist, int(n.tier))  # ascending: closer + lower tier = better

    return sorted(candidates, key=_score)


def harmonic_to_tier_preference(harmonic: int) -> NodeTier:
    """
    Map a harmonic field value to the preferred NodeTier for routing.

    Harmonic ranges per spec Section 5.4:
      224-255  ARCHIVAL  → route directly to COLD archive
      192-223  ACTIVE    → Hot backbone only
      128-191  REFLECTIVE → prefer Hot
       64-127  MEMORY    → standard path (Warm)
        0- 63  BACKGROUND → any path (Warm)

    Args:
        harmonic: Harmonic field value [0-255].

    Returns:
        NodeTier indicating the preferred tier.
    """
    if harmonic >= 224:
        return NodeTier.COLD    # ARCHIVAL → route directly to archive
    elif harmonic >= 192:
        return NodeTier.HOT     # ACTIVE → Hot backbone only
    elif harmonic >= 128:
        return NodeTier.HOT     # REFLECTIVE → prefer Hot
    elif harmonic >= 64:
        return NodeTier.WARM    # MEMORY → standard path
    else:
        return NodeTier.WARM    # BACKGROUND → any path


# ---------------------------------------------------------------------------
# Hot Backbone Maintenance
# ---------------------------------------------------------------------------

def detect_backbone_gaps(neighbor_map: List[NodeRecord]) -> List[int]:
    """
    Return theta sector indices with insufficient Hot node coverage.

    Sector i covers theta values in [i*64, (i+1)*64 - 1].
    A sector is considered a gap when it has fewer than MIN_HOT_NODES_PER_SECTOR
    (3) Hot nodes.

    Args:
        neighbor_map: All known NodeRecords (any tier) visible to this node.

    Returns:
        List of sector indices (0-7) that are under-covered.
    """
    hot_nodes = [n for n in neighbor_map if n.tier == NodeTier.HOT]
    sector_counts = [0] * THETA_SECTORS

    for node in hot_nodes:
        sector = node.theta // 64
        sector_counts[sector] += 1

    return [i for i, count in enumerate(sector_counts) if count < _GAP_THRESHOLD]


# ---------------------------------------------------------------------------
# Consent Propagation Policy
# ---------------------------------------------------------------------------

def should_propagate_consent_change(
    node_tier: NodeTier,
    delta_phi: int,
    affected_sectors: int,
) -> str:
    """
    Decide how to propagate a consent change based on node tier and magnitude.

    Returns a propagation strategy string:
      "FIELD_BROADCAST"   — immediate T2-speed field broadcast (Hot tier)
      "GOSSIP_NOW"        — gossip immediately (significant Warm change)
      "GOSSIP_BATCH"      — bundle with next scheduled gossip (minor Warm change)
      "GOSSIP_AND_HEDERA" — gossip + Hedera anchor (major Cold change)
      "HEDERA_ONLY"       — Hedera anchor only (minor Cold or any Frozen change)

    Args:
        node_tier:        Tier of the node deciding propagation.
        delta_phi:        Signed change in phi consent level.
        affected_sectors: Number of theta sectors affected (not used in current
                          policy but reserved for future tier-specific logic).

    Returns:
        Propagation strategy string.
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

    else:  # NodeTier.FROZEN
        # Frozen nodes never change consent except by explicit revocation;
        # all changes are anchored on Hedera.
        return "HEDERA_ONLY"


# ---------------------------------------------------------------------------
# Stuck Packet Detection
# ---------------------------------------------------------------------------

def is_packet_stuck(
    packet_hop_count: int,
    time_at_node_ns: int,
    node_tier: NodeTier,
) -> bool:
    """
    Detect whether a packet is stuck at this node.

    A packet is considered stuck if either:
      - It has exceeded MAX_HOP_COUNT (32) hops, OR
      - It has been held at this node longer than the tier-appropriate
        HOLD_TIMEOUT_NS threshold.

    Args:
        packet_hop_count: Number of hops the packet has traversed so far.
        time_at_node_ns:  How long (nanoseconds) the packet has been at this node.
        node_tier:        Tier of the current node.

    Returns:
        True if the packet should be considered stuck and recovery escalation
        should be triggered; False otherwise.
    """
    return (
        packet_hop_count > MAX_HOP_COUNT
        or time_at_node_ns > HOLD_TIMEOUT_NS[node_tier]
    )


__all__ = [
    # Constants
    "THETA_SECTORS",
    "MIN_HOT_NODES_PER_SECTOR",
    "BACKBONE_UPGRADE_EPOCH_TTL",
    "MAX_HOP_COUNT",
    "ROUTING_GRADIENT_MIN",
    "ANGULAR_TOLERANCE_RAD",
    "FIELD_PULSE_INTERVAL_NS",
    "GOSSIP_BATCH_INTERVAL_S",
    "GOSSIP_TTL_HOPS",
    "HEDERA_PHI_THRESHOLD",
    "WARM_BOOTSTRAP_TIMEOUT_S",
    "COLD_REFRESH_INTERVAL_S",
    "MULTICAST_GROUP",
    "MULTICAST_PORT",
    "HOLD_TIMEOUT_NS",
    # Enums
    "NodeTier",
    # Data classes
    "NodeRecord",
    "RoutingDecision",
    "FieldPulse",
    "ConsentProbe",
    "ConsentProbeResponse",
    "EpochGossipMessage",
    "BackboneUpgradeRequest",
    # Functions
    "angular_distance",
    "make_routing_decision",
    "rank_next_hops",
    "harmonic_to_tier_preference",
    "detect_backbone_gaps",
    "should_propagate_consent_change",
    "is_packet_stuck",
]
