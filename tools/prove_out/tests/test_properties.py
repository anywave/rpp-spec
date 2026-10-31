"""Finite-domain claims and counterexamples; all mutations are named in README."""

from collections import Counter
from fractions import Fraction
import math
import os
import sys

import pytest

from rpp.address import from_components, from_raw
from rpp.address_canonical import RPPAddress, ThetaSector, coherence
from rpp.coherence import compute_coherence_score, compute_binding_coefficient, compute_complecount, is_binding_valid
from rpp.consent import Sector, ConsentContext, ConsentState, check_consent
from rpp.consent_header import ConsentState as HeaderState
from rpp.geometry import TorusPoint, ToroidalStateVector, antipodal, verify_self_coherence
from rpp.sector_router import RoutableSector, can_access_sector, is_universal_access
from rpp.transitions import FallbackGate
from tools.prove_out import proposed
from tools.prove_out.experiments import sweeps, sector_rows, render
from hardware.verilog.spintronic_sim import SpinSite, SHELL_T2, RAC_T2_MULT


@pytest.fixture(autouse=True)
def in_memory_mutant(monkeypatch):
    mutation = os.environ.get("PROVE_OUT_MUTATION")
    module = sys.modules[__name__]
    if mutation == "score_max":
        monkeypatch.setattr(module, "compute_coherence_score", lambda *_: 0)
    elif mutation == "binding_threshold":
        monkeypatch.setattr(module, "is_binding_valid", lambda *_: True)
    elif mutation == "legacy_boundary":
        monkeypatch.setattr(Sector, "from_theta", classmethod(lambda cls, _: cls.GENE))
    elif mutation == "proposal_theta":
        monkeypatch.setattr(proposed, "address_affinity", lambda *_: 1.0)
    elif mutation == "proposal_progress":
        monkeypatch.setattr(proposed, "progress_index", lambda *_: Fraction(0))
    elif mutation == "complement":
        monkeypatch.setattr(module, "verify_self_coherence", lambda _: dict(coherence_score=1.0, coherent=True, anomaly_count=0))
    elif mutation == "spin_decay":
        monkeypatch.setattr(SpinSite, "step", lambda *_args, **_kwargs: None)


def test_weighted_score_formula_and_monotonicity():
    # 10,201 fixed input pairs; increasing either supplied fraction cannot lower score.
    for e in range(101):
        for c in range(101):
            actual = compute_coherence_score(e / 100, c / 100)
            assert actual == int(165 * (e / 100)) + int(509 * (c / 100))
            assert 0 <= actual <= 674
            if e:
                assert actual >= compute_coherence_score((e - 1) / 100, c / 100)
            if c:
                assert actual >= compute_coherence_score(e / 100, (c - 1) / 100)


def test_binding_and_stage_all_raw_scores():
    for score in range(675):
        assert is_binding_valid(compute_binding_coefficient(score)) == (score >= 137)
        assert compute_complecount(score) == 7 * score // 674


def test_nonfinite_input_is_not_rejected_by_shipped_score():
    # Characterization of a declared-domain edge, not evidence of calibration.
    assert compute_coherence_score(float("nan"), 0.0) == 165


def test_valid_address_similarity_is_symmetric_bounded_and_identity():
    points = [RPPAddress(t, p, w, r) for t in range(1, 28) for p in (1, 6) for w in (0, 4) for r in (0.0, 1.0)]
    for a in points:
        assert coherence(a, a) == 1.0
        for b in points:
            assert 0 <= coherence(a, b) <= 1
            assert coherence(a, b) == coherence(b, a)


def test_reserved_constructor_states_break_unqualified_similarity_claim():
    a = RPPAddress(1, 1, 0, 0.0)
    assert coherence(a, RPPAddress(31, 1, 0, 0.0)) > 1.0
    null = RPPAddress(0, 1, 0, 0.0)
    assert coherence(null, null) == 0.7


def test_complement_consistency_declines_with_one_input_drift():
    p = TorusPoint(0.5, 0.7, 1.0)
    a = antipodal(p)
    values = []
    for tick in range(11):
        o = TorusPoint(a.theta + tick / 500, a.phi, a.amplitude)
        tsv = ToroidalStateVector(p, [p], [o], 0.0, 0.0, TorusPoint(0.0, 0.0, 0.0))
        values.append(verify_self_coherence(tsv)["coherence_score"])
    assert values[0] == 1.0 and values[-1] == 0.0
    assert values == sorted(values, reverse=True)


