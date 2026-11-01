"""Additional finite claims; each test states a mutation that its assertions detect."""

import json
import os
from pathlib import Path

import pytest

from tools.prove_out import completion


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def selected_mutation(monkeypatch):
    mutation = os.environ.get("PROVE_OUT_MUTATION")
    if mutation == "completion_binding":
        monkeypatch.setattr(completion, "is_binding_valid", lambda _: True)
    elif mutation == "completion_matrix":
        monkeypatch.setattr(completion, "can_access_sector", lambda *_: True)
    elif mutation == "completion_grid_guard":
        monkeypatch.setattr(completion, "read_log", lambda _: ({}, {}, {}, {}))
    elif mutation == "completion_projection":
        original = completion.sector_rows
        def changed_rows():
            rows = original()
            rows[0]["projected_theta_v2"] = 2
            return rows
        monkeypatch.setattr(completion, "sector_rows", changed_rows)


def test_all_raw_score_thresholds_and_stages():
    """Mutation: move binding137 to138, skip a score, or return constant stage0."""
    rows = completion.policy_rows()
    assert [r["score"] for r in rows] == list(range(675))
    assert all(r["binding"] == (r["score"] >= 137) for r in rows)
    assert all(r["stage"] == 7 * r["score"] // 674 for r in rows)
    assert [r["score"] for r in rows if r["score"] and r["stage"] != rows[r["score"] - 1]["stage"]] == [97, 193, 289, 386, 482, 578, 674]


def test_all_sector_access_states_and_void_exception():
    """Mutation: allow BRIDGE in emergency, allow nonzero VOID, or omit a state."""
    rows = completion.access_rows()
    expected = {
        "FULL_CONSENT": {"CORE", "GENE", "MEMORY", "WITNESS", "DREAM", "BRIDGE", "GUARDIAN", "SHADOW"},
        "ATTENTIVE": {"MEMORY", "WITNESS", "BRIDGE", "GUARDIAN"},
        "DIMINISHED_CONSENT": {"BRIDGE", "GUARDIAN", "SHADOW"},
        "SUSPENDED_CONSENT": {"BRIDGE", "GUARDIAN"},
        "EMERGENCY_OVERRIDE": {"GUARDIAN"},
    }
    assert len(rows) == 45
    for row in rows:
        assert row["at_674"] == (row["sector"] in expected[row["state"]])
        assert row["at_zero"] == (row["sector"] == "VOID" or row["sector"] in expected[row["state"]])


def test_sector_projection_table_has_every_theta_once():
    """Mutation: remove/reorder a theta row or project theta0 to2 instead of1."""
    rows = completion.sector_table().splitlines()[8:]
    assert len(rows) == 512
    for theta, row in enumerate(rows):
        fields = [s.strip() for s in row.split("|")[1:-1]]
        assert int(fields[0]) == theta
        assert int(fields[2]) == theta * 27 // 512 + 1


def test_real_rtl_comparisons_keep_disagreements_visible():
    """Mutation: silently report equality or remove one threshold/grid point."""
    data = json.loads((ROOT / "results/completion/summary.json").read_text(encoding="utf-8"))
    assert data["score_points"] == 3072
    assert data["score_mismatches"] == {"exact": 0, "approximate": 3060, "lut": 2940}
    assert data["threshold_mismatches"] == {"exact": 0, "approximate": 967, "lut": 345}
    assert data["decreases"] == {"approximate_completion": 63, "approximate_entropy": 5,
                                 "exact_completion": 0, "exact_entropy": 0,
                                 "lut_completion": 32, "lut_entropy": 0}
    assert data["derivation_points"] == 32 and data["named_derivation_mismatches"] == 13
    assert data["fallback_points"] == 207360
    assert data["fallback_component_mismatches"] == {"any": 134400, "theta": 134400, "phi_zero": 0, "omega": 0, "radius": 0}
    assert data["trigger_points"] == 34 and data["condition_inverted_trigger_mismatches"] == 0
    assert data["trigger_first_true_indices"] == [12, 29]


def test_rtl_grid_rejects_missing_rows(tmp_path):
    """Mutation: remove complete-grid validation and accept a partial run."""
    path = tmp_path / "truncated.log"
    path.write_text("DERIVE,0,0,2\n", encoding="utf-8")
    try:
        completion.read_log(path)
    except ValueError as error:
        assert "incomplete" in str(error)
    else:
        assert False, "incomplete RTL evidence was accepted"


def test_rtl_grid_rejects_duplicate_rows(tmp_path):
    """Mutation: overwrite duplicate keys and hide a repeated simulator row."""
    path = tmp_path / "duplicate.log"
    path.write_text("DERIVE,0,0,2\nDERIVE,0,0,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        completion.read_log(path)


def test_rtl_grid_refuses_unknown_and_malformed_values(tmp_path):
    """Mutation: convert unknown x to0 or ignore malformed recognized rows."""
    path = tmp_path / "unknown.log"
    path.write_text("DERIVE,0,0,x\n", encoding="utf-8")
    with pytest.raises(ValueError):
        completion.read_log(path)
    path.write_text("DERIVE,0,0,2,9\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed"):
        completion.read_log(path)


def test_generated_policy_tables_are_byte_repeatable():
    """Mutation: introduce a timestamp, randomness, unstable ordering, or a dropped row."""
    first = (completion.policy_rows(), completion.access_rows(), completion.sector_table())
    assert first == (completion.policy_rows(), completion.access_rows(), completion.sector_table())
    assert len(first[0]) == 675 and len(first[1]) == 45
