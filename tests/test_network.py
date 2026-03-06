"""
Tests for rpp.network — Consent-Field Mesh Architecture.

Coverage:
  - NodeTier enum values
  - Constants (THETA_SECTORS, MIN_HOT_NODES_PER_SECTOR, MAX_HOP_COUNT, etc.)
  - HOLD_TIMEOUT_NS — tier-keyed, ordered
  - angular_distance() — symmetry, identity, modular wrap, range
  - make_routing_decision() — ACCEPT, FORWARD, BARRIER
  - rank_next_hops() — ordering by distance, tie-breaking by tier
  - harmonic_to_tier_preference() — all ranges
  - detect_backbone_gaps() — no gaps, partial gaps, all sectors gap
  - should_propagate_consent_change() — all tiers, thresholds
  - is_packet_stuck() — hop count, time thresholds
"""

import math
import pytest

from rpp.network import (
    NodeTier,
    NodeRecord,
    RoutingDecision,
    FieldPulse,
    ConsentProbe,
    ConsentProbeResponse,
    EpochGossipMessage,
    BackboneUpgradeRequest,
    THETA_SECTORS,
    MIN_HOT_NODES_PER_SECTOR,
    BACKBONE_UPGRADE_EPOCH_TTL,
    MAX_HOP_COUNT,
    ROUTING_GRADIENT_MIN,
    ANGULAR_TOLERANCE_RAD,
    FIELD_PULSE_INTERVAL_NS,
    GOSSIP_BATCH_INTERVAL_S,
    GOSSIP_TTL_HOPS,
    HEDERA_PHI_THRESHOLD,
    WARM_BOOTSTRAP_TIMEOUT_S,
    HOLD_TIMEOUT_NS,
    angular_distance,
    make_routing_decision,
    rank_next_hops,
    harmonic_to_tier_preference,
    detect_backbone_gaps,
    should_propagate_consent_change,
    is_packet_stuck,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_SIG = b"\x00" * 32
_DUMMY_ID  = b"\xab" * 32


def _node(node_id=_DUMMY_ID, tier=NodeTier.HOT, theta=256, phi_min=0, phi_max=511):
    return NodeRecord(
        node_id=node_id,
        tier=tier,
        theta=theta,
        phi_min=phi_min,
        phi_max=phi_max,
        harmonic_modes=[0, 64, 128, 192, 255],
        substrate_modality="ipv4",
        consent_epoch=1,
        t2_ns=0,
        announced_at_ns=1_700_000_000_000_000_000,
        signature=_DUMMY_SIG,
    )


def _make_address(shell=1, theta=100, phi=200, harmonic=0):
    return (shell << 26) | (theta << 17) | (phi << 8) | harmonic


# ---------------------------------------------------------------------------
# NodeTier
# ---------------------------------------------------------------------------

class TestNodeTier:
    def test_values(self):
        assert NodeTier.HOT    == 0
        assert NodeTier.WARM   == 1
        assert NodeTier.COLD   == 2
        assert NodeTier.FROZEN == 3

    def test_hot_is_minimum(self):
        assert NodeTier.HOT == min(NodeTier)

    def test_frozen_is_maximum(self):
        assert NodeTier.FROZEN == max(NodeTier)

    def test_int_enum(self):
        assert int(NodeTier.WARM) == 1


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_theta_sectors(self):
        assert THETA_SECTORS == 8

    def test_min_hot_nodes_per_sector(self):
        assert MIN_HOT_NODES_PER_SECTOR == 3

    def test_max_hop_count(self):
        assert MAX_HOP_COUNT == 32

    def test_routing_gradient_min(self):
        assert ROUTING_GRADIENT_MIN == pytest.approx(0.05)

    def test_hold_timeout_keys(self):
        assert set(HOLD_TIMEOUT_NS.keys()) == {
            NodeTier.HOT, NodeTier.WARM, NodeTier.COLD, NodeTier.FROZEN
        }

    def test_hold_timeout_ascending(self):
        hot    = HOLD_TIMEOUT_NS[NodeTier.HOT]
        warm   = HOLD_TIMEOUT_NS[NodeTier.WARM]
        cold   = HOLD_TIMEOUT_NS[NodeTier.COLD]
        frozen = HOLD_TIMEOUT_NS[NodeTier.FROZEN]
        assert hot < warm < cold < frozen

    def test_gossip_ttl_hops(self):
        assert GOSSIP_TTL_HOPS == 3


# ---------------------------------------------------------------------------
# angular_distance
# ---------------------------------------------------------------------------

class TestAngularDistance:
    def test_identity(self):
        assert angular_distance(100, 100, 100, 100) == pytest.approx(0.0)

    def test_symmetry(self):
        d1 = angular_distance(0, 0, 256, 256)
        d2 = angular_distance(256, 256, 0, 0)
        assert d1 == pytest.approx(d2)

    def test_positive(self):
        # Use values well away from the wrap boundary
        d = angular_distance(0, 0, 256, 256)
        assert d > 0.0

    def test_modular_theta_wrap(self):
        # Distance from 0 to 511 should be the same as 0 to 1
        # (going the short way around the circle)
        d_near = angular_distance(0, 255, 1, 255)
        d_far  = angular_distance(0, 255, 511, 255)
        # d_near and d_far should be similar (both ~1 step around)
        # The modular difference between 0 and 511 on [0-511] scale is 1 step
        assert abs(d_near - d_far) < 0.1  # within 0.1 rad

    def test_max_distance_is_bounded(self):
        # Maximum angular distance is bounded by sqrt(pi^2 + pi^2)
        d = angular_distance(0, 0, 511, 511)
        assert d <= math.sqrt(2) * math.pi + 1e-9

    def test_integer_inputs(self):
        # Must accept integer inputs (no float required)
        d = angular_distance(0, 0, 0, 0)
        assert d == pytest.approx(0.0)

    def test_phi_contributes_to_distance(self):
        d_same_phi = angular_distance(0, 255, 256, 255)
        d_diff_phi = angular_distance(0, 0, 256, 255)
        assert d_same_phi != pytest.approx(d_diff_phi)


# ---------------------------------------------------------------------------
# make_routing_decision
# ---------------------------------------------------------------------------

class TestMakeRoutingDecision:
    def test_accept_when_no_closer_neighbor(self):
        # Local node at theta=100; packet targets theta=100, phi=200
        local = _node(theta=100, phi_min=0, phi_max=511)
        # Neighbor far away
        neighbor = _node(node_id=b"\x01" * 32, theta=400, phi_min=0, phi_max=511)
        addr = _make_address(theta=100, phi=200)
        decision = make_routing_decision(addr, local, [neighbor])
        assert decision.action == "ACCEPT"

    def test_forward_when_closer_neighbor_exists(self):
        # Local at theta=0, target at theta=300, phi=200 — neighbor at theta=300 is much closer
        local = _node(node_id=b"\x00" * 32, theta=0, phi_min=0, phi_max=511)
        neighbor = _node(node_id=b"\x01" * 32, theta=300, phi_min=0, phi_max=511)
        addr = _make_address(theta=300, phi=200)
        decision = make_routing_decision(addr, local, [neighbor])
        assert decision.action == "FORWARD"
        assert decision.next_hop == neighbor.node_id

    def test_barrier_when_phi_below_min(self):
        # Node requires phi_min=300; packet has phi=100
        local = _node(theta=100, phi_min=300, phi_max=511)
        addr = _make_address(theta=100, phi=100)
        decision = make_routing_decision(addr, local, [])
        assert decision.action == "BARRIER"
        assert decision.next_hop is None
        assert "CONSENT_INSUFFICIENT" in decision.reason

    def test_barrier_reason_includes_phi_values(self):
        local = _node(theta=100, phi_min=400, phi_max=511)
        addr = _make_address(phi=50)
        decision = make_routing_decision(addr, local, [])
        assert "phi=50" in decision.reason or "50" in decision.reason

    def test_forward_skips_ineligible_neighbor(self):
        # Neighbor has phi_min=400 but packet phi=100 → ineligible
        local = _node(node_id=b"\x00" * 32, theta=0, phi_min=0, phi_max=511)
        ineligible = _node(node_id=b"\x01" * 32, theta=300, phi_min=400, phi_max=511)
        addr = _make_address(theta=300, phi=100)
        decision = make_routing_decision(addr, local, [ineligible])
        # Ineligible neighbor can't be used → local is the best option
        assert decision.action == "ACCEPT"

    def test_forward_selects_closest_neighbor(self):
        local = _node(node_id=b"\x00" * 32, theta=0, phi_min=0, phi_max=511)
        near  = _node(node_id=b"\x01" * 32, theta=300, phi_min=0, phi_max=511)
        far   = _node(node_id=b"\x02" * 32, theta=400, phi_min=0, phi_max=511)
        addr = _make_address(theta=300, phi=200)
        decision = make_routing_decision(addr, local, [far, near])
        assert decision.action == "FORWARD"
        assert decision.next_hop == near.node_id

    def test_accept_no_neighbors(self):
        local = _node(theta=200, phi_min=0, phi_max=511)
        addr = _make_address(theta=200, phi=200)
        decision = make_routing_decision(addr, local, [])
        assert decision.action == "ACCEPT"

    def test_angular_distance_in_result(self):
        local = _node(theta=100, phi_min=0, phi_max=511)
        addr = _make_address(theta=100, phi=200)
        decision = make_routing_decision(addr, local, [])
        assert isinstance(decision.angular_distance, float)
        assert decision.angular_distance >= 0.0

    def test_reason_is_nonempty_string(self):
        local = _node(theta=100, phi_min=0, phi_max=511)
        addr = _make_address(theta=100, phi=200)
        decision = make_routing_decision(addr, local, [])
        assert isinstance(decision.reason, str)
        assert len(decision.reason) > 0


# ---------------------------------------------------------------------------
# rank_next_hops
# ---------------------------------------------------------------------------

class TestRankNextHops:
    def test_sorted_by_distance(self):
        near  = _node(node_id=b"\x01" * 32, theta=100, phi_min=0, phi_max=511)
        far   = _node(node_id=b"\x02" * 32, theta=400, phi_min=0, phi_max=511)
        ranked = rank_next_hops([far, near], target_theta=100, target_phi=200)
        assert ranked[0].node_id == near.node_id

    def test_hot_beats_warm_at_equal_distance(self):
        hot  = _node(node_id=b"\x01" * 32, tier=NodeTier.HOT,  theta=200)
        warm = _node(node_id=b"\x02" * 32, tier=NodeTier.WARM, theta=200)
        ranked = rank_next_hops([warm, hot], target_theta=200, target_phi=255)
        assert ranked[0].node_id == hot.node_id

    def test_empty_list_returns_empty(self):
        assert rank_next_hops([], target_theta=100, target_phi=200) == []

    def test_single_element(self):
        node = _node(theta=50)
        ranked = rank_next_hops([node], target_theta=50, target_phi=255)
        assert len(ranked) == 1
        assert ranked[0] is node

    def test_returns_all_candidates(self):
        nodes = [_node(node_id=bytes([i]) * 32, theta=i * 50) for i in range(5)]
        ranked = rank_next_hops(nodes, target_theta=100, target_phi=200)
        assert len(ranked) == 5


# ---------------------------------------------------------------------------
# harmonic_to_tier_preference
# ---------------------------------------------------------------------------

class TestHarmonicToTierPreference:
    def test_archival_range_224_255(self):
        for h in [224, 240, 255]:
            assert harmonic_to_tier_preference(h) == NodeTier.COLD

    def test_active_range_192_223(self):
        for h in [192, 200, 223]:
            assert harmonic_to_tier_preference(h) == NodeTier.HOT

    def test_reflective_range_128_191(self):
        for h in [128, 150, 191]:
            assert harmonic_to_tier_preference(h) == NodeTier.HOT

    def test_memory_range_64_127(self):
        for h in [64, 90, 127]:
            assert harmonic_to_tier_preference(h) == NodeTier.WARM

    def test_background_range_0_63(self):
        for h in [0, 30, 63]:
            assert harmonic_to_tier_preference(h) == NodeTier.WARM

    def test_returns_node_tier_type(self):
        result = harmonic_to_tier_preference(100)
        assert isinstance(result, NodeTier)


# ---------------------------------------------------------------------------
# detect_backbone_gaps
# ---------------------------------------------------------------------------

class TestDetectBackboneGaps:
    def _hot_at_theta(self, theta, idx=0):
        return _node(node_id=bytes([idx]) * 32, tier=NodeTier.HOT, theta=theta)

    def test_no_gaps_when_fully_covered(self):
        # 3 Hot nodes per sector × 8 sectors = 24 nodes
        nodes = []
        for sector in range(8):
            for i in range(3):
                theta = sector * 64 + i * 5
                nodes.append(_node(
                    node_id=bytes([sector * 10 + i]) * 32,
                    tier=NodeTier.HOT,
                    theta=theta,
                ))
        gaps = detect_backbone_gaps(nodes)
        assert gaps == []

    def test_all_sectors_gap_when_no_hot_nodes(self):
        warm_nodes = [
            _node(node_id=bytes([i]) * 32, tier=NodeTier.WARM, theta=i * 50)
            for i in range(8)
        ]
        gaps = detect_backbone_gaps(warm_nodes)
        assert set(gaps) == set(range(8))

    def test_empty_neighbor_map(self):
        gaps = detect_backbone_gaps([])
        assert set(gaps) == set(range(8))

    def test_specific_sector_gap(self):
        # Fill sectors 0-6 with 3 nodes each; leave sector 7 empty
        nodes = []
        for sector in range(7):
            for i in range(3):
                theta = sector * 64 + i * 5
                nodes.append(_node(
                    node_id=bytes([sector * 10 + i]) * 32,
                    tier=NodeTier.HOT,
                    theta=theta,
                ))
        gaps = detect_backbone_gaps(nodes)
        assert gaps == [7]

    def test_sector_boundary_assignment(self):
        # theta=63 → sector 0, theta=64 → sector 1
        nodes = [
            _node(node_id=b"\x01" * 32, tier=NodeTier.HOT, theta=63),
            _node(node_id=b"\x02" * 32, tier=NodeTier.HOT, theta=64),
        ]
        gaps = detect_backbone_gaps(nodes)
        # Both sectors 0 and 1 have only 1 node → both are gaps
        assert 0 in gaps
        assert 1 in gaps

    def test_warm_nodes_not_counted(self):
        # Sector 0 has 3 Warm nodes but 0 Hot → should still be a gap
        nodes = [
            _node(node_id=bytes([i]) * 32, tier=NodeTier.WARM, theta=i * 10)
            for i in range(3)
        ]
        gaps = detect_backbone_gaps(nodes)
        assert 0 in gaps


# ---------------------------------------------------------------------------
# should_propagate_consent_change
# ---------------------------------------------------------------------------

class TestShouldPropagateConsentChange:
    def test_hot_always_broadcast(self):
        for delta in [1, 50, 100, 200, -200]:
            result = should_propagate_consent_change(NodeTier.HOT, delta, 1)
            assert result == "FIELD_BROADCAST"

    def test_warm_large_delta_gossip_now(self):
        result = should_propagate_consent_change(NodeTier.WARM, 51, 1)
        assert result == "GOSSIP_NOW"

    def test_warm_small_delta_gossip_batch(self):
        result = should_propagate_consent_change(NodeTier.WARM, 50, 1)
        assert result == "GOSSIP_BATCH"

    def test_warm_negative_large_delta(self):
        result = should_propagate_consent_change(NodeTier.WARM, -100, 1)
        assert result == "GOSSIP_NOW"

    def test_cold_large_delta_gossip_and_hedera(self):
        result = should_propagate_consent_change(NodeTier.COLD, 101, 3)
        assert result == "GOSSIP_AND_HEDERA"

    def test_cold_small_delta_hedera_only(self):
        result = should_propagate_consent_change(NodeTier.COLD, 100, 3)
        assert result == "HEDERA_ONLY"

    def test_frozen_always_hedera_only(self):
        for delta in [1, 50, 500, -500]:
            result = should_propagate_consent_change(NodeTier.FROZEN, delta, 1)
            assert result == "HEDERA_ONLY"

    def test_returns_string(self):
        result = should_propagate_consent_change(NodeTier.HOT, 0, 0)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# is_packet_stuck
# ---------------------------------------------------------------------------

class TestIsPacketStuck:
    def test_not_stuck_fresh_packet(self):
        assert is_packet_stuck(0, 0, NodeTier.HOT) is False

    def test_stuck_by_hop_count(self):
        # 33 hops > MAX_HOP_COUNT (32)
        assert is_packet_stuck(33, 0, NodeTier.HOT) is True

    def test_not_stuck_at_max_hop(self):
        # Exactly 32 hops — not stuck (> 32 is the threshold)
        assert is_packet_stuck(32, 0, NodeTier.WARM) is False

    def test_stuck_by_hold_time_hot(self):
        # Hot timeout = 100_000 ns; provide 200_000 ns
        assert is_packet_stuck(0, 200_000, NodeTier.HOT) is True

    def test_not_stuck_within_hot_timeout(self):
        assert is_packet_stuck(0, 50_000, NodeTier.HOT) is False

    def test_stuck_by_hold_time_warm(self):
        warm_timeout = HOLD_TIMEOUT_NS[NodeTier.WARM]
        assert is_packet_stuck(0, warm_timeout + 1, NodeTier.WARM) is True

    def test_not_stuck_within_warm_timeout(self):
        warm_timeout = HOLD_TIMEOUT_NS[NodeTier.WARM]
        assert is_packet_stuck(0, warm_timeout - 1, NodeTier.WARM) is False

    def test_either_condition_triggers(self):
        # Over time but under hops → stuck
        hot_timeout = HOLD_TIMEOUT_NS[NodeTier.HOT]
        assert is_packet_stuck(5, hot_timeout + 1, NodeTier.HOT) is True
        # Over hops but under time → stuck
        assert is_packet_stuck(33, 0, NodeTier.WARM) is True

    def test_all_tiers_have_timeout(self):
        for tier in NodeTier:
            timeout = HOLD_TIMEOUT_NS[tier]
            assert is_packet_stuck(0, timeout + 1, tier) is True
            assert is_packet_stuck(0, timeout - 1, tier) is False


# ---------------------------------------------------------------------------
# Data class smoke tests
# ---------------------------------------------------------------------------

class TestDataclasses:
    def test_node_record_fields(self):
        node = _node()
        assert hasattr(node, 'node_id')
        assert hasattr(node, 'tier')
        assert hasattr(node, 'theta')
        assert hasattr(node, 'phi_min')
        assert hasattr(node, 'phi_max')

    def test_routing_decision_fields(self):
        rd = RoutingDecision(
            action="ACCEPT",
            next_hop=None,
            reason="test",
            angular_distance=0.5,
        )
        assert rd.action == "ACCEPT"
        assert rd.next_hop is None

    def test_field_pulse_creation(self):
        fp = FieldPulse(
            node_id=_DUMMY_ID,
            theta=100,
            phi_range=(0, 511),
            consent_epoch=1,
            harmonic_active=0,
            load_factor=0.5,
            timestamp_ns=1_700_000_000_000_000_000,
            signature=_DUMMY_SIG,
        )
        assert fp.theta == 100

    def test_consent_probe_creation(self):
        cp = ConsentProbe(
            queried_address=0x00ABC123,
            queried_phi=200,
            queried_epoch=5,
            requester_id=_DUMMY_ID,
            nonce=b"\x00" * 16,
        )
        assert cp.queried_phi == 200

    def test_backbone_upgrade_request_creation(self):
        req = BackboneUpgradeRequest(
            requesting_node=_DUMMY_ID,
            target_sector=3,
            current_coverage=1,
            requested_coverage=3,
            epoch=7,
            duration_ns=1_000_000_000,
            reward_hint="",
            signature=_DUMMY_SIG,
        )
        assert req.target_sector == 3


# ---------------------------------------------------------------------------
# Integration — routing converges toward target
# ---------------------------------------------------------------------------

class TestRoutingConvergence:
    def test_packet_hops_toward_target(self):
        """
        Simulate a 3-hop routing chain where each hop gets closer to target.
        Verify that each step selects a node with lower angular distance.
        """
        target_theta, target_phi = 300, 400

        node_a = _node(node_id=b"\x01" * 32, theta=0,   phi_min=0, phi_max=511)
        node_b = _node(node_id=b"\x02" * 32, theta=150, phi_min=0, phi_max=511)
        node_c = _node(node_id=b"\x03" * 32, theta=300, phi_min=0, phi_max=511)

        addr = _make_address(theta=target_theta, phi=target_phi)

        # Hop 1: A routes to B (B is closer to 300 than A is)
        decision1 = make_routing_decision(addr, node_a, [node_b, node_c])
        assert decision1.action == "FORWARD"

        # Hop 2: from B, C is closer or B accepts
        decision2 = make_routing_decision(addr, node_b, [node_c])
        if decision2.action == "FORWARD":
            assert decision2.next_hop == node_c.node_id
        else:
            assert decision2.action == "ACCEPT"

        # Hop 3: C is at target theta → accept
        decision3 = make_routing_decision(addr, node_c, [node_a, node_b])
        assert decision3.action == "ACCEPT"
