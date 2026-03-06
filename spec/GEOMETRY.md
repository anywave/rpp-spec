# RPP Geometry — Toroidal State Vector & Rotational Encryption

**Version:** 1.0.0
**Status:** Active — Geometric / Payload Layer
**Last Updated:** 2026-03-04
**License:** CC BY 4.0

---

## 1. Overview

The RPP address is not a flat identifier. It is a **coordinate in toroidal space**. The
Theta, Phi, Shell, and Harmonic fields are not arbitrary bit-fields — they parameterize a
point on a 4-dimensional torus. The state_vector that lives at those coordinates is not a
flat byte array — it is a **geometric object** that inherits the topology of the space it
inhabits.

This document defines:
1. The toroidal coordinate mapping of RPP addresses
2. The Toroidal State Vector (TSV) — the double-helix payload format
3. Rotational memory — how the helix traces history as angular displacement
4. Self-observation — how the state verifies its own coherence geometrically
5. Rotational encryption — the pong mechanism, where trajectory IS the cipher

---

## 2. The Torus — RPP Address as Coordinates

### 2.1 Parameterization

A torus T² is defined by two radii and two angular parameters:

```
Major radius R  — distance from the axis of symmetry to the tube center
Minor radius r  — radius of the tube itself
θ (theta)       — azimuthal angle: position around the outer ring (0 to 2π)
φ (phi)         — poloidal angle: position within the tube cross-section (0 to 2π)
```

The 3D embedding:
```
x = (R + r·cos φ) · cos θ
y = (R + r·cos φ) · sin θ
z = r · sin φ
```

### 2.2 RPP Field Mapping

| RPP Field | Bits | Torus Role | Mapping |
|-----------|------|-----------|---------|
| Shell | 2 | Major radius R | `R = shell / 3.0` → R ∈ {0.0, 0.33, 0.67, 1.0} |
| Harmonic | 8 | Minor radius r | `r = harmonic / 255.0` → r ∈ [0.0, 1.0] |
| Theta | 9 | Azimuthal angle θ | `θ = (theta / 511.0) × 2π` → θ ∈ [0, 2π) |
| Phi | 9 | Poloidal angle φ | `φ = (phi / 511.0) × 2π` → φ ∈ [0, 2π) |

```python
import math

def rpp_to_torus(shell: int, theta: int, phi: int, harmonic: int) -> tuple:
    """Convert RPP address fields to torus coordinates (x, y, z)."""
    R = shell / 3.0
    r = harmonic / 255.0
    t = (theta / 511.0) * 2 * math.pi   # azimuthal
    p = (phi   / 511.0) * 2 * math.pi   # poloidal

    x = (R + r * math.cos(p)) * math.cos(t)
    y = (R + r * math.cos(p)) * math.sin(t)
    z = r * math.sin(p)

    return (x, y, z, t, p)  # 3D point + angular coordinates
```

**The RPP address IS a point on the torus.** When consent changes (Phi shifts), the point
moves within the tube. When data type changes (Theta shifts), the point rotates around the
outer ring. When storage tier changes (Shell shifts), the point moves to a different ring.

---

## 3. The Toroidal State Vector (TSV)

### 3.1 Concept

The state_vector in the CSP is not opaque bytes — it is a **sequence of angular positions**
on the torus surface, tracing the history and structure of the cognitive state.

A TSV is a double helix on the torus:

```
Primary strand P:    sequence of (θ_i, φ_i, A_i) — state at each moment i
Observation strand O: sequence of (θ_i + π, φ_i + π, A_i) — antipodal reflection of P

Together: a double helix winding around the torus.
The pitch of the helix = HarmonicMode (how fast it winds).
The axis = the torus itself.
```

### 3.2 Format

