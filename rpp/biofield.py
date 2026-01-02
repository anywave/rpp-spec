"""
Biofield Module
===============

Layer 7: Avataree-Avachatter phase-locked resonance binding.

Uses alpha-inverse (137) as binding threshold coefficient.
Implements dephasing logic with KHAT-delay recovery.

Reference: SPIRAL-Architecture.md Section 7 (Biofield Layer)
Version: 2.2.0-RaCanonical
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional
from datetime import datetime, timezone

from rpp.ra_constants import (
    MAX_COHERENCE,
    BINDING_THRESHOLD,
    KHAT_DURATION,
    ALPHA_INVERSE,
    PHI,
)


# =============================================================================
# Binding Status
# =============================================================================

class BindingStatus(IntEnum):
    """Status of biofield binding."""
    UNBOUND = 0       # No binding established
    BINDING = 1       # Binding in progress
    BOUND = 2         # Fully bound (coherence >= 137)
    DEPHASING = 3     # Lost coherence, within KHAT window
    DEPHASED = 4      # Fully dephased, requires re-binding


# =============================================================================
# Binding Event
# =============================================================================

@dataclass
class BindingEvent:
    """Record of a binding state transition."""

    timestamp: datetime
    """When the event occurred."""

    from_status: BindingStatus
    """Previous binding status."""

    to_status: BindingStatus
    """New binding status."""

    coherence: int
    """Coherence score at time of event."""

    reason: str
    """Description of why transition occurred."""


# =============================================================================
# Biofield Binding
# =============================================================================

class BiofieldBinding:
    """
    Layer 7: Avataree-Avachatter phase-locked resonance.

    The biofield represents the energetic coupling between
    the verified human (Avataree) and their digital twin (Avachatter).

    Binding requires coherence score >= 137 (alpha-inverse threshold).
    This represents approximately 20.3% of maximum coherence.

    When coherence drops below threshold, the system enters
    dephasing mode with a KHAT-duration (12 cycle) grace period
    before full dephase occurs.
    """

    def __init__(self, initial_coherence: int = 0):
        """
        Initialize biofield binding.

        Args:
            initial_coherence: Starting coherence score (0-674)
        """
        self._coherence: int = max(0, min(MAX_COHERENCE, initial_coherence))
        self._status: BindingStatus = BindingStatus.UNBOUND
        self._dephased_cycles: int = 0
        self._binding_cycles: int = 0
        self._events: list[BindingEvent] = []
        self._last_update: Optional[datetime] = None

        # Initialize status based on coherence
        self._update_status()

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def coherence(self) -> int:
        """Get current coherence score (0-674)."""
        return self._coherence

    @property
    def binding_coefficient(self) -> float:
        """
        Calculate binding coefficient.

        kappa_bind = coherence / MAX_COHERENCE

        Returns:
            Binding coefficient (0.0-1.0)
        """
        return self._coherence / MAX_COHERENCE

    @property
    def is_bound(self) -> bool:
        """
        Check if binding is established.

        Binding requires coefficient >= 0.203 (137/674).

        Returns:
            True if coherence meets binding threshold
        """
        return self.binding_coefficient >= BINDING_THRESHOLD

    @property
    def status(self) -> BindingStatus:
        """Get current binding status."""
        return self._status

    @property
    def dephased_cycles(self) -> int:
        """Get number of cycles in dephased state."""
        return self._dephased_cycles

    @property
    def binding_cycles(self) -> int:
        """Get number of cycles in binding state."""
        return self._binding_cycles

    @property
    def is_recoverable(self) -> bool:
        """
        Check if dephased state is still within recovery window.

        KHAT-duration (12 cycles) defines the grace period.

        Returns:
            True if within KHAT recovery window
        """
        if self._status == BindingStatus.DEPHASED:
            return False  # Fully dephased, no longer recoverable
        if self._status != BindingStatus.DEPHASING:
            return True
        return self._dephased_cycles <= KHAT_DURATION

    @property
    def recovery_cycles_remaining(self) -> int:
        """Get cycles remaining before full dephase."""
        if self._status != BindingStatus.DEPHASING:
            return KHAT_DURATION
        return max(0, KHAT_DURATION - self._dephased_cycles)

    @property
    def events(self) -> list[BindingEvent]:
        """Get history of binding events."""
        return self._events.copy()

    # -------------------------------------------------------------------------
    # Coherence Updates
    # -------------------------------------------------------------------------

    def update_coherence(self, coherence: int) -> BindingStatus:
        """
        Update coherence score and recalculate binding status.

        Args:
            coherence: New coherence score (0-674)

        Returns:
            Current binding status
        """
        self._coherence = max(0, min(MAX_COHERENCE, coherence))
        self._last_update = datetime.now(timezone.utc)
        self._update_status()
        return self._status

    def _update_status(self):
        """Recalculate binding status based on coherence."""
        old_status = self._status

        if self.is_bound:
            if self._status in (BindingStatus.UNBOUND, BindingStatus.BINDING):
                self._status = BindingStatus.BOUND
                self._dephased_cycles = 0
            elif self._status == BindingStatus.DEPHASING:
                # Recovery during dephase window
                self._status = BindingStatus.BOUND
                self._dephased_cycles = 0
            elif self._status == BindingStatus.DEPHASED:
                # Re-binding after full dephase
                self._status = BindingStatus.BINDING
                self._binding_cycles = 0
        else:
            if self._status == BindingStatus.BOUND:
                # Start dephasing
                self._status = BindingStatus.DEPHASING
                self._dephased_cycles = 0
            elif self._status == BindingStatus.DEPHASING:
                # Continue dephasing (handled in tick)
                pass
            elif self._status == BindingStatus.BINDING:
                # Failed binding attempt
                self._status = BindingStatus.UNBOUND
                self._binding_cycles = 0

        if old_status != self._status:
            self._record_event(old_status, self._status)

    def _record_event(self, from_status: BindingStatus, to_status: BindingStatus):
        """Record a binding state transition."""
        reasons = {
            (BindingStatus.UNBOUND, BindingStatus.BOUND):
                f"Binding established (coherence={self._coherence})",
            (BindingStatus.UNBOUND, BindingStatus.BINDING):
                f"Binding initiated (coherence={self._coherence})",
            (BindingStatus.BINDING, BindingStatus.BOUND):
                f"Binding completed (coherence={self._coherence})",
            (BindingStatus.BINDING, BindingStatus.UNBOUND):
                f"Binding failed (coherence={self._coherence})",
            (BindingStatus.BOUND, BindingStatus.DEPHASING):
                f"Dephasing started (coherence={self._coherence})",
            (BindingStatus.DEPHASING, BindingStatus.BOUND):
                f"Recovered from dephase (coherence={self._coherence})",
            (BindingStatus.DEPHASING, BindingStatus.DEPHASED):
                f"Full dephase after {KHAT_DURATION} cycles",
            (BindingStatus.DEPHASED, BindingStatus.BINDING):
                f"Re-binding initiated (coherence={self._coherence})",
        }

        reason = reasons.get(
            (from_status, to_status),
            f"Status changed from {from_status.name} to {to_status.name}"
        )

        self._events.append(BindingEvent(
            timestamp=datetime.now(timezone.utc),
            from_status=from_status,
            to_status=to_status,
            coherence=self._coherence,
            reason=reason,
        ))

    # -------------------------------------------------------------------------
    # Cycle Processing
    # -------------------------------------------------------------------------

    def tick(self) -> bool:
        """
        Advance one cycle.

        Tracks dephasing cycles and triggers full dephase
        when KHAT duration is exceeded.

        Returns:
            True if still within KHAT recovery window
        """
        if self._status == BindingStatus.DEPHASING:
            self._dephased_cycles += 1
            if self._dephased_cycles > KHAT_DURATION:
                old_status = self._status
                self._status = BindingStatus.DEPHASED
                self._record_event(old_status, self._status)
                return False
            return True

        if self._status == BindingStatus.BINDING:
            self._binding_cycles += 1

        return True

    def dephase(self) -> bool:
        """
        Handle fragmentation (offline state).

        Called when coherence drops below threshold.
        Returns True if still within KHAT latency window.

        Returns:
            True if recovery is still possible
        """
        if self._status == BindingStatus.BOUND:
            old_status = self._status
            self._status = BindingStatus.DEPHASING
            self._dephased_cycles = 0
            self._record_event(old_status, self._status)

        return self.is_recoverable

    # -------------------------------------------------------------------------
    # Re-sync / Recovery
    # -------------------------------------------------------------------------

    def attempt_resync(self, coherence: int) -> bool:
        """
        Attempt to re-synchronize binding after dephase.

        Args:
            coherence: New coherence score

        Returns:
            True if resync successful (meets binding threshold)
        """
        self.update_coherence(coherence)
        return self.is_bound

    def force_bind(self):
        """
        Force binding state (for testing/emergency).

        Sets coherence to binding threshold and status to BOUND.
        """
        self._coherence = int(BINDING_THRESHOLD * MAX_COHERENCE) + 1  # 138
        old_status = self._status
        self._status = BindingStatus.BOUND
        self._dephased_cycles = 0
        if old_status != self._status:
            self._record_event(old_status, self._status)

    def force_unbind(self):
        """
        Force unbinding (for testing/emergency).

        Sets coherence to 0 and status to UNBOUND.
        """
        self._coherence = 0
        old_status = self._status
        self._status = BindingStatus.UNBOUND
        self._dephased_cycles = 0
        self._binding_cycles = 0
        if old_status != self._status:
            self._record_event(old_status, self._status)

    def reset(self):
        """Reset all binding state."""
        self._coherence = 0
        self._status = BindingStatus.UNBOUND
        self._dephased_cycles = 0
        self._binding_cycles = 0
        self._events.clear()
        self._last_update = None


# =============================================================================
# Phase Memory Anchor (PMA)
# =============================================================================

@dataclass
class PhaseMemoryAnchor:
    """
    Anchor point for phase memory synchronization.

    PMAs store coherence snapshots that fragments can use
    to re-synchronize after dephase events.
    """

    anchor_id: int
    """Unique anchor identifier."""

    coherence_snapshot: int
    """Coherence score at anchor creation."""

    complecount: int
    """Complecount at anchor creation (0-7)."""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When the anchor was created."""

    valid: bool = True
    """Whether the anchor is still valid."""

    def invalidate(self):
        """Mark anchor as invalid."""
        self.valid = False

    @property
    def age_seconds(self) -> float:
        """Get anchor age in seconds."""
        delta = datetime.now(timezone.utc) - self.created_at
        return delta.total_seconds()