@pytest.mark.parametrize("value,allowed", [(0.399999, False), (0.4, True), (0.400001, True)])
def test_consent_threshold_is_caller_input_not_binding_threshold(value, allowed):
    context = ConsentContext(ConsentState.FULL_CONSENT, soul_id="synthetic-local-id", coherence_score=value)
    assert check_consent(96, 450, "write", context).allowed is allowed
    assert compute_binding_coefficient(137) < 0.4


def test_fallback_requires_thirteen_not_twelve_below_threshold_updates():
    gate = FallbackGate()
    for _ in range(12):
        assert gate.update(136) is False
    assert gate.update(136) is True
    assert gate.update(137) is False


def test_v1_partition_is_total_disjoint_and_matches_consent_for_all_theta():
    labels = [Sector.from_theta(t).value for t in range(512)]
    counts = Counter(labels)
    assert set(counts.values()) == {64} and len(counts) == 8
    for t in range(512):
        assert from_components(0, t, 0, 0).sector_name.lower() == labels[t]
        intervals = [(name, range(i * 64, (i + 1) * 64)) for i, name in enumerate(counts)]
        assert sum(t in interval for _, interval in intervals) == 1


def test_v1_sector_is_independent_of_other_fields():
    for t in range(512):
        expected = Sector.from_theta(t).value
        for shell in range(4):
            for phi in (0, 255, 511):
                for harmonic in (0, 127, 255):
                    a = from_components(shell, t, phi, harmonic)
                    assert from_raw(a.raw).sector_name.lower() == expected


def test_v2_ordinary_sector_ranges_are_total_and_disjoint():
    expected = [("CORE", 1, 3), ("GENE", 4, 6), ("MEMORY", 7, 10), ("WITNESS", 11, 13),
                ("DREAM", 14, 17), ("BRIDGE", 18, 20), ("GUARDIAN", 21, 24), ("SHADOW", 25, 27)]
    for theta in range(1, 28):
        matches = [name for name, first, last in expected if first <= theta <= last]
        assert matches == [ThetaSector.from_theta(theta).name]


def test_cross_layer_projection_is_lossy_not_name_stable():
    rows = sector_rows()
    assert sum(row["same_name"] for row in rows) == 36
    assert sum(not row["same_name"] for row in rows) == 476


def test_authorization_uses_runtime_matrix_not_universal_label():
    assert is_universal_access(RoutableSector.BRIDGE)
    assert not can_access_sector(HeaderState.EMERGENCY_OVERRIDE, RoutableSector.BRIDGE, 674)
    assert can_access_sector(HeaderState.EMERGENCY_OVERRIDE, RoutableSector.VOID, 0)
    assert not can_access_sector(HeaderState.EMERGENCY_OVERRIDE, RoutableSector.VOID, 674)


def test_proposed_progress_has_explicit_counts_and_exact_endpoints():
    assert proposed.progress_index(0, 10, 0, 10) == 0
    assert proposed.progress_index(10, 10, 10, 10) == 1
    assert proposed.progress_index(1, 2, 1, 2) == Fraction(1, 2)


@pytest.mark.parametrize("values", [(True, 2, 1, 2), (1, 0, 1, 2), (3, 2, 1, 2), (1, 2, -1, 2)])
def test_proposed_progress_rejects_undefined_inputs(values):
    with pytest.raises(ValueError):
        proposed.progress_index(*values)


def test_proposed_affinity_reaches_both_endpoints():
    a = (1, 1, 0, 0.0)
    assert proposed.address_affinity(a, a) == 1.0
    assert proposed.address_affinity(a, (14, 6, 4, 1.0)) == 0.0


@pytest.mark.parametrize("a", [(0, 1, 0, 0.0), (31, 1, 0, 0.0), (1, 8, 0, 0.0), (1, 1, 0, float("nan")), (1, 1, 0, True)])
def test_proposed_affinity_refuses_reserved_and_nonfinite_states(a):
    with pytest.raises(ValueError):
        proposed.address_affinity(a, (1, 1, 0, 0.0))


def test_sweep_bytes_are_repeatable_and_have_one_changed_input():
    first = sweeps()
    assert len(first) == 150
    assert first == sweeps()
    assert render(first).encode("utf-8") == render(sweeps()).encode("utf-8")


def test_isolated_spin_site_implements_its_exponential_simulation():
    values = []
    for tick in range(11):
        site = SpinSite(1, 1, 0)
        site.excite(0.8)
        initial = site.coherence
        site.step(tick * 10, 0.01)
        expected = initial * math.exp(-(tick * 10) / (SHELL_T2[0] * RAC_T2_MULT[1]))
        assert math.isclose(site.coherence, expected, rel_tol=1e-12, abs_tol=1e-15)
        values.append(site.coherence)
    assert values == sorted(values, reverse=True) and values[-1] < values[0]
