"""Invalid coordinator metadata is an incomplete review, never clean/drift status."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from tools.drift import checker


ROOT = Path(__file__).resolve().parents[3]
CATALOG = json.loads(checker.DATA.read_text(encoding="utf-8"))


def write_catalog(tmp_path, value):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8", newline="\n")
    return path


def corrupt(name):
    value = deepcopy(CATALOG)
    if name == "not_object":
        return []
    if name == "missing_rules":
        value.pop("rules")
    elif name == "zero_rules":
        value["rules"] = []
    elif name == "unknown_rule":
        value["rules"][0]["rule_id"] = "UNKNOWN-1"
    elif name == "duplicate_rule":
        value["rules"][1] = deepcopy(value["rules"][0])
    elif name == "missing_rule_field":
        value["rules"][0].pop("severity")
    elif name == "downgraded_rule":
        value["rules"][0]["severity"] = "LOW"
    elif name == "radius_wrong_tag":
        next(r for r in value["rules"] if r["rule_id"] == "VER-RADIUS-API")["tag"] = "IMPOSED"
    elif name == "ties_wrong_tag":
        next(r for r in value["rules"] if r["rule_id"] == "VER-RADIUS-TIES")["tag"] = "SOURCED"
    elif name == "bad_guard":
        value["guards"][0]["path"] = []
    elif name == "missing_guard_field":
        value["guards"][0].pop("rule_id")
    elif name == "unknown_guard_rule":
        value["guards"][0]["rule_id"] = "UNKNOWN-1"
    elif name == "accepted_baseline":
        value["baselines"][0]["status"] = "accepted"
    elif name == "zero_baselines":
        value["baselines"] = []
    elif name == "duplicate_baseline_id":
        value["baselines"][1]["id"] = value["baselines"][0]["id"]
    elif name == "baseline_hash_mismatch":
        value["baselines"][0]["sha256"] = "0" * 64
    elif name == "baseline_boolean_line":
        value["baselines"][0]["line"] = True
    elif name == "missing_baseline_text":
        value["baselines"][0].pop("text")
    elif name == "missing_anchor":
        value["software_must_anchors"].pop()
    elif name == "anchor_hash_mismatch":
        value["software_must_anchors"][0]["sha256"] = "0" * 64
    elif name == "accepted_steward":
        value["steward_items"][0]["status"] = "accepted"
    elif name == "steward_wrong_passages_type":
        value["steward_items"][0]["passages"] = {}
    elif name == "missing_steward_passage_field":
        value["steward_items"][0]["passages"][0].pop("end")
    elif name == "accepted_advisory":
        value["advisories"][0]["status"] = "accepted"
    elif name == "zero_scanned_paths":
        value["scanned_paths"] = []
    elif name == "bool_survey_count":
        value["rules_not_checkable"] = True
    elif name == "missing_source_revision":
        value.pop("source_revision")
    elif name == "wrong_container_type":
        value["address_paths"] = "rpp/address.py"
    else:
        raise ValueError("unknown catalog test mutation")
    return value


CORRUPTIONS = [
    "not_object", "missing_rules", "zero_rules", "unknown_rule", "duplicate_rule", "missing_rule_field",
    "downgraded_rule", "radius_wrong_tag", "ties_wrong_tag", "bad_guard", "missing_guard_field",
    "unknown_guard_rule", "accepted_baseline", "zero_baselines", "duplicate_baseline_id",
    "baseline_hash_mismatch", "baseline_boolean_line", "missing_baseline_text", "missing_anchor",
    "anchor_hash_mismatch", "accepted_steward", "steward_wrong_passages_type", "missing_steward_passage_field",
    "accepted_advisory", "zero_scanned_paths", "bool_survey_count", "missing_source_revision", "wrong_container_type",
]


@pytest.mark.parametrize("name", CORRUPTIONS)
def test_invalid_catalog_is_tool_error(tmp_path, name):
    path = write_catalog(tmp_path, corrupt(name))
    caught = False
    try:
        checker.load_catalog(path)
    except checker.ToolError:
        caught = True
    assert caught, f"Invalid catalog was accepted: {name}"


def test_valid_catalog_control(tmp_path):
    path = write_catalog(tmp_path, CATALOG)
    assert checker.load_catalog(path) == CATALOG


@pytest.mark.parametrize("name", ["missing_rules", "zero_rules", "missing_baseline_text", "accepted_steward"])
def test_invalid_catalog_cli_status_two_without_reports(tmp_path, monkeypatch, capsys, name):
    from tools.drift import __main__ as command

    path = write_catalog(tmp_path, corrupt(name))
    monkeypatch.setattr(checker, "DATA", path)
    output = tmp_path / "reports"
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(sys, "argv", ["drift", "check", "--base", checker.SOURCE_REVISION,
                                     "--head", checker.SOURCE_REVISION, "--output-dir", str(output)])
    assert command.main() == 2
    capture = capsys.readouterr()
    assert "Traceback" not in capture.err
    assert "catalog" in capture.err
    assert not (output / "drift-report.json").exists()


@pytest.mark.parametrize("payload", [b"{broken", b"\xff", b"null", b"true"])
def test_invalid_catalog_bytes_are_tool_error(tmp_path, payload):
    path = tmp_path / "catalog.json"
    path.write_bytes(payload)
    caught = False
    try:
        checker.load_catalog(path)
    except checker.ToolError:
        caught = True
    assert caught


@pytest.mark.parametrize("error", [KeyError("do-not-print-me"), TypeError("do-not-print-me")])
def test_unexpected_metadata_error_is_sanitized_exit_two(tmp_path, monkeypatch, capsys, error):
    from tools.drift import __main__ as command

    def fail(*_):
        raise error

    monkeypatch.setattr(command, "check", fail)
    monkeypatch.setattr(sys, "argv", ["drift", "check", "--base", checker.SOURCE_REVISION,
                                     "--head", checker.SOURCE_REVISION, "--output-dir", str(tmp_path)])
    assert command.main() == 2
    capture = capsys.readouterr()
    assert "Traceback" not in capture.err
    assert "do-not-print-me" not in capture.err
    assert "invalid coordinator metadata" in capture.err
