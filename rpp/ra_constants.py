"""
Ra Constants Module
====================

Mathematical foundation for SPIRAL protocol addressing and coherence.
All coordinates and thresholds derive from these Ra-symbolic constants.

Reference: SPIRAL-Architecture.md Section 7 (Ra Constants Foundation)
Version: 2.2.0-RaCanonical
"""

from __future__ import annotations

import math
from typing import Final

# =============================================================================
# Core Ra Constants (Raw Values)
# =============================================================================

# Golden Ratio - coherence attractor, entropy modulation
PHI: Final[float] = 1.6180339887498948482
"""Golden Ratio (φ). Governs coherence thresholds and harmonic scaling."""

# Euler's Number - decay/convergence damping
E: Final[float] = 2.718281828459045
"""Euler's number (e). Governs RADEL smoothing and decay patterns."""

# Square Root of 10 - dimensional collapse, fallback timing
SQRT_10: Final[float] = 3.16227766016838
"""Square root of 10 (√10). Governs KHAT timing and dimensional collapse."""

# Fine-Structure Constant Inverse - binding threshold, ETF duration
ALPHA_INVERSE: Final[float] = 137.035999084
"""Fine-structure constant inverse (α⁻¹ ≈ 137). Binding threshold."""

# Ankh - master harmonic, complecount weight
ANKH: Final[float] = 5.08938
"""Ankh constant (𝔄). Master harmonic for coherence completion weight."""


# =============================================================================
# Scaled Constants (Integer Representations)
# =============================================================================

# Scale factor: multiply by 100 and round for integer representation
GREEN_PHI_SCALED: Final[int] = 165
"""GREEN_PHI scaled (φ × 100 ≈ 162, rounded to 165 for digital root symmetry)."""

ANKH_SCALED: Final[int] = 509
"""ANKH scaled (𝔄 × 100 ≈ 509)."""

RADEL_SCALED: Final[int] = 271
"""RADEL scaled (e × 100 ≈ 272, using 271 for harmonic alignment)."""

KHAT_SCALED: Final[int] = 316
"""KHAT scaled (√10 × 100 ≈ 316)."""

ALPHA_INV_SCALED: Final[int] = 137
"""ALPHA_INVERSE scaled (integer portion)."""


# =============================================================================
# Coherence Constants
# =============================================================================

MAX_COHERENCE: Final[int] = 674
"""Maximum coherence score (GREEN_PHI_SCALED + ANKH_SCALED = 165 + 509)."""

BINDING_THRESHOLD: Final[float] = ALPHA_INV_SCALED / MAX_COHERENCE
"""Minimum binding coefficient (137/674 ≈ 0.203). Below this, fragmentation mode."""


# =============================================================================
# Consent State Thresholds (4-bit, 0-15)
# =============================================================================

# φ-based thresholds for 5-state ACSP
PHI_THRESHOLD_4BIT: Final[int] = 10
"""FULL_CONSENT threshold (φ × 16 ≈ 9.89, rounded to 10)."""

ATTENTIVE_THRESHOLD_4BIT: Final[int] = 7
"""ATTENTIVE threshold (early engagement zone)."""

DIMINISHED_THRESHOLD_4BIT: Final[int] = 6
"""DIMINISHED_CONSENT threshold ((1-φ) × 16 ≈ 6.11, rounded to 6)."""

SUSPENDED_THRESHOLD_4BIT: Final[int] = 2
"""SUSPENDED_CONSENT boundary (φ² × 16 ≈ 2.3, rounded to 2)."""


# =============================================================================
# Timing Constants (Cycles)
# =============================================================================

KHAT_DURATION: Final[int] = 12
"""KHAT timing in cycles (316 mod 16 = 12). Fallback gate duration."""

ETF_DURATION: Final[int] = 9
"""ETF timing in cycles (137 mod 16 = 9). Emergency freeze duration."""

DWELL_BASE: Final[int] = 3
"""Base dwell time (ceil(φ²) = ceil(2.618) = 3 cycles)."""

DWELL_FULL: Final[int] = 19
"""FULL_CONSENT dwell time (floor(φ × √α⁻¹) ≈ floor(18.94) = 19 cycles)."""

REFLECTION_DELAY: Final[int] = 4
"""Consent reflection delay (3-4 cycles between detection and reflection)."""