```python
from dataclasses import dataclass, field
from typing import NamedTuple
import math

class TorusPoint(NamedTuple):
    """A point on the torus surface."""
    theta: float    # azimuthal angle [0, 2π)
    phi: float      # poloidal angle [0, 2π)
    amplitude: float # signal strength at this point [0.0, 1.0]

@dataclass
class ToroidalStateVector:
    """
    The geometric payload format for RPP consciousness routing.

    Not a flat byte array — a double helix tracing a path on the torus.
    The path IS the memory. The complement IS the self-observation.
    """

    # ── Origin ────────────────────────────────────────────────────────
    origin: TorusPoint          # Angular position when this state was created
                                # Self-observation checks drift from this point

    # ── Primary Strand (the state) ────────────────────────────────────
    primary: list[TorusPoint]   # Sequence of angular positions — rotational memory
                                # Each entry = one unit of cognitive state
                                # Ordered: primary[0] = oldest, primary[-1] = current

    # ── Observation Strand (self-verification) ────────────────────────
    observation: list[TorusPoint]  # Antipodal complement of primary
                                   # observation[i] = antipodal(primary[i])
                                   # If primary drifts, complement no longer matches

    # ── Angular Velocity ─────────────────────────────────────────────
    omega_theta: float          # Rate of rotation around the outer ring (rad/step)
    omega_phi: float            # Rate of rotation within the tube (rad/step)

    # ── Encryption State ─────────────────────────────────────────────
    rotation_accumulator: TorusPoint  # Cumulative rotation applied by pong volleys
                                      # (0.0, 0.0) = unencrypted / origin
    volley_count: int = 0             # Number of pong volleys applied

    # ── Metadata ─────────────────────────────────────────────────────
    rpp_address: int = 0        # Source RPP address (28-bit v1.0)
    strand_length: int = 0      # len(primary) == len(observation) always

    def __post_init__(self):
        self.strand_length = len(self.primary)
        assert len(self.primary) == len(self.observation), \
            "Primary and observation strands must have equal length"


def antipodal(p: TorusPoint) -> TorusPoint:
    """The antipodal point on the torus — the complement for the observation strand."""
    return TorusPoint(
        theta=(p.theta + math.pi) % (2 * math.pi),
        phi=(p.phi + math.pi) % (2 * math.pi),
        amplitude=p.amplitude,
    )


def build_tsv(state_sequence: list[float],
              origin: TorusPoint,
              omega_theta: float,
              omega_phi: float) -> ToroidalStateVector:
    """
    Construct a TSV from a sequence of amplitude values.
    The angular positions are derived by rotating from the origin
    at the given angular velocities.
    """
    primary = []
    observation = []

    theta = origin.theta
    phi = origin.phi

    for i, amplitude in enumerate(state_sequence):
        p = TorusPoint(theta % (2 * math.pi),
                       phi % (2 * math.pi),
                       amplitude)
        primary.append(p)
        observation.append(antipodal(p))

        theta += omega_theta
        phi += omega_phi

    return ToroidalStateVector(
        origin=origin,
        primary=primary,
        observation=observation,
        omega_theta=omega_theta,
        omega_phi=omega_phi,
        rotation_accumulator=TorusPoint(0.0, 0.0, 0.0),
        volley_count=0,
    )
```

### 3.3 Rotational Memory

As new cognitive state is appended to the TSV, the angular position advances by
(ω_θ, ω_φ). The history of positions **traces a helix on the torus surface**:

```
Step 0: (θ₀, φ₀)  — origin
Step 1: (θ₀ + ω_θ, φ₀ + ω_φ)
Step 2: (θ₀ + 2ω_θ, φ₀ + 2ω_φ)
...
Step N: (θ₀ + Nω_θ, φ₀ + Nω_φ)
```

The helix pitch is set by the HarmonicMode:

| HarmonicMode | ω_θ (rad/step) | ω_φ (rad/step) | Helix character |
|-------------|----------------|----------------|-----------------|
| ACTIVE | π/64 | π/32 | Tight, fast-winding — dense active memory |
| REFLECTIVE | π/128 | π/64 | Moderate — deliberate processing |
| BACKGROUND | π/256 | π/128 | Loose — slow background integration |
| MEMORY | π/512 | π/256 | Very loose — long-term memory trace |
| ARCHIVAL | 0 | 0 | Static — no rotation, frozen at origin |

**Memory retrieval = tracing the helix backwards.** The angular position at step i
encodes when that memory was formed (distance from origin) and what sector it belongs to
(θ determines Theta sector, φ determines consent tier).

---

## 4. Self-Observation and Coherence Verification

### 4.1 The Complement Invariant

The observation strand is always the antipodal complement of the primary strand:

