"""
Tests for Transitions Module
============================

Tests for state transition dynamics.
"""

import pytest

from rpp.transitions import (
    TransitionDirection,
    DwellTimer,
    ConsentReflector,
    FallbackGate,
    ETFGate,
    TransitionManager,
)
from rpp.consent_header import ConsentState
from rpp.ra_constants import (
    DWELL_BASE,
    DWELL_FULL,
    KHAT_DURATION,
    ETF_DURATION,
    REFLECTION_DELAY,
)


# =============================================================================
# Test TransitionDirection
# =============================================================================

class TestTransitionDirection:
    """Tests for TransitionDirection enum."""

    def test_direction_values(self):
        """Direction enum should have correct values."""
        assert TransitionDirection.NONE == 0
        assert TransitionDirection.UPGRADE == 1
        assert TransitionDirection.DOWNGRADE == 2


# =============================================================================
# Test DwellTimer
# =============================================================================

class TestDwellTimer:
    """Tests for dwell time tracking."""

    def test_initial_state(self):
        """Initial state should be None."""
        timer = DwellTimer()
        assert timer.current_state is None
        assert timer.cycles_in_state == 0

    def test_first_transition_immediate(self):
        """First state transition should be immediate."""
        timer = DwellTimer()
        result = timer.request_transition(ConsentState.FULL_CONSENT)
        assert result is True
        assert timer.current_state == ConsentState.FULL_CONSENT

    def test_downgrade_immediate(self):
        """Downgrade transitions should be immediate."""
        timer = DwellTimer()
        timer.request_transition(ConsentState.FULL_CONSENT)

        # Downgrade to ATTENTIVE should be immediate
        result = timer.request_transition(ConsentState.ATTENTIVE)
        assert result is True
        assert timer.current_state == ConsentState.ATTENTIVE

    def test_upgrade_requires_dwell(self):
        """Upgrade transitions should require dwell time."""
        timer = DwellTimer()
        timer.request_transition(ConsentState.ATTENTIVE)

        # First upgrade request should fail
        result = timer.request_transition(ConsentState.FULL_CONSENT)
        assert result is False

    def test_full_consent_dwell_requirement(self):
        """FULL_CONSENT requires DWELL_FULL cycles."""
        timer = DwellTimer()
        timer.request_transition(ConsentState.ATTENTIVE)

        # Request upgrade to FULL - first request starts the counter
        result = timer.request_transition(ConsentState.FULL_CONSENT)
        assert result is False

        # Wait for required cycles
        for i in range(DWELL_FULL):
            timer.tick()

        # After waiting, should succeed
        result = timer.request_transition(ConsentState.FULL_CONSENT)
        assert result is True

    def test_attentive_dwell_requirement(self):
        """ATTENTIVE requires DWELL_BASE cycles."""
        timer = DwellTimer()
        timer.request_transition(ConsentState.DIMINISHED_CONSENT)

        # Request upgrade to ATTENTIVE - first request starts counter
        result = timer.request_transition(ConsentState.ATTENTIVE)
        assert result is False

        # Wait for required cycles
        for i in range(DWELL_BASE):
            timer.tick()

        # Should succeed after DWELL_BASE
        result = timer.request_transition(ConsentState.ATTENTIVE)
        assert result is True

    def test_suspended_immediate(self):
        """Transition to SUSPENDED should be immediate."""
        timer = DwellTimer()
        timer.request_transition(ConsentState.FULL_CONSENT)

        result = timer.request_transition(ConsentState.SUSPENDED_CONSENT)
        assert result is True

    def test_can_transition_to(self):
        """can_transition_to should check requirements."""
        timer = DwellTimer()
        timer.request_transition(ConsentState.ATTENTIVE)

        # Can't upgrade yet
        assert not timer.can_transition_to(ConsentState.FULL_CONSENT)

        # Can downgrade
        assert timer.can_transition_to(ConsentState.SUSPENDED_CONSENT)


# =============================================================================
# Test ConsentReflector
# =============================================================================

class TestConsentReflector:
    """Tests for consent reflection delay."""

    def test_initial_state(self):
        """Initial state should be None."""
        reflector = ConsentReflector()
        assert reflector.detected_state is None
        assert reflector.reflected_state is None

    def test_delay_value(self):
        """Default delay should be REFLECTION_DELAY."""
        reflector = ConsentReflector()
        assert reflector.delay == REFLECTION_DELAY

    def test_detection(self):
        """Detection should store state."""
        reflector = ConsentReflector()
        result = reflector.detect(ConsentState.FULL_CONSENT)

        assert result == ConsentState.FULL_CONSENT
        assert reflector.detected_state == ConsentState.FULL_CONSENT

    def test_reflection_after_delay(self):
        """Reflection should occur after delay cycles."""
        reflector = ConsentReflector()
        reflector.detect(ConsentState.FULL_CONSENT)

        # Not ready yet
        for i in range(REFLECTION_DELAY - 1):
            reflector.tick()
            assert not reflector.should_reflect()
            assert reflector.reflect() is None

        # Ready after delay
        reflector.tick()
        assert reflector.should_reflect()
        result = reflector.reflect()
        assert result == ConsentState.FULL_CONSENT

    def test_force_reflect(self):
        """Force reflect should bypass delay."""
        reflector = ConsentReflector()
        reflector.detect(ConsentState.ATTENTIVE)

        # No ticks, force reflect
        result = reflector.force_reflect()
        assert result == ConsentState.ATTENTIVE

    def test_new_detection_resets_counter(self):
        """New detection should reset cycle counter."""
        reflector = ConsentReflector()
        reflector.detect(ConsentState.FULL_CONSENT)

        # Partial progress
        reflector.tick()
        reflector.tick()

        # New detection
        reflector.detect(ConsentState.ATTENTIVE)

        # Should need full delay again
        assert not reflector.should_reflect()


