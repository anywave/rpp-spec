"""
Tests for HRDA Module
=====================

Tests for Harmonic Reflection & Derivation Algorithm.
"""

import pytest

from rpp.hrda import (
    WEIGHT_HRV,
    WEIGHT_EEG,
    WEIGHT_BREATH,
    HRDASignals,
    RADELSmoother,
    HRDAProcessor,
    create_signals,
    signals_to_consent_inputs,
)
from rpp.ra_constants import RADEL_ALPHA


# =============================================================================
# Test HRDA Weights
# =============================================================================

class TestHRDAWeights:
    """Tests for HRDA weight constants."""

    def test_weights_sum_to_one(self):
        """Biometric weights should sum to 1.0."""
        total = WEIGHT_HRV + WEIGHT_EEG + WEIGHT_BREATH
        assert abs(total - 1.0) < 0.001

    def test_hrv_highest_weight(self):
        """HRV should have highest weight (50%)."""
        assert WEIGHT_HRV == 0.50
        assert WEIGHT_HRV > WEIGHT_EEG
        assert WEIGHT_HRV > WEIGHT_BREATH

    def test_eeg_middle_weight(self):
        """EEG should have middle weight (30%)."""
        assert WEIGHT_EEG == 0.30

    def test_breath_lowest_weight(self):
        """Breath should have lowest weight (20%)."""
        assert WEIGHT_BREATH == 0.20


# =============================================================================
# Test HRDASignals
# =============================================================================

class TestHRDASignals:
    """Tests for HRDASignals dataclass."""

    def test_default_values(self):
        """Default signals should be neutral."""
        signals = HRDASignals()
        assert signals.somatic_coherence == 0
        assert signals.phase_entropy_index == 0
        assert signals.complecount_trace == 0
        assert signals.emotional_valence == 8  # Neutral

    def test_value_clamping(self):
        """Values should be clamped to valid ranges."""
        signals = HRDASignals(
            somatic_coherence=20,  # Max 15
            phase_entropy_index=50,  # Max 31
            complecount_trace=10,  # Max 7
            verbal_signal_strength=5,  # Max 3
        )
        assert signals.somatic_coherence == 15
        assert signals.phase_entropy_index == 31
        assert signals.complecount_trace == 7
        assert signals.verbal_signal_strength == 3

    def test_negative_clamping(self):
        """Negative values should clamp to 0."""
        signals = HRDASignals(
            somatic_coherence=-5,
            phase_entropy_index=-10,
        )
        assert signals.somatic_coherence == 0
        assert signals.phase_entropy_index == 0

    def test_encode_decode_roundtrip(self):
        """Encoding then decoding should preserve values."""
        original = HRDASignals(
            somatic_coherence=12,
            phase_entropy_index=25,
            complecount_trace=5,
            verbal_signal_strength=2,
            symbolic_activation=4,
            emotional_valence=10,
            intentional_vector=200,
            temporal_continuity=2,
            integrity_hash=7,
        )
        encoded = original.to_bytes()
        decoded = HRDASignals.from_bytes(encoded)

        assert decoded.somatic_coherence == original.somatic_coherence
        assert decoded.phase_entropy_index == original.phase_entropy_index
        assert decoded.complecount_trace == original.complecount_trace
        assert decoded.verbal_signal_strength == original.verbal_signal_strength
        assert decoded.symbolic_activation == original.symbolic_activation
        assert decoded.emotional_valence == original.emotional_valence
        assert decoded.intentional_vector == original.intentional_vector
        assert decoded.temporal_continuity == original.temporal_continuity
        assert decoded.integrity_hash == original.integrity_hash

    def test_byte_length(self):
        """Encoded signals should be exactly 5 bytes."""
        signals = HRDASignals()
        assert len(signals.to_bytes()) == 5

    def test_integrity_hash(self):
        """Integrity hash should validate correctly."""
        signals = HRDASignals(somatic_coherence=10, verbal_signal_strength=2)
        signals.integrity_hash = signals.compute_integrity()
        assert signals.validate_integrity()

    def test_integrity_mismatch(self):
        """Modified signals should fail integrity check."""
        signals = HRDASignals(somatic_coherence=10)
        signals.integrity_hash = signals.compute_integrity()
        signals.somatic_coherence = 5  # Modify after hash
        assert not signals.validate_integrity()

    def test_emotional_signed_property(self):
        """Emotional valence should convert to/from signed."""
        signals = HRDASignals()

        signals.emotional_valence = 8  # Neutral
        assert signals.emotional_signed == 0

        signals.emotional_valence = 15  # Max positive
        assert signals.emotional_signed == 7

        signals.emotional_valence = 0  # Max negative
        assert signals.emotional_signed == -8

    def test_emotional_signed_setter(self):
        """Setting signed emotional should update valence."""
        signals = HRDASignals()

        signals.emotional_signed = 0
        assert signals.emotional_valence == 8

        signals.emotional_signed = 5
        assert signals.emotional_valence == 13


