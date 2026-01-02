"""
Tests for Biofield Module
=========================

Tests for biofield binding and phase memory.
"""

import pytest

from rpp.biofield import (
    BindingStatus,
    BindingEvent,
    BiofieldBinding,
    PhaseMemoryAnchor,
    PhaseMemoryField,
    compute_binding_threshold_score,
    is_coherence_binding,
)
from rpp.ra_constants import (
    MAX_COHERENCE,
    BINDING_THRESHOLD,
    KHAT_DURATION,
    ALPHA_INVERSE,
)


# =============================================================================
# Test Binding Status
# =============================================================================

class TestBindingStatus:
    """Tests for BindingStatus enum."""

    def test_status_values(self):
        """Status enum should have correct values."""
        assert BindingStatus.UNBOUND == 0
        assert BindingStatus.BINDING == 1
        assert BindingStatus.BOUND == 2
        assert BindingStatus.DEPHASING == 3
        assert BindingStatus.DEPHASED == 4


# =============================================================================
# Test BiofieldBinding Initialization
# =============================================================================

class TestBiofieldBindingInit:
    """Tests for BiofieldBinding initialization."""

    def test_default_initialization(self):
        """Default init should start unbound with zero coherence."""
        binding = BiofieldBinding()
        assert binding.coherence == 0
        assert binding.status == BindingStatus.UNBOUND
        assert binding.dephased_cycles == 0

    def test_initial_coherence_clamped(self):
        """Initial coherence should be clamped to valid range."""
        binding = BiofieldBinding(initial_coherence=1000)
        assert binding.coherence == MAX_COHERENCE

        binding = BiofieldBinding(initial_coherence=-50)
        assert binding.coherence == 0

    def test_high_coherence_starts_bound(self):
        """High initial coherence should start in BOUND state."""
        binding = BiofieldBinding(initial_coherence=500)
        assert binding.status == BindingStatus.BOUND


# =============================================================================
# Test Binding Coefficient
# =============================================================================

class TestBindingCoefficient:
    """Tests for binding coefficient calculation."""

    def test_zero_coherence_zero_coefficient(self):
        """Zero coherence should give zero coefficient."""
        binding = BiofieldBinding(initial_coherence=0)
        assert binding.binding_coefficient == 0.0

    def test_max_coherence_one_coefficient(self):
        """Max coherence should give coefficient of 1.0."""
        binding = BiofieldBinding(initial_coherence=MAX_COHERENCE)
        assert binding.binding_coefficient == 1.0

    def test_binding_threshold_coherence(self):
        """Coherence at threshold should give ~0.203."""
        binding = BiofieldBinding(initial_coherence=137)
        assert abs(binding.binding_coefficient - BINDING_THRESHOLD) < 0.01

    def test_is_bound_below_threshold(self):
        """Below threshold should not be bound."""
        binding = BiofieldBinding(initial_coherence=100)
        assert not binding.is_bound

    def test_is_bound_at_threshold(self):
        """At or above threshold should be bound."""
        binding = BiofieldBinding(initial_coherence=137)
        assert binding.is_bound

    def test_is_bound_above_threshold(self):
        """Above threshold should be bound."""
        binding = BiofieldBinding(initial_coherence=500)
        assert binding.is_bound


# =============================================================================
# Test Coherence Updates
# =============================================================================

class TestCoherenceUpdates:
    """Tests for coherence update behavior."""

    def test_update_coherence_clamped(self):
        """Update coherence should clamp to valid range."""
        binding = BiofieldBinding()
        binding.update_coherence(1000)
        assert binding.coherence == MAX_COHERENCE

        binding.update_coherence(-50)
        assert binding.coherence == 0

    def test_update_from_unbound_to_bound(self):
        """Updating coherence above threshold should bind."""
        binding = BiofieldBinding()
        assert binding.status == BindingStatus.UNBOUND

        binding.update_coherence(500)
        assert binding.status == BindingStatus.BOUND

    def test_update_from_bound_to_dephasing(self):
        """Dropping below threshold should start dephasing."""
        binding = BiofieldBinding(initial_coherence=500)
        assert binding.status == BindingStatus.BOUND

        binding.update_coherence(50)
        assert binding.status == BindingStatus.DEPHASING

    def test_update_recovery_during_dephase(self):
        """Rising above threshold during dephase should recover."""
        binding = BiofieldBinding(initial_coherence=500)
        binding.update_coherence(50)  # Start dephasing
        assert binding.status == BindingStatus.DEPHASING

        binding.update_coherence(500)  # Recover
        assert binding.status == BindingStatus.BOUND