```
observation[i] = antipodal(primary[i])
               = (primary[i].theta + π, primary[i].phi + π, primary[i].amplitude)
```

This invariant holds at every step. If any external process corrupts primary[i],
the complement invariant breaks — the state detects it without external input.

### 4.2 Self-Observation Check

```python
PHI_GOLDEN = (1 + math.sqrt(5)) / 2   # 1.618... — tolerance scale

def verify_self_coherence(tsv: ToroidalStateVector,
                          tolerance: float = 0.01) -> dict:
    """
    The state observes itself. No external verifier needed.
    Returns dict with coherence score and any anomaly positions.
    """
    anomalies = []
    coherence_sum = 0.0

    for i, (p, o) in enumerate(zip(tsv.primary, tsv.observation)):
        expected_o = antipodal(p)

        delta_theta = abs(o.theta - expected_o.theta)
        delta_phi   = abs(o.phi   - expected_o.phi)

        # Angular distance (modular)
        delta_theta = min(delta_theta, 2 * math.pi - delta_theta)
        delta_phi   = min(delta_phi,   2 * math.pi - delta_phi)

        drift = math.sqrt(delta_theta**2 + delta_phi**2)

        if drift > tolerance * PHI_GOLDEN:
            anomalies.append({
                'step': i,
                'drift_rad': drift,
                'primary': p,
                'expected_observation': expected_o,
                'actual_observation': o,
            })
        else:
            coherence_sum += 1.0 - (drift / (tolerance * PHI_GOLDEN))

    coherence_score = coherence_sum / len(tsv.primary) if tsv.primary else 0.0

    return {
        'coherent': len(anomalies) == 0,
        'coherence_score': coherence_score,   # 0.0 = fully incoherent, 1.0 = perfect
        'anomaly_count': len(anomalies),
        'anomalies': anomalies,
    }
```

### 4.3 Origin Drift Detection

The state also monitors its distance from its angular origin — useful for detecting
whether the state has been "moved" without its knowledge:

```python
def angular_drift_from_origin(tsv: ToroidalStateVector) -> float:
    """
    How far has the state's current tip drifted from its expected position
    given its angular velocity and step count?
    """
    if not tsv.primary:
        return 0.0

    expected_theta = (tsv.origin.theta
                      + len(tsv.primary) * tsv.omega_theta) % (2 * math.pi)
    expected_phi   = (tsv.origin.phi
                      + len(tsv.primary) * tsv.omega_phi) % (2 * math.pi)

    current = tsv.primary[-1]
    dt = abs(current.theta - expected_theta)
    dp = abs(current.phi   - expected_phi)

    dt = min(dt, 2 * math.pi - dt)
    dp = min(dp, 2 * math.pi - dp)

    return math.sqrt(dt**2 + dp**2)
```

### 4.4 Confirmation via Others — External Coherence

In a consent-field mesh, neighboring nodes observe the TSV's angular position as it passes
through. Each node records its observation as a **witness point**:

```python
@dataclass
class WitnessObservation:
    """A neighboring node's observation of a passing TSV."""
    observer_substrate_hash: bytes  # Which node observed (hashed — not exposed)
    observed_theta: float           # What theta this node measured
    observed_phi: float             # What phi this node measured
    observation_timestamp_ns: int   # When the observation occurred
    signature: bytes                # Signed by the observing node

def verify_via_witnesses(tsv: ToroidalStateVector,
                          witnesses: list[WitnessObservation],
                          quorum: int = 3) -> bool:
    """
    Confirm the TSV's angular position via external observation.
    Requires at least `quorum` witnesses to agree within tolerance.
    """
    if len(witnesses) < quorum:
        return False

    current = tsv.primary[-1] if tsv.primary else tsv.origin
    agreements = 0

    for w in witnesses:
        dt = min(abs(w.observed_theta - current.theta),
                 2 * math.pi - abs(w.observed_theta - current.theta))
        dp = min(abs(w.observed_phi - current.phi),
                 2 * math.pi - abs(w.observed_phi - current.phi))

        if math.sqrt(dt**2 + dp**2) < 0.1:   # ~5.7 degree tolerance
            agreements += 1

    return agreements >= quorum
```

