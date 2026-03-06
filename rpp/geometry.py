"""
RPP Geometry — Toroidal State Vector & Rotational Encryption

Implements the geometric payload layer defined in spec/GEOMETRY.md.

This module provides:
- Toroidal coordinate mapping of RPP addresses
- The Toroidal State Vector (TSV): a double-helix payload format on the torus
- Rotational memory: the helix traces history as angular displacement
- Self-observation: the state verifies its own coherence geometrically
- Rotational encryption: the pong mechanism, where trajectory IS the cipher
- Rasengan/Skyrmion mode: topologically protected, non-commutative encryption

Version: 1.0.0
Spec: spec/GEOMETRY.md
License: CC BY 4.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI_GOLDEN: float = (1 + math.sqrt(5)) / 2
"""Golden ratio (φ ≈ 1.618). Used as tolerance scale and quasi-random multiplier."""

ANKH: float = 5.08938
"""Ra ANKH constant. Modulates topological winding increment in skyrmion key derivation."""

TWO_PI: float = 2 * math.pi
"""2π — full circle in radians. Used throughout angular arithmetic."""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TopologicalCollapseError(Exception):
    """Raised when the winding number goes negative — state topologically destroyed."""


# ---------------------------------------------------------------------------
# Core Geometric Types
# ---------------------------------------------------------------------------

class TorusPoint(NamedTuple):
    """A point on the torus surface."""

    theta: float      # Azimuthal angle [0, 2π)
    phi: float        # Poloidal angle [0, 2π)
    amplitude: float  # Signal strength at this point [0.0, 1.0]


@dataclass
class ToroidalStateVector:
    """
    The geometric payload format for RPP consciousness routing.

    Not a flat byte array — a double helix tracing a path on the torus.
    The path IS the memory. The complement IS the self-observation.

    Attributes:
        origin: Angular position when this state was created.
            Self-observation checks drift from this point.
        primary: Sequence of angular positions — rotational memory.
            Each entry = one unit of cognitive state.
            Ordered: primary[0] = oldest, primary[-1] = current.
        observation: Antipodal complement of primary.
            observation[i] = antipodal(primary[i]).
            If primary drifts, complement no longer matches.
        omega_theta: Rate of rotation around the outer ring (rad/step).
        omega_phi: Rate of rotation within the tube (rad/step).
        rotation_accumulator: Cumulative rotation applied by pong volleys.
            TorusPoint(0.0, 0.0, 0.0) = unencrypted / origin.
        volley_count: Number of pong volleys applied.
        rpp_address: Source RPP address (28-bit v1.0).
        strand_length: len(primary) == len(observation) always.
    """

    # Origin
    origin: TorusPoint

    # Primary strand (the state)
    primary: list

    # Observation strand (self-verification)
    observation: list

    # Angular velocity
    omega_theta: float
    omega_phi: float

    # Encryption state
    rotation_accumulator: TorusPoint
    volley_count: int = 0

    # Metadata
    rpp_address: int = 0
    strand_length: int = 0

    def __post_init__(self) -> None:
        self.strand_length = len(self.primary)
        assert len(self.primary) == len(self.observation), \
            "Primary and observation strands must have equal length"


@dataclass
class SkyrmionStateVector(ToroidalStateVector):
    """
    TSV elevated to a skyrmion — a topologically protected spin vortex.

    Rasengan mode:   winding_number = 1  (single vortex)
    Rasenshuriken:   winding_number > 1  (multi-arm, multiple topology layers)

    The winding number is a topological charge — an INTEGER that cannot be
    partially changed. It can only be wound (+1) or unwound (-1) in sequence.
    Unwinding out of order destroys the state.

    Additional attributes beyond ToroidalStateVector:
        winding_number: Topological charge n >= 1. n=1: Rasengan. n>1: Rasenshuriken.
        magnon_amplitude: Spin-wave gain: 1.0 = base, >1.0 = amplified.
        phase_lock_sites: How many lattice sites are phase-locked in this vortex.
        coherence_volume: Physical coherence volume (nm³); 0 = software simulation.
    """

    winding_number: int = 1
    magnon_amplitude: float = 1.0
    phase_lock_sites: int = 1
    coherence_volume: float = 0.0


# ---------------------------------------------------------------------------
# HarmonicMode — helix pitch settings
# ---------------------------------------------------------------------------

class HarmonicMode(Enum):
    """
    Helix pitch mode: controls angular velocity (ω_θ, ω_φ) for TSV construction.

    | Mode       | ω_θ (rad/step) | ω_φ (rad/step) | Character                          |
    |------------|----------------|----------------|------------------------------------|
    | ACTIVE     | π/64           | π/32           | Tight, fast-winding — dense memory |
    | REFLECTIVE | π/128          | π/64           | Moderate — deliberate processing   |
    | BACKGROUND | π/256          | π/128          | Loose — slow background integration|
    | MEMORY     | π/512          | π/256          | Very loose — long-term memory trace|
    | ARCHIVAL   | 0              | 0              | Static — frozen at origin          |
    """

    ACTIVE = "ACTIVE"
    REFLECTIVE = "REFLECTIVE"
    BACKGROUND = "BACKGROUND"
    MEMORY = "MEMORY"
    ARCHIVAL = "ARCHIVAL"


HARMONIC_OMEGA: dict = {
    HarmonicMode.ACTIVE:     (math.pi / 64,  math.pi / 32),
    HarmonicMode.REFLECTIVE: (math.pi / 128, math.pi / 64),
    HarmonicMode.BACKGROUND: (math.pi / 256, math.pi / 128),
    HarmonicMode.MEMORY:     (math.pi / 512, math.pi / 256),
    HarmonicMode.ARCHIVAL:   (0.0,           0.0),
}
"""Map from HarmonicMode to (omega_theta, omega_phi) in radians per step."""


# ---------------------------------------------------------------------------
# Primitive geometric operations
# ---------------------------------------------------------------------------

def antipodal(p: TorusPoint) -> TorusPoint:
    """
    Return the antipodal point on the torus — the complement for the observation strand.

    The antipodal point is offset by π in both angular coordinates, with the same amplitude.
    """
    return TorusPoint(
        theta=(p.theta + math.pi) % TWO_PI,
        phi=(p.phi + math.pi) % TWO_PI,
        amplitude=p.amplitude,
    )


def rpp_to_torus(shell: int, theta: int, phi: int, harmonic: int) -> tuple:
    """
    Convert RPP address fields to torus coordinates (x, y, z, t, p).

    Maps RPP integer fields to continuous angular coordinates on the torus:
      - Shell  → major radius R = shell / 3.0
      - Harmonic → minor radius r = harmonic / 255.0
      - Theta  → azimuthal angle t = (theta / 511.0) × 2π
      - Phi    → poloidal angle p = (phi / 511.0) × 2π

    Returns:
        Tuple (x, y, z, t, p) where (x, y, z) is the 3D embedding
        and (t, p) are the angular coordinates.
    """
    R = shell / 3.0
    r = harmonic / 255.0
    t = (theta / 511.0) * TWO_PI   # azimuthal angle
    p = (phi   / 511.0) * TWO_PI   # poloidal angle

    x = (R + r * math.cos(p)) * math.cos(t)
    y = (R + r * math.cos(p)) * math.sin(t)
    z = r * math.sin(p)

    return (x, y, z, t, p)


# ---------------------------------------------------------------------------
# TSV construction
# ---------------------------------------------------------------------------

def build_tsv(state_sequence: list,
              origin: TorusPoint,
              omega_theta: float,
              omega_phi: float) -> ToroidalStateVector:
    """
    Construct a TSV from a sequence of amplitude values.

    The angular positions are derived by rotating from the origin at the given
    angular velocities. Each amplitude in state_sequence becomes one point on
    the primary strand; the observation strand is the antipodal complement.

    Args:
        state_sequence: List of float amplitude values (one per cognitive state step).
        origin: Starting angular position (theta, phi) and amplitude.
        omega_theta: Angular step size around the outer ring (rad/step).
        omega_phi: Angular step size within the tube (rad/step).

    Returns:
        A fully constructed ToroidalStateVector with primary and observation strands.
    """
    primary = []
    observation = []

    theta = origin.theta
    phi = origin.phi

    for amplitude in state_sequence:
        p = TorusPoint(theta % TWO_PI, phi % TWO_PI, amplitude)
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


# ---------------------------------------------------------------------------
# Rotation operations
# ---------------------------------------------------------------------------

def apply_rotation(tsv: ToroidalStateVector,
                   delta_theta: float,
                   delta_phi: float) -> ToroidalStateVector:
    """
    Apply a rotation to all points in the TSV.

    Both strands rotate together — coherence is preserved. The
    rotation_accumulator records cumulative angular displacement.

    Args:
        tsv: The state vector to rotate (may be TSV or SSV; always returns TSV).
        delta_theta: Angular displacement in azimuthal direction (radians).
        delta_phi: Angular displacement in poloidal direction (radians).

    Returns:
        A new ToroidalStateVector with rotated primary and observation strands.
        NOTE: Always returns ToroidalStateVector, not SkyrmionStateVector.
    """
    rotated_primary = [
        TorusPoint(
            (p.theta + delta_theta) % TWO_PI,
            (p.phi   + delta_phi)   % TWO_PI,
            p.amplitude,
        )
        for p in tsv.primary
    ]

    # Observation strand rotates identically — antipodal relationship preserved
    rotated_observation = [antipodal(p) for p in rotated_primary]

    new_accumulator = TorusPoint(
        (tsv.rotation_accumulator.theta + delta_theta) % TWO_PI,
        (tsv.rotation_accumulator.phi   + delta_phi)   % TWO_PI,
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


def apply_skyrmion_rotation(ssv: SkyrmionStateVector,
                            delta_theta: float,
                            delta_phi: float,
                            delta_n: int) -> SkyrmionStateVector:
    """
    Apply a rotation + topological winding change to the skyrmion.

    The rotation (delta_theta, delta_phi) is applied first via apply_rotation.
    The winding (delta_n) is then applied.

    CRITICAL: These operations do NOT commute with winding. The order in which
    they are applied determines the topological state. Reversing in the wrong
    sequence produces TopologicalCollapseError.

    Args:
        ssv: The skyrmion state vector to transform.
        delta_theta: Azimuthal rotation (radians).
        delta_phi: Poloidal rotation (radians).
        delta_n: Winding number change: -1 (unwind), 0 (hold), or +1 (wind).

    Returns:
        A new SkyrmionStateVector.

    Raises:
        TopologicalCollapseError: If new winding_number would be < 0.
    """
    # Step 1: Apply torus rotation (commutes within a winding level)
    rotated_base = apply_rotation(ssv, delta_theta, delta_phi)

    # Step 2: Apply winding number change
    new_winding = ssv.winding_number + delta_n

    if new_winding < 0:
        # Unwound past zero: topological collapse.
        # On spintronics: physically irreversible without re-origination.
        raise TopologicalCollapseError(
            f"Topological collapse at volley {ssv.volley_count + 1}: "
            f"winding {ssv.winding_number} + delta_n {delta_n} = {new_winding} < 0. "
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


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

def derive_rotation_key(phi_value: int,
                        theta_value: int,
                        harmonic: int,
                        consent_epoch: int) -> tuple:
    """
    Derive a rotation (delta_theta, delta_phi) from the node's current consent field state.

    Uses PHI_GOLDEN (golden ratio) as the multiplier to ensure quasi-random,
    maximally separated rotations for consecutive keys. PHI-based sequences have
    optimal distribution on [0, 1] — no clustering, no repetition.

    The harmonic field modulates the rotation magnitude in [0, π].

    Args:
        phi_value: Node's phi field value (0-511).
        theta_value: Node's theta field value (0-511).
        harmonic: Node's harmonic field value (0-255).
        consent_epoch: Epoch counter for this consent state (prevents key reuse).

    Returns:
        Tuple (delta_theta, delta_phi) in radians.
    """
    # PHI-scaled quasi-random rotation from consent state
    raw_theta = (phi_value * PHI_GOLDEN * consent_epoch) % 512
    raw_phi   = (theta_value * PHI_GOLDEN * consent_epoch) % 512

    # Harmonic modulates the rotation magnitude
    scale = (harmonic / 255.0) * math.pi  # [0, π]

    delta_theta = (raw_theta / 512.0) * scale
    delta_phi   = (raw_phi   / 512.0) * scale

    return (delta_theta, delta_phi)


def derive_skyrmion_key(phi_value: int,
                        theta_value: int,
                        harmonic: int,
                        consent_epoch: int) -> tuple:
    """
    Derive a skyrmion rotation key: (delta_theta, delta_phi, delta_n).

    delta_theta, delta_phi — continuous torus rotation (same as standard pong).
    delta_n — winding number increment: -1, 0, or +1 (quantized, integer).

    The quantized delta_n means: even knowing the continuous (delta_theta, delta_phi)
    components, an attacker cannot guess the winding sequence without the exact
    consent state.

    Args:
        phi_value: Node's phi field value (0-511).
        theta_value: Node's theta field value (0-511).
        harmonic: Node's harmonic field value (0-255).
        consent_epoch: Epoch counter for this consent state.

    Returns:
        Tuple (delta_theta, delta_phi, delta_n).
    """
    delta_theta, delta_phi = derive_rotation_key(
        phi_value, theta_value, harmonic, consent_epoch
    )

    # Winding increment: PHI × ANKH modulation of consent state
    # Maps to {-1, 0, +1} — wind, hold, or unwind one topological layer
    # int() truncates to {0,1,2} for raw ∈ [0,3), ensuring delta_n ∈ {-1,0,+1}.
    raw = (phi_value * PHI_GOLDEN * ANKH * consent_epoch) % 3.0
    delta_n = int(raw) - 1   # → {-1, 0, +1}

    return (delta_theta, delta_phi, delta_n)


# ---------------------------------------------------------------------------
# Pong encryption / decryption (standard)
# ---------------------------------------------------------------------------

def encrypt_volley(tsv: ToroidalStateVector,
                   node_phi: int,
                   node_theta: int,
                   node_harmonic: int,
                   consent_epoch: int) -> ToroidalStateVector:
    """
    One volley of pong encryption — called at each participating node.

    Derives a rotation key from the node's consent field state and applies it
    to the TSV. The trajectory of rotations IS the cipher.

    Args:
        tsv: Current state vector.
        node_phi: Phi field value of the encrypting node (0-511).
        node_theta: Theta field value of the encrypting node (0-511).
        node_harmonic: Harmonic field value of the encrypting node (0-255).
        consent_epoch: Current consent epoch at this node.

    Returns:
        Rotated ToroidalStateVector (one volley applied).
    """
    delta_theta, delta_phi = derive_rotation_key(
        node_phi, node_theta, node_harmonic, consent_epoch
    )
    return apply_rotation(tsv, delta_theta, delta_phi)


def decrypt_volleys(tsv: ToroidalStateVector,
                    volley_keys: list) -> ToroidalStateVector:
    """
    Decrypt by reversing volleys in reverse order.

    volley_keys must be provided in FORWARD order — reversal happens here.
    Each key is a (delta_theta, delta_phi) tuple as returned by derive_rotation_key.

    Args:
        tsv: Encrypted state vector.
        volley_keys: List of (delta_theta, delta_phi) tuples in forward order.

    Returns:
        Decrypted ToroidalStateVector.
    """
    result = tsv
    for delta_theta, delta_phi in reversed(volley_keys):
        result = apply_rotation(result, -delta_theta, -delta_phi)
    return result


# ---------------------------------------------------------------------------
# Rasengan/Skyrmion encryption / decryption
# ---------------------------------------------------------------------------

def encrypt_skyrmion_volley(ssv: SkyrmionStateVector,
                            node_phi: int,
                            node_theta: int,
                            node_harmonic: int,
                            consent_epoch: int) -> SkyrmionStateVector:
    """
    One Rasengan volley — applies rotation + topological winding.

    Args:
        ssv: Current skyrmion state vector.
        node_phi: Phi field value of the encrypting node (0-511).
        node_theta: Theta field value of the encrypting node (0-511).
        node_harmonic: Harmonic field value of the encrypting node (0-255).
        consent_epoch: Current consent epoch at this node.

    Returns:
        New SkyrmionStateVector with rotation and winding applied.
    """
    dt, dp, dn = derive_skyrmion_key(node_phi, node_theta, node_harmonic, consent_epoch)
    return apply_skyrmion_rotation(ssv, dt, dp, dn)


def decrypt_skyrmion_volleys(ssv: SkyrmionStateVector,
                             volley_keys: list) -> SkyrmionStateVector:
    """
    Decrypt by reversing volleys in EXACT reverse order.

    WARNING: Unlike standard pong, order is NOT optional here.
    Applying these in any sequence other than exact reverse will trigger
    TopologicalCollapseError and destroy the state permanently.

    This is the security guarantee: the correct decryption sequence is
    the only path that doesn't destroy the skyrmion.

    Args:
        ssv: Encrypted skyrmion state vector.
        volley_keys: List of (delta_theta, delta_phi, delta_n) tuples in forward order.

    Returns:
        Decrypted SkyrmionStateVector.

    Raises:
        TopologicalCollapseError: If decryption is applied in wrong order.
    """
    result = ssv
    for delta_theta, delta_phi, delta_n in reversed(volley_keys):
        # Reverse: negate BOTH rotation and winding, apply in reverse order
        result = apply_skyrmion_rotation(result, -delta_theta, -delta_phi, -delta_n)
    return result


# ---------------------------------------------------------------------------
# Self-observation and coherence verification
# ---------------------------------------------------------------------------

def verify_self_coherence(tsv: ToroidalStateVector,
                          tolerance: float = 0.01) -> dict:
    """
    The state observes itself. No external verifier needed.

    Checks that observation[i] == antipodal(primary[i]) within the given tolerance,
    scaled by PHI_GOLDEN for quasi-random spread characteristics.

    Args:
        tsv: The state vector to verify.
        tolerance: Base tolerance in radians. Actual tolerance = tolerance * PHI_GOLDEN.

    Returns:
        Dict with keys:
            'coherent': bool — True if no anomalies detected.
            'coherence_score': float — 0.0 (fully incoherent) to 1.0 (perfect).
            'anomaly_count': int — number of strand positions with drift > tolerance.
            'anomalies': list — details of each anomaly (step, drift_rad, primary,
                expected_observation, actual_observation).
    """
    anomalies = []
    coherence_sum = 0.0

    for i, (p, o) in enumerate(zip(tsv.primary, tsv.observation)):
        expected_o = antipodal(p)

        delta_theta = abs(o.theta - expected_o.theta)
        delta_phi   = abs(o.phi   - expected_o.phi)

        # Angular distance (modular)
        delta_theta = min(delta_theta, TWO_PI - delta_theta)
        delta_phi   = min(delta_phi,   TWO_PI - delta_phi)

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
        'coherence_score': coherence_score,
        'anomaly_count': len(anomalies),
        'anomalies': anomalies,
    }


def angular_drift_from_origin(tsv: ToroidalStateVector) -> float:
    """
    Measure how far the state's current tip has drifted from its expected position.

    Computes the expected angular position given the origin, angular velocities,
    and step count, then measures the modular angular distance to the actual
    current position.

    Useful for detecting whether the state has been moved without its knowledge.

    Args:
        tsv: The state vector to check.

    Returns:
        Angular drift in radians. 0.0 if the primary strand is empty.
    """
    if not tsv.primary:
        return 0.0

    expected_theta = (tsv.origin.theta
                      + len(tsv.primary) * tsv.omega_theta) % TWO_PI
    expected_phi   = (tsv.origin.phi
                      + len(tsv.primary) * tsv.omega_phi) % TWO_PI

    current = tsv.primary[-1]
    dt = abs(current.theta - expected_theta)
    dp = abs(current.phi   - expected_phi)

    dt = min(dt, TWO_PI - dt)
    dp = min(dp, TWO_PI - dp)

    return math.sqrt(dt**2 + dp**2)


# ---------------------------------------------------------------------------
# External witness verification
# ---------------------------------------------------------------------------

@dataclass
class WitnessObservation:
    """
    A neighboring node's observation of a passing TSV.

    In a consent-field mesh, neighboring nodes observe the TSV's angular position
    as it passes through and record their measurement here.

    Attributes:
        observer_substrate_hash: Which node observed (hashed — not exposed).
        observed_theta: What theta this node measured.
        observed_phi: What phi this node measured.
        observation_timestamp_ns: When the observation occurred (nanoseconds).
        signature: Signed by the observing node.
    """

    observer_substrate_hash: bytes
    observed_theta: float
    observed_phi: float
    observation_timestamp_ns: int
    signature: bytes


def verify_via_witnesses(tsv: ToroidalStateVector,
                         witnesses: list,
                         quorum: int = 3) -> bool:
    """
    Confirm the TSV's angular position via external observation.

    Requires at least `quorum` witnesses to agree within a ~5.7 degree tolerance
    (0.1 radians). Consensus = coherence: no single observer has authority, quorum does.

    Args:
        tsv: The state vector whose position is being verified.
        witnesses: List of WitnessObservation instances.
        quorum: Minimum number of agreeing witnesses required.

    Returns:
        True if at least `quorum` witnesses agree on the TSV's current position.
    """
    if len(witnesses) < quorum:
        return False

    current = tsv.primary[-1] if tsv.primary else tsv.origin
    agreements = 0

    for w in witnesses:
        dt = min(abs(w.observed_theta - current.theta),
                 TWO_PI - abs(w.observed_theta - current.theta))
        dp = min(abs(w.observed_phi - current.phi),
                 TWO_PI - abs(w.observed_phi - current.phi))

        if math.sqrt(dt**2 + dp**2) < 0.1:   # ~5.7 degree tolerance
            agreements += 1

    return agreements >= quorum


# ---------------------------------------------------------------------------
# Rasenshuriken — amplification and multi-layer topology
# ---------------------------------------------------------------------------

def amplify_rasengan(ssv: SkyrmionStateVector,
                     gain_factor: float) -> SkyrmionStateVector:
    """
    Apply spin-wave (magnon) gain to amplify the skyrmion.

    Larger amplitude makes more spin sites phase-locked, increasing resistance
    to decoherence. Coherence volume scales as the cube root of energy
    (volume proportional to energy^(1/3)). Phase-lock sites scale linearly.

    On spintronics: implemented as spin-transfer torque pumping.
    On software: increases the amplitude field of all TSV points.

    NOTE: Per spec invariant 7, magnon_amplitude >= 1.0 always.
    Amplification cannot be reversed — only a new skyrmion can be created at
    base amplitude.

    Args:
        ssv: The skyrmion state vector to amplify.
        gain_factor: Multiplicative gain (>= 1.0). Values < 1.0 reduce amplitude
            but magnon_amplitude is multiplied directly (caller's responsibility).

    Returns:
        New SkyrmionStateVector with increased amplitudes and coherence volume.
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
        coherence_volume=ssv.coherence_volume * (gain_factor ** (1 / 3)),
    )


