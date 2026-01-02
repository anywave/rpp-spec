"""
Coherence Module
================

Ra-symbolic coherence computation for SPIRAL protocol.
Implements the coherence formula: (φ × E) + (𝔄 × C) = 674 max

Reference: SPIRAL-Architecture.md Section 6 (Coherence Scoring)
Version: 2.2.0-RaCanonical
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Final

from .ra_constants import (
    GREEN_PHI_SCALED,
    ANKH_SCALED,
    MAX_COHERENCE,
    BINDING_THRESHOLD,
    ALPHA_INV_SCALED,
)


# =============================================================================
# Complecount States
# =============================================================================

class ComplecountState(IntEnum):
    """
    Complecount state based on coherence level.

    Values 0-7 represent completion stages:
    - 0: No coherence (fragmented)
    - 1-6: Partial completion stages
    - 7: Full completion (triggers completion flag)
    """
    FRAGMENTED = 0
    EMERGING = 1
    DEVELOPING = 2
    STABILIZING = 3
    CONSOLIDATING = 4
    MATURING = 5
    COHERING = 6
    COMPLETE = 7  # Triggers completion flag


# =============================================================================
# Coherence Result
# =============================================================================

@dataclass(frozen=True)
class CoherenceResult:
    """Result of coherence computation."""

    score: int
    """Raw coherence score (0-674)."""

    binding_coefficient: float
    """Binding coefficient (score / MAX_COHERENCE)."""

    complecount: int
    """Complecount value (0-7)."""

    state: ComplecountState
    """Complecount state enum."""

    is_binding_valid: bool
    """Whether binding coefficient exceeds threshold (0.203)."""

    completion_flag: bool
    """True when complecount reaches 7."""

    engagement_weight: int
    """GREEN_PHI contribution (φ × E component)."""

    completion_weight: int
    """ANKH contribution (𝔄 × C component)."""


# =============================================================================
# Core Computation Functions
# =============================================================================

def compute_coherence_score(
    engagement: float,
    completion: float,
) -> int:
    """
    Compute coherence score using Ra-symbolic formula.

    Formula: coherence = (φ × E) + (𝔄 × C)
    Where:
        φ = GREEN_PHI_SCALED (165)
        E = engagement (0.0 to 1.0)
        𝔄 = ANKH_SCALED (509)
        C = completion (0.0 to 1.0)

    Args:
        engagement: Engagement level (0.0 to 1.0)
        completion: Completion level (0.0 to 1.0)

    Returns:
        Coherence score (0 to 674)
    """
    # Clamp inputs to valid range
    engagement = max(0.0, min(1.0, engagement))
    completion = max(0.0, min(1.0, completion))

    # Ra-symbolic formula
    engagement_component = int(GREEN_PHI_SCALED * engagement)
    completion_component = int(ANKH_SCALED * completion)

    score = engagement_component + completion_component

    # Ensure within bounds
    return min(MAX_COHERENCE, max(0, score))


def compute_binding_coefficient(score: int) -> float:
    """
    Compute binding coefficient from coherence score.

    The binding coefficient determines whether the system
    remains bound or enters fragmentation mode.

    Args:
        score: Coherence score (0-674)

    Returns:
        Binding coefficient (0.0 to 1.0)
    """
    if score <= 0:
        return 0.0
    return min(1.0, score / MAX_COHERENCE)


def is_binding_valid(coefficient: float) -> bool:
    """
    Check if binding coefficient exceeds threshold.

    Threshold is α⁻¹ / MAX_COHERENCE = 137/674 ≈ 0.203
    Below threshold, system enters fragmentation mode.

    Args:
        coefficient: Binding coefficient (0.0 to 1.0)

    Returns:
        True if binding is valid (above threshold)
    """
    return coefficient >= BINDING_THRESHOLD


def compute_complecount(score: int) -> int:
    """
    Compute complecount from coherence score.

    Complecount ranges from 0-7, representing completion stages.
    At complecount=7, the completion flag is triggered.

    Args:
        score: Coherence score (0-674)

    Returns:
        Complecount value (0-7)
    """
    if score <= 0:
        return 0

    # Map score to 0-7 range
    # Each complecount level represents ~96 points of coherence
    # (674 / 7 ≈ 96.3)
    complecount = int((score / MAX_COHERENCE) * 7)

    return min(7, max(0, complecount))


def get_complecount_state(complecount: int) -> ComplecountState:
    """
    Get the complecount state enum from complecount value.

    Args:
        complecount: Complecount value (0-7)

    Returns:
        ComplecountState enum
    """
    complecount = max(0, min(7, complecount))
    return ComplecountState(complecount)


# =============================================================================
# High-Level API
# =============================================================================

def compute_coherence(
    engagement: float,
    completion: float,
) -> CoherenceResult:
    """
    Compute full coherence result with all derived values.

    This is the primary API for coherence computation, returning
    a complete CoherenceResult with score, binding, complecount,
    and completion flag.

    Args:
        engagement: Engagement level (0.0 to 1.0)
        completion: Completion level (0.0 to 1.0)

    Returns:
        CoherenceResult with all computed values

    Example:
        >>> result = compute_coherence(0.8, 0.9)
        >>> result.score
        590
        >>> result.complecount
        6
        >>> result.completion_flag
        False
    """
    # Compute component weights
    engagement_weight = int(GREEN_PHI_SCALED * max(0.0, min(1.0, engagement)))
    completion_weight = int(ANKH_SCALED * max(0.0, min(1.0, completion)))

    # Compute score
    score = compute_coherence_score(engagement, completion)

    # Compute derived values
    coefficient = compute_binding_coefficient(score)
    complecount = compute_complecount(score)
    state = get_complecount_state(complecount)
    binding_valid = is_binding_valid(coefficient)

    # Completion flag triggers at complecount = 7
    completion_flag = (complecount == 7)

    return CoherenceResult(
        score=score,
        binding_coefficient=coefficient,
        complecount=complecount,
        state=state,
        is_binding_valid=binding_valid,
        completion_flag=completion_flag,
        engagement_weight=engagement_weight,
        completion_weight=completion_weight,
    )


# =============================================================================
# Utility Functions
# =============================================================================

def score_to_percentage(score: int) -> float:
    """
    Convert coherence score to percentage.

    Args:
        score: Coherence score (0-674)

    Returns:
        Percentage (0.0 to 100.0)
    """
    return (score / MAX_COHERENCE) * 100.0


def percentage_to_score(percentage: float) -> int:
    """
    Convert percentage to coherence score.

    Args:
        percentage: Percentage (0.0 to 100.0)

    Returns:
        Coherence score (0-674)
    """
    percentage = max(0.0, min(100.0, percentage))
    return int((percentage / 100.0) * MAX_COHERENCE)


def minimum_binding_score() -> int:
    """
    Get the minimum score required for valid binding.

    Returns:
        Minimum coherence score (137)
    """
    return ALPHA_INV_SCALED


def describe_coherence(result: CoherenceResult) -> str:
    """
    Generate a human-readable description of coherence state.

    Args:
        result: CoherenceResult to describe

    Returns:
        Descriptive string
    """
    percentage = score_to_percentage(result.score)

    if result.completion_flag:
        status = "COMPLETE - Full coherence achieved"
    elif result.is_binding_valid:
        status = f"BOUND - {result.state.name} stage"
    else:
        status = "FRAGMENTED - Below binding threshold"

    return (
        f"Coherence: {result.score}/{MAX_COHERENCE} ({percentage:.1f}%)\n"
        f"Status: {status}\n"
        f"Complecount: {result.complecount}/7\n"
        f"Binding: {result.binding_coefficient:.3f} "
        f"(threshold: {BINDING_THRESHOLD:.3f})"
    )