# =============================================================================
# Test RADELSmoother
# =============================================================================

class TestRADELSmoother:
    """Tests for RADEL exponential smoothing."""

    def test_default_alpha(self):
        """Default alpha should be RADEL_ALPHA (1/e)."""
        smoother = RADELSmoother()
        assert abs(smoother.alpha - RADEL_ALPHA) < 0.001

    def test_first_value_passthrough(self):
        """First value should pass through unchanged."""
        smoother = RADELSmoother()
        result = smoother.smooth(0.8)
        assert result == 0.8

    def test_smoothing_effect(self):
        """Subsequent values should be smoothed."""
        smoother = RADELSmoother()
        smoother.smooth(0.0)  # Initialize at 0
        result = smoother.smooth(1.0)  # Jump to 1
        # Should be between 0 and 1, closer to previous
        assert 0.3 < result < 0.5  # ~0.368

    def test_smooth_int(self):
        """Integer smoothing should work correctly."""
        smoother = RADELSmoother()
        smoother.reset(0.5)
        result = smoother.smooth_int(15, max_value=15)
        assert 7 <= result <= 15

    def test_reset(self):
        """Reset should clear smoothing history."""
        smoother = RADELSmoother()
        smoother.smooth(0.5)
        smoother.reset(1.0)
        assert smoother.value == 1.0


# =============================================================================
# Test HRDAProcessor
# =============================================================================

class TestHRDAProcessor:
    """Tests for HRDA signal processor."""

    def test_compute_somatic_coherence(self):
        """Somatic coherence should be weighted sum."""
        processor = HRDAProcessor()
        # All at 1.0 should give 15
        result = processor.compute_somatic_coherence(
            hrv=1.0, eeg=1.0, breath=1.0,
            apply_smoothing=False,
        )
        assert result == 15

    def test_compute_somatic_zero(self):
        """Zero inputs should give zero coherence."""
        processor = HRDAProcessor()
        result = processor.compute_somatic_coherence(
            hrv=0.0, eeg=0.0, breath=0.0,
            apply_smoothing=False,
        )
        assert result == 0

    def test_compute_somatic_weighted(self):
        """Result should reflect HRV weight dominance."""
        processor = HRDAProcessor()
        # Only HRV at 1.0, others at 0
        result = processor.compute_somatic_coherence(
            hrv=1.0, eeg=0.0, breath=0.0,
            apply_smoothing=False,
        )
        expected = int(WEIGHT_HRV * 15)  # 7
        assert result == expected

    def test_compute_phase_entropy(self):
        """Phase entropy should combine variance and jitter."""
        processor = HRDAProcessor()
        # High variance and jitter
        result = processor.compute_phase_entropy(1.0, 1.0)
        assert result == 31  # Max entropy

        # Low variance and jitter
        result = processor.compute_phase_entropy(0.0, 0.0)
        assert result == 0

    def test_process_signals(self):
        """Process signals should return complete HRDASignals."""
        processor = HRDAProcessor()
        signals = processor.process_signals(
            hrv=0.8,
            eeg=0.7,
            breath=0.6,
            verbal=2,
            symbolic=3,
        )
        assert isinstance(signals, HRDASignals)
        assert signals.verbal_signal_strength == 2
        assert signals.symbolic_activation == 3
        assert signals.validate_integrity()


# =============================================================================
# Test Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_signals(self):
        """create_signals should create valid signals."""
        signals = create_signals(somatic=10, verbal=2)
        assert signals.somatic_coherence == 10
        assert signals.verbal_signal_strength == 2
        assert signals.validate_integrity()

    def test_signals_to_consent_inputs(self):
        """Should extract consent inputs from signals."""
        signals = HRDASignals(somatic_coherence=12, verbal_signal_strength=3)
        somatic, verbal = signals_to_consent_inputs(signals)
        assert somatic == 12
        assert verbal == 3
