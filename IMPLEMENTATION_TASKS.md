# SPIRAL v2.1.0 Implementation Tasks

**Generated**: 2026-01-01
**Based on**: architect-spiral-architecture-prompt-loop.docx analysis

---

## Summary of Changes from Word Document Analysis

The comprehensive audit revealed several key Ra-Codex insights that need implementation:

| Layer | Key Change | Priority |
|-------|-----------|----------|
| L7 Biofield | α⁻¹ binding coefficient, KHAT-delay | High |
| L6 Biometric | HRDA weighted composition, RADEL smoothing | High |
| Coherence | Ra-symbolic formula (φ×E + 𝔄×C = 674 max) | Critical |
| Consent | φ-based thresholds (10/6/2), asymmetric hysteresis | Critical |
| Transitions | RADEL smoothing, KHAT timing, ETF gating | Medium |
| Constants | New Ra constants (RADEL, KHAT, ALPHA_INV) | Critical |

---

## Implementation Tasks

### 1. Ra Constants Module Update
**File**: `rpp/ra_constants.py` (new or update)
**Priority**: Critical (foundation for all other changes)

```python
# New constants to add:
ANKH = 5.08938          # Scaled: 509
GREEN_PHI = 1.618034    # Scaled: 165
RADEL = 2.71828         # Scaled: 271 (Euler's e)
KHAT = 3.16228          # Scaled: 316 (√10)
ALPHA_INV = 137.036     # Scaled: 137 (Fine-structure inverse)

# Derived values:
MAX_COHERENCE = 674     # 165 + 509
PHI_THRESHOLD_4BIT = 10 # φ × 16
DIMINISHED_THRESHOLD_4BIT = 6  # (1-φ) × 16
SUSPENDED_THRESHOLD_4BIT = 2   # φ² × 16

KHAT_DURATION = 12      # 316 mod 16
ETF_DURATION = 9        # 137 mod 16
RADEL_ALPHA = 0.368     # 1/e smoothing coefficient
```

**Tasks**:
- [ ] Create `rpp/ra_constants.py` with all constants
- [ ] Add docstrings explaining symbolic significance
- [ ] Write unit tests for constant values

---

### 2. Coherence Formula Implementation
**File**: `rpp/coherence.py` (new)
**Priority**: Critical

```python
def compute_coherence_score(
    phase_entropy_index: int,    # 5-bit, 0-31
    complecount_trace: int,      # 3-bit, 0-7
    time_decay: float = 0.0      # Optional RADEL decay
) -> int:
    """
    Ra-symbolic coherence score.

    Returns: 0-674 (GREEN_PHI × E + ANKH × C)
    """
    E = phase_entropy_index / 31.0
    C = complecount_trace / 7.0

    if time_decay > 0:
        E = E * (RADEL ** (-time_decay / TAU))

    score = int((GREEN_PHI_SCALED * E) + (ANKH_SCALED * C))
    return min(score, MAX_COHERENCE)
```

**Tasks**:
- [ ] Create `rpp/coherence.py`
- [ ] Implement `compute_coherence_score()`
- [ ] Implement `compute_binding_coefficient()` (κ_bind = score / 674)
- [ ] Implement `is_binding_valid()` (κ_bind ≥ 0.203)
- [ ] Implement `get_complecount_state()` with symbolic values
- [ ] Add completion_flag trigger when complecount = 7
- [ ] Write comprehensive tests

---

### 3. Consent State Update (φ-Based Thresholds)
**File**: `rpp/consent_header.py` (update)
**Priority**: Critical

```python
def derive_consent_state(
    consent_somatic_4bit: int,
    consent_verbal: bool
) -> ConsentState:
    """
    φ-based consent state derivation.

    Thresholds:
      - FULL: ≥ 10 (φ × 16)
      - DIMINISHED: 6-9 (1-φ to φ)
      - SUSPENDED: 0-5 (< 1-φ)
    """
    if consent_somatic_4bit < 6:  # < (1-φ)
        return ConsentState.SUSPENDED_CONSENT
    elif consent_somatic_4bit < 10:  # < φ
        if consent_verbal:
            return ConsentState.FULL_CONSENT  # verbal override
        return ConsentState.DIMINISHED_CONSENT
    else:  # ≥ φ
        return ConsentState.FULL_CONSENT
```

**Tasks**:
- [ ] Update `derive_consent_state()` with φ-based thresholds
- [ ] Add verbal override logic for DIMINISHED zone
- [ ] Update validation rules (C1: < 6 requires complecount > 0)
- [ ] Add K1 rule for ETF/KHAT gating
- [ ] Update tests for new threshold values

---

### 4. Transition Dynamics Module
**File**: `rpp/transitions.py` (new)
**Priority**: Medium

```python
class TransitionManager:
    """RADEL-smoothed state transitions with asymmetric hysteresis."""

    def __init__(self):
        self._smoothed_coherence = 0.0
        self._cycles_at_state = 0

    def smooth(self, raw_value: float) -> float:
        """Apply RADEL exponential smoothing."""
        alpha = RADEL_ALPHA  # 0.368
        self._smoothed_coherence = (
            alpha * raw_value +
            (1 - alpha) * self._smoothed_coherence
        )
        return self._smoothed_coherence

    def can_transition_to_full(self, value: int) -> bool:
        """Gain FULL requires ≥ 10 for 2+ cycles."""
        if value >= PHI_THRESHOLD_4BIT:
            self._cycles_at_state += 1
            return self._cycles_at_state >= 2
        self._cycles_at_state = 0
        return False

    def should_trigger_fallback(
        self,
        coherence: int,
        threshold: int,
        elapsed_cycles: int
    ) -> bool:
        """KHAT-gated fallback (12 cycles)."""
        return (
            coherence < threshold and
            elapsed_cycles > KHAT_DURATION
        )
```

