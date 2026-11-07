"""Synthetic assembly witnesses; these tests perform no native or Cargo runs."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from tools.prove_out import reproduce

def build():
    group = {"cases": [{"name": "synthetic-fixture", "classification": "killed"}], "variants": 1,
             "killed": 1, "equivalent_exclusions": 0, "fail_closed_non_assertion_exclusions": 0,
             "eligible_non_equivalent_survivors": 0}
    receipts = {"schema_version": 2, "source_sha256": {"fixture.py": "a" * 64}}
    receipts.update({name: deepcopy(group) for name in reproduce.MUTATION_GROUPS})
    return {"payload": {"ra": {"points": 3072}, "readouts": {"sector": "PROVED"}},
            "artifacts": {"native.csv": b"input,score\n0,0\n"},
            "receipts": receipts}

def test_equal_complete_inputs_produce_exact_bytes_and_derived_verification():
    """Failing mutation: invent verification hashes, omit receipts, or hash the final summary into itself."""
    first, second = build(), build()
    outputs = reproduce.assemble(first, second)
    assert outputs == reproduce.assemble(deepcopy(first), deepcopy(second))
    assert set(outputs) == {"native.csv", "summary.json", "primary-payload.json", "mutation-receipts.json", "determinism.json"}
    assert outputs["native.csv"] == first["artifacts"]["native.csv"]
    assert outputs["primary-payload.json"] == reproduce.serialize(first["payload"])
    assert outputs["mutation-receipts.json"] == reproduce.serialize(first["receipts"])
    summary, determinism = (json.loads(outputs[name]) for name in ("summary.json", "determinism.json"))
    assert summary["ra"] == first["payload"]["ra"] and summary["readouts"] == first["payload"]["readouts"]
    assert "verification" in summary
    verification = summary["verification"]
    assert verification["schema_version"] == 2 and verification["native_complete_runs"] == 2
    assert verification["whole_summary_byte_identical"] is True
    assert verification["unit_guard_mutations"] == first["receipts"]["unit_guard_mutations"]
    assert all(verification[group] == first["receipts"][group] for group in reproduce.MUTATION_GROUPS)
    assert verification["source_sha256"] == first["receipts"]["source_sha256"]
    for field, name in (("primary_payload_sha256", "primary-payload.json"), ("mutation_receipts_sha256", "mutation-receipts.json"), ("determinism_receipt_sha256", "determinism.json")):
        assert verification[field] == sha256(outputs[name]).hexdigest()
    assert verification["byte_identical_files"] == ["mutation-receipts.json", "native.csv", "primary-payload.json"]
    assert determinism["complete_runs"] == 2 and determinism["byte_identical"] is True
    assert determinism["files"] == {name: {"sha256": sha256(outputs[name]).hexdigest(), "bytes": len(outputs[name])} for name in verification["byte_identical_files"]}
    assert "summary.json" not in determinism["files"] and "determinism.json" not in determinism["files"]

@pytest.mark.parametrize("component", ("payload", "receipts"))
def test_second_run_metric_or_receipt_only_change_is_rejected(component):
    """Failing mutation: compare only artifact bytes and silently retain first-run metrics or receipts."""
    first, second = build(), build()
    if component == "payload":
        second["payload"]["ra"]["points"] += 1
    else:
        second["receipts"]["unit_guard_mutations"]["cases"][0]["name"] = "second-valid-fixture"
    with pytest.raises(AssertionError):
        reproduce.assemble(first, second)


@pytest.mark.parametrize("mutation", ("missing", "changed", "extra"))
def test_second_run_artifact_inventory_or_byte_change_is_rejected(mutation):
    """Failing mutation: ignore a missing/extra artifact or compare names without their exact bytes."""
    first, second = build(), build()
    if mutation == "missing":
        second["artifacts"].pop("native.csv")
    elif mutation == "changed":
        second["artifacts"]["native.csv"] = b"input,score\n0,1\n"
    else:
        second["artifacts"]["extra.csv"] = b"extra\n"
    with pytest.raises(AssertionError):
        reproduce.assemble(first, second)


@pytest.mark.parametrize("name", ("summary.json", "primary-payload.json", "mutation-receipts.json", "determinism.json", "SUMMARY.JSON", "../escape.csv", "/absolute.csv", "a\\b.csv", "a:b.csv", "", ".", "..", "summary.json.", "summary.json ", "data.csv.", "data.csv ", "CON.csv", "nul.csv", "LPT1.csv", "com9.csv", "bad\x00.csv", "bad\x1f.csv", "name .csv", "café.csv"))
def test_reserved_or_unsafe_primary_artifact_names_are_rejected(name):
    """Failing mutation: allow output overwrites, directory escapes, Windows aliases or nonportable names."""
    first = build()
    first["artifacts"] = {name: b"inert\n"}
    with pytest.raises(ValueError):
        reproduce.assemble(first, deepcopy(first))


def test_casefold_artifact_collisions_and_nonbyte_content_are_rejected():
    """Failing mutation: allow Windows case aliases or implicit text encoding in the primary byte inventory."""
    for artifacts in ({"Data.csv": b"one", "data.csv": b"two"}, {"native.csv": "text"}, {"native.csv": bytearray(b"data")}):
        first = dict(build(), artifacts=artifacts)
        with pytest.raises(ValueError):
            reproduce.assemble(first, deepcopy(first))


def test_receipts_cannot_replace_derived_verification_or_its_schema():
    """Failing mutation: accept an old schema, receipt-authored run count, or preexisting payload verification."""
    for mutation in ("old-schema", "reserved-count"):
        first = build()
        first["receipts"]["schema_version" if mutation == "old-schema" else "native_complete_runs"] = 1 if mutation == "old-schema" else 999
        with pytest.raises(ValueError):
            reproduce.assemble(first, deepcopy(first))
    first = build()
    first["payload"]["verification"] = {"whole_summary_byte_identical": True}
    with pytest.raises(ValueError):
        reproduce.assemble(first, deepcopy(first))


@pytest.mark.parametrize("mutation", ("missing", "empty", "empty-cases", "missing-field"))
def test_every_receipt_group_requires_observed_cases_and_all_count_fields(mutation):
    """Failing mutation: skip a required group, accept empty observations or invent a missing count."""
    for name in reproduce.MUTATION_GROUPS:
        first = build()
        if mutation == "missing":
            first["receipts"].pop(name)
        elif mutation == "empty":
            first["receipts"][name] = {}
        elif mutation == "empty-cases":
            first["receipts"][name]["cases"] = []
        else:
            first["receipts"][name].pop("killed")
        with pytest.raises(ValueError):
            reproduce.assemble(first, deepcopy(first))


@pytest.mark.parametrize("mutation", ("empty-receipts", "missing-sources", "empty-sources", "variants-bool", "variants-count", "negative-count", "classification-count", "unknown-classification"))
def test_receipt_sources_and_classification_counts_must_match_actual_case_inventory(mutation):
    """Failing mutation: accept absent fingerprints, bool/negative counts or incoherent case classifications."""
    first = build()
    receipt = first["receipts"]
    group = receipt["unit_guard_mutations"]
    if mutation == "empty-receipts":
        receipt.clear()
    elif mutation == "missing-sources":
        receipt.pop("source_sha256")
    elif mutation == "empty-sources":
        receipt["source_sha256"] = {}
    elif mutation == "unknown-classification":
        group["cases"][0]["classification"] = "unknown"
    else:
        field, value = {"variants-bool": ("variants", True), "variants-count": ("variants", 2),
                        "negative-count": ("killed", -1), "classification-count": ("equivalent_exclusions", 1)}[mutation]
        group[field] = value
    with pytest.raises(ValueError):
        reproduce.assemble(first, deepcopy(first))


def test_serialization_is_canonical_lf_utf8_and_rejects_nonfinite_json():
    """Failing mutation: use insertion order/platform newlines or emit NaN/Infinity JSON tokens."""
    value = {"z": {"b": 2, "a": 1}, "label": "café"}
    data = reproduce.serialize(value)
    assert data == reproduce.serialize(dict(reversed(list(value.items())))) and json.loads(data) == value
    assert data.endswith(b"\n") and b"\r\n" not in data
    for invalid in (float("nan"), float("inf"), -float("inf")):
        with pytest.raises(ValueError):
            reproduce.serialize({"nested": [invalid]})


@pytest.mark.parametrize("value", ([], None, "text", {1: 2}, {False: "bad"}, {(1, 2): "bad"}), ids=("list", "null", "text", "integer-key", "bool-key", "tuple-key"))
def test_serializer_rejects_nonobjects_and_unquoted_nonstring_top_keys(value):
    """Failing unquoted-key mutation emits invalid JSON; missing object guard admits unsupported payloads."""
    with pytest.raises(ValueError):
        reproduce.serialize(value)
