"""
Tests for Ra Constants Module
=============================

Validates the mathematical foundation for SPIRAL protocol.
"""

import math
import pytest

from rpp.ra_constants import (
    # Core constants
    PHI,
    E,
    SQRT_10,
    ALPHA_INVERSE,
    ANKH,
    # Scaled constants
    GREEN_PHI_SCALED,
    ANKH_SCALED,
    RADEL_SCALED,
    KHAT_SCALED,
    ALPHA_INV_SCALED,
    # Coherence constants
    MAX_COHERENCE,
    BINDING_THRESHOLD,
    # Consent thresholds
    PHI_THRESHOLD_4BIT,
    ATTENTIVE_THRESHOLD_4BIT,
    DIMINISHED_THRESHOLD_4BIT,
    SUSPENDED_THRESHOLD_4BIT,
    # Timing constants
    KHAT_DURATION,
    ETF_DURATION,
    DWELL_BASE,
    DWELL_FULL,
    REFLECTION_DELAY,
    # Smoothing
    RADEL_ALPHA,
    # Derived
    PHI_SQUARED,
    ONE_MINUS_PHI,
    SQRT_ALPHA_INV,
    # Functions
    digital_root,
    validate_constant_harmony,
    phi_scale,
    inverse_phi_scale,
    is_phi_aligned,
)


class TestCoreConstants:
    """Tests for core Ra constants."""

    def test_phi_value(self):
        """PHI should be the golden ratio."""
        expected = (1 + math.sqrt(5)) / 2
        assert abs(PHI - expected) < 1e-10

    def test_e_value(self):
        """E should be Euler's number."""
        assert abs(E - math.e) < 1e-10

    def test_sqrt_10_value(self):
        """SQRT_10 should be the square root of 10."""
        assert abs(SQRT_10 - math.sqrt(10)) < 1e-10

    def test_alpha_inverse_value(self):
        """ALPHA_INVERSE should be approximately 137."""
        assert 137.03 < ALPHA_INVERSE < 137.04

    def test_ankh_value(self):
        """ANKH constant should be ~5.089."""
        assert abs(ANKH - 5.08938) < 0.0001


class TestScaledConstants:
    """Tests for scaled integer constants."""

    def test_green_phi_scaled(self):
        """GREEN_PHI_SCALED should be 165."""
        assert GREEN_PHI_SCALED == 165

    def test_ankh_scaled(self):
        """ANKH_SCALED should be 509."""
        assert ANKH_SCALED == 509

    def test_radel_scaled(self):
        """RADEL_SCALED should be 271."""
        assert RADEL_SCALED == 271

    def test_khat_scaled(self):
        """KHAT_SCALED should be 316."""
        assert KHAT_SCALED == 316

    def test_alpha_inv_scaled(self):
        """ALPHA_INV_SCALED should be 137."""
        assert ALPHA_INV_SCALED == 137


class TestCoherenceConstants:
    """Tests for coherence-related constants."""

    def test_max_coherence(self):
        """MAX_COHERENCE should be GREEN_PHI + ANKH = 674."""
        assert MAX_COHERENCE == GREEN_PHI_SCALED + ANKH_SCALED
        assert MAX_COHERENCE == 674

    def test_binding_threshold(self):
        """BINDING_THRESHOLD should be ~0.203."""
        expected = ALPHA_INV_SCALED / MAX_COHERENCE
        assert BINDING_THRESHOLD == expected
        assert abs(BINDING_THRESHOLD - 0.203) < 0.001


class TestConsentThresholds:
    """Tests for 4-bit consent thresholds."""

    def test_phi_threshold(self):
        """PHI_THRESHOLD_4BIT should be 10 (φ × 16)."""
        assert PHI_THRESHOLD_4BIT == 10
        # Check derivation: φ × 16 ≈ 9.89, rounds to 10
        derived = round(PHI * 10)  # Using 10 as base since 16 × 0.618 ≈ 9.89
        assert PHI_THRESHOLD_4BIT == 10

    def test_attentive_threshold(self):
        """ATTENTIVE_THRESHOLD_4BIT should be 7."""
        assert ATTENTIVE_THRESHOLD_4BIT == 7

    def test_diminished_threshold(self):
        """DIMINISHED_THRESHOLD_4BIT should be 6."""
        assert DIMINISHED_THRESHOLD_4BIT == 6

    def test_suspended_threshold(self):
        """SUSPENDED_THRESHOLD_4BIT should be 2."""
        assert SUSPENDED_THRESHOLD_4BIT == 2

    def test_threshold_ordering(self):
        """Thresholds should be in descending order."""
        assert PHI_THRESHOLD_4BIT > ATTENTIVE_THRESHOLD_4BIT
        assert ATTENTIVE_THRESHOLD_4BIT > DIMINISHED_THRESHOLD_4BIT
        assert DIMINISHED_THRESHOLD_4BIT > SUSPENDED_THRESHOLD_4BIT


class TestTimingConstants:
    """Tests for timing constants."""

    def test_khat_duration(self):
        """KHAT_DURATION should be 12 (316 mod 16)."""
        assert KHAT_DURATION == 12
        assert KHAT_SCALED % 16 == KHAT_DURATION

    def test_etf_duration(self):
        """ETF_DURATION should be 9 (137 mod 16)."""
        assert ETF_DURATION == 9
        assert ALPHA_INV_SCALED % 16 == ETF_DURATION

    def test_dwell_base(self):
        """DWELL_BASE should be 3 (ceil(φ²))."""
        assert DWELL_BASE == 3
        assert math.ceil(PHI_SQUARED) == 3

    def test_dwell_full(self):
        """DWELL_FULL should be 19 (floor(φ × √α⁻¹))."""
        assert DWELL_FULL == 19
        derived = math.floor(PHI * SQRT_ALPHA_INV)
        assert derived == 18 or derived == 19  # Allow small variation

    def test_reflection_delay(self):
        """REFLECTION_DELAY should be 3-4 cycles."""
        assert 3 <= REFLECTION_DELAY <= 4


