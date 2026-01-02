"""
HRDA Module (Harmonic Reflection & Derivation Algorithm)
=========================================================

Processes biometric signals with Ra-symbolic weighting for consent derivation.
Implements RADEL smoothing and extended signal channels.

Reference: SPIRAL-Architecture.md Section 6 (Biometric Signal Processing)
Version: 2.2.0-RaCanonical
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Optional

from rpp.ra_constants import (
    RADEL_ALPHA,
    PHI,
    PHI_THRESHOLD_4BIT,
    ATTENTIVE_THRESHOLD_4BIT,
    DIMINISHED_THRESHOLD_4BIT,
)


# =============================================================================
# HRDA Weight Constants
# =============================================================================

# Biometric signal weights per Ra-Codex harmonic field principles
WEIGHT_HRV: Final[float] = 0.50      # Heart Rate Variability (primary)
WEIGHT_EEG: Final[float] = 0.30      # Brainwave coherence
WEIGHT_BREATH: Final[float] = 0.20   # Respiration phase-lock

# Extended signal weights
WEIGHT_VERBAL: Final[float] = 0.15   # Verbal signal contribution
WEIGHT_SYMBOLIC: Final[float] = 0.10 # Symbolic activation contribution


# =============================================================================
# HRDA Signals Dataclass
# =============================================================================

@dataclass
class HRDASignals:
    """
    Complete HRDA signal structure.

    Core signals (required):
        somatic_coherence: 4 bits (0-15) - Overall body-aligned consent
        phase_entropy_index: 5 bits (0-31) - Phase disorder measure
        complecount_trace: 3 bits (0-7) - Completion stage

    Extended signals (optional):
        verbal_signal_strength: 2 bits (0-3) - Verbal consent strength
        symbolic_activation: 3 bits (0-7) - Symbolic/ritual engagement
        emotional_valence: 4 bits (0-15) - Emotional state (-7 to +7, biased)
        intentional_vector: 8 bits (0-255) - Directional intent
        temporal_continuity: 2 bits (0-3) - Session continuity
        integrity_hash: 4 bits (0-15) - Signal integrity check
    """

    # Core signals (required)
    somatic_coherence: int = 0          # 4 bits (0-15)
    phase_entropy_index: int = 0        # 5 bits (0-31)
    complecount_trace: int = 0          # 3 bits (0-7)

    # Extended signals (optional, default to neutral)
    verbal_signal_strength: int = 0     # 2 bits (0-3)
    symbolic_activation: int = 0        # 3 bits (0-7)
    emotional_valence: int = 8          # 4 bits (0-15), 8 = neutral
    intentional_vector: int = 0         # 8 bits (0-255)
    temporal_continuity: int = 0        # 2 bits (0-3)
    integrity_hash: int = 0             # 4 bits (0-15)

    def __post_init__(self):
        """Validate signal ranges."""
        self._clamp_values()

    def _clamp_values(self):
        """Clamp all values to valid ranges."""
        self.somatic_coherence = max(0, min(15, self.somatic_coherence))
        self.phase_entropy_index = max(0, min(31, self.phase_entropy_index))
        self.complecount_trace = max(0, min(7, self.complecount_trace))
        self.verbal_signal_strength = max(0, min(3, self.verbal_signal_strength))
        self.symbolic_activation = max(0, min(7, self.symbolic_activation))
        self.emotional_valence = max(0, min(15, self.emotional_valence))
        self.intentional_vector = max(0, min(255, self.intentional_vector))
        self.temporal_continuity = max(0, min(3, self.temporal_continuity))
        self.integrity_hash = max(0, min(15, self.integrity_hash))

    def to_bytes(self) -> bytes:
        """
        Pack all signals into 5 bytes.

        Layout:
            Byte 0: [7:4] somatic_coherence, [3:0] verbal + temporal
            Byte 1: [7:3] phase_entropy_index, [2:0] complecount_trace
            Byte 2: [7:5] symbolic_activation, [4:1] emotional_valence, [0] reserved
            Byte 3: intentional_vector (8 bits)
            Byte 4: [7:4] integrity_hash, [3:0] reserved
        """
        byte0 = ((self.somatic_coherence & 0x0F) << 4) | \
                ((self.verbal_signal_strength & 0x03) << 2) | \
                (self.temporal_continuity & 0x03)

        byte1 = ((self.phase_entropy_index & 0x1F) << 3) | \
                (self.complecount_trace & 0x07)

        byte2 = ((self.symbolic_activation & 0x07) << 5) | \
                ((self.emotional_valence & 0x0F) << 1)

        byte3 = self.intentional_vector & 0xFF

        byte4 = (self.integrity_hash & 0x0F) << 4

        return bytes([byte0, byte1, byte2, byte3, byte4])

    @classmethod
    def from_bytes(cls, data: bytes) -> HRDASignals:
        """Unpack signals from 5 bytes."""
        if len(data) < 5:
            raise ValueError(f"Expected 5 bytes, got {len(data)}")

        somatic_coherence = (data[0] >> 4) & 0x0F
        verbal_signal_strength = (data[0] >> 2) & 0x03
        temporal_continuity = data[0] & 0x03

        phase_entropy_index = (data[1] >> 3) & 0x1F
        complecount_trace = data[1] & 0x07

        symbolic_activation = (data[2] >> 5) & 0x07
        emotional_valence = (data[2] >> 1) & 0x0F

        intentional_vector = data[3]

        integrity_hash = (data[4] >> 4) & 0x0F

        return cls(
            somatic_coherence=somatic_coherence,
            phase_entropy_index=phase_entropy_index,
            complecount_trace=complecount_trace,
            verbal_signal_strength=verbal_signal_strength,
            symbolic_activation=symbolic_activation,
            emotional_valence=emotional_valence,
            intentional_vector=intentional_vector,
            temporal_continuity=temporal_continuity,
            integrity_hash=integrity_hash,
        )

    def compute_integrity(self) -> int:
        """
        Compute integrity hash from signal values.

        Uses simple XOR-based hash for quick validation.
        """
        combined = (
            self.somatic_coherence ^
            self.phase_entropy_index ^
            self.complecount_trace ^
            self.verbal_signal_strength ^
            self.symbolic_activation ^
            self.emotional_valence ^
            (self.intentional_vector & 0x0F) ^
            ((self.intentional_vector >> 4) & 0x0F) ^
            self.temporal_continuity
        )
        return combined & 0x0F

    def validate_integrity(self) -> bool:
        """Check if integrity hash matches computed value."""
        return self.integrity_hash == self.compute_integrity()

    @property
    def emotional_signed(self) -> int:
        """Get emotional valence as signed value (-7 to +7)."""
        return self.emotional_valence - 8

    @emotional_signed.setter
    def emotional_signed(self, value: int):
        """Set emotional valence from signed value (-7 to +7)."""
        self.emotional_valence = max(0, min(15, value + 8))


# =============================================================================
# RADEL Smoother
# =============================================================================

class RADELSmoother:
    """
    RADEL exponential smoothing for signal transitions.

    Uses α = 1/e ≈ 0.368 for smoothing coefficient.
    Provides hysteresis and jitter reduction.
    """

    def __init__(self, alpha: float = RADEL_ALPHA):
        """
        Initialize smoother.

        Args:
            alpha: Smoothing coefficient (default: 1/e ≈ 0.368)
        """
        self._alpha = alpha
        self._smoothed_value: float = 0.0
        self._initialized: bool = False

    @property
    def alpha(self) -> float:
        """Get smoothing coefficient."""
        return self._alpha

    @property
    def value(self) -> float:
        """Get current smoothed value."""
        return self._smoothed_value

    def reset(self, initial_value: float = 0.0):
        """Reset smoother to initial value."""
        self._smoothed_value = initial_value
        self._initialized = True

    def smooth(self, raw_value: float) -> float:
        """
        Apply RADEL exponential smoothing.

        Formula: smoothed = α × raw + (1 - α) × previous

        Args:
            raw_value: New raw input value

        Returns:
            Smoothed value
        """
        if not self._initialized:
            self._smoothed_value = raw_value
            self._initialized = True
        else:
            self._smoothed_value = (
                self._alpha * raw_value +
                (1 - self._alpha) * self._smoothed_value
            )
        return self._smoothed_value

    def smooth_int(self, raw_value: int, max_value: int = 15) -> int:
        """
        Apply smoothing and return integer result.

        Args:
            raw_value: Raw integer input
            max_value: Maximum output value

        Returns:
            Smoothed integer value
        """
        normalized = raw_value / max_value
        smoothed = self.smooth(normalized)
        return int(smoothed * max_value)


# =============================================================================
# HRDA Processor
# =============================================================================

class HRDAProcessor:
    """
    Harmonic Reflection & Derivation Algorithm processor.

    Processes biometric signals with Ra-symbolic weighting
    and RADEL smoothing.
    """

    def __init__(self):
        """Initialize HRDA processor with smoothers."""
        self._hrv_smoother = RADELSmoother()
        self._eeg_smoother = RADELSmoother()
        self._breath_smoother = RADELSmoother()
        self._somatic_smoother = RADELSmoother()

    def compute_somatic_coherence(
        self,
        hrv: float,
        eeg: float,
        breath: float,
        apply_smoothing: bool = True,
    ) -> int:
        """
        Compute 4-bit somatic coherence from biometric inputs.

        Uses weighted composition:
            HRV: 50%, EEG: 30%, Breath: 20%

        Args:
            hrv: Heart rate variability (0.0-1.0)
            eeg: Brainwave coherence (0.0-1.0)
            breath: Respiration phase-lock (0.0-1.0)
            apply_smoothing: Whether to apply RADEL smoothing

        Returns:
            Somatic coherence (0-15)
        """
        # Clamp inputs
        hrv = max(0.0, min(1.0, hrv))
        eeg = max(0.0, min(1.0, eeg))
        breath = max(0.0, min(1.0, breath))

        # Apply individual smoothing
        if apply_smoothing:
            hrv = self._hrv_smoother.smooth(hrv)
            eeg = self._eeg_smoother.smooth(eeg)
            breath = self._breath_smoother.smooth(breath)

        # Weighted composition
        raw = (
            WEIGHT_HRV * hrv +
            WEIGHT_EEG * eeg +
            WEIGHT_BREATH * breath
        )

        # Apply final smoothing
        if apply_smoothing:
            raw = self._somatic_smoother.smooth(raw)

        # Scale to 4-bit (0-15)
        return int(raw * 15)

    def compute_phase_entropy(
        self,
        signal_variance: float,
        temporal_jitter: float,
    ) -> int:
        """
        Compute phase entropy index from signal characteristics.

        Higher entropy indicates more disorder/uncertainty.

        Args:
            signal_variance: Variance in signals (0.0-1.0)
            temporal_jitter: Timing irregularity (0.0-1.0)

        Returns:
            Phase entropy index (0-31)
        """
        variance = max(0.0, min(1.0, signal_variance))
        jitter = max(0.0, min(1.0, temporal_jitter))

        # Combine with φ-based weighting
        phi_weight = PHI - 1  # 0.618
        entropy = phi_weight * variance + (1 - phi_weight) * jitter

        return int(entropy * 31)

    def process_signals(
        self,
        hrv: float,
        eeg: float,
        breath: float,
        verbal: int = 0,
        symbolic: int = 0,
        emotional: int = 8,
        signal_variance: float = 0.0,
        temporal_jitter: float = 0.0,
    ) -> HRDASignals:
        """
        Process all biometric inputs into HRDA signals.

        Args:
            hrv: Heart rate variability (0.0-1.0)
            eeg: Brainwave coherence (0.0-1.0)
            breath: Respiration phase-lock (0.0-1.0)
            verbal: Verbal signal strength (0-3)
            symbolic: Symbolic activation (0-7)
            emotional: Emotional valence (0-15, 8=neutral)
            signal_variance: Signal variance for entropy (0.0-1.0)
            temporal_jitter: Temporal jitter for entropy (0.0-1.0)

        Returns:
            HRDASignals with all computed values
        """
        somatic = self.compute_somatic_coherence(hrv, eeg, breath)
        entropy = self.compute_phase_entropy(signal_variance, temporal_jitter)

        signals = HRDASignals(
            somatic_coherence=somatic,
            phase_entropy_index=entropy,
            complecount_trace=0,  # Set externally based on coherence
            verbal_signal_strength=verbal,
            symbolic_activation=symbolic,
            emotional_valence=emotional,
        )

        # Compute integrity hash
        signals.integrity_hash = signals.compute_integrity()

        return signals

    def reset(self):
        """Reset all smoothers."""
        self._hrv_smoother.reset()
        self._eeg_smoother.reset()
        self._breath_smoother.reset()
        self._somatic_smoother.reset()


# =============================================================================
# Convenience Functions
# =============================================================================

def create_signals(
    somatic: int,
    verbal: int = 0,
    entropy: int = 0,
    complecount: int = 0,
) -> HRDASignals:
    """
    Create HRDASignals with common values.

    Args:
        somatic: Somatic coherence (0-15)
        verbal: Verbal signal strength (0-3)
        entropy: Phase entropy index (0-31)
        complecount: Completion trace (0-7)

    Returns:
        HRDASignals instance
    """
    signals = HRDASignals(
        somatic_coherence=somatic,
        phase_entropy_index=entropy,
        complecount_trace=complecount,
        verbal_signal_strength=verbal,
    )
    signals.integrity_hash = signals.compute_integrity()
    return signals


def signals_to_consent_inputs(signals: HRDASignals) -> tuple[int, int]:
    """
    Extract consent derivation inputs from HRDA signals.

    Returns:
        (consent_somatic_4bit, verbal_signal_strength)
    """
    return (signals.somatic_coherence, signals.verbal_signal_strength)