# =============================================================================
# Test Dephasing
# =============================================================================

class TestDephasing:
    """Tests for dephasing behavior."""

    def test_dephase_from_bound(self):
        """Dephase should transition from BOUND to DEPHASING."""
        binding = BiofieldBinding(initial_coherence=500)
        result = binding.dephase()

        assert result is True  # Still recoverable
        assert binding.status == BindingStatus.DEPHASING

    def test_dephase_recoverable_within_khat(self):
        """Should be recoverable within KHAT duration."""
        binding = BiofieldBinding(initial_coherence=500)
        binding.dephase()

        for i in range(KHAT_DURATION):
            binding.tick()
            assert binding.is_recoverable

    def test_dephase_full_after_khat(self):
        """Should fully dephase after KHAT duration."""
        binding = BiofieldBinding(initial_coherence=500)
        binding.dephase()

        for i in range(KHAT_DURATION + 1):
            binding.tick()

        assert binding.status == BindingStatus.DEPHASED
        assert not binding.is_recoverable

    def test_recovery_cycles_remaining(self):
        """Should track remaining recovery cycles."""
        binding = BiofieldBinding(initial_coherence=500)
        binding.dephase()

        assert binding.recovery_cycles_remaining == KHAT_DURATION

        for i in range(5):
            binding.tick()

        assert binding.recovery_cycles_remaining == KHAT_DURATION - 5


# =============================================================================
# Test Resync
# =============================================================================

class TestResync:
    """Tests for resync behavior."""

    def test_resync_success(self):
        """Resync with high coherence should succeed."""
        binding = BiofieldBinding(initial_coherence=500)
        binding.dephase()
        binding.tick()
        binding.tick()

        result = binding.attempt_resync(500)
        assert result is True
        assert binding.status == BindingStatus.BOUND

    def test_resync_failure(self):
        """Resync with low coherence should fail."""
        binding = BiofieldBinding(initial_coherence=500)
        binding.dephase()

        result = binding.attempt_resync(50)
        assert result is False
        assert binding.status == BindingStatus.DEPHASING

    def test_resync_after_full_dephase(self):
        """Resync after full dephase should start rebinding."""
        binding = BiofieldBinding(initial_coherence=500)
        binding.dephase()

        # Fully dephase
        for i in range(KHAT_DURATION + 1):
            binding.tick()

        assert binding.status == BindingStatus.DEPHASED

        # Attempt resync
        binding.attempt_resync(500)
        assert binding.status == BindingStatus.BINDING


# =============================================================================
# Test Force Operations
# =============================================================================

class TestForceOperations:
    """Tests for force bind/unbind."""

    def test_force_bind(self):
        """Force bind should establish binding."""
        binding = BiofieldBinding()
        binding.force_bind()

        assert binding.status == BindingStatus.BOUND
        assert binding.is_bound

    def test_force_unbind(self):
        """Force unbind should clear binding."""
        binding = BiofieldBinding(initial_coherence=500)
        binding.force_unbind()

        assert binding.status == BindingStatus.UNBOUND
        assert binding.coherence == 0

    def test_reset(self):
        """Reset should clear all state."""
        binding = BiofieldBinding(initial_coherence=500)
        binding.dephase()
        binding.tick()

        binding.reset()

        assert binding.coherence == 0
        assert binding.status == BindingStatus.UNBOUND
        assert binding.dephased_cycles == 0
        assert len(binding.events) == 0


# =============================================================================
# Test Events
# =============================================================================

class TestBindingEvents:
    """Tests for binding event recording."""

    def test_events_recorded(self):
        """State transitions should be recorded as events."""
        binding = BiofieldBinding()
        binding.update_coherence(500)  # Unbound -> Bound

        assert len(binding.events) >= 1

    def test_event_contains_info(self):
        """Events should contain relevant information."""
        binding = BiofieldBinding()
        binding.update_coherence(500)

        event = binding.events[0]
        assert event.from_status == BindingStatus.UNBOUND
        assert event.to_status == BindingStatus.BOUND
        assert event.coherence == 500
        assert len(event.reason) > 0