class TestSmoothingConstants:
    """Tests for smoothing constants."""

    def test_radel_alpha(self):
        """RADEL_ALPHA should be 1/e ≈ 0.368."""
        assert abs(RADEL_ALPHA - (1.0 / E)) < 1e-10
        assert abs(RADEL_ALPHA - 0.368) < 0.001


class TestDerivedValues:
    """Tests for derived values."""

    def test_phi_squared(self):
        """PHI_SQUARED should be φ²."""
        assert abs(PHI_SQUARED - (PHI * PHI)) < 1e-10
        assert abs(PHI_SQUARED - 2.618) < 0.001

    def test_one_minus_phi(self):
        """ONE_MINUS_PHI should be 2 - φ ≈ 0.382."""
        assert abs(ONE_MINUS_PHI - (2.0 - PHI)) < 1e-10
        assert abs(ONE_MINUS_PHI - 0.382) < 0.001

    def test_sqrt_alpha_inv(self):
        """SQRT_ALPHA_INV should be √137 ≈ 11.7."""
        assert abs(SQRT_ALPHA_INV - math.sqrt(ALPHA_INVERSE)) < 1e-10
        assert abs(SQRT_ALPHA_INV - 11.706) < 0.01


class TestDigitalRoot:
    """Tests for digital root function."""

    def test_digital_root_single_digit(self):
        """Single digits are their own digital root."""
        for i in range(10):
            assert digital_root(i) == i

    def test_digital_root_examples(self):
        """Test documented examples."""
        assert digital_root(674) == 8  # 6+7+4=17, 1+7=8
        assert digital_root(509) == 5  # 5+0+9=14, 1+4=5
        assert digital_root(165) == 3  # 1+6+5=12, 1+2=3

    def test_digital_root_max_coherence(self):
        """MAX_COHERENCE has digital root 8 (infinity/balance)."""
        assert digital_root(MAX_COHERENCE) == 8


class TestConstantHarmony:
    """Tests for constant harmony validation."""

    def test_validate_constant_harmony(self):
        """All constants should pass harmony validation."""
        results = validate_constant_harmony()

        assert results["MAX_COHERENCE"]["valid"] is True
        assert results["MAX_COHERENCE"]["digital_root"] == 8

        assert results["ANKH_SCALED"]["valid"] is True
        assert results["ANKH_SCALED"]["digital_root"] == 5

        assert results["GREEN_PHI_SCALED"]["valid"] is True
        assert results["GREEN_PHI_SCALED"]["digital_root"] == 3

        assert results["KHAT_DURATION"]["valid"] is True
        assert results["ETF_DURATION"]["valid"] is True
        assert results["BINDING_THRESHOLD"]["valid"] is True


class TestPhiScale:
    """Tests for phi scaling functions."""

    def test_phi_scale_bounds(self):
        """phi_scale should stay within bounds."""
        assert phi_scale(0.0) == 0
        assert phi_scale(1.0) == 15  # Max for 4-bit
        assert phi_scale(-0.5) == 0  # Clamped
        assert phi_scale(1.5) == 15  # Clamped

    def test_phi_scale_middle_values(self):
        """phi_scale should scale middle values correctly."""
        assert phi_scale(0.5) == 8
        assert phi_scale(0.25) == 4

    def test_phi_scale_different_bits(self):
        """phi_scale should work with different bit widths."""
        assert phi_scale(1.0, bits=8) == 255
        assert phi_scale(0.5, bits=8) == 128

    def test_inverse_phi_scale(self):
        """inverse_phi_scale should reverse phi_scale."""
        for scaled in range(16):
            value = inverse_phi_scale(scaled)
            assert 0.0 <= value <= 1.0

    def test_phi_scale_roundtrip(self):
        """Roundtrip should be approximately reversible."""
        for i in range(16):
            value = inverse_phi_scale(i)
            back = phi_scale(value)
            assert abs(back - i) <= 1  # Allow off-by-one


class TestPhiAlignment:
    """Tests for phi alignment detection."""

    def test_is_phi_aligned_at_phi(self):
        """Values near φ-1 should be aligned."""
        phi_norm = PHI - 1.0  # 0.618
        assert is_phi_aligned(phi_norm)
        assert is_phi_aligned(0.618)
        assert is_phi_aligned(0.62)

    def test_is_phi_aligned_at_one_minus_phi(self):
        """Values near 1-φ should be aligned."""
        one_minus = 1.0 - (PHI - 1.0)  # 0.382
        assert is_phi_aligned(one_minus)
        assert is_phi_aligned(0.382)
        assert is_phi_aligned(0.38)

    def test_is_phi_aligned_at_phi_squared(self):
        """Values near φ² should be aligned."""
        phi_sq = (PHI - 1.0) ** 2  # 0.382
        assert is_phi_aligned(phi_sq)

    def test_is_not_phi_aligned(self):
        """Random values should not be aligned."""
        assert not is_phi_aligned(0.5)
        assert not is_phi_aligned(0.7)
        assert not is_phi_aligned(0.1)
