"""Finite Python wrap and malformed-fraction counterfactual witnesses."""
import json

import pytest

from rpp import address_canonical as canonical
from tools.prove_out import coherence_cases
from tools.prove_out.verdict_mutations import selected_mutation


def no_wrap_distance(a, b):
    """Runtime counterfactual only; the actual core coherence function still runs."""
    return (0.30 * (abs(a.theta - b.theta) / 13.5)
            + 0.40 * (abs(a.phi - b.phi) / 5.0)
            + 0.20 * (abs(a.omega - b.omega) / 4.0)
            + 0.10 * abs(a.radius - b.radius))


@pytest.fixture(autouse=True)
def selected_runtime_mutation(monkeypatch):
    # Two-factor, test-only gate; the evidence module reads no environment.
    if selected_mutation() == "python-no-wrap":
        monkeypatch.setattr(canonical, "address_distance", no_wrap_distance)


def test_all_ordinary_theta_pairs_match_declared_circular_formula():
    """Executed mutant python-no-wrap substitutes abs-distance in the actual core helper."""
    result = coherence_cases.run_checks()
    summary = result["summary"]["ordinary_theta"]
    assert summary["ordinary_pairs"] == summary["actual_coherence_calls"] == summary["symmetry_checks"] == 729
    assert summary["formula_mismatches"] == summary["symmetry_mismatches"] == summary["range_failures"] == 0
    assert summary["wrap_pairs"] == 182 and summary["maximum"] == 1.0
    rows = {(row["source_theta"], row["target_theta"]): row for row in result["theta_rows"]}
    assert set(rows) == {(a, b) for a in range(1, 28) for b in range(1, 28)}
    assert rows[1, 27]["actual"] == rows[27, 1]["actual"] == 1.0 - 0.30 * (1 / 13.5)


def test_actual_no_wrap_helper_mutation_is_rejected(monkeypatch):
    """Failing mutation omit-declared-formula-check would accept the no-wrap helper."""
    monkeypatch.setattr(canonical, "address_distance", no_wrap_distance)
    with pytest.raises(AssertionError, match="circular"):
        coherence_cases.run_checks()


def test_fractional_counterexamples_record_actual_nonfinite_and_clamping_results():
    """Failing mutations hide-NaN-counterexample or label an out-of-contract call rejected."""
    rows = {row["case"]: row for row in coherence_cases._fractional_counterexamples()}
    assert len(rows) == 10
    for driver, weight, stage in (("engagement", 165, 1), ("completion", 509, 5)):
        for kind in ("negative", "negative-infinity", "above-one", "nan", "positive-infinity"):
            row = rows[driver + "-" + kind]
            expected = 0 if kind in {"negative", "negative-infinity"} else weight
            assert row["score_api"] == row["score"] == expected
            assert row["binding_coefficient"] == expected / 674
            assert row["stage"] == (0 if expected == 0 else stage)
            assert row["completion_flag"] is False
    assert rows["engagement-nan"]["engagement"] == rows["completion-nan"]["completion"] == "NaN"
    assert rows["engagement-nan"]["engagement_weight"] == 165
    assert rows["completion-nan"]["completion_weight"] == 509


def test_strict_json_and_lf_artifacts_ignore_ambient_mutation(monkeypatch):
    """Failing mutations leak-ambient-ID, emit-raw-NaN or switch CSV output to CRLF."""
    monkeypatch.delenv("CX017_MUTATION_RUNNER", raising=False)
    monkeypatch.setenv("CX017_MUTATION", "python-no-wrap")
    assert selected_mutation() is None
    first = coherence_cases.run_checks()
    second = coherence_cases.run_checks()
    assert all(isinstance(row[field], str) for row in first["counterexamples"] for field in ("engagement", "completion"))
    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(second, sort_keys=True, allow_nan=False)
    outputs = coherence_cases.csv_artifacts(first)
    assert outputs == coherence_cases.csv_artifacts(second)
    assert all(b"\r" not in value for value in outputs.values())
    assert len(outputs["python-theta-pairs.csv"].splitlines()) == 730
    assert len(outputs["fractional-input-counterexamples.csv"].splitlines()) == 11