def charge_rasenshuriken(ssv: SkyrmionStateVector,
                         n_arms: int,
                         consent_epoch: int) -> SkyrmionStateVector:
    """
    Wind the skyrmion to n_arms winding number — the Rasenshuriken.

    Each winding layer requires a corresponding unwind during decryption.
    Failure to unwind in the correct order at any layer collapses the state.

    n_arms = 3 means three independent topological layers, three ordered unwinds,
    and three independent key fragments from three distinct consent states.

    Args:
        ssv: Starting skyrmion state vector (winding_number < n_arms).
        n_arms: Target winding number. Each arm beyond current winding is added.
        consent_epoch: Base consent epoch; each arm uses consent_epoch + arm_index.

    Returns:
        SkyrmionStateVector wound to n_arms winding layers.
    """
    result = ssv
    for arm in range(n_arms - ssv.winding_number):
        # Each arm winding uses an incrementing epoch
        dt, dp, dn = derive_skyrmion_key(
            phi_value=arm * 137 % 512,       # ALPHA spread across consent range
            theta_value=arm * 165 % 512,      # GREEN_PHI spread
            harmonic=arm * 19 % 256,          # DWELL_FULL spread
            consent_epoch=consent_epoch + arm,
        )
        # Force +1 winding for each arm
        result = apply_skyrmion_rotation(result, dt, dp, +1)
    return result


