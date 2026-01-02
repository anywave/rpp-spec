"""
Transitions Module
==================

State transition dynamics with RADEL smoothing, dwell timers,
asymmetric hysteresis, and consent reflection.

Reference: SPIRAL-Architecture.md Section 5 (Transition Dynamics)
Version: 2.2.0-RaCanonical
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from rpp.ra_constants import (
    RADEL_ALPHA,
    PHI_THRESHOLD_4BIT,
    ATTENTIVE_THRESHOLD_4BIT,
    DIMINISHED_THRESHOLD_4BIT,
    KHAT_DURATION,
    ETF_DURATION,
    DWELL_BASE,
    DWELL_FULL,
    REFLECTION_DELAY,
)
from rpp.consent_header import ConsentState


# =============================================================================
# Transition Direction
# =============================================================================

class TransitionDirection(IntEnum):
    """Direction of consent state transition."""
    NONE = 0       # No transition
    UPGRADE = 1    # Moving to higher consent (harder)
    DOWNGRADE = 2  # Moving to lower consent (easier)


# =============================================================================
# Dwell Timer
# =============================================================================

class DwellTimer:
    """
    Track dwell time for state transitions.

    Dwell times (from Ra constants):
        - FULL_CONSENT entry: 18-19 cycles (DWELL_FULL)
        - ATTENTIVE/DIMINISHED entry: 3 cycles (DWELL_BASE)
        - SUSPENDED/EMERGENCY: immediate (0 cycles)

    Asymmetric: gaining consent is harder than losing it.
    """

    def __init__(self):
        """Initialize dwell timer."""
        self._current_state: Optional[ConsentState] = None
        self._cycles_in_state: int = 0
        self._target_state: Optional[ConsentState] = None
        self._cycles_at_target: int = 0

    @property
    def current_state(self) -> Optional[ConsentState]:
        """Get current consent state."""
        return self._current_state

    @property
    def cycles_in_state(self) -> int:
        """Get cycles spent in current state."""
        return self._cycles_in_state

    def set_state(self, state: ConsentState):
        """Set current state (resets cycle counter)."""
        if state != self._current_state:
            self._current_state = state
            self._cycles_in_state = 0
            self._target_state = None
            self._cycles_at_target = 0

    def tick(self):
        """Advance one cycle."""
        self._cycles_in_state += 1
        if self._target_state is not None:
            self._cycles_at_target += 1

    def request_transition(self, target: ConsentState) -> bool:
        """
        Request transition to target state.

        Args:
            target: Desired target state

        Returns:
            True if transition is allowed
        """
        if self._current_state is None:
            # First state, allow immediately
            self.set_state(target)
            return True

        if target == self._current_state:
            # Already in target state
            return True

        # Determine transition direction
        direction = self._get_direction(target)

        if direction == TransitionDirection.DOWNGRADE:
            # Downgrade is immediate (asymmetric)
            self.set_state(target)
            return True

        # Upgrade requires dwell time
        required_dwell = self._get_required_dwell(target)

        if self._target_state != target:
            # New target, reset counter
            self._target_state = target
            self._cycles_at_target = 0
            return False

        if self._cycles_at_target >= required_dwell:
            # Dwell requirement met
            self.set_state(target)
            return True

        return False

    def _get_direction(self, target: ConsentState) -> TransitionDirection:
        """Determine transition direction."""
        if self._current_state is None:
            return TransitionDirection.NONE

        # Lower value = higher consent
        if target.value < self._current_state.value:
            return TransitionDirection.UPGRADE
        elif target.value > self._current_state.value:
            return TransitionDirection.DOWNGRADE
        return TransitionDirection.NONE

    def _get_required_dwell(self, target: ConsentState) -> int:
        """Get required dwell time for target state."""
        if target == ConsentState.FULL_CONSENT:
            return DWELL_FULL  # 18-19 cycles
        elif target in (ConsentState.ATTENTIVE, ConsentState.DIMINISHED_CONSENT):
            return DWELL_BASE  # 3 cycles
        else:
            return 0  # Immediate for SUSPENDED/EMERGENCY

    def can_transition_to(self, target: ConsentState) -> bool:
        """
        Check if transition to target is currently allowed.

        Args:
            target: Target state to check

        Returns:
            True if dwell requirements are met
        """
        if self._current_state is None:
            return True

        if target == self._current_state:
            return True

        direction = self._get_direction(target)
        if direction == TransitionDirection.DOWNGRADE:
            return True  # Always immediate

        # Check dwell for upgrade
        if self._target_state != target:
            return False

        required = self._get_required_dwell(target)
        return self._cycles_at_target >= required


# =============================================================================
# Consent Reflector
# =============================================================================

class ConsentReflector:
    """
    Handle detection/reflection phase separation.

    The reflection delay (3-4 cycles) provides time between
    consent detection and reflection back to the Avataree.
    This allows for graceful state transitions and prevents
    thrashing.
    """

    def __init__(self, delay: int = REFLECTION_DELAY):
        """
        Initialize consent reflector.

        Args:
            delay: Cycles between detection and reflection (default: 4)
        """
        self._delay = delay
        self._detected_state: Optional[ConsentState] = None
        self._reflected_state: Optional[ConsentState] = None
        self._cycles_since_detection: int = 0
        self._pending_reflection: bool = False

    @property
    def delay(self) -> int:
        """Get reflection delay in cycles."""
        return self._delay

    @property
    def detected_state(self) -> Optional[ConsentState]:
        """Get most recently detected state."""
        return self._detected_state

    @property
    def reflected_state(self) -> Optional[ConsentState]:
        """Get currently reflected state."""
        return self._reflected_state

    def detect(self, state: ConsentState) -> ConsentState:
        """
        Detection phase: measure current consent state.

        Args:
            state: Detected consent state

        Returns:
            The detected state
        """
        if state != self._detected_state:
            self._detected_state = state
            self._cycles_since_detection = 0
            self._pending_reflection = True
        return state

    def tick(self):
        """Advance one cycle."""
        if self._pending_reflection:
            self._cycles_since_detection += 1

    def should_reflect(self) -> bool:
        """Check if reflection delay has elapsed."""
        return (
            self._pending_reflection and
            self._cycles_since_detection >= self._delay
        )

    def reflect(self) -> Optional[ConsentState]:
        """
        Reflection phase: mirror state back to Avataree.

        Returns:
            Reflected state if delay elapsed, None otherwise
        """
        if self.should_reflect():
            self._reflected_state = self._detected_state
            self._pending_reflection = False
            return self._reflected_state
        return None

    def force_reflect(self) -> ConsentState:
        """
        Force immediate reflection (bypass delay).

        Used for emergency state changes.

        Returns:
            Reflected state
        """
        self._reflected_state = self._detected_state
        self._pending_reflection = False
        self._cycles_since_detection = 0
        return self._reflected_state


# =============================================================================
# Fallback Gate
# =============================================================================

class FallbackGate:
    """
    KHAT-gated fallback timing.

    When coherence drops below threshold, waits KHAT_DURATION (12 cycles)
    before triggering fallback. This prevents spurious fallbacks from
    momentary dips.
    """

    def __init__(self, threshold: int = 137):
        """
        Initialize fallback gate.

        Args:
            threshold: Coherence threshold for fallback (default: 137)
        """
        self._threshold = threshold
        self._below_threshold_cycles: int = 0
        self._fallback_triggered: bool = False

    @property
    def threshold(self) -> int:
        """Get fallback threshold."""
        return self._threshold

    @property
    def cycles_below(self) -> int:
        """Get cycles below threshold."""
        return self._below_threshold_cycles

    @property
    def fallback_triggered(self) -> bool:
        """Check if fallback has been triggered."""
        return self._fallback_triggered

    def update(self, coherence: int) -> bool:
        """
        Update fallback gate with current coherence.

        Args:
            coherence: Current coherence score

        Returns:
            True if fallback should trigger
        """
        if coherence < self._threshold:
            self._below_threshold_cycles += 1
            if self._below_threshold_cycles > KHAT_DURATION:
                self._fallback_triggered = True
                return True
        else:
            self._below_threshold_cycles = 0
            self._fallback_triggered = False

        return False

    def should_fallback(self) -> bool:
        """Check if fallback should be active."""
        return self._fallback_triggered

    def reset(self):
        """Reset fallback gate."""
        self._below_threshold_cycles = 0
        self._fallback_triggered = False


# =============================================================================
# ETF Gate
# =============================================================================

class ETFGate:
    """
    Emergency Temporal Freeze gate.

    ETF triggers after ETF_DURATION (9 cycles) of emergency condition.
    Locks system to GUARDIAN sector only.
    """

    def __init__(self):
        """Initialize ETF gate."""
        self._emergency_cycles: int = 0
        self._etf_active: bool = False

    @property
    def is_active(self) -> bool:
        """Check if ETF is active."""
        return self._etf_active

    @property
    def emergency_cycles(self) -> int:
        """Get cycles in emergency state."""
        return self._emergency_cycles

    def update(self, is_emergency: bool) -> bool:
        """
        Update ETF gate with emergency status.

        Args:
            is_emergency: Whether emergency condition exists

        Returns:
            True if ETF should activate
        """
        if is_emergency:
            self._emergency_cycles += 1
            if self._emergency_cycles >= ETF_DURATION:
                self._etf_active = True
                return True
        else:
            self._emergency_cycles = 0
            self._etf_active = False

        return False

    def activate(self):
        """Force ETF activation."""
        self._etf_active = True

    def deactivate(self):
        """Deactivate ETF."""
        self._etf_active = False
        self._emergency_cycles = 0


# =============================================================================
# Transition Manager
# =============================================================================

class TransitionManager:
    """
    Complete transition management with all dynamics.

    Combines:
    - RADEL smoothing
    - Dwell timing
    - Consent reflection
    - Fallback gating
    - ETF handling
    """

    def __init__(self):
        """Initialize transition manager."""
        self._dwell_timer = DwellTimer()
        self._reflector = ConsentReflector()
        self._fallback_gate = FallbackGate()
        self._etf_gate = ETFGate()
        self._smoothed_somatic: float = 0.0
        self._current_cycle: int = 0

    @property
    def current_state(self) -> Optional[ConsentState]:
        """Get current consent state."""
        return self._dwell_timer.current_state

    @property
    def reflected_state(self) -> Optional[ConsentState]:
        """Get currently reflected state."""
        return self._reflector.reflected_state

    @property
    def cycle(self) -> int:
        """Get current cycle count."""
        return self._current_cycle

    def smooth_somatic(self, raw_somatic: int) -> int:
        """
        Apply RADEL smoothing to somatic value.

        Args:
            raw_somatic: Raw somatic value (0-15)

        Returns:
            Smoothed somatic value (0-15)
        """
        normalized = raw_somatic / 15.0
        self._smoothed_somatic = (
            RADEL_ALPHA * normalized +
            (1 - RADEL_ALPHA) * self._smoothed_somatic
        )
        return int(self._smoothed_somatic * 15)

    def process_cycle(
        self,
        detected_state: ConsentState,
        coherence: int,
        is_emergency: bool = False,
    ) -> dict:
        """
        Process one cycle of transition dynamics.

        Args:
            detected_state: Detected consent state
            coherence: Current coherence score
            is_emergency: Whether emergency condition exists

        Returns:
            Dict with cycle results
        """
        self._current_cycle += 1

        # Update gates
        fallback_trigger = self._fallback_gate.update(coherence)
        etf_trigger = self._etf_gate.update(is_emergency)

        # Override state if ETF active
        if self._etf_gate.is_active:
            detected_state = ConsentState.EMERGENCY_OVERRIDE

        # Detection phase
        self._reflector.detect(detected_state)

        # Request transition
        transition_allowed = self._dwell_timer.request_transition(detected_state)

        # Tick timers
        self._dwell_timer.tick()
        self._reflector.tick()

        # Reflection phase
        reflected = self._reflector.reflect()

        return {
            'cycle': self._current_cycle,
            'detected_state': detected_state,
            'current_state': self._dwell_timer.current_state,
            'reflected_state': reflected,
            'transition_allowed': transition_allowed,
            'fallback_triggered': fallback_trigger,
            'etf_active': self._etf_gate.is_active,
            'dwell_cycles': self._dwell_timer.cycles_in_state,
        }

    def reset(self):
        """Reset all transition state."""
        self._dwell_timer = DwellTimer()
        self._reflector = ConsentReflector()
        self._fallback_gate.reset()
        self._etf_gate.deactivate()
        self._smoothed_somatic = 0.0
        self._current_cycle = 0
