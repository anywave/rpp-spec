"""
Tests for rpp.geometry — Toroidal State Vector, pong encryption, Rasengan/Skyrmion.

Spec: spec/GEOMETRY.md
"""

import math
import pytest
from rpp.geometry import (
    PHI_GOLDEN, ANKH, TWO_PI,
    TorusPoint, ToroidalStateVector, SkyrmionStateVector,
    TopologicalCollapseError, HarmonicMode, HARMONIC_OMEGA,
    antipodal, rpp_to_torus, build_tsv,
    apply_rotation, apply_skyrmion_rotation,
    derive_rotation_key, derive_skyrmion_key,
    encrypt_volley, decrypt_volleys,
    encrypt_skyrmion_volley, decrypt_skyrmion_volleys,
    verify_self_coherence, angular_drift_from_origin,
    amplify_rasengan, charge_rasenshuriken, to_skyrmion,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def origin():
    return TorusPoint(0.0, math.pi, 1.0)

@pytest.fixture
def simple_tsv(origin):
    amplitudes = [0.1, 0.5, 0.9, 0.3, 0.7]
    return build_tsv(amplitudes, origin, math.pi / 64, math.pi / 32)

@pytest.fixture
def simple_ssv(simple_tsv):
    return to_skyrmion(simple_tsv, winding_number=1)


# ─── Constants ────────────────────────────────────────────────────────────────

def test_phi_golden():
    assert abs(PHI_GOLDEN - 1.61803398875) < 1e-8

def test_ankh_value():
    assert ANKH == 5.08938

def test_two_pi():
    assert abs(TWO_PI - 2 * math.pi) < 1e-12


# ─── TorusPoint ───────────────────────────────────────────────────────────────

def test_torus_point_named_tuple():
    p = TorusPoint(1.0, 2.0, 0.5)
    assert p.theta == 1.0
    assert p.phi == 2.0
    assert p.amplitude == 0.5

def test_antipodal_shifts_by_pi():
    p = TorusPoint(0.5, 1.0, 0.8)
    o = antipodal(p)
    assert abs(o.theta - (0.5 + math.pi) % TWO_PI) < 1e-12
    assert abs(o.phi   - (1.0 + math.pi) % TWO_PI) < 1e-12
    assert o.amplitude == p.amplitude

def test_antipodal_wraps_modulo():
    p = TorusPoint(math.pi * 1.5, math.pi * 1.8, 1.0)
    o = antipodal(p)
    assert 0.0 <= o.theta < TWO_PI
    assert 0.0 <= o.phi   < TWO_PI

def test_double_antipodal_roundtrip():
    p = TorusPoint(1.2, 2.4, 0.6)
    assert abs(antipodal(antipodal(p)).theta - p.theta) < 1e-10
    assert abs(antipodal(antipodal(p)).phi   - p.phi)   < 1e-10


# ─── rpp_to_torus ─────────────────────────────────────────────────────────────

def test_rpp_to_torus_returns_five_values():
    result = rpp_to_torus(0, 0, 0, 0)
    assert len(result) == 5

def test_rpp_to_torus_origin():
    x, y, z, t, p = rpp_to_torus(0, 0, 0, 0)
    # shell=0 → R=0, harmonic=0 → r=0, theta=0 → t=0, phi=0 → p=0
    # x = (0 + 0*cos(0))*cos(0) = 0
    assert abs(x) < 1e-10
    assert abs(y) < 1e-10
    assert abs(z) < 1e-10

def test_rpp_to_torus_max():
    x, y, z, t, p = rpp_to_torus(3, 511, 511, 255)
    # shell=3 → R=1.0, harmonic=255 → r=1.0
    # should produce a non-trivial point
    assert not (x == 0 and y == 0 and z == 0)


# ─── build_tsv ────────────────────────────────────────────────────────────────

def test_build_tsv_strand_parity(simple_tsv):
    assert len(simple_tsv.primary) == len(simple_tsv.observation)
    assert simple_tsv.strand_length == 5

def test_build_tsv_antipodal_invariant(simple_tsv):
    for p, o in zip(simple_tsv.primary, simple_tsv.observation):
        expected = antipodal(p)
        assert abs(o.theta - expected.theta) < 1e-12
        assert abs(o.phi   - expected.phi)   < 1e-12
        assert o.amplitude == p.amplitude

def test_build_tsv_origin_preserved(simple_tsv, origin):
    assert simple_tsv.origin == origin

def test_build_tsv_angles_are_bounded(simple_tsv):
    for p in simple_tsv.primary:
        assert 0.0 <= p.theta < TWO_PI
        assert 0.0 <= p.phi   < TWO_PI

def test_build_tsv_amplitudes_preserved(origin):
    amps = [0.0, 0.25, 0.5, 0.75, 1.0]
    tsv = build_tsv(amps, origin, 0.1, 0.1)
    recovered = [p.amplitude for p in tsv.primary]
    assert recovered == amps

def test_build_tsv_rotation_accumulator_zero(simple_tsv):
    acc = simple_tsv.rotation_accumulator
    assert acc.theta == 0.0
    assert acc.phi == 0.0


# ─── apply_rotation ───────────────────────────────────────────────────────────

def test_apply_rotation_shifts_angles(simple_tsv):
    dt, dp = 0.5, 0.3
    original_thetas = [p.theta for p in simple_tsv.primary]
    rotated = apply_rotation(simple_tsv, dt, dp)
    for orig, p in zip(original_thetas, rotated.primary):
        expected = (orig + dt) % TWO_PI
        assert abs(p.theta - expected) < 1e-12

def test_apply_rotation_preserves_amplitudes(simple_tsv):
    rotated = apply_rotation(simple_tsv, 1.0, 0.5)
    for orig, rot in zip(simple_tsv.primary, rotated.primary):
        assert orig.amplitude == rot.amplitude

def test_apply_rotation_maintains_antipodal_invariant(simple_tsv):
    rotated = apply_rotation(simple_tsv, 0.7, 0.3)
    for p, o in zip(rotated.primary, rotated.observation):
        expected = antipodal(p)
        assert abs(o.theta - expected.theta) < 1e-12

def test_apply_rotation_increments_volley_count(simple_tsv):
    assert simple_tsv.volley_count == 0
    rotated = apply_rotation(simple_tsv, 0.1, 0.1)
    assert rotated.volley_count == 1

def test_apply_rotation_updates_accumulator(simple_tsv):
    dt, dp = 0.4, 0.6
    rotated = apply_rotation(simple_tsv, dt, dp)
    assert abs(rotated.rotation_accumulator.theta - dt) < 1e-12
    assert abs(rotated.rotation_accumulator.phi   - dp) < 1e-12

def test_apply_rotation_returns_tsv_not_ssv(simple_tsv):
    rotated = apply_rotation(simple_tsv, 0.1, 0.1)
    assert type(rotated) is ToroidalStateVector

def test_rotation_inverse_roundtrip(simple_tsv):
    dt, dp = 1.234, 0.567
    rotated = apply_rotation(simple_tsv, dt, dp)
    restored = apply_rotation(rotated, -dt, -dp)
    for orig, res in zip(simple_tsv.primary, restored.primary):
        assert abs(orig.theta - res.theta % TWO_PI) < 1e-10


# ─── derive_rotation_key ──────────────────────────────────────────────────────

def test_derive_rotation_key_returns_two_floats():
    dt, dp = derive_rotation_key(256, 128, 128, 7)
    assert isinstance(dt, float)
    assert isinstance(dp, float)

def test_derive_rotation_key_bounded_by_pi():
    # scale = (harmonic/255)*pi ≤ pi, so delta ≤ pi
    for phi in [0, 128, 256, 511]:
        for harmonic in [0, 64, 128, 255]:
            dt, dp = derive_rotation_key(phi, 256, harmonic, 3)
            assert 0.0 <= dt <= math.pi
            assert 0.0 <= dp <= math.pi

def test_derive_rotation_key_zero_harmonic_gives_zero():
    dt, dp = derive_rotation_key(256, 128, 0, 5)
    assert dt == 0.0
    assert dp == 0.0

def test_derive_rotation_key_deterministic():
    k1 = derive_rotation_key(200, 100, 150, 3)
    k2 = derive_rotation_key(200, 100, 150, 3)
    assert k1 == k2

def test_derive_rotation_key_epoch_changes_key():
    k1 = derive_rotation_key(200, 100, 150, 1)
    k2 = derive_rotation_key(200, 100, 150, 2)
    assert k1 != k2


# ─── derive_skyrmion_key ──────────────────────────────────────────────────────

def test_derive_skyrmion_key_returns_three_values():
    dt, dp, dn = derive_skyrmion_key(256, 128, 128, 7)
    assert isinstance(dt, float)
    assert isinstance(dp, float)
    assert isinstance(dn, int)

def test_derive_skyrmion_key_dn_is_quantized():
    for phi in range(0, 512, 64):
        for epoch in range(1, 10):
            _, _, dn = derive_skyrmion_key(phi, 128, 128, epoch)
            assert dn in (-1, 0, 1)

def test_derive_skyrmion_key_continuous_part_matches_rotation_key():
    phi, theta, harmonic, epoch = 300, 150, 200, 5
    dt_sk, dp_sk, _ = derive_skyrmion_key(phi, theta, harmonic, epoch)
    dt_rot, dp_rot  = derive_rotation_key(phi, theta, harmonic, epoch)
    assert dt_sk == dt_rot
    assert dp_sk == dp_rot


# ─── to_skyrmion ──────────────────────────────────────────────────────────────

def test_to_skyrmion_default_winding(simple_tsv):
    ssv = to_skyrmion(simple_tsv)
    assert ssv.winding_number == 1

def test_to_skyrmion_preserves_strands(simple_tsv):
    ssv = to_skyrmion(simple_tsv)
    assert ssv.primary == simple_tsv.primary
    assert ssv.strand_length == simple_tsv.strand_length

def test_to_skyrmion_type(simple_tsv):
    ssv = to_skyrmion(simple_tsv)
    assert isinstance(ssv, SkyrmionStateVector)
    assert isinstance(ssv, ToroidalStateVector)


# ─── apply_skyrmion_rotation ──────────────────────────────────────────────────

def test_apply_skyrmion_rotation_winds_up(simple_ssv):
    result = apply_skyrmion_rotation(simple_ssv, 0.1, 0.1, +1)
    assert result.winding_number == 2

def test_apply_skyrmion_rotation_winds_down(simple_ssv):
    # wind up first
    wound = apply_skyrmion_rotation(simple_ssv, 0.1, 0.1, +1)
    unwound = apply_skyrmion_rotation(wound, 0.1, 0.1, -1)
    assert unwound.winding_number == 1

def test_apply_skyrmion_rotation_collapse_on_negative_winding(simple_ssv):
    with pytest.raises(TopologicalCollapseError):
        apply_skyrmion_rotation(simple_ssv, 0.0, 0.0, -2)  # winding 1-2 = -1

def test_apply_skyrmion_rotation_zero_delta_n_no_collapse(simple_ssv):
    result = apply_skyrmion_rotation(simple_ssv, 0.1, 0.2, 0)
    assert result.winding_number == 1

def test_apply_skyrmion_rotation_returns_ssv(simple_ssv):
    result = apply_skyrmion_rotation(simple_ssv, 0.1, 0.1, 0)
    assert isinstance(result, SkyrmionStateVector)

def test_apply_skyrmion_rotation_preserves_magnon(simple_ssv):
    result = apply_skyrmion_rotation(simple_ssv, 0.1, 0.1, 0)
    assert result.magnon_amplitude == simple_ssv.magnon_amplitude


# ─── Pong: encrypt/decrypt roundtrip ─────────────────────────────────────────

NODE_PARAMS = [
    (128, 90,  200, 5),   # Alpha
    (300, 180, 160, 5),   # Beta
    (450, 270, 80,  5),   # Gamma
]

def test_standard_pong_roundtrip(simple_tsv):
    tsv = simple_tsv
    keys = []
    for phi, theta, harmonic, epoch in NODE_PARAMS:
        dt, dp = derive_rotation_key(phi, theta, harmonic, epoch)
        keys.append((dt, dp))
        tsv = encrypt_volley(tsv, phi, theta, harmonic, epoch)

    decrypted = decrypt_volleys(tsv, keys)
    for orig, dec in zip(simple_tsv.primary, decrypted.primary):
        assert abs(orig.theta - dec.theta % TWO_PI) < 1e-9
        assert abs(orig.phi   - dec.phi   % TWO_PI) < 1e-9

def test_standard_pong_changes_positions(simple_tsv):
    tsv = simple_tsv
    for phi, theta, harmonic, epoch in NODE_PARAMS:
        tsv = encrypt_volley(tsv, phi, theta, harmonic, epoch)
    # At least some positions must have changed
    diffs = [abs(orig.theta - enc.theta)
             for orig, enc in zip(simple_tsv.primary, tsv.primary)]
    assert any(d > 0.01 for d in diffs)

def test_skyrmion_pong_roundtrip(simple_ssv):
    ssv = simple_ssv
    keys = []
    for phi, theta, harmonic, epoch in NODE_PARAMS:
        dt, dp, dn = derive_skyrmion_key(phi, theta, harmonic, epoch)
        keys.append((dt, dp, dn))
        ssv = encrypt_skyrmion_volley(ssv, phi, theta, harmonic, epoch)

    decrypted = decrypt_skyrmion_volleys(ssv, keys)
    assert decrypted.winding_number == simple_ssv.winding_number
    for orig, dec in zip(simple_ssv.primary, decrypted.primary):
        assert abs(orig.theta - dec.theta % TWO_PI) < 1e-9

def test_skyrmion_collapse_on_forced_over_unwind(simple_ssv):
    """Forced negative winding triggers TopologicalCollapseError."""
    with pytest.raises(TopologicalCollapseError):
        apply_skyrmion_rotation(simple_ssv, 0.0, 0.0, -5)


# ─── verify_self_coherence ────────────────────────────────────────────────────

def test_self_coherence_perfect_on_fresh_tsv(simple_tsv):
    result = verify_self_coherence(simple_tsv)
    assert result['coherent'] is True
    assert result['anomaly_count'] == 0
    assert result['coherence_score'] > 0.99

def test_self_coherence_perfect_after_rotation(simple_tsv):
    rotated = apply_rotation(simple_tsv, 1.234, 0.567)
    result = verify_self_coherence(rotated)
    assert result['coherent'] is True

def test_self_coherence_detects_tampered_observation(simple_tsv):
    # Corrupt one observation point
    bad_obs = list(simple_tsv.observation)
    bad_obs[0] = TorusPoint(0.0, 0.0, bad_obs[0].amplitude)
    tampered = ToroidalStateVector(
        origin=simple_tsv.origin,
        primary=simple_tsv.primary,
        observation=bad_obs,
        omega_theta=simple_tsv.omega_theta,
        omega_phi=simple_tsv.omega_phi,
        rotation_accumulator=simple_tsv.rotation_accumulator,
    )
    result = verify_self_coherence(tampered, tolerance=0.001)
    # At least one anomaly detected (the corrupted point)
    assert result['anomaly_count'] >= 1


# ─── angular_drift_from_origin ───────────────────────────────────────────────

def test_angular_drift_zero_for_archival_mode(origin):
    # ARCHIVAL mode: omega_theta=0, omega_phi=0
    tsv = build_tsv([0.5, 0.5, 0.5], origin, 0.0, 0.0)
    # All points at origin — drift should be near zero
    drift = angular_drift_from_origin(tsv)
    assert drift < 1e-10

def test_angular_drift_empty_tsv(origin):
    tsv = build_tsv([], origin, 0.1, 0.1)
    assert angular_drift_from_origin(tsv) == 0.0


# ─── HarmonicMode ────────────────────────────────────────────────────────────

def test_harmonic_mode_values():
    assert HarmonicMode.ACTIVE    in HARMONIC_OMEGA
    assert HarmonicMode.ARCHIVAL  in HARMONIC_OMEGA
    assert len(HARMONIC_OMEGA) == 5

def test_archival_mode_zero_omega():
    omega_t, omega_p = HARMONIC_OMEGA[HarmonicMode.ARCHIVAL]
    assert omega_t == 0.0
    assert omega_p == 0.0

def test_active_mode_fastest_omega():
    omega_t_active,  _ = HARMONIC_OMEGA[HarmonicMode.ACTIVE]
    omega_t_archival, _ = HARMONIC_OMEGA[HarmonicMode.ARCHIVAL]
    assert omega_t_active > omega_t_archival


# ─── amplify_rasengan ────────────────────────────────────────────────────────

def test_amplify_rasengan_increases_magnon(simple_ssv):
    amplified = amplify_rasengan(simple_ssv, 2.0)
    assert amplified.magnon_amplitude == 2.0

def test_amplify_rasengan_caps_amplitude_at_one(simple_ssv):
    amplified = amplify_rasengan(simple_ssv, 10.0)
    for p in amplified.primary:
        assert p.amplitude <= 1.0

def test_amplify_rasengan_preserves_winding(simple_ssv):
    amplified = amplify_rasengan(simple_ssv, 3.0)
    assert amplified.winding_number == simple_ssv.winding_number

def test_amplify_rasengan_increases_phase_lock_sites(simple_ssv):
    amplified = amplify_rasengan(simple_ssv, 4.0)
    assert amplified.phase_lock_sites >= simple_ssv.phase_lock_sites


# ─── charge_rasenshuriken ────────────────────────────────────────────────────

def test_charge_rasenshuriken_winds_to_n(simple_ssv):
    rasenshuriken = charge_rasenshuriken(simple_ssv, n_arms=3, consent_epoch=5)
    assert rasenshuriken.winding_number == 3

def test_charge_rasenshuriken_noop_if_already_wound(simple_ssv):
    already_wound = to_skyrmion(simple_ssv, winding_number=3)
    result = charge_rasenshuriken(already_wound, n_arms=3, consent_epoch=5)
    assert result.winding_number == 3