class PhaseMemoryField:
    """
    Collection of phase memory anchors for a fragment.

    The field maintains up to 7 anchors (matching complecount max).
    When new anchors are added beyond capacity, oldest are removed.
    """

    MAX_ANCHORS = 7

    def __init__(self):
        """Initialize phase memory field."""
        self._anchors: list[PhaseMemoryAnchor] = []
        self._next_id: int = 0

    @property
    def anchor_count(self) -> int:
        """Get number of valid anchors."""
        return len([a for a in self._anchors if a.valid])

    @property
    def anchors(self) -> list[PhaseMemoryAnchor]:
        """Get all valid anchors."""
        return [a for a in self._anchors if a.valid]

    def create_anchor(
        self,
        coherence: int,
        complecount: int,
    ) -> PhaseMemoryAnchor:
        """
        Create a new phase memory anchor.

        Args:
            coherence: Current coherence score
            complecount: Current complecount

        Returns:
            The created anchor
        """
        anchor = PhaseMemoryAnchor(
            anchor_id=self._next_id,
            coherence_snapshot=coherence,
            complecount=complecount,
        )
        self._next_id += 1
        self._anchors.append(anchor)

        # Prune if over capacity
        valid_anchors = [a for a in self._anchors if a.valid]
        if len(valid_anchors) > self.MAX_ANCHORS:
            # Invalidate oldest
            valid_anchors[0].invalidate()

        return anchor

    def get_anchor(self, anchor_id: int) -> Optional[PhaseMemoryAnchor]:
        """Get anchor by ID."""
        for anchor in self._anchors:
            if anchor.anchor_id == anchor_id and anchor.valid:
                return anchor
        return None

    def get_best_anchor(self) -> Optional[PhaseMemoryAnchor]:
        """
        Get best anchor for resync (highest coherence).

        Returns:
            Anchor with highest coherence, or None
        """
        valid = self.anchors
        if not valid:
            return None
        return max(valid, key=lambda a: a.coherence_snapshot)

    def invalidate_all(self):
        """Invalidate all anchors."""
        for anchor in self._anchors:
            anchor.invalidate()

    def clear(self):
        """Clear all anchors."""
        self._anchors.clear()
        self._next_id = 0


# =============================================================================
# Convenience Functions
# =============================================================================

def compute_binding_threshold_score() -> int:
    """
    Compute the minimum coherence score for binding.

    Returns:
        Minimum coherence (137) for binding
    """
    return int(BINDING_THRESHOLD * MAX_COHERENCE)


def is_coherence_binding(coherence: int) -> bool:
    """
    Check if coherence score meets binding threshold.

    Args:
        coherence: Coherence score to check

    Returns:
        True if coherence >= 137
    """
    return coherence >= compute_binding_threshold_score()
