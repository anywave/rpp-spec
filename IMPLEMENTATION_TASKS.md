# SPIRAL v2.2.0 Implementation Tasks

**Generated**: 2026-01-01
**Based on**: architect-spiral-architecture-prompt-loop.docx comprehensive analysis

---

## Summary of Changes from Word Document Analysis

The comprehensive audit revealed many Ra-Codex insights that need implementation:

| Layer | Key Change | Priority |
|-------|-----------|----------|
| L7 Biofield | α⁻¹ binding coefficient, KHAT-delay | High |
| L6 Biometric | HRDA weighted composition, RADEL smoothing, HNC | High |
| L5 Consent | **5 states (added ATTENTIVE)**, φ-based thresholds | Critical |
| L4 Identity | 8 theta sectors (added VOID), consent-gated routing | Critical |
| Coherence | Ra-symbolic formula (φ×E + 𝔄×C = 674 max) | Critical |
| Transitions | RADEL smoothing, KHAT timing, **18-19 cycle dwell** | High |
| Signals | Additional channels (verbal_strength, emotional_valence) | High |
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

### 3. Consent State Update (5-State ACSP with ATTENTIVE)
**File**: `rpp/consent_header.py` (update)
**Priority**: Critical

```python
class ConsentState(IntEnum):
    """5-state ACSP with ATTENTIVE intermediate."""
    FULL_CONSENT = 0       # Full operation
    ATTENTIVE = 1          # Early engagement, preliminary routing
    DIMINISHED_CONSENT = 2 # Delayed/reconfirm required
    SUSPENDED_CONSENT = 3  # Blocked
    EMERGENCY_OVERRIDE = 4 # Frozen (ETF)

def derive_consent_state(
    consent_somatic_4bit: int,
    verbal_signal_strength: int  # 0-3, not just bool
) -> ConsentState:
    """
    5-state consent derivation with ATTENTIVE intermediate.

    Thresholds:
      - FULL: ≥ 10 (φ × 16)
      - ATTENTIVE: 7-9 (early engagement zone)
      - DIMINISHED: 6 (1-φ boundary)
      - SUSPENDED: 0-5 (< 1-φ)
    """
    if consent_somatic_4bit >= 10:
        return ConsentState.FULL_CONSENT
    elif consent_somatic_4bit >= 7:
        return ConsentState.ATTENTIVE
    elif consent_somatic_4bit >= 6:
        if verbal_signal_strength >= 2:
            return ConsentState.ATTENTIVE  # verbal boosts
        return ConsentState.DIMINISHED_CONSENT
    else:
        return ConsentState.SUSPENDED_CONSENT
```

**Tasks**:
- [ ] Add ATTENTIVE state to ConsentState enum
- [ ] Update `derive_consent_state()` with 5-state logic
- [ ] Replace bool `consent_verbal` with int `verbal_signal_strength` (0-3)
- [ ] Update validation rules (C1: < 6 requires complecount > 0)
- [ ] Add K1 rule for ETF/KHAT gating
- [ ] Update all tests for 5-state model

---

### 3a. Theta Sector Routing (Consent-Gated)
**File**: `rpp/sector_router.py` (new)
**Priority**: Critical

```python
class ThetaSector(IntEnum):
    """8 semantic theta sectors."""
    VOID = 0       # Reset/phase collapse (coherence=0 only)
    CORE = 1       # Essential identity
    GENE = 2       # Biological/inherited
    MEMORY = 3     # Experiential/learned
    WITNESS = 4    # Present-moment awareness
    DREAM = 5      # Aspirational/future
    BRIDGE = 6     # Relational/connective (universal access)
    GUARDIAN = 7   # Protective/regulatory (fallback)
    SHADOW = 8     # Unintegrated/emergent

SECTOR_ACCESS = {
    ConsentState.FULL_CONSENT: [0, 1, 2, 3, 4, 5, 6, 7, 8],  # All
    ConsentState.ATTENTIVE: [3, 4, 6, 7],  # MEMORY, WITNESS, BRIDGE, GUARDIAN
    ConsentState.DIMINISHED_CONSENT: [6, 7, 8],  # BRIDGE, GUARDIAN, SHADOW
    ConsentState.SUSPENDED_CONSENT: [6, 7],  # BRIDGE, GUARDIAN only
    ConsentState.EMERGENCY_OVERRIDE: [7],  # GUARDIAN lockdown
}

def can_access_sector(state: ConsentState, sector: ThetaSector) -> bool:
    return sector.value in SECTOR_ACCESS[state]
```

