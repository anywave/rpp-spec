"""Synthetic assembly witnesses; these tests perform no native or Cargo runs."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from tools.prove_out import reproduce

def build():
    return {"payload": {"ra": {"points": 3072}, "readouts": {"sector": "PROVED"}},
            "artifacts": {"native.csv": b"input,score\n0,0\n"},
            "receipts": {"schema_version": 2, "guard_mutations": {"killed": 1, "survived": 0}}}

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
    assert verification["guard_mutations"] == first["receipts"]["guard_mutations"]
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
        second["receipts"]["guard_mutations"]["killed"] += 1
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


@pytest.mark.parametrize("name", ("summary.json", "primary-payload.json", "mutation-receipts.json", "determinism.json", "SUMMARY.JSON", "../escape.csv", "/absolute.csv", "a\\b.csv", "a:b.csv", "", ".", ".."))
def test_reserved_or_unsafe_primary_artifact_names_are_rejected(name):
    """Failing mutation: allow a primary artifact to overwrite generated output or escape a flat directory."""
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
    for bad in ({"schema_version": 1}, {"schema_version": 2, "native_complete_runs": 999}):
        first = dict(build(), receipts=bad)
        with pytest.raises(ValueError):
            reproduce.assemble(first, deepcopy(first))
    first = build()
    first["payload"]["verification"] = {"whole_summary_byte_identical": True}
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
