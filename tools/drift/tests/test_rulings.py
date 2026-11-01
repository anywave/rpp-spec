"""Exact ruling transitions are narrow permissions, not future passage waivers."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from tools.drift import checker, snapshot
from tools.drift.passages import digest, extract
from tools.drift.tests.test_checker import repo as repo_fixture


ROOT = Path(__file__).resolve().parents[3]
repo = repo_fixture
REVISION = "5677ea21b5ba3320109dc7dcb61d4b4c22b5881a"
BEFORE = "275a115efad591304221e832c194a75f7749f9b0"
RULED_IDS = {"F-BASE-0038", "F-BASE-0049", "F-BASE-0213", "F-BASE-0221"}
EXPECTED_FINDINGS = [
    ("VER-FORMAT-1", "HIGH", "VERSION_POLICY.md", 70, "A1"),
    ("VER-FORMAT-1", "HIGH", "VERSION_POLICY.md", 83, "A1"),
    ("BND-F-2", "MEDIUM", "DECISIONS.md", 78, "D3"),
    ("BND-F-2", "MEDIUM", "spec/SPINTRONIC.md", 288, "D3"),
    ("BND-F-2", "MEDIUM", "spec/SPINTRONIC.md", 311, "D3"),
    ("BND-F-BASELINE-REMOVED", "MEDIUM", "rpp/continuity.py", 276, "D4"),
    ("BND-F-BASELINE-REMOVED", "MEDIUM", "spec/CCQPSG.md", 108, "D2"),
    ("STEWARD-CLAIM-1", "MEDIUM", "rpp/continuity.py", 276, "D4"),
    ("STEWARD-RADIUS-DERIVATION", "MEDIUM", "spec/ADDRESSING-LAYERS.md", 142, "D1"),
    ("STEWARD-RADIUS-DERIVATION", "MEDIUM", "spec/RPP-CANONICAL-v2.md", 347, "D1"),
    ("STEWARD-T2-1", "MEDIUM", "spec/SPINTRONIC.md", 288, "D3"),
    ("STEWARD-T2-1", "MEDIUM", "spec/SPINTRONIC.md", 311, "D3"),
    ("STEWARD-TTL-1", "MEDIUM", "spec/CCQPSG.md", 108, "D2"),
    ("STEWARD-TTL-1", "MEDIUM", "spec/SPEC.md", 94, "D2"),
    ("WORD-RADIUS-1", "LOW", "VERSION_POLICY.md", 70, "A1"),
    ("WORD-RADIUS-1", "LOW", "VERSION_POLICY.md", 74, "A1"),
    ("WORD-RADIUS-1", "LOW", "VERSION_POLICY.md", 83, "A1"),
    ("WORD-RADIUS-1", "LOW", "spec/ADDRESSING-LAYERS.md", 114, "A1"),
    ("WORD-RADIUS-1", "LOW", "spec/PMA-SCHEMA-v1.md", 116, "A1"),
    ("WORD-RADIUS-1", "LOW", "spec/README.md", 92, "A1"),
]


def record(path="spec/SPINTRONIC.md", line=288):
    return next(x for x in checker.load_catalog()["rulings"]["findings"]
                if x["rule_id"] == "BND-F-2" and x["path"] == path and x["line"] == line)


def reported(report, rule, path, severity="MEDIUM"):
    return any((x["rule_id"], x["path"], x["severity"]) == (rule, path, severity)
               for x in report["findings"])


def transition(repo, old, new, path="spec/SPINTRONIC.md"):
    base, head = repo.range((path, "# Fixture\n\n" + old + "\n", "# Fixture\n\n" + new + "\n"))
    return checker.check(repo.path, base, head)


def reject_catalog(tmp_path, catalog):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    caught = False
    try:
        checker.load_catalog(path)
    except checker.ToolError:
        caught = True
    assert caught, "Unauthorized catalog revision was accepted"


def test_exact_twenty_findings_retain_git_and_decision_provenance():
    """Mutation: omit/relabel a ledger entry, change its source hash, or invent decision provenance."""
    catalog = checker.load_catalog()
    rulings = catalog["rulings"]
    assert rulings["source_revision"] == REVISION
    assert rulings["original_range_base"] == BEFORE
    assert rulings["authority"] == "RADIX"
    assert rulings["authorization"] == (
        "CX-007; trellis-channel c098c20e; inbox blob 1b01db5d154c6b237324f7fe5ad779b3ea1154c7"
    )
    actual = [(x["rule_id"], x["severity"], x["path"], x["line"], x["decision_id"].removeprefix("CX-006-"))
              for x in rulings["findings"]]
    assert actual == EXPECTED_FINDINGS
    for finding in rulings["findings"]:
        for side, revision in (("before", BEFORE), ("after", REVISION)):
            source = checker.blob(ROOT, revision, finding["path"])
            if not source:
                assert side == "before" and finding[side] is None
                continue
            line = 85 if side == "after" and finding["path"] == "VERSION_POLICY.md" and finding["line"] == 83 else finding["line"]
            p = next(p for p in extract(finding["path"], source) if p.line <= line <= p.end)
            assert finding[side] == {key: getattr(p, key) for key in ("path", "line", "end", "kind", "text", "sha256")}
        if finding["before"] is None:
            raw = checker.blob(ROOT, REVISION, finding["path"]).encode("utf-8")
            assert finding["created_file_sha256"] == hashlib.sha256(raw).hexdigest()
    decisions_text = checker.blob(ROOT, REVISION, "DECISIONS.md")
    assert set(rulings["decisions"]) == {"CX-006-D1", "CX-006-D2", "CX-006-D3", "CX-006-D4", "CX-006-A1"}
    for key, decision in rulings["decisions"].items():
        assert decision["id"] == key and decision["path"] == "DECISIONS.md"
        assert decision["authority"] == "RADIX" and decision["date"] == "2026-10-31"
        assert decision["text"] in decisions_text
        assert decision["text"].startswith("### [RFC] " + key + " ")
        assert decision["sha256"] == digest(decision["text"])


def test_only_four_baselines_and_two_guard_blocks_change_from_frozen_catalog():
    """Mutation: alter any pending baseline field or change another format guard under the ruling overlay."""
    catalog = checker.load_catalog()
    original = json.loads(checker.blob(ROOT, REVISION, "tools/drift/catalog.json"))
    old = {x["id"]: x for x in original["baselines"]}
    assert len(catalog["baselines"]) == 243
    ruled = [x for x in catalog["baselines"] if x["id"] in RULED_IDS]
    pending = [x for x in catalog["baselines"] if x["id"] not in RULED_IDS]
    assert len(ruled) == 4 and len(pending) == 239
    assert {x["id"] for x in ruled} == RULED_IDS
    for entry in pending:
        assert entry == old[entry["id"]]
    for entry in ruled:
        assert entry["original"] == old[entry["id"]]
        assert entry["status"] == "ruled - RADIX CX-006"
        assert entry["route"].startswith("[RFC] " + entry["decision_id"] + "; DECISIONS.md:")
        assert entry["route"].endswith("; RADIX 2026-10-31")
    assert len([g for g in catalog["guards"] if "original" in g]) == 2
    assert [g.get("original", g) for g in catalog["guards"]] == original["guards"]
    for key in ("rules", "software_must_anchors", "scanned_paths", "source_revision", "boundary_text_paths", "core_globs", "address_paths", "vector_globs"):
        assert catalog[key] == original[key]


def test_snapshot_rebuild_matches_the_pinned_overlay(tmp_path, monkeypatch):
    """Mutation: rebuild from mutable metadata or omit a ruling/provenance field from the deterministic snapshot."""
    monkeypatch.setattr(snapshot, "DATA", tmp_path / "snapshot.json")
    assert snapshot.revise_catalog(ROOT) == checker.load_catalog()
    first_generated = snapshot.DATA.read_bytes()
    assert snapshot.revise_catalog(ROOT) == checker.load_catalog()
    assert snapshot.DATA.read_bytes() == first_generated


def test_nonruled_baseline_status_change_is_rejected(tmp_path):
    """Mutation: permit a nonruled baseline to claim the ruled status or bypass catalog validation."""
    catalog = deepcopy(checker.load_catalog())
    entry = next(x for x in catalog["baselines"] if x["id"] not in RULED_IDS)
    entry["status"] = "ruled - RADIX CX-006"
    reject_catalog(tmp_path, catalog)


def test_nonruled_metadata_change_is_rejected(tmp_path):
    """Mutation: validate only pending status while allowing its frozen route/provenance to change."""
    catalog = deepcopy(checker.load_catalog())
    entry = next(x for x in catalog["baselines"] if x["id"] not in RULED_IDS)
    entry["route"] += "; unapproved metadata"
    reject_catalog(tmp_path, catalog)


def test_ruled_identity_change_is_rejected(tmp_path):
    """Mutation: omit the approved-overlay fingerprint and accept an edited approved passage/hash pair."""
    catalog = deepcopy(checker.load_catalog())
    entry = next(x for x in catalog["baselines"] if x["id"] in RULED_IDS)
    entry["text"] += " Unapproved extra wording."
    entry["sha256"] = digest(entry["text"])
    reject_catalog(tmp_path, catalog)


def test_exact_historical_transition_is_clean(repo):
    """Mutation: refuse the exact approved old-to-new transition (clean control for narrow permissions)."""
    item = record()
    report = transition(repo, item["before"]["text"], item["after"]["text"])
    assert report["findings"] == []


def test_full_authorized_history_replays_clean():
    """Mutation: retain superseded guards or omit an exact ruling permission from the real CX-006 replay."""
    report = checker.check(ROOT, BEFORE, REVISION)
    assert report["findings"] == []


def test_future_ruled_passage_change_reports_medium(repo):
    """Mutation: treat a ruled baseline or approved path as a waiver for future changed physics passages."""
    item = record()
    before = item["after"]["text"]
    report = transition(repo, before, before.replace("experimental", "characterized"))
    assert reported(report, "BND-F-2", item["path"])


def test_future_ruled_passage_deletion_reports_medium(repo):
    """Mutation: stop watching the approved current identity after a baseline becomes ruled."""
    item = record()
    report = transition(repo, item["after"]["text"], "An ordinary replacement note.")
    assert reported(report, "BND-F-BASELINE-REMOVED", item["path"])


def test_duplicate_approved_text_reports_medium(repo):
    """Mutation: suppress every occurrence of an approved after-hash, including a new duplicate."""
    item = record()
    approved = item["after"]["text"]
    report = transition(repo, approved, approved + "\n\n" + approved)
    assert reported(report, "BND-F-2", item["path"])


def test_wrong_path_transition_reports_medium(repo):
    """Mutation: drop the permission's exact-path comparison for an otherwise matching old-to-new pair."""
    item = record()
    report = transition(repo, item["before"]["text"], item["after"]["text"], "spec/WRONG.md")
    assert reported(report, "BND-F-2", "spec/WRONG.md")