# =============================================================================
# Test Phase Memory Anchor
# =============================================================================

class TestPhaseMemoryAnchor:
    """Tests for PhaseMemoryAnchor."""

    def test_anchor_creation(self):
        """Anchor should store coherence and complecount."""
        anchor = PhaseMemoryAnchor(
            anchor_id=1,
            coherence_snapshot=500,
            complecount=5,
        )
        assert anchor.coherence_snapshot == 500
        assert anchor.complecount == 5
        assert anchor.valid is True

    def test_anchor_invalidation(self):
        """Invalidation should mark anchor as invalid."""
        anchor = PhaseMemoryAnchor(
            anchor_id=1,
            coherence_snapshot=500,
            complecount=5,
        )
        anchor.invalidate()
        assert anchor.valid is False

    def test_anchor_age(self):
        """Age should be calculated from creation."""
        anchor = PhaseMemoryAnchor(
            anchor_id=1,
            coherence_snapshot=500,
            complecount=5,
        )
        # Age should be very small (just created)
        assert anchor.age_seconds < 1.0


# =============================================================================
# Test Phase Memory Field
# =============================================================================

class TestPhaseMemoryField:
    """Tests for PhaseMemoryField."""

    def test_field_initialization(self):
        """Field should start empty."""
        field = PhaseMemoryField()
        assert field.anchor_count == 0

    def test_create_anchor(self):
        """Creating anchor should add to field."""
        field = PhaseMemoryField()
        anchor = field.create_anchor(coherence=500, complecount=5)

        assert field.anchor_count == 1
        assert anchor.coherence_snapshot == 500

    def test_get_anchor(self):
        """Should retrieve anchor by ID."""
        field = PhaseMemoryField()
        anchor = field.create_anchor(coherence=500, complecount=5)

        retrieved = field.get_anchor(anchor.anchor_id)
        assert retrieved is not None
        assert retrieved.coherence_snapshot == 500

    def test_get_best_anchor(self):
        """Should return anchor with highest coherence."""
        field = PhaseMemoryField()
        field.create_anchor(coherence=300, complecount=3)
        field.create_anchor(coherence=600, complecount=6)
        field.create_anchor(coherence=400, complecount=4)

        best = field.get_best_anchor()
        assert best is not None
        assert best.coherence_snapshot == 600

    def test_max_anchors_pruning(self):
        """Should prune oldest when exceeding max."""
        field = PhaseMemoryField()

        # Create 8 anchors (max is 7)
        for i in range(8):
            field.create_anchor(coherence=100 * (i + 1), complecount=i % 7)

        assert field.anchor_count == 7

    def test_invalidate_all(self):
        """Should invalidate all anchors."""
        field = PhaseMemoryField()
        field.create_anchor(coherence=500, complecount=5)
        field.create_anchor(coherence=600, complecount=6)

        field.invalidate_all()
        assert field.anchor_count == 0

    def test_clear(self):
        """Should clear all anchors."""
        field = PhaseMemoryField()
        field.create_anchor(coherence=500, complecount=5)
        field.create_anchor(coherence=600, complecount=6)

        field.clear()
        assert field.anchor_count == 0
        assert len(field._anchors) == 0


# =============================================================================
# Test Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_compute_binding_threshold_score(self):
        """Should return 137 (alpha-inverse threshold)."""
        threshold = compute_binding_threshold_score()
        assert threshold == 137

    def test_is_coherence_binding_below(self):
        """Below threshold should return False."""
        assert not is_coherence_binding(100)

    def test_is_coherence_binding_at(self):
        """At threshold should return True."""
        assert is_coherence_binding(137)

    def test_is_coherence_binding_above(self):
        """Above threshold should return True."""
        assert is_coherence_binding(500)


# =============================================================================
# Test KHAT Duration Constant
# =============================================================================

class TestKHATDuration:
    """Tests for KHAT duration value."""

    def test_khat_duration_value(self):
        """KHAT_DURATION should be 12 cycles."""
        assert KHAT_DURATION == 12

    def test_binding_threshold_value(self):
        """BINDING_THRESHOLD should be ~0.203."""
        expected = 137 / 674
        assert abs(BINDING_THRESHOLD - expected) < 0.001