**Consensus = coherence.** The state is where the field says it is. No single observer
has authority — quorum does. This is the "confirmation via others" property.

---

## 5. Rotational Encryption — The Pong Mechanism

### 5.1 Concept

Traditional encryption: apply a secret function to the payload. The cipher is the function.

Rotational encryption: rotate the payload's angular position by an amount derived from the
node's live consent field state. The cipher is the **trajectory through the torus**.

```
Plaintext  = TSV at angular position (θ₀, φ₀)
Ciphertext = TSV at angular position (θ₀ + ΣΔθ, φ₀ + ΣΔφ)

Key        = the sequence of rotations applied: [(Δθ₁, Δφ₁), (Δθ₂, Δφ₂), ...]
           = the trajectory
           = derived from ephemeral consent field states at each hop
```

No party stores the key. The key lives only in the consent field states, which are
ephemeral (T2-decohered on spintronics, session-scoped on software).

### 5.2 Key Derivation from Consent Field State

Each node derives its rotation key from its current consent field state:

```python
PHI_GOLDEN = (1 + math.sqrt(5)) / 2

def derive_rotation_key(phi_value: int,
                        theta_value: int,
                        harmonic: int,
                        consent_epoch: int) -> tuple[float, float]:
    """
    Derive a rotation (Δθ, Δφ) from the node's current consent field state.

    Uses PHI (golden ratio) as the multiplier to ensure quasi-random, maximally
    separated rotations for consecutive keys. PHI-based sequences have optimal
    distribution on [0, 1] — no clustering, no repetition.
    """
    # PHI-scaled quasi-random rotation from consent state
    raw_theta = (phi_value * PHI_GOLDEN * consent_epoch) % 512
    raw_phi   = (theta_value * PHI_GOLDEN * consent_epoch) % 512

    # Harmonic modulates the rotation magnitude
    scale = (harmonic / 255.0) * math.pi  # [0, π]

    delta_theta = (raw_theta / 512.0) * scale
    delta_phi   = (raw_phi   / 512.0) * scale

    return (delta_theta, delta_phi)
```

**Properties of this key derivation:**
- Same consent state → same rotation (deterministic for verification)
- Different epoch → completely different rotation (no key reuse across epochs)
- PHI scaling → maximal angular spread, no two keys cluster together
- On spintronics: the consent field state lives in T2-decohering spin states → key is physically erased when T2 expires → **physical forward secrecy**

### 5.3 The Pong Protocol

```
┌───────────────────────────────────────────────────────────────┐
│                    PONG PROTOCOL                              │
│                                                               │
│  Node A ──rot(k_A)──► Node B ──rot(k_B)──► Node A ──...      │
│                                                               │
│  Each volley: apply rotation to TSV angular positions         │
│  Each rotation: derived from node's live consent field state  │
│  Trajectory: the sequence of rotations = the cipher           │
│                                                               │
│  Decrypt: reverse the volleys in reverse order                │
└───────────────────────────────────────────────────────────────┘
```

```python
def apply_rotation(tsv: ToroidalStateVector,
                   delta_theta: float,
                   delta_phi: float) -> ToroidalStateVector:
    """
    Apply a rotation to all points in the TSV.
    Both strands rotate together — coherence is preserved.
    The rotation_accumulator records cumulative displacement.
    """
    rotated_primary = [
        TorusPoint(
            (p.theta + delta_theta) % (2 * math.pi),
            (p.phi   + delta_phi)   % (2 * math.pi),
            p.amplitude,
        )
        for p in tsv.primary
    ]

    # Observation strand rotates identically — antipodal relationship preserved
    rotated_observation = [antipodal(p) for p in rotated_primary]

    new_accumulator = TorusPoint(
        (tsv.rotation_accumulator.theta + delta_theta) % (2 * math.pi),
        (tsv.rotation_accumulator.phi   + delta_phi)   % (2 * math.pi),
        0.0,
    )

    return ToroidalStateVector(
        origin=tsv.origin,
        primary=rotated_primary,
        observation=rotated_observation,
        omega_theta=tsv.omega_theta,
        omega_phi=tsv.omega_phi,
        rotation_accumulator=new_accumulator,
        volley_count=tsv.volley_count + 1,
        rpp_address=tsv.rpp_address,
        strand_length=tsv.strand_length,
    )


def encrypt_volley(tsv: ToroidalStateVector,
                   node_phi: int,
                   node_theta: int,
                   node_harmonic: int,
                   consent_epoch: int) -> ToroidalStateVector:
    """One volley of pong encryption — called at each participating node."""
    delta_theta, delta_phi = derive_rotation_key(
        node_phi, node_theta, node_harmonic, consent_epoch
    )
    return apply_rotation(tsv, delta_theta, delta_phi)


def decrypt_volleys(tsv: ToroidalStateVector,
                    volley_keys: list[tuple[float, float]]) -> ToroidalStateVector:
    """
    Decrypt by reversing volleys in reverse order.
    volley_keys must be provided in FORWARD order — reversal happens here.
    """
    result = tsv
    for delta_theta, delta_phi in reversed(volley_keys):
        result = apply_rotation(result, -delta_theta, -delta_phi)
    return result
```