# =============================================================================
# Test FallbackGate
# =============================================================================

class TestFallbackGate:
    """Tests for KHAT-gated fallback."""

    def test_initial_state(self):
        """Initial state should not be triggered."""
        gate = FallbackGate()
        assert gate.cycles_below == 0
        assert not gate.fallback_triggered

    def test_above_threshold_no_trigger(self):
        """Above threshold should not trigger fallback."""
        gate = FallbackGate(threshold=137)

        for _ in range(20):
            result = gate.update(200)  # Above threshold
            assert result is False

        assert not gate.fallback_triggered

    def test_below_threshold_counts(self):
        """Below threshold should count cycles."""
        gate = FallbackGate(threshold=137)

        gate.update(100)  # Below
        assert gate.cycles_below == 1

        gate.update(100)
        assert gate.cycles_below == 2

    def test_triggers_after_khat_duration(self):
        """Should trigger after KHAT_DURATION cycles."""
        gate = FallbackGate(threshold=137)

        for i in range(KHAT_DURATION):
            result = gate.update(100)
            assert result is False

        # One more triggers
        result = gate.update(100)
        assert result is True
        assert gate.fallback_triggered

    def test_recovery_resets(self):
        """Rising above threshold should reset."""
        gate = FallbackGate(threshold=137)

        # Count some cycles below
        for _ in range(5):
            gate.update(100)

        # Rise above
        gate.update(200)

        assert gate.cycles_below == 0
        assert not gate.fallback_triggered


# =============================================================================
# Test ETFGate
# =============================================================================

class TestETFGate:
    """Tests for Emergency Temporal Freeze gate."""

    def test_initial_state(self):
        """Initial state should not be active."""
        gate = ETFGate()
        assert not gate.is_active
        assert gate.emergency_cycles == 0

    def test_emergency_counts(self):
        """Emergency condition should count cycles."""
        gate = ETFGate()

        gate.update(is_emergency=True)
        assert gate.emergency_cycles == 1

        gate.update(is_emergency=True)
        assert gate.emergency_cycles == 2

    def test_activates_after_duration(self):
        """ETF should activate after ETF_DURATION."""
        gate = ETFGate()

        for i in range(ETF_DURATION - 1):
            result = gate.update(is_emergency=True)
            assert result is False

        result = gate.update(is_emergency=True)
        assert result is True
        assert gate.is_active

    def test_recovery_deactivates(self):
        """Non-emergency should deactivate."""
        gate = ETFGate()
        gate.activate()
        assert gate.is_active

        gate.update(is_emergency=False)
        assert not gate.is_active


# =============================================================================
# Test TransitionManager
# =============================================================================

class TestTransitionManager:
    """Tests for complete transition manager."""

    def test_initial_state(self):
        """Initial state should be None."""
        manager = TransitionManager()
        assert manager.current_state is None
        assert manager.cycle == 0

    def test_process_cycle(self):
        """Process cycle should return results dict."""
        manager = TransitionManager()

        result = manager.process_cycle(
            detected_state=ConsentState.FULL_CONSENT,
            coherence=500,
        )

        assert 'cycle' in result
        assert 'detected_state' in result
        assert 'current_state' in result
        assert 'transition_allowed' in result

    def test_smooth_somatic(self):
        """Smoothing should dampen changes."""
        manager = TransitionManager()

        # Initial value
        result1 = manager.smooth_somatic(15)

        # Jump to 0
        result2 = manager.smooth_somatic(0)

        # Should be between 0 and 15
        assert 0 < result2 < 15

    def test_etf_overrides_state(self):
        """ETF should override detected state."""
        manager = TransitionManager()

        # Process with emergency
        for _ in range(ETF_DURATION + 1):
            result = manager.process_cycle(
                detected_state=ConsentState.FULL_CONSENT,
                coherence=500,
                is_emergency=True,
            )

        # State should be EMERGENCY_OVERRIDE
        assert result['etf_active']

    def test_reset(self):
        """Reset should clear all state."""
        manager = TransitionManager()

        # Do some processing
        manager.process_cycle(ConsentState.FULL_CONSENT, 500)
        manager.process_cycle(ConsentState.FULL_CONSENT, 500)

        assert manager.cycle == 2

        # Reset
        manager.reset()

        assert manager.cycle == 0
        assert manager.current_state is None


# =============================================================================
# Test Dwell Time Constants
# =============================================================================

class TestDwellConstants:
    """Tests for dwell time constant values."""

    def test_dwell_full_value(self):
        """DWELL_FULL should be 19 cycles."""
        assert DWELL_FULL == 19

    def test_dwell_base_value(self):
        """DWELL_BASE should be 3 cycles."""
        assert DWELL_BASE == 3

    def test_khat_duration_value(self):
        """KHAT_DURATION should be 12 cycles."""
        assert KHAT_DURATION == 12

    def test_etf_duration_value(self):
        """ETF_DURATION should be 9 cycles."""
        assert ETF_DURATION == 9

    def test_reflection_delay_value(self):
        """REFLECTION_DELAY should be 4 cycles."""
        assert REFLECTION_DELAY == 4