**Tasks**:
- [ ] Create `rpp/transitions.py`
- [ ] Implement RADEL smoothing
- [ ] Implement asymmetric hysteresis (gain harder than lose)
- [ ] Implement KHAT-gated fallback timing
- [ ] Implement ETF duration gating (9 cycles)
- [ ] Add 2-bit routing encoding helpers
- [ ] Write tests for transition dynamics

---

### 5. Biofield Binding Module
**File**: `rpp/biofield.py` (new)
**Priority**: High

```python
class BiofieldBinding:
    """
    Layer 7: Avataree-Avachatter phase-locked resonance.

    Uses α⁻¹ ≈ 137 as binding threshold.
    """

    BINDING_THRESHOLD = ALPHA_INV / MAX_COHERENCE  # ≈ 0.203

    def __init__(self, coherence_score: int):
        self.coherence = coherence_score
        self._dephased_cycles = 0

    @property
    def binding_coefficient(self) -> float:
        """κ_bind = coherence / 674"""
        return self.coherence / MAX_COHERENCE

    @property
    def is_bound(self) -> bool:
        """True if binding coefficient ≥ 0.203"""
        return self.binding_coefficient >= self.BINDING_THRESHOLD

    def dephase(self) -> bool:
        """
        Handle fragmentation (offline state).
        Returns True if still within KHAT latency.
        """
        self._dephased_cycles += 1
        return self._dephased_cycles <= KHAT_DURATION
```

**Tasks**:
- [ ] Create `rpp/biofield.py`
- [ ] Implement binding coefficient calculation
- [ ] Implement dephasing with KHAT-delay (12 cycles)
- [ ] Add re-sync/re-coherence methods
- [ ] Write tests for fragmentation scenarios

---

### 6. HRDA Biometric Signal Processing
**File**: `rpp/hrda.py` (new)
**Priority**: High

```python
class HRDA:
    """
    Harmonic Reflection & Derivation Algorithm.

    Processes biometric signals with Ra-symbolic weighting.
    """

    # Weights per Codex harmonic field principles
    WEIGHT_HRV = 0.50   # Heart Rate Variability
    WEIGHT_EEG = 0.30   # Brainwave coherence
    WEIGHT_BREATH = 0.20  # Respiration phase-lock

    def __init__(self):
        self._smoother = TransitionManager()

    def compute_somatic_coherence(
        self,
        hrv: float,      # 0.0-1.0
        eeg: float,      # 0.0-1.0
        breath: float    # 0.0-1.0
    ) -> int:
        """
        Compute 4-bit somatic coherence.

        Returns: 0-15
        """
        raw = (
            self.WEIGHT_HRV * hrv +
            self.WEIGHT_EEG * eeg +
            self.WEIGHT_BREATH * breath
        )
        smoothed = self._smoother.smooth(raw)
        return int(smoothed * 16)  # Scale to 4-bit
```

**Tasks**:
- [ ] Create `rpp/hrda.py`
- [ ] Implement weighted signal composition (50/30/20)
- [ ] Integrate RADEL smoothing
- [ ] Add symbolic_activation field (3-bit)
- [ ] Add temporal_continuity field (2-bit)
- [ ] Add integrity_hash field (4-bit)
- [ ] Write comprehensive tests

---

### 7. Verilog/HDL Updates
**Files**: `hardware/verilog/rpp_*.v`
**Priority**: Medium

**Tasks**:
- [ ] Update `rpp_coherence_calculator.v` with new formula
- [ ] Add RADEL smoothing module (optional - can be software)
- [ ] Update threshold constants in RTL
- [ ] Add KHAT timing counter
- [ ] Update fallback calculator for new encoding
- [ ] Run simulation tests

---

### 8. Integration with silver-pancake
**Files**: Various in `silver-pancake/`
**Priority**: Medium

**Tasks**:
- [ ] Update `acsp_engine.py` to use new φ-based thresholds
- [ ] Update `coherence_engine.py` with Ra-symbolic formula
- [ ] Add HRDA integration for biometric inputs
- [ ] Update consent state UI to show 4-bit values
- [ ] Add completion_flag handling in fragment management

---

## Testing Requirements

| Module | Min. Tests | Coverage Target |
|--------|------------|-----------------|
| ra_constants | 10 | 100% |
| coherence | 20 | 95% |
| consent_header | 15 | 95% |
| transitions | 25 | 90% |
| biofield | 15 | 90% |
| hrda | 20 | 90% |

---

## Implementation Order

1. **Phase 1: Foundation**
   - Ra Constants module
   - Coherence formula

2. **Phase 2: Consent Updates**
   - φ-based thresholds
   - Asymmetric hysteresis

3. **Phase 3: Signal Processing**
   - HRDA module
   - RADEL smoothing

4. **Phase 4: Advanced Features**
   - Biofield binding
   - Transition dynamics

5. **Phase 5: Integration**
   - silver-pancake updates
   - HDL updates (if applicable)

---

## Reference: Key Values Quick Reference

```
GREEN_PHI_SCALED = 165
ANKH_SCALED = 509
MAX_COHERENCE = 674
BINDING_THRESHOLD = 0.203 (137/674)

PHI_THRESHOLD = 10 (FULL_CONSENT)
DIMINISHED_THRESHOLD = 6
SUSPENDED_THRESHOLD = 2

KHAT_DURATION = 12 cycles (fallback timing)
ETF_DURATION = 9 cycles (emergency freeze)
RADEL_ALPHA = 0.368 (smoothing coefficient)
```