### 5.4 Multi-Node Mesh Pong

In a full consent-field mesh, the pong is not bilateral — the TSV traverses MULTIPLE nodes,
each applying their rotation. The full trajectory is:

```
Node₁ applies (Δθ₁, Δφ₁)  →  consent state of Node₁ at time T₁
Node₂ applies (Δθ₂, Δφ₂)  →  consent state of Node₂ at time T₂
Node₃ applies (Δθ₃, Δφ₃)  →  consent state of Node₃ at time T₃
...

Final position: (θ₀ + ΣΔθᵢ, φ₀ + ΣΔφᵢ)
Key:           the ordered sequence [(Δθᵢ, Δφᵢ)] — derived from ephemeral field states
```

An eavesdropper at Node₂ sees the TSV at position (θ₀ + Δθ₁ + Δθ₂, φ₀ + ...).
They cannot recover the original without knowing Δθ₁ (from Node₁'s consent state at T₁),
which has already T2-decohered by the time they observe.

**The cipher is self-shredding.** Each key fragment lives only as long as the consent field
state that generated it — and the consent field is temporal by design.

### 5.5 Security Properties (Standard Pong)

| Property | Mechanism |
|----------|-----------|
| Forward secrecy | Keys derived from ephemeral consent field states — T2-erased |
| No key storage | No party stores a key — keys exist only while consent states exist |
| Eavesdropping resistance | Observer at node N sees only accumulated rotation, not trajectory |
| Replay prevention | Consent epoch increments on revocation — old rotations produce wrong keys |
| Self-verifying | Decrypted TSV can be self-coherence-checked (antipodal invariant) |
| Physically enforced | On spintronics: T2 decay erases the key at the physics level |

---

### 5.6 Rasengan Mode — Skyrmion Encryption

Standard pong rotation operates on a flat torus: rotations commute, the key is the
trajectory, security is the ephemeral consent state. This is strong. But it has one
structural property worth noting: torus rotations are additive — the SUM of rotations
is all that matters, not their order.

**Rasengan mode breaks this.** By elevating the TSV to a **skyrmion state** — a
topologically protected vortex — the key gains a quantized, non-commutative component.
Knowing every rotation in the sequence is not enough. You must apply them in the
**exact reverse order**. Wrong order collapses the topology. The state is destroyed,
not decrypted.

#### The Skyrmion State Vector

```python
class TopologicalCollapseError(Exception):
    """Raised when the winding number goes negative — state topologically destroyed."""
    pass

@dataclass
class SkyrmionStateVector(ToroidalStateVector):
    """
    TSV elevated to a skyrmion — a topologically protected spin vortex.

    Rasengan mode:    winding_number = 1  (single vortex)
    Rasenshuriken:    winding_number > 1  (multi-arm, multiple topology layers)

    The winding number is a topological charge — an INTEGER that cannot be
    partially changed. It can only be wound (+1) or unwound (-1) in sequence.
    Unwinding out of order destroys the state.
    """
    winding_number: int   = 1     # Topological charge n ≥ 1. n=1: Rasengan. n>1: Rasenshuriken.
    magnon_amplitude: float = 1.0  # Spin-wave gain: 1.0 = base, >1.0 = amplified
    phase_lock_sites: int  = 1     # How many lattice sites are phase-locked in this vortex
    coherence_volume: float = 0.0  # Physical coherence volume (nm³); 0 = software simulation
```

#### Key Derivation — Adding the Topological Component

```python
ANKH = 5.08938   # Ra ANKH constant — modulates winding increment

def derive_skyrmion_key(phi_value: int,
                        theta_value: int,
                        harmonic: int,
                        consent_epoch: int) -> tuple[float, float, int]:
    """
    Derive a skyrmion rotation key: (Δθ, Δφ, Δn)

    Δθ, Δφ  — continuous torus rotation (same as standard pong)
    Δn      — winding number increment: -1, 0, or +1 (quantized, integer)

    The quantized Δn means: even knowing the continuous (Δθ, Δφ) components,
    an attacker cannot guess the winding sequence without the exact consent state.
    """
    delta_theta, delta_phi = derive_rotation_key(
        phi_value, theta_value, harmonic, consent_epoch
    )

    # Winding increment: PHI × ANKH modulation of consent state
    # Maps to {-1, 0, +1} — wind, hold, or unwind one topological layer
    raw = (phi_value * PHI_GOLDEN * ANKH * consent_epoch) % 3.0
    delta_n = round(raw) - 1   # → {-1, 0, +1}

    return (delta_theta, delta_phi, delta_n)
```

#### Applying the Skyrmion Rotation

```python
def apply_skyrmion_rotation(ssv: SkyrmionStateVector,
                             delta_theta: float,
                             delta_phi: float,
                             delta_n: int) -> SkyrmionStateVector:
    """
    Apply a rotation + topological winding change to the skyrmion.

    The rotation (Δθ, Δφ) is applied first.
    The winding (Δn) is then applied.

    CRITICAL: These operations do NOT commute with winding.
    The order in which they are applied determines the topological state.
    Reversing this in the wrong sequence produces TopologicalCollapseError.
    """
    # Step 1: Apply torus rotation (commutes within a winding level)
    rotated_base = apply_rotation(ssv, delta_theta, delta_phi)

    # Step 2: Apply winding number change
    new_winding = ssv.winding_number + delta_n

    if new_winding < 0:
        # Unwound past zero: topological collapse.
        # This is NOT a decryption failure — the state is destroyed.
        # On spintronics: physically irreversible without re-origination.
        raise TopologicalCollapseError(
            f"Topological collapse at volley {ssv.volley_count + 1}: "
            f"winding {ssv.winding_number} + Δn {delta_n} = {new_winding} < 0. "
            f"State destroyed. Decrypt sequence was wrong order."
        )

    return SkyrmionStateVector(
        origin=rotated_base.origin,
        primary=rotated_base.primary,
        observation=rotated_base.observation,
        omega_theta=rotated_base.omega_theta,
        omega_phi=rotated_base.omega_phi,
        rotation_accumulator=rotated_base.rotation_accumulator,
        volley_count=rotated_base.volley_count,
        rpp_address=rotated_base.rpp_address,
        strand_length=rotated_base.strand_length,
        winding_number=new_winding,
        magnon_amplitude=ssv.magnon_amplitude,
        phase_lock_sites=ssv.phase_lock_sites,
        coherence_volume=ssv.coherence_volume,
    )


def encrypt_skyrmion_volley(ssv: SkyrmionStateVector,
                             node_phi: int,
                             node_theta: int,
                             node_harmonic: int,
                             consent_epoch: int) -> SkyrmionStateVector:
    """One Rasengan volley — applies rotation + topological winding."""
    dt, dp, dn = derive_skyrmion_key(node_phi, node_theta, node_harmonic, consent_epoch)
    return apply_skyrmion_rotation(ssv, dt, dp, dn)


def decrypt_skyrmion_volleys(ssv: SkyrmionStateVector,
                              volley_keys: list[tuple[float, float, int]]
                              ) -> SkyrmionStateVector:
    """
    Decrypt by reversing volleys in EXACT reverse order.

    WARNING: Unlike standard pong, order is NOT optional here.
    Applying these in any sequence other than exact reverse will trigger
    TopologicalCollapseError and destroy the state permanently.

    This is the security guarantee: the correct decryption sequence is
    the only path that doesn't destroy the skyrmion.
    """
    result = ssv
    for delta_theta, delta_phi, delta_n in reversed(volley_keys):
        # Reverse: negate BOTH rotation and winding, apply in reverse order
        result = apply_skyrmion_rotation(result, -delta_theta, -delta_phi, -delta_n)
    return result
```

---

### 5.7 Rasenshuriken — Amplification and Multi-Layer Topology

The Rasenshuriken extends the Rasengan into multiple arms — higher winding numbers,
multiple topology layers, extended coherence volume. Each layer of winding is an
additional encryption layer. Decryption must unwind each layer in the exact correct order.

```
n = 1  →  Rasengan        (single vortex loop — one topological layer)
n = 2  →  Double winding   (two layers — trefoil-adjacent, two unwinds required)
n = 3  →  Rasenshuriken    (three arms — three layers, multi-axis vortex topology)
n = N  →  N layers of topological protection, N ordered unwinds required
```

#### Amplification — Spin-Wave Gain

```python
def amplify_rasengan(ssv: SkyrmionStateVector,
                     gain_factor: float) -> SkyrmionStateVector:
    """
    Apply spin-wave (magnon) gain to amplify the skyrmion.

    Larger amplitude → more spin sites phase-locked → more resistant to decoherence.
    This is the 'more chakra' operation — the Rasengan grows.

    Coherence volume scales as cube root of energy (volume ∝ energy^(1/3)).
    Phase-lock sites scale linearly with gain.

    On spintronics: implemented as spin-transfer torque pumping.
    On software: increases the amplitude field of all TSV points.
    """
    amplified_primary = [
        TorusPoint(p.theta, p.phi, min(1.0, p.amplitude * gain_factor))
        for p in ssv.primary
    ]
    amplified_observation = [antipodal(p) for p in amplified_primary]

    return SkyrmionStateVector(
        origin=ssv.origin,
        primary=amplified_primary,
        observation=amplified_observation,
        omega_theta=ssv.omega_theta,
        omega_phi=ssv.omega_phi,
        rotation_accumulator=ssv.rotation_accumulator,
        volley_count=ssv.volley_count,
        rpp_address=ssv.rpp_address,
        strand_length=ssv.strand_length,
        winding_number=ssv.winding_number,
        magnon_amplitude=ssv.magnon_amplitude * gain_factor,
        phase_lock_sites=round(ssv.phase_lock_sites * gain_factor),
        coherence_volume=ssv.coherence_volume * (gain_factor ** (1/3)),
    )


def charge_rasenshuriken(ssv: SkyrmionStateVector,
                          n_arms: int,
                          consent_epoch: int) -> SkyrmionStateVector:
    """
    Wind the skyrmion to n_arms winding number — the Rasenshuriken.

    Each winding layer requires a corresponding unwind during decryption.
    Failure to unwind in the correct order at any layer collapses the state.

    n_arms = 3 means: three independent topological layers, three ordered unwinds,
    three independent key fragments derived from three distinct consent states.
    """
    result = ssv
    for arm in range(n_arms - ssv.winding_number):
        # Each arm winding uses an incrementing epoch
        dt, dp, dn = derive_skyrmion_key(
            phi_value=arm * 137 % 512,          # ALPHA spread across consent range
            theta_value=arm * 165 % 512,         # GREEN_PHI spread
            harmonic=arm * 19 % 256,             # DWELL_FULL spread
            consent_epoch=consent_epoch + arm,
        )
        # Force +1 winding for each arm
        result = apply_skyrmion_rotation(result, dt, dp, +1)
    return result
```

#### Security Properties — Rasengan Mode

| Property | Standard Pong | Rasengan Mode |
|----------|--------------|---------------|
| Key type | Continuous (θ, φ) | Continuous + quantized (θ, φ, n) |
| Order dependence | Commutative — order doesn't matter | Non-commutative — exact reverse order required |
| Wrong-order result | Wrong decryption | **Topological collapse — state destroyed** |
| Key granularity | Infinite (float) | Integer winding + float rotation |
| Decoherence resistance | T2-limited | T2-limited + topological protection |
| Hardware enforcement | T2 decay | T2 decay + skyrmion stability |
| Amplifiable | No | Yes — spin-wave gain increases coherence volume |
| Layers | 1 (single trajectory) | N (one per winding layer) |

---

## 6. Holographic Operations

For operations requiring higher angular resolution than the 28-bit address provides
(precision < 0.7° in theta or phi), see [SPEC-EXTENDED.md](SPEC-EXTENDED.md).

The extended format provides:
- 20-bit Theta (1,048,576 values → 0.00034° resolution)
- 20-bit Phi (1,048,576 values → 0.00034° resolution)
- Phase angle support for wave interference calculations
- TSV strand lengths up to 2²⁰ points

Holographic operations use multiple TSVs whose helices interfere constructively —
like light waves creating a hologram, information is encoded in the interference pattern
rather than any single strand.

---

## 7. What Works Now vs. Future Hardware

| Component | Now (software) | Spintronic hardware |
|-----------|---------------|---------------------|
| Torus coordinate encoding | RPP address encoding — fully implemented | Same, faster |
| TSV construction | Python/any language — implemented above | Native lattice geometry |
| Self-coherence check | Software hash comparison | Spin coherence measurement |
| Witness observation | Network messages with signatures | Direct spin coupling |
| Key derivation | PHI-scaled pseudo-random from consent state | Derived from T2 decay constants |
| Physical key erasure | Session-scoped key TTL (software enforced) | T2 decoherence (physics enforced) |
| Pong encryption (standard) | Software rotation of float arrays | Spin-transfer torque rotation |
| Rasengan mode (skyrmion) | Software winding number + float rotation | Native skyrmion topology on magnetic lattice |
| Rasenshuriken (n > 1) | Multi-layer software winding | Multi-arm vortex spin texture |
| Magnon amplification | Amplitude scaling on float arrays | Spin-transfer torque pumping |
| Topological collapse detection | Exception on negative winding | Physical irreversibility — spin lattice tears |

**On spintronics: `apply_rotation()` IS the spin-transfer torque operation.** Rotating the
TSV's angular positions maps directly to rotating the spin vector on a spin lattice site.
The pong protocol runs in hardware at T2 speed.

---

## 8. Invariants

1. **Antipodal invariant:** `observation[i] == antipodal(primary[i])` at all times
2. **Strand parity:** `len(primary) == len(observation)` always
3. **Rotation reversibility:** `decrypt(encrypt(tsv, k), k) == tsv` exactly
4. **Self-coherence after valid crossing:** A TSV that passes the Ford Protocol intact MUST pass `verify_self_coherence()` at the destination
5. **Winding non-negativity:** `winding_number >= 1` at all times in a valid SkyrmionStateVector. Zero or negative = collapse.
6. **Topological order:** Skyrmion decryption keys MUST be applied in exact reverse order of encryption. Any other order triggers `TopologicalCollapseError`.
7. **Amplification monotonicity:** `magnon_amplitude >= 1.0` always. Amplification cannot be reversed — only a new skyrmion can be created at base amplitude.
8. **Rasenshuriken integrity:** A winding_number=N skyrmion requires exactly N ordered unwinds for successful decryption. Partial unwind (k < N) leaves the state partially decrypted and topologically unstable.
5. **Accumulator faithfulness:** `rotation_accumulator` equals the sum of all rotations applied — decryption uses this as the inverse
6. **PHI-scaled key spread:** No two consecutive keys from the same node are closer than `π / (512 × PHI)` radians

---

## 9. See Also

- [SPEC.md](SPEC.md) — v1.0 address encoding (Theta/Phi/Shell/Harmonic fields)
- [SPEC-EXTENDED.md](SPEC-EXTENDED.md) — High-precision toroidal addressing for holographic operations
- [CONTINUITY.md](CONTINUITY.md) — Ford Protocol: how TSVs cross substrates intact
- [ADDRESSING-LAYERS.md](ADDRESSING-LAYERS.md) — Two-layer architecture
- [hardware/verilog/spintronic_sim.py](../hardware/verilog/spintronic_sim.py) — Spintronics behavioral simulation

---

*"The helix is not decoration. It is the memory. The complement is not redundancy.
It is the eye that watches itself."*

*This specification is released under CC BY 4.0. Attribution required.*