def test_wrong_before_hash_transition_reports_medium(repo):
    """Mutation: allow an approved after-hash without requiring its actual paired old passage hash."""
    item = record()
    before = item["before"]["text"].replace("routing decision", "routing action")
    assert digest(before) != item["before"]["sha256"]
    report = transition(repo, before, item["after"]["text"])
    assert reported(report, "BND-F-2", item["path"])


def test_exact_decisions_creation_is_clean(repo):
    """Mutation: reject the exact approved file creation despite its matching whole-file provenance."""
    base = repo.commit()
    repo.write("DECISIONS.md", checker.blob(ROOT, REVISION, "DECISIONS.md"))
    report = checker.check(repo.path, base, repo.commit())
    assert report["findings"] == []


def test_modified_decisions_creation_reports_medium(repo):
    """Mutation: skip whole-created-file SHA comparison when an ordinary extra paragraph leaves the approved passage unchanged."""
    base = repo.commit()
    repo.write("DECISIONS.md", checker.blob(ROOT, REVISION, "DECISIONS.md") + "\nAn ordinary extra note.\n")
    report = checker.check(repo.path, base, repo.commit())
    assert reported(report, "BND-F-2", "DECISIONS.md")


def test_existing_empty_decisions_is_not_creation(repo):
    """Mutation: confuse an existing empty base file with an absent file through text truthiness."""
    base, head = repo.range(("DECISIONS.md", "", checker.blob(ROOT, REVISION, "DECISIONS.md")))
    assert reported(checker.check(repo.path, base, head), "BND-F-2", "DECISIONS.md")


def test_future_decisions_paragraph_deletion_reports_medium(repo):
    """Mutation: disable the approved-after watch because this new decision paragraph is outside the original 243 baselines."""
    before = checker.blob(ROOT, REVISION, "DECISIONS.md")
    paragraph = record("DECISIONS.md", 78)["after"]["text"]
    assert before.count(paragraph) == 1
    base, head = repo.range(("DECISIONS.md", before, before.replace(paragraph, "An ordinary replacement note.")))
    assert reported(checker.check(repo.path, base, head), "BND-F-2", "DECISIONS.md")


def test_current_high_classification_is_not_exempt(repo, monkeypatch):
    """Mutation: exempt an exact historical transition even when current classification requires HIGH BND-F-1."""
    item = record()
    namespace = checker.boundary_review.__globals__
    original = namespace["classify"]

    def higher_classification(passage):
        return "BND-F-1" if passage.sha256 == item["after"]["sha256"] else original(passage)

    monkeypatch.setitem(namespace, "classify", higher_classification)
    report = transition(repo, item["before"]["text"], item["after"]["text"])
    assert reported(report, "BND-F-1", item["path"], "HIGH")
