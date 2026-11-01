"""Ruling validation remains active in actual optimized Python subprocesses."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
BASE = "990905c185f14dcb5adec2fdcab295775604656d"
MODES = [False, True]
CORRUPTIONS = [
    "pending_status", "pending_text", "guard_shift", "guard_range",
    "decision_header", "baseline_kind", "source_widths", "approved_wording",
    "generated_ranges",
]

# The child intentionally contains no assert statements: python -O must not
# remove either the implementation checks or the regression's own failure logic.
CHILD = r'''
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from tools.drift import checker, rulings, snapshot
from tools.drift.passages import digest, extract

root = Path.cwd()
case = sys.argv[1]
output = Path(sys.argv[2])
base = sys.argv[3]
original = json.loads(checker.blob(root, rulings.REVISION, "tools/drift/catalog.json"))

def source(revision, path):
    value = checker.blob(root, revision, path)
    if revision != rulings.REVISION:
        return value
    if case == "decision_header" and path == "DECISIONS.md":
        return value.replace("### [RFC] CX-006-D1 ", "### [RFC] CX-006-D0 ", 1)
    if case == "baseline_kind" and path == "rpp/continuity.py":
        passage = next(p for p in extract(path, value) if p.line == 269 and p.kind == "docstring")
        lines = value.split("\n")
        lines[passage.line - 1:passage.end] = ["    # Replaced docstring passage"] * (passage.end - passage.line + 1)
        return "\n".join(lines)
    if case == "source_widths" and path == "VERSION_POLICY.md":
        return value.replace("| Theta field position | Bits 31:27 |", "| Theta field position | Bits 30:26 |", 1)
    if case == "approved_wording" and path == "VERSION_POLICY.md":
        return value.replace("(r_enc << 13)", "(r_bad << 13)", 1)
    return value

if case == "snapshot_cli":
    def invalid_source(revision, path):
        value = checker.blob(root, revision, path)
        if revision == rulings.REVISION and path == "DECISIONS.md":
            value = value.replace("### [RFC] CX-006-D1 ", "### [RFC] CX-006-D0 ", 1)
        return value

    raw_blob = snapshot.blob
    def snapshot_blob(repository, revision, path):
        if Path(repository).resolve() != root.resolve():
            raise RuntimeError("Snapshot left its intended checkout")
        return invalid_source(revision, path)

    snapshot.blob = snapshot_blob
    snapshot.DATA = output / "unexpected-snapshot.json"
    sys.argv = ["snapshot"]
    status = snapshot.main()
    if status != 2:
        raise RuntimeError("Invalid snapshot source did not return status 2")
    if snapshot.DATA.exists():
        raise RuntimeError("Invalid snapshot source wrote a catalog")
    raise SystemExit(status)

if case == "note":
    current = checker.load_catalog()
    prior = json.loads(checker.blob(root, base, "tools/drift/catalog.json"))
    stripped = deepcopy(current)
    entry = next(item for item in stripped["baselines"] if item["id"] == "F-BASE-0038")
    if entry.pop("note", None) != rulings.NOTE_0038:
        raise RuntimeError("The exact 0038 explanation is missing")
    if stripped != prior:
        raise RuntimeError("Metadata changed beyond the exact 0038 note")

    foundation = deepcopy(prior)
    foundation.pop("catalog_revision")
    foundation.pop("rulings")
    groups = ("baselines", "guards", "steward_items", "advisories")
    for group in groups:
        foundation[group] = [item.get("original", item) for item in foundation[group]]
    approved = {group: [item for item in prior[group] if "original" in item] for group in groups}
    approved["rulings"] = prior["rulings"]
    def signature(value):
        data = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(data).hexdigest()
    if signature(foundation) != checker.FOUNDATION_SHA256:
        raise RuntimeError("The frozen foundation fingerprint changed")
    if signature(approved) != checker.APPROVED_OVERLAY_SHA256:
        raise RuntimeError("The approved-overlay fingerprint changed")

    target = output / "invalid-note.json"
    for invalid in (None, rulings.NOTE_0038 + " Unapproved suffix."):
        corrupted = deepcopy(current)
        item = next(item for item in corrupted["baselines"] if item["id"] == "F-BASE-0038")
        if invalid is None:
            item.pop("note")
        else:
            item["note"] = invalid
        target.write_text(json.dumps(corrupted), encoding="utf-8")
        try:
            checker.load_catalog(target)
        except checker.ToolError:
            pass
        else:
            raise RuntimeError("Invalid or absent explanatory note was accepted")
    print("NOTE_ONLY_AND_INVALID_NOTES_REJECTED")
    raise SystemExit(0)

if case == "pending_status":
    original["baselines"][0]["status"] = "ruled - RADIX CX-006"
elif case == "pending_text":
    item = original["baselines"][0]
    item["text"] += " Unapproved replacement."
    item["sha256"] = digest(item["text"])
elif case == "guard_shift":
    original["guards"][0]["text"] = original["guards"][0]["text"].replace("Bits 31:27", "Bits 30:26", 1)
elif case == "guard_range":
    original["guards"][2]["text"] = original["guards"][2]["text"].replace("| Radius | 0 | 255 |", "| Radius | 0 | 254 |", 1)
elif case == "generated_ranges":
    class ChangedRange(str):
        def replace(self, old, new, count=-1):
            changed = super().replace(old, new, count)
            if old == "Normalized 0-1":
                changed = changed.replace("| Radius | 0 | 255 |", "| Radius | 0 | 254 |", 1)
            return changed
    original["guards"][2]["text"] = ChangedRange(original["guards"][2]["text"])

if case == "clean":
    if not issubclass(rulings.RulingError, ValueError):
        raise RuntimeError("RulingError must remain a ValueError subtype")
    rebuilt = rulings.apply_rulings(original, source)
    if rebuilt != checker.load_catalog():
        raise RuntimeError("Clean rule application differs from the checked catalog")
    print("CLEAN_EXACT_OVERLAY")
    raise SystemExit(0)

messages = {
    "pending_status": "Frozen ruling input differs",
    "pending_text": "Frozen ruling input differs",
    "guard_shift": "Frozen ruling input differs",
    "guard_range": "Frozen ruling input differs",
    "decision_header": "section header differs",
    "baseline_kind": "passage kind changed",
    "source_widths": "field widths or positions",
    "approved_wording": "beyond approved wording",
    "generated_ranges": "fields or ranges",
}
try:
    rulings.apply_rulings(original, source)
except rulings.RulingError as error:
    if messages[case] not in str(error):
        raise RuntimeError("A different validation branch rejected " + case + ": " + str(error))
    print("REJECTED " + case)
else:
    raise RuntimeError("Invalid ruling input accepted: " + case)
'''


def run_child(tmp_path, optimized, case):
    command = [sys.executable]
    if optimized:
        command.append("-O")
    command += ["-c", CHILD, case, str(tmp_path), BASE]
    environment = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
    return subprocess.run(command, cwd=ROOT, env=environment, capture_output=True,
                          encoding="utf-8", timeout=60, check=False)


@pytest.mark.parametrize("optimized", MODES, ids=["normal", "optimized"])
def test_clean_ruling_overlay_matches_catalog_in_both_python_modes(tmp_path, optimized):
    """Failing mutation: reject valid input or omit the exact 0038 note during rebuilding."""
    result = run_child(tmp_path, optimized, "clean")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "CLEAN_EXACT_OVERLAY"


@pytest.mark.parametrize("case", CORRUPTIONS, ids=CORRUPTIONS)
@pytest.mark.parametrize("optimized", MODES, ids=["normal", "optimized"])
def test_invalid_ruling_inputs_fail_in_real_optimized_subprocess(tmp_path, optimized, case):
    """Failing mutation: remove a require_ruling check or restore an optimization-disabled assert."""
    result = run_child(tmp_path, optimized, case)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "REJECTED " + case
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("optimized", MODES, ids=["normal", "optimized"])
def test_only_exact_0038_note_is_added_and_invalid_notes_are_rejected(tmp_path, optimized):
    """Failing mutation: broaden the fingerprint exclusion or accept altered/missing 0038 notes."""
    result = run_child(tmp_path, optimized, "note")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "NOTE_ONLY_AND_INVALID_NOTES_REJECTED"


@pytest.mark.parametrize("optimized", MODES, ids=["normal", "optimized"])
def test_snapshot_cli_invalid_source_returns_two_without_traceback(tmp_path, optimized):
    """Failing mutation: stop catching RulingError or write a snapshot after invalid source validation."""
    result = run_child(tmp_path, optimized, "snapshot_cli")
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert result.stderr.strip() == "snapshot: tool error: invalid ruling source or catalog"
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "unexpected-snapshot.json").exists()