# =============================================================================
# Smoothing Constants
# =============================================================================

RADEL_ALPHA: Final[float] = 1.0 / E
"""RADEL smoothing coefficient (1/e ≈ 0.368)."""


# =============================================================================
# Derived Values
# =============================================================================

PHI_SQUARED: Final[float] = PHI * PHI
"""φ² ≈ 2.618. Used for dwell time calculation."""

ONE_MINUS_PHI: Final[float] = 1.0 - (PHI - 1.0)
"""1 - (φ-1) = 2 - φ ≈ 0.382. Diminished threshold base."""

SQRT_ALPHA_INV: Final[float] = math.sqrt(ALPHA_INVERSE)
"""√α⁻¹ ≈ 11.705. Used for dwell time calculation."""


# =============================================================================
# Digital Root Validation
# =============================================================================

def digital_root(n: int) -> int:
    """
    Compute the digital root of a number.

    The digital root is the recursive sum of digits until single digit.
    Used for harmonic validation of constants.

    Examples:
        digital_root(674) = 6+7+4 = 17 → 1+7 = 8
        digital_root(509) = 5+0+9 = 14 → 1+4 = 5
        digital_root(165) = 1+6+5 = 12 → 1+2 = 3
    """
    if n == 0:
        return 0
    return 1 + (n - 1) % 9


def validate_constant_harmony() -> dict:
    """
    Validate the harmonic relationships between constants.

    Returns dict with validation results for each constant.
    """
    return {
        "MAX_COHERENCE": {
            "value": MAX_COHERENCE,
            "digital_root": digital_root(MAX_COHERENCE),
            "expected_root": 8,  # Infinity/balance
            "valid": digital_root(MAX_COHERENCE) == 8,
        },
        "ANKH_SCALED": {
            "value": ANKH_SCALED,
            "digital_root": digital_root(ANKH_SCALED),
            "expected_root": 5,  # ANKH root
            "valid": digital_root(ANKH_SCALED) == 5,
        },
        "GREEN_PHI_SCALED": {
            "value": GREEN_PHI_SCALED,
            "digital_root": digital_root(GREEN_PHI_SCALED),
            "expected_root": 3,  # Triad symmetry
            "valid": digital_root(GREEN_PHI_SCALED) == 3,
        },
        "KHAT_DURATION": {
            "value": KHAT_DURATION,
            "formula": "316 mod 16",
            "expected": 12,
            "valid": KHAT_SCALED % 16 == KHAT_DURATION,
        },
        "ETF_DURATION": {
            "value": ETF_DURATION,
            "formula": "137 mod 16",
            "expected": 9,
            "valid": ALPHA_INV_SCALED % 16 == ETF_DURATION,
        },
        "BINDING_THRESHOLD": {
            "value": round(BINDING_THRESHOLD, 3),
            "formula": "137/674",
            "expected": 0.203,
            "valid": abs(BINDING_THRESHOLD - 0.203) < 0.001,
        },
    }


# =============================================================================
# Convenience Functions
# =============================================================================

def phi_scale(value: float, bits: int = 4) -> int:
    """
    Scale a 0.0-1.0 value to n-bit integer using φ-based quantization.

    Args:
        value: Input value (0.0 to 1.0)
        bits: Number of bits (default 4 = 0-15)

    Returns:
        Scaled integer value
    """
    max_val = (1 << bits) - 1
    return min(max_val, max(0, int(value * (max_val + 1))))


def inverse_phi_scale(scaled: int, bits: int = 4) -> float:
    """
    Convert n-bit scaled value back to 0.0-1.0.

    Args:
        scaled: Scaled integer value
        bits: Number of bits (default 4 = 0-15)

    Returns:
        Float value (0.0 to 1.0)
    """
    max_val = (1 << bits)
    return scaled / max_val


def is_phi_aligned(value: float, tolerance: float = 0.01) -> bool:
    """
    Check if a value is aligned with φ-based thresholds.

    Args:
        value: Value to check (0.0 to 1.0)
        tolerance: Alignment tolerance

    Returns:
        True if value is near φ, 1-φ, or φ²
    """
    phi_norm = PHI - 1.0  # 0.618
    targets = [phi_norm, 1.0 - phi_norm, phi_norm * phi_norm]
    return any(abs(value - t) < tolerance for t in targets)
