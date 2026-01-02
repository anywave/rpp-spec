"""
Tests for HNC Module
====================

Tests for Harmonic Nexus Core.
"""

import pytest

from rpp.hnc import (
    FragmentStatus,
    FragmentState,
    ConflictResult,
    HarmonicNexusCore,
    create_hnc_with_fragments,
)
from rpp.ra_constants import MAX_COHERENCE, BINDING_THRESHOLD


# =============================================================================
# Test FragmentStatus
# =============================================================================

class TestFragmentStatus:
    """Tests for FragmentStatus enum."""

    def test_status_values(self):
        """Status enum should have correct values."""
        assert FragmentStatus.ACTIVE == 0
        assert FragmentStatus.IDLE == 1
        assert FragmentStatus.SYNCING == 2
        assert FragmentStatus.DEPHASED == 3
        assert FragmentStatus.OFFLINE == 4


# =============================================================================
# Test FragmentState
# =============================================================================

class TestFragmentState:
    """Tests for FragmentState dataclass."""

    def test_default_values(self):
        """Default state should be idle with zero coherence."""
        state = FragmentState(fragment_id="test")
        assert state.coherence == 0
        assert state.priority == 1.0
        assert state.status == FragmentStatus.IDLE
        assert state.complecount == 0

    def test_value_clamping(self):
        """Values should be clamped to valid ranges."""
        state = FragmentState(
            fragment_id="test",
            coherence=1000,  # Max 674
            priority=5.0,  # Max 2.0
            complecount=10,  # Max 7
        )
        assert state.coherence == MAX_COHERENCE
        assert state.priority == 2.0
        assert state.complecount == 7

    def test_weighted_score(self):
        """Weighted score should be coherence × priority."""
        state = FragmentState(
            fragment_id="test",
            coherence=500,
            priority=1.5,
        )
        assert state.weighted_score == 750.0

    def test_is_bound(self):
        """is_bound should check binding threshold."""
        # Below threshold
        state = FragmentState(fragment_id="test", coherence=100)
        assert not state.is_bound

        # Above threshold (137/674 ≈ 0.203)
        state = FragmentState(fragment_id="test", coherence=200)
        assert state.is_bound

    def test_is_complete(self):
        """is_complete should check complecount=7."""
        state = FragmentState(fragment_id="test", complecount=6)
        assert not state.is_complete

        state = FragmentState(fragment_id="test", complecount=7)
        assert state.is_complete


# =============================================================================
# Test HarmonicNexusCore Registration
# =============================================================================