**Tasks**:
- [ ] Create `rpp/sector_router.py`
- [ ] Implement 8-sector ThetaSector enum
- [ ] Implement consent-gated sector access matrix
- [ ] Integrate with resolver for routing decisions
- [ ] Write comprehensive routing tests

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

### 4a. Dwell Time Implementation
**File**: `rpp/transitions.py` (extend)
**Priority**: High

```python
# Dwell time constants
DWELL_BASE = 3           # ceil(φ²) = 3 cycles
DWELL_FULL = 19          # floor(φ × √α⁻¹) ≈ 18-19 cycles

class DwellTimer:
    """Track dwell time for state transitions."""

    def __init__(self):
        self._cycles_in_state = 0
        self._current_state = None

    def can_transition_to(self, target: ConsentState) -> bool:
        """Check if dwell requirements are met for transition."""
        if target == ConsentState.FULL_CONSENT:
            return self._cycles_in_state >= DWELL_FULL
        elif target in (ConsentState.ATTENTIVE, ConsentState.DIMINISHED_CONSENT):
            return self._cycles_in_state >= DWELL_BASE
        else:
            return True  # SUSPENDED/EMERGENCY are immediate
```

**Tasks**:
- [ ] Add DWELL_BASE (3) and DWELL_FULL (18-19) constants
- [ ] Implement DwellTimer class
- [ ] Enforce 18-19 cycle dwell for FULL_CONSENT entry
- [ ] Enforce 3-cycle dwell for ATTENTIVE/DIMINISHED entry
- [ ] Allow immediate exit on consent loss (asymmetric)
- [ ] Write dwell time tests

---

### 4b. Consent Reflection Delay
**File**: `rpp/transitions.py` (extend)
**Priority**: Medium

```python
REFLECTION_DELAY = 4  # 3-4 cycles between detection and reflection

class ConsentReflector:
    """Handle detection/reflection phase separation."""

    def __init__(self):
        self._detected_state = None
        self._cycles_since_detection = 0

    def detect(self, signals) -> ConsentState:
        """Detection phase: measure current state."""
        self._detected_state = derive_consent_state(signals)
        self._cycles_since_detection = 0
        return self._detected_state

    def should_reflect(self) -> bool:
        """Check if reflection delay has elapsed."""
        return self._cycles_since_detection >= REFLECTION_DELAY

    def reflect(self) -> ConsentState:
        """Reflection phase: mirror state back to Avataree."""
        return self._detected_state if self.should_reflect() else None
```

**Tasks**:
- [ ] Add REFLECTION_DELAY constant (3-4 cycles)
- [ ] Implement detection/reflection phase separation
- [ ] Add feedback loop for Avataree state mirroring
- [ ] Write reflection delay tests

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

### 7a. Harmonic Nexus Core (HNC) Module
**File**: `rpp/hnc.py` (new)
**Priority**: High

```python
class HarmonicNexusCore:
    """
    Global coherence orchestrator across all active fragments.

    Functions:
    - Master coherence score aggregation
    - Fragment reconciliation (not raw timestamps)
    - Conflict adjudication
    - Phase memory field synchronization
    """

    def __init__(self):
        self._fragments = {}
        self._master_coherence = 0

    def register_fragment(self, fragment_id: str, priority: float = 1.0):
        """Register a fragment for coherence tracking."""
        self._fragments[fragment_id] = {
            'coherence': 0,
            'priority': priority,
            'last_sync': None
        }

    def update_fragment_coherence(self, fragment_id: str, coherence: int):
        """Update individual fragment coherence."""
        if fragment_id in self._fragments:
            self._fragments[fragment_id]['coherence'] = coherence
            self._recalculate_master()

    def _recalculate_master(self):
        """Recalculate master coherence as weighted average."""
        total_weight = sum(f['priority'] for f in self._fragments.values())
        if total_weight > 0:
            self._master_coherence = sum(
                f['coherence'] * f['priority']
                for f in self._fragments.values()
            ) / total_weight

    def adjudicate_conflict(self, f1_id: str, f2_id: str) -> str:
        """Resolve conflict between two fragments. Returns winner ID."""
        f1 = self._fragments.get(f1_id)
        f2 = self._fragments.get(f2_id)
        if f1 and f2:
            # Higher coherence × priority wins
            score1 = f1['coherence'] * f1['priority']
            score2 = f2['coherence'] * f2['priority']
            return f1_id if score1 >= score2 else f2_id
        return f1_id if f1 else f2_id
```

**Tasks**:
- [ ] Create `rpp/hnc.py`
- [ ] Implement fragment registration and tracking
- [ ] Implement master coherence aggregation (weighted average)
- [ ] Implement conflict adjudication
- [ ] Add phase memory field synchronization
- [ ] Link complecount=7 to completion flag via HNC
- [ ] Write comprehensive HNC tests