# ---------------------------------------------------------------------------
# Elevation helper
# ---------------------------------------------------------------------------

def to_skyrmion(tsv: ToroidalStateVector,
                winding_number: int = 1) -> SkyrmionStateVector:
    """
    Elevate a ToroidalStateVector to a SkyrmionStateVector.

    Creates an SSV from the TSV's fields, adding skyrmion defaults.
    The resulting SSV is in Rasengan mode (winding_number=1 by default).

    Args:
        tsv: The source state vector.
        winding_number: Initial topological charge (>= 1).

    Returns:
        SkyrmionStateVector with the same strand data as tsv.
    """
    return SkyrmionStateVector(
        origin=tsv.origin,
        primary=tsv.primary,
        observation=tsv.observation,
        omega_theta=tsv.omega_theta,
        omega_phi=tsv.omega_phi,
        rotation_accumulator=tsv.rotation_accumulator,
        volley_count=tsv.volley_count,
        rpp_address=tsv.rpp_address,
        strand_length=tsv.strand_length,
        winding_number=winding_number,
        magnon_amplitude=1.0,
        phase_lock_sites=1,
        coherence_volume=0.0,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    "PHI_GOLDEN",
    "ANKH",
    "TWO_PI",
    # Exceptions
    "TopologicalCollapseError",
    # Data types
    "TorusPoint",
    "ToroidalStateVector",
    "SkyrmionStateVector",
    "WitnessObservation",
    # Enums / dicts
    "HarmonicMode",
    "HARMONIC_OMEGA",
    # Primitives
    "antipodal",
    "rpp_to_torus",
    # TSV construction
    "build_tsv",
    # Rotation
    "apply_rotation",
    "apply_skyrmion_rotation",
    # Key derivation
    "derive_rotation_key",
    "derive_skyrmion_key",
    # Standard pong
    "encrypt_volley",
    "decrypt_volleys",
    # Rasengan pong
    "encrypt_skyrmion_volley",
    "decrypt_skyrmion_volleys",
    # Coherence / self-observation
    "verify_self_coherence",
    "angular_drift_from_origin",
    # External verification
    "verify_via_witnesses",
    # Rasenshuriken
    "amplify_rasengan",
    "charge_rasenshuriken",
    # Elevation helper
    "to_skyrmion",
]