class TestHNCRegistration:
    """Tests for fragment registration."""

    def test_register_fragment(self):
        """Should register fragment and track it."""
        hnc = HarmonicNexusCore()
        state = hnc.register_fragment("frag1", priority=1.5)

        assert state.fragment_id == "frag1"
        assert state.priority == 1.5
        assert hnc.fragment_count == 1

    def test_unregister_fragment(self):
        """Should unregister fragment."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1")
        assert hnc.fragment_count == 1

        result = hnc.unregister_fragment("frag1")
        assert result is True
        assert hnc.fragment_count == 0

    def test_unregister_nonexistent(self):
        """Should return False for nonexistent fragment."""
        hnc = HarmonicNexusCore()
        result = hnc.unregister_fragment("nonexistent")
        assert result is False

    def test_get_fragment(self):
        """Should retrieve fragment by ID."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1", priority=1.2)

        state = hnc.get_fragment("frag1")
        assert state is not None
        assert state.priority == 1.2

    def test_active_fragments(self):
        """Should return only active fragments."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1")
        hnc.register_fragment("frag2")
        hnc.set_fragment_status("frag2", FragmentStatus.OFFLINE)

        active = hnc.active_fragments
        assert len(active) == 1
        assert active[0].fragment_id == "frag1"


# =============================================================================
# Test HNC Coherence Updates
# =============================================================================

class TestHNCCoherence:
    """Tests for coherence updates."""

    def test_update_fragment_coherence(self):
        """Should update fragment coherence."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1")

        result = hnc.update_fragment_coherence("frag1", coherence=500)
        assert result is True
        assert hnc.get_fragment("frag1").coherence == 500

    def test_update_nonexistent(self):
        """Should return False for nonexistent fragment."""
        hnc = HarmonicNexusCore()
        result = hnc.update_fragment_coherence("nonexistent", coherence=500)
        assert result is False

    def test_update_sets_status(self):
        """Update should set status based on coherence."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1")

        # Above binding threshold
        hnc.update_fragment_coherence("frag1", coherence=500)
        assert hnc.get_fragment("frag1").status == FragmentStatus.ACTIVE

        # Below binding threshold
        hnc.update_fragment_coherence("frag1", coherence=50)
        assert hnc.get_fragment("frag1").status == FragmentStatus.DEPHASED


# =============================================================================
# Test Master Coherence
# =============================================================================

class TestMasterCoherence:
    """Tests for master coherence calculation."""

    def test_single_fragment(self):
        """Master coherence should equal single fragment."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1", initial_coherence=400)

        assert hnc.master_coherence == 400.0

    def test_weighted_average(self):
        """Master should be weighted average."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1", priority=1.0, initial_coherence=200)
        hnc.register_fragment("frag2", priority=1.0, initial_coherence=400)

        # (200*1 + 400*1) / (1+1) = 300
        assert hnc.master_coherence == 300.0

    def test_priority_weighting(self):
        """Higher priority should weight more."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1", priority=1.0, initial_coherence=200)
        hnc.register_fragment("frag2", priority=2.0, initial_coherence=400)

        # (200*1 + 400*2) / (1+2) = 1000/3 ≈ 333.3
        assert abs(hnc.master_coherence - 333.33) < 1

    def test_master_complecount(self):
        """Master complecount should be minimum."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1", initial_coherence=500)
        hnc.register_fragment("frag2", initial_coherence=500)
        hnc.update_fragment_coherence("frag1", coherence=500, complecount=5)
        hnc.update_fragment_coherence("frag2", coherence=500, complecount=3)

        assert hnc.master_complecount == 3

    def test_completion_flag(self):
        """Completion flag when all fragments at 7."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1", initial_coherence=674)
        hnc.register_fragment("frag2", initial_coherence=674)

        # Not complete yet
        hnc.update_fragment_coherence("frag1", coherence=674, complecount=7)
        hnc.update_fragment_coherence("frag2", coherence=674, complecount=5)
        assert not hnc.completion_flag

        # Now complete
        hnc.update_fragment_coherence("frag2", coherence=674, complecount=7)
        assert hnc.completion_flag


# =============================================================================
# Test Conflict Adjudication
# =============================================================================

class TestConflictAdjudication:
    """Tests for conflict resolution."""

    def test_higher_coherence_wins(self):
        """Higher weighted coherence should win."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1", priority=1.0, initial_coherence=300)
        hnc.register_fragment("frag2", priority=1.0, initial_coherence=500)

        result = hnc.adjudicate_conflict("frag1", "frag2")
        assert result.winner_id == "frag2"
        assert result.loser_id == "frag1"

    def test_priority_affects_outcome(self):
        """Higher priority can overcome lower coherence."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1", priority=2.0, initial_coherence=300)  # 600
        hnc.register_fragment("frag2", priority=1.0, initial_coherence=500)  # 500

        result = hnc.adjudicate_conflict("frag1", "frag2")
        assert result.winner_id == "frag1"

    def test_conflict_margin(self):
        """Result should include score margin."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1", priority=1.0, initial_coherence=300)
        hnc.register_fragment("frag2", priority=1.0, initial_coherence=500)

        result = hnc.adjudicate_conflict("frag1", "frag2")
        assert result.margin == 200.0


# =============================================================================
# Test Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_hnc_with_fragments(self):
        """Should create HNC with pre-registered fragments."""
        hnc = create_hnc_with_fragments(["f1", "f2", "f3"], initial_coherence=100)

        assert hnc.fragment_count == 3
        assert hnc.get_fragment("f1").coherence == 100
        assert hnc.get_fragment("f2").coherence == 100
        assert hnc.get_fragment("f3").coherence == 100


# =============================================================================
# Test Coherence Summary
# =============================================================================

class TestCoherenceSummary:
    """Tests for coherence summary."""

    def test_summary_structure(self):
        """Summary should have expected fields."""
        hnc = HarmonicNexusCore()
        hnc.register_fragment("frag1", initial_coherence=500)

        summary = hnc.get_coherence_summary()

        assert 'fragment_count' in summary
        assert 'master_coherence' in summary
        assert 'completion_flag' in summary
        assert 'fragments' in summary
        assert len(summary['fragments']) == 1

    def test_empty_summary(self):
        """Empty HNC should return zero summary."""
        hnc = HarmonicNexusCore()
        summary = hnc.get_coherence_summary()

        assert summary['fragment_count'] == 0
        assert summary['master_coherence'] == 0