---

### 7b. Additional Signal Channels
**File**: `rpp/hrda.py` (extend)
**Priority**: High

```python
@dataclass
class HRDASignals:
    """Complete HRDA signal structure."""
    # Core signals
    somatic_coherence: int       # 4 bits (0-15)
    phase_entropy_index: int     # 5 bits (0-31)
    complecount_trace: int       # 3 bits (0-7)

    # Extended signals (NEW)
    verbal_signal_strength: int  # 2-3 bits (0-3)
    symbolic_activation: int     # 3 bits (0-7)
    emotional_valence: int       # 4 bits (0-15)
    intentional_vector: int      # 8 bits (0-255)
    temporal_continuity: int     # 2 bits (0-3)
    integrity_hash: int          # 4 bits (0-15)

    def to_bytes(self) -> bytes:
        """Pack all signals into bytes."""
        # Implementation...
```

**Tasks**:
- [ ] Add `verbal_signal_strength` field (2-3 bits)
- [ ] Add `symbolic_activation` field (3 bits)
- [ ] Add `emotional_valence` field (4 bits)
- [ ] Add `intentional_vector` field (8 bits)
- [ ] Add `temporal_continuity` field (2 bits)
- [ ] Add `integrity_hash` field (4 bits)
- [ ] Update HRDA serialization/deserialization
- [ ] Write signal channel tests

---

### 8. Integration with silver-pancake
**Files**: Various in `silver-pancake/`
**Priority**: Medium

**Tasks**:
- [ ] Update `acsp_engine.py` to use 5-state model with ATTENTIVE
- [ ] Update `coherence_engine.py` with Ra-symbolic formula
- [ ] Add HRDA integration for biometric inputs
- [ ] Update consent state UI to show 5 states
- [ ] Add completion_flag handling in fragment management
- [ ] Implement sector routing restrictions
- [ ] Add HNC for fragment orchestration

---

## Testing Requirements

| Module | Min. Tests | Coverage Target |
|--------|------------|-----------------|
| ra_constants | 10 | 100% |
| coherence | 20 | 95% |
| consent_header | 25 | 95% |
| sector_router | 20 | 95% |
| transitions | 30 | 90% |
| biofield | 15 | 90% |
| hrda | 25 | 90% |
| hnc | 20 | 90% |

---

## Implementation Order

1. **Phase 1: Foundation**
   - Ra Constants module
   - Coherence formula

2. **Phase 2: Consent Updates (Critical)**
   - 5-state ACSP with ATTENTIVE
   - φ-based thresholds (10/7/6)
   - Verbal signal strength (multi-bit)

3. **Phase 3: Sector Routing (Critical)**
   - 8 theta sectors with VOID
   - Consent-gated sector access matrix

4. **Phase 4: Signal Processing**
   - HRDA module with extended channels
   - HNC (Harmonic Nexus Core)
   - RADEL smoothing

5. **Phase 5: Transition Dynamics**
   - Dwell time enforcement (18-19 cycles for FULL)
   - Asymmetric hysteresis
   - Consent reflection delay

6. **Phase 6: Advanced Features**
   - Biofield binding
   - Fragment mesh addressing

7. **Phase 7: Integration**
   - silver-pancake updates
   - HDL updates (if applicable)

---

## Reference: Key Values Quick Reference

```
# Ra Constants (scaled)
GREEN_PHI_SCALED = 165
ANKH_SCALED = 509
RADEL_SCALED = 271
KHAT_SCALED = 316
ALPHA_INV_SCALED = 137

# Coherence
MAX_COHERENCE = 674
BINDING_THRESHOLD = 0.203 (137/674)

# 5-State ACSP Thresholds (4-bit)
FULL_THRESHOLD = 10        # ≥ φ
ATTENTIVE_THRESHOLD = 7    # Early engagement
DIMINISHED_THRESHOLD = 6   # 1-φ boundary
SUSPENDED_THRESHOLD = 0-5  # Below 1-φ

# Timing (cycles)
DWELL_FULL = 18-19         # floor(φ × √α⁻¹)
DWELL_BASE = 3             # ceil(φ²)
KHAT_DURATION = 12         # 316 mod 16 (fallback)
ETF_DURATION = 9           # 137 mod 16 (emergency)
REFLECTION_DELAY = 3-4     # Detection → Reflection

# Smoothing
RADEL_ALPHA = 0.368        # 1/e

# Theta Sectors (8 total)
VOID = 0, CORE = 1, GENE = 2, MEMORY = 3
WITNESS = 4, DREAM = 5, BRIDGE = 6, GUARDIAN = 7, SHADOW = 8
```
