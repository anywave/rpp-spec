"""
HNC Module (Harmonic Nexus Core)
=================================

Global coherence orchestrator across all active fragments.
Handles master coherence aggregation, conflict adjudication,
and phase memory synchronization.

Reference: SPIRAL-Architecture.md Section 6 (Harmonic Nexus Core)
Version: 2.2.0-RaCanonical
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone

from rpp.ra_constants import (
    MAX_COHERENCE,
    BINDING_THRESHOLD,
    PHI,
)
from rpp.coherence import (
    compute_coherence,
    CoherenceResult,
    ComplecountState,
)


# =============================================================================
# Fragment State
# =============================================================================

class FragmentStatus(IntEnum):
    """Status of a registered fragment."""
    ACTIVE = 0       # Fully operational
    IDLE = 1         # Connected but inactive
    SYNCING = 2      # Synchronizing state
    DEPHASED = 3     # Lost coherence, attempting recovery
    OFFLINE = 4      # Disconnected


@dataclass
class FragmentState:
    """State tracking for a single fragment."""

    fragment_id: str
    """Unique identifier for the fragment."""

    coherence: int = 0
    """Current coherence score (0-674)."""

    priority: float = 1.0
    """Priority weight for conflict resolution (0.0-2.0)."""

    status: FragmentStatus = FragmentStatus.IDLE
    """Current fragment status."""

    complecount: int = 0
    """Current complecount (0-7)."""

    last_sync: Optional[datetime] = None
    """Last synchronization timestamp."""

    phase_memory_ref: int = 0
    """Reference to phase memory anchor (PMA)."""

    def __post_init__(self):
        """Validate and clamp values."""
        self.coherence = max(0, min(MAX_COHERENCE, self.coherence))
        self.priority = max(0.0, min(2.0, self.priority))
        self.complecount = max(0, min(7, self.complecount))

    @property
    def weighted_score(self) -> float:
        """Get priority-weighted coherence score."""
        return self.coherence * self.priority

    @property
    def is_bound(self) -> bool:
        """Check if fragment is above binding threshold."""
        coefficient = self.coherence / MAX_COHERENCE
        return coefficient >= BINDING_THRESHOLD

    @property
    def is_complete(self) -> bool:
        """Check if fragment has reached completion (complecount=7)."""
        return self.complecount == 7


# =============================================================================
# Conflict Resolution
# =============================================================================

@dataclass
class ConflictResult:
    """Result of conflict adjudication between fragments."""

    winner_id: str
    """ID of winning fragment."""

    loser_id: str
    """ID of losing fragment."""

    winner_score: float
    """Winning weighted score."""

    loser_score: float
    """Losing weighted score."""

    reason: str
    """Explanation for resolution."""

    @property
    def margin(self) -> float:
        """Score margin between winner and loser."""
        return self.winner_score - self.loser_score


# =============================================================================
# Harmonic Nexus Core
# =============================================================================

class HarmonicNexusCore:
    """
    Global coherence orchestrator across all active fragments.

    Functions:
    - Master coherence score aggregation
    - Fragment registration and tracking
    - Conflict adjudication (not raw timestamps)
    - Phase memory field synchronization
    - Completion flag propagation
    """

    def __init__(self):
        """Initialize the Harmonic Nexus Core."""
        self._fragments: Dict[str, FragmentState] = {}
        self._master_coherence: float = 0.0
        self._master_complecount: int = 0
        self._completion_flag: bool = False
        self._sync_generation: int = 0

    # -------------------------------------------------------------------------
    # Fragment Registration
    # -------------------------------------------------------------------------

    def register_fragment(
        self,
        fragment_id: str,
        priority: float = 1.0,
        initial_coherence: int = 0,
    ) -> FragmentState:
        """
        Register a new fragment for coherence tracking.

        Args:
            fragment_id: Unique identifier for the fragment
            priority: Priority weight (0.0-2.0, default 1.0)
            initial_coherence: Initial coherence score

        Returns:
            FragmentState for the registered fragment
        """
        state = FragmentState(
            fragment_id=fragment_id,
            priority=priority,
            coherence=initial_coherence,
            status=FragmentStatus.ACTIVE,
            last_sync=datetime.now(timezone.utc),
        )
        self._fragments[fragment_id] = state
        self._recalculate_master()
        return state

    def unregister_fragment(self, fragment_id: str) -> bool:
        """
        Unregister a fragment.

        Args:
            fragment_id: Fragment to unregister

        Returns:
            True if fragment was removed
        """
        if fragment_id in self._fragments:
            del self._fragments[fragment_id]
            self._recalculate_master()
            return True
        return False

    def get_fragment(self, fragment_id: str) -> Optional[FragmentState]:
        """Get fragment state by ID."""
        return self._fragments.get(fragment_id)

    @property
    def fragment_count(self) -> int:
        """Get number of registered fragments."""
        return len(self._fragments)

    @property
    def active_fragments(self) -> List[FragmentState]:
        """Get all active fragments."""
        return [
            f for f in self._fragments.values()
            if f.status == FragmentStatus.ACTIVE
        ]

    # -------------------------------------------------------------------------
    # Coherence Updates
    # -------------------------------------------------------------------------

    def update_fragment_coherence(
        self,
        fragment_id: str,
        coherence: int,
        complecount: int = 0,
    ) -> bool:
        """
        Update coherence for a specific fragment.

        Args:
            fragment_id: Fragment to update
            coherence: New coherence score (0-674)
            complecount: New complecount (0-7)

        Returns:
            True if update successful
        """
        if fragment_id not in self._fragments:
            return False

        fragment = self._fragments[fragment_id]
        fragment.coherence = max(0, min(MAX_COHERENCE, coherence))
        fragment.complecount = max(0, min(7, complecount))
        fragment.last_sync = datetime.now(timezone.utc)

        # Update status based on coherence
        if fragment.is_bound:
            fragment.status = FragmentStatus.ACTIVE
        else:
            fragment.status = FragmentStatus.DEPHASED

        self._recalculate_master()
        return True

    def set_fragment_status(
        self,
        fragment_id: str,
        status: FragmentStatus,
    ) -> bool:
        """Set fragment status."""
        if fragment_id not in self._fragments:
            return False
        self._fragments[fragment_id].status = status
        return True

    # -------------------------------------------------------------------------
    # Master Coherence
    # -------------------------------------------------------------------------

    def _recalculate_master(self):
        """Recalculate master coherence as weighted average."""
        active = self.active_fragments
        if not active:
            self._master_coherence = 0.0
            self._master_complecount = 0
            self._completion_flag = False
            return

        total_weight = sum(f.priority for f in active)
        if total_weight > 0:
            self._master_coherence = sum(
                f.coherence * f.priority for f in active
            ) / total_weight

            # Master complecount is minimum of all active fragments
            self._master_complecount = min(f.complecount for f in active)

            # Completion flag: all fragments at complecount=7
            self._completion_flag = all(f.is_complete for f in active)
        else:
            self._master_coherence = 0.0
            self._master_complecount = 0
            self._completion_flag = False

        self._sync_generation += 1

    @property
    def master_coherence(self) -> float:
        """Get master coherence (weighted average)."""
        return self._master_coherence

    @property
    def master_coherence_int(self) -> int:
        """Get master coherence as integer."""
        return int(self._master_coherence)

    @property
    def master_complecount(self) -> int:
        """Get master complecount (minimum across fragments)."""
        return self._master_complecount

    @property
    def completion_flag(self) -> bool:
        """Get completion flag (True when all fragments complete)."""
        return self._completion_flag

    @property
    def is_bound(self) -> bool:
        """Check if master coherence is above binding threshold."""
        coefficient = self._master_coherence / MAX_COHERENCE
        return coefficient >= BINDING_THRESHOLD

    @property
    def sync_generation(self) -> int:
        """Get current sync generation counter."""
        return self._sync_generation

    # -------------------------------------------------------------------------
    # Conflict Adjudication
    # -------------------------------------------------------------------------

    def adjudicate_conflict(
        self,
        fragment1_id: str,
        fragment2_id: str,
    ) -> Optional[ConflictResult]:
        """
        Resolve conflict between two fragments.

        Uses weighted coherence score (coherence × priority).
        Higher score wins.

        Args:
            fragment1_id: First fragment ID
            fragment2_id: Second fragment ID

        Returns:
            ConflictResult or None if fragments not found
        """
        f1 = self._fragments.get(fragment1_id)
        f2 = self._fragments.get(fragment2_id)

        if not f1 or not f2:
            return None

        score1 = f1.weighted_score
        score2 = f2.weighted_score

        if score1 >= score2:
            return ConflictResult(
                winner_id=fragment1_id,
                loser_id=fragment2_id,
                winner_score=score1,
                loser_score=score2,
                reason=f"Higher weighted coherence ({score1:.1f} vs {score2:.1f})",
            )
        else:
            return ConflictResult(
                winner_id=fragment2_id,
                loser_id=fragment1_id,
                winner_score=score2,
                loser_score=score1,
                reason=f"Higher weighted coherence ({score2:.1f} vs {score1:.1f})",
            )

    def find_conflicts(self) -> List[tuple[str, str]]:
        """
        Find potential conflicts (fragments with same priority competing).

        Returns:
            List of (fragment1_id, fragment2_id) tuples
        """
        conflicts = []
        fragments = list(self._fragments.values())

        for i, f1 in enumerate(fragments):
            for f2 in fragments[i + 1:]:
                # Conflict if priorities are similar but coherence differs significantly
                if abs(f1.priority - f2.priority) < 0.1:
                    coherence_diff = abs(f1.coherence - f2.coherence)
                    if coherence_diff > MAX_COHERENCE * 0.2:  # >20% difference
                        conflicts.append((f1.fragment_id, f2.fragment_id))

        return conflicts

    # -------------------------------------------------------------------------
    # Phase Memory Synchronization
    # -------------------------------------------------------------------------

    def sync_phase_memory(
        self,
        fragment_id: str,
        phase_memory_ref: int,
    ) -> bool:
        """
        Update phase memory reference for a fragment.

        Args:
            fragment_id: Fragment to update
            phase_memory_ref: New PMA reference

        Returns:
            True if successful
        """
        if fragment_id not in self._fragments:
            return False

        self._fragments[fragment_id].phase_memory_ref = phase_memory_ref
        self._fragments[fragment_id].status = FragmentStatus.SYNCING
        return True

    def complete_sync(self, fragment_id: str) -> bool:
        """
        Mark fragment sync as complete.

        Args:
            fragment_id: Fragment that completed sync

        Returns:
            True if successful
        """
        if fragment_id not in self._fragments:
            return False

        fragment = self._fragments[fragment_id]
        fragment.status = FragmentStatus.ACTIVE
        fragment.last_sync = datetime.now(timezone.utc)
        return True

    # -------------------------------------------------------------------------
    # Aggregate Operations
    # -------------------------------------------------------------------------

    def get_coherence_summary(self) -> dict:
        """Get summary of coherence across all fragments."""
        active = self.active_fragments
        if not active:
            return {
                'fragment_count': 0,
                'master_coherence': 0,
                'master_complecount': 0,
                'completion_flag': False,
                'is_bound': False,
                'fragments': [],
            }

        return {
            'fragment_count': len(active),
            'master_coherence': self.master_coherence_int,
            'master_complecount': self._master_complecount,
            'completion_flag': self._completion_flag,
            'is_bound': self.is_bound,
            'sync_generation': self._sync_generation,
            'fragments': [
                {
                    'id': f.fragment_id,
                    'coherence': f.coherence,
                    'complecount': f.complecount,
                    'priority': f.priority,
                    'status': f.status.name,
                    'is_bound': f.is_bound,
                }
                for f in active
            ],
        }

    def propagate_completion(self) -> Set[str]:
        """
        Propagate completion flag to all fragments when master reaches 7.

        Returns:
            Set of fragment IDs that were updated
        """
        if not self._completion_flag:
            return set()

        updated = set()
        for fragment in self._fragments.values():
            if fragment.complecount < 7:
                fragment.complecount = 7
                updated.add(fragment.fragment_id)

        return updated


# =============================================================================
# Convenience Functions
# =============================================================================

def create_hnc_with_fragments(
    fragment_ids: List[str],
    initial_coherence: int = 0,
) -> HarmonicNexusCore:
    """
    Create HNC with pre-registered fragments.

    Args:
        fragment_ids: List of fragment IDs to register
        initial_coherence: Initial coherence for all fragments

    Returns:
        Configured HarmonicNexusCore
    """
    hnc = HarmonicNexusCore()
    for fid in fragment_ids:
        hnc.register_fragment(fid, initial_coherence=initial_coherence)
    return hnc
