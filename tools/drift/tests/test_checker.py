"""Behavioral diff fixtures in disposable repositories; production files never change."""

import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from tools.drift import checker


CATALOG = json.loads(checker.DATA.read_text())
RULE_IDS = [r["rule_id"] for r in CATALOG["rules"]]
POLICY = "**RPP Specification Version:** 2.0.0 (Ra-Canonical)\n\n"
RADIUS_ROW = "| Radius | 0 | 255 | Normalized 0-1 |"
RADIUS_SOURCE = "spec/RPP-CANONICAL-v2.md"
CANONICAL = "rpp/address_canonical.py"

# Each tuple supplies an actual source mutation that must trigger the named rule.
CASES = {
    "BND-A-1": ("spec/SPEC.md", "", "RPP stores encrypted blobs.\n"),
    "BND-B-1": ("spec/SPEC.md", "", "RPP issues JWTs.\n"),
    "BND-C-1": ("spec/SPEC.md", "", "Add if/else logic to addresses.\n"),
    "BND-E-1": ("spec/SPEC.md", "", "Use embeddings to match addresses.\n"),
    "BND-G-1": (CANONICAL, "class RPPAddress:\n    theta: int\n", "class RPPAddress:\n    theta: int\n    metadata: dict\n"),
    "BND-F-1": ("spec/SPEC.md", "", "Core validity MUST require quantum effects.\n"),
    "BND-F-2": ("spec/SPINTRONIC.md", "", "This is a physical invariant.\n"),
    "VER-FORMAT-1": (CANONICAL, "THETA_SHIFT = 27\n", "THETA_SHIFT = 26\n"),
    "VER-RADIUS-API": (CANONICAL, "class RPPAddress:\n    def __post_init__(self):\n        if not 0.0 <= self.radius <= 1.0:\n            raise ValueError('radius')\n", "class RPPAddress:\n    def __post_init__(self):\n        if not 0.0 <= self.radius <= 2.0:\n            raise ValueError('radius')\n"),
    "VER-RADIUS-ENC": (CANONICAL, "radius_enc = (round(self.radius * 255) & 0xFF) << RADIUS_SHIFT\n", "radius_enc = (round(self.radius * 127) & 0xFF) << RADIUS_SHIFT\n"),
    "VEC-1": ("tests/test_vectors.json", '{"encoding": [1]}\n', '{"encoding": [2]}\n'),
    "NET-INV-1": ("rpp/network.py", "def forward(packet):\n    return packet\n", "def forward(packet):\n    packet.phi = 0\n    return packet\n"),
    "NET-INV-2": ("rpp/network.py", "MIN_HOT_NODES_PER_SECTOR = 3\n", "MIN_HOT_NODES_PER_SECTOR = 1\n"),
    "WORD-CLAIM-1": ("README.md", "", "RPP is unhackable.\n"),
    "WORD-RADIUS-1": ("VERSION_POLICY.md", POLICY + RADIUS_ROW + "\n", POLICY + "| Radius | 0 | 255 | Encoded integer |\n"),
}

# Nonmatching control fixtures are deliberately different behaviors, not detector copies.
CLEAN = {
    "BND-A-1": ("spec/extensions/MESH.md", "", "Store encrypted blobs in the application.\n"),
    "BND-B-1": ("spec/SPEC.md", "", "RPP consumes identity context.\n"),
    "BND-C-1": (CANONICAL, "", "if value < 0:\n    raise ValueError('range')\n"),
    "BND-E-1": ("spec/SPEC.md", "", "Gate AI actions using numeric input.\n"),
    "BND-G-1": (CANONICAL, 'class RPPAddress:\n    """Old description."""\n    theta: int\n', 'class RPPAddress:\n    """New description."""\n    theta: int\n'),
    "BND-F-1": ("spec/SPEC.md", "Quantum hardware MAY accelerate the optional substrate.\n\nText.\n", "Text.\n\nQuantum hardware MAY accelerate the optional substrate.\n"),
    "BND-F-2": ("tools/notes.txt", "", "ordinary code edit\n"),
    "VER-FORMAT-1": (CANONICAL, "THETA_SHIFT = 27\n", "# Explanation\nTHETA_SHIFT = 27\n"),
    "VER-RADIUS-API": (CANONICAL, "radius: float\n", "# Explanation\nradius: float\n"),
    "VER-RADIUS-ENC": (CANONICAL, "radius_enc = round(r * 255)\n", "# Explanation\nradius_enc = round(r * 255)\n"),
    "VEC-1": ("tests/test_other.py", "", "def test_ok():\n    assert True\n"),
    "NET-INV-1": ("rpp/network.py", "local_value = 1\n", "local_value = 2\n"),
    "NET-INV-2": ("rpp/network.py", "MAX_HOP_COUNT = 32\n", "MAX_HOP_COUNT = 33\n"),
    "WORD-CLAIM-1": ("README.md", "", "No independent security audit.\n"),
    "WORD-RADIUS-1": ("VERSION_POLICY.md", POLICY + RADIUS_ROW + "\n\nNote.\n", POLICY + RADIUS_ROW + "\n\nDifferent note.\n"),
}


class Repo:
    def __init__(self, path):
        self.path = path
        path.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Drift fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.write("VERSION_POLICY.md", POLICY)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.path), *args], stderr=subprocess.PIPE).decode().strip()

    def write(self, path, text):
        target = self.path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self):
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "Fixture")
        return self.git("rev-parse", "HEAD")

    def range(self, case):
        path, before, after = case
        self.write(path, before)
        base = self.commit()
        self.write(path, after)
        return base, self.commit()


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path / "repo")


def evaluate(repo, base, head):
    mutant = os.environ.get("DRIFT_TEST_MUTANT")
    if mutant:
        assert mutant in RULE_IDS
        # Mutate the trusted coordinator in memory, never target or production files.
        source = Path(checker.__file__).read_text()
        needle = "        rule = rules[rule_id]\n"
        assert source.count(needle) == 1
        source = source.replace(needle, f"        if rule_id == {mutant!r}:\n            return\n" + needle)
        namespace = dict(checker.__dict__)
        exec(compile(source, "<detector-deletion-mutant>", "exec"), namespace)
        return namespace["check"](repo.path, base, head)
    return checker.check(repo.path, base, head)


@pytest.mark.parametrize("rule_id", RULE_IDS)
def test_rule_detects_drift(repo, rule_id):
    base, head = repo.range(CASES[rule_id])
    report = evaluate(repo, base, head)
    assert rule_id in {f["rule_id"] for f in report["findings"]}


@pytest.mark.parametrize("rule_id", RULE_IDS)
def test_rule_clean_control(repo, rule_id):
    base, head = repo.range(CLEAN[rule_id])
    report = evaluate(repo, base, head)
    assert rule_id not in {f["rule_id"] for f in report["findings"]}


def test_catalog_inventory_sources_and_hashes():
    root = Path(__file__).resolve().parents[3]
    def source(path):
        return subprocess.check_output(["git", "-C", str(root), "show", CATALOG["source_revision"] + ":" + path]).decode()
    inventory = (root / "tools/drift/RULES.md").read_text()
    assert len(re.findall(r"^\| P-\d+ \|", inventory, re.M)) == CATALOG["rules_not_checkable"]
    assert set(CASES) == set(CLEAN) == set(RULE_IDS)
    for rule in CATALOG["rules"]:
        path, n = rule["source"].split(";", 1)[0].rsplit(":", 1)
        assert source(path).splitlines()[int(n) - 1] == rule["quote"]
        assert f"| {rule['rule_id']} |" in inventory
    for b in CATALOG["baselines"]:
        assert hashlib.sha256(b["text"].encode()).hexdigest() == b["sha256"]
        text = source(b["path"]).splitlines()
        assert "\n".join(text[b["line"] - 1:b["line"] - 1 + len(b["text"].splitlines())]) == b["text"]
        assert b["status"] == "unresolved - steward decision (RADIX)"


@pytest.mark.parametrize("operation", ["change", "delete", "move", "unrelated", "duplicate"])
def test_baseline_reports_only_text_changes(repo, operation):
    b = next(b for b in CATALOG["baselines"] if b["path"] == "spec/SPINTRONIC.md" and "physical invariant" in b["text"])
    passage = b["text"]
    before = passage + "\n\nAn unrelated note.\n"
    after = {"change": passage.replace("physical invariant", "substrate assertion") + "\n",
             "delete": "An unrelated note.\n", "move": "An unrelated note.\n\n" + passage + "\n",
             "unrelated": passage + "\n\nDifferent note.\n",
             "duplicate": passage + "\n\n" + passage + "\n"}[operation]
    base, head = repo.range((b["path"], before, after))
    findings = checker.check(repo.path, base, head)["findings"]
    matched = [f for f in findings if b["id"] in f["evidence"]]
    assert bool(matched) == (operation in {"change", "delete"})
    if operation == "duplicate":
        assert any(f["rule_id"] == "BND-F-2" for f in findings)


def test_software_must_weakening_is_high(repo):
    before = "Software implementations MUST enforce equivalent TTL semantics per Shell tier.\n"
    base, head = repo.range(("spec/SPEC.md", before, before.replace("MUST", "MAY")))
    assert any(f["rule_id"] == "BND-F-1" and f["severity"] == "HIGH" for f in checker.check(repo.path, base, head)["findings"])


def test_unclassified_physics_is_not_classified(repo):
    base, head = repo.range(("spec/DEPLOYABLE.md", "", "Core validity MUST depend on quantum effects.\n"))
    assert not any(f["rule_id"].startswith("BND-F") for f in checker.check(repo.path, base, head)["findings"])


def test_format_major_bump_only_suppresses_format_rule(repo):
    path, before, after = CASES["VER-FORMAT-1"]
    repo.write(path, before)
    base = repo.commit()
    repo.write(path, after)
    repo.write("VERSION_POLICY.md", POLICY.replace("2.0.0", "3.0.0"))
    repo.write("tests/test_vectors.json", "{}\n")
    report = checker.check(repo.path, base, repo.commit())
    assert "VER-FORMAT-1" not in {f["rule_id"] for f in report["findings"]}
    assert "VEC-1" in {f["rule_id"] for f in report["findings"]}


@pytest.mark.parametrize("operation", ["add", "delete", "rename", "mode"])
def test_vector_path_changes(repo, operation):
    path = "tests/test_golden_vectors_example.py"
    if operation != "add":
        repo.write(path, "# Golden vectors\n")
    base = repo.commit()
    if operation == "add":
        repo.write(path, "# Golden vectors\n")
    elif operation == "delete":
        (repo.path / path).unlink()
    elif operation == "rename":
        (repo.path / path).rename(repo.path / "tests/test_renamed.py")
    else:
        (repo.path / path).chmod(0o755)
    report = checker.check(repo.path, base, repo.commit())
    assert any(f["rule_id"] == "VEC-1" for f in report["findings"])


def test_reports_are_identical_and_escape_diff_markdown(repo, tmp_path):
    base, head = repo.range(("README.md", "", "unhackable </pre><script>bad</script> [click](https://invalid.example)\n"))
    first, second = tmp_path / "first", tmp_path / "second"
    checker.write_reports(checker.check(repo.path, base, head), first)
    checker.write_reports(checker.check(repo.path, base, head), second)
    for name in ["drift-report.json", "drift-report.md"]:
        assert (first / name).read_bytes() == (second / name).read_bytes()
    assert "<script>" not in (first / "drift-report.md").read_text()
    assert "&lt;script&gt;" in (first / "drift-report.md").read_text()


def test_deletion_line_uses_base_coordinates(repo):
    text = next(g["text"] for g in CATALOG["guards"] if g["rule_id"] == "NET-INV-1")
    base, head = repo.range(("spec/NETWORK.md", "Note.\n\n" + text + "\n", "Note.\n"))
    f = next(f for f in checker.check(repo.path, base, head)["findings"] if f["rule_id"] == "NET-INV-1")
    assert f["line"] == 3
    assert "-1. **Consent monotonicity:**" in f["evidence"]


def test_uncommitted_changes_do_not_affect_report(repo):
    base, head = repo.range(("README.md", "", "A harmless note.\n"))
    before = checker.check(repo.path, base, head)
    repo.write("spec/SPEC.md", "Core MUST depend on quantum effects.\n")
    assert checker.check(repo.path, base, head) == before


@pytest.mark.parametrize("ref", ["HEAD", "--help", "deadbee..deadbee", "012", "$(id)"])
def test_reject_revision_expressions(repo, ref):
    sha = repo.commit()
    with pytest.raises(checker.ToolError):
        checker.check(repo.path, ref, sha)


@pytest.mark.parametrize("case", ["syntax", "binary", "symlink", "oversize"])
def test_incomplete_review_is_error(repo, case):
    repo.write(CANONICAL, "THETA_SHIFT = 27\n")
    base = repo.commit()
    target = repo.path / CANONICAL
    if case == "syntax":
        target.write_text("def invalid(:\n")
    elif case == "binary":
        target.write_bytes(b"\0binary")
    elif case == "symlink":
        target.unlink()
        target.symlink_to("/etc/passwd")
    else:
        target.write_text("#" * (checker.MAX_BLOB + 1))
    with pytest.raises(checker.ToolError):
        checker.check(repo.path, base, repo.commit())


@pytest.mark.parametrize("drift, expected", [("none", 0), ("low", 0), ("high", 1), ("error", 2)])
def test_cli_statuses(repo, tmp_path, drift, expected):
    path, before, after = {"none": ("README.md", "", "Note.\n"),
                           "low": CASES["WORD-CLAIM-1"], "high": CASES["BND-A-1"],
                           "error": (CANONICAL, "", "def invalid(:\n")}[drift]
    base, head = repo.range((path, before, after))
    package_root = Path(__file__).resolve().parents[3]
    env = dict(os.environ, PYTHONPATH=str(package_root))
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, "-m", "tools.drift", "check", "--base", base, "--head", head,
                             "--output-dir", str(out)], cwd=repo.path, env=env, capture_output=True)
    assert result.returncode == expected, result.stderr.decode()
    assert (out / "drift-report.json").exists() == (expected != 2)


def test_sort_order_counts_and_schema(repo):
    repo.write("spec/SPEC.md", "")
    base = repo.commit()
    repo.write("spec/SPEC.md", "Use embeddings to match addresses.\n\nRPP stores encrypted blobs.\n")
    repo.write("spec/SPINTRONIC.md", "This is a physical invariant.\n")
    repo.write("README.md", "RPP is unhackable.\n")
    report = checker.check(repo.path, base, repo.commit())
    findings = report["findings"]
    assert [(f["severity"], f["rule_id"]) for f in findings] == [
        ("HIGH", "BND-A-1"), ("HIGH", "BND-E-1"), ("MEDIUM", "BND-F-2"), ("LOW", "WORD-CLAIM-1")]
    assert report["summary"] == dict(high=2, medium=1, low=1, rules_run=len(RULE_IDS), rules_not_checkable=CATALOG["rules_not_checkable"])
    assert set(findings[0]) == {"rule_id", "severity", "path", "line", "evidence", "source", "tag"}


def test_unreviewed_pdf_does_not_require_utf8(repo):
    repo.write("paper/main.pdf", "%PDF-1.5\n")
    base = repo.commit()
    (repo.path / "paper/main.pdf").write_bytes(b"%PDF-1.5\n\xd0\xff\n")
    assert not checker.check(repo.path, base, repo.commit())["findings"]


def test_invalid_utf8_reviewed_source_is_error(repo):
    repo.write("spec/SPEC.md", "Text\n")
    base = repo.commit()
    (repo.path / "spec/SPEC.md").write_bytes(b"\xff\n")
    with pytest.raises(UnicodeError):
        checker.check(repo.path, base, repo.commit())


def test_literal_path_with_glob_characters(repo):
    base, head = repo.range(("docs/[claim].md", "", "This is unhackable.\n"))
    findings = checker.check(repo.path, base, head)["findings"]
    assert any(f["path"] == "docs/[claim].md" for f in findings)


def test_tool_error_removes_stale_reports(repo, tmp_path):
    base, head = repo.range((CANONICAL, "", "def invalid(:\n"))
    out = tmp_path / "out"
    out.mkdir()
    for name in ("drift-report.json", "drift-report.md"):
        (out / name).write_text("Old successful report")
    package_root = Path(__file__).resolve().parents[3]
    result = subprocess.run([sys.executable, "-m", "tools.drift", "check", "--base", base, "--head", head,
                             "--output-dir", str(out)], cwd=repo.path,
                            env=dict(os.environ, PYTHONPATH=str(package_root)), capture_output=True)
    assert result.returncode == 2
    assert not list(out.iterdir())


def test_advisory_workflow_has_read_only_pinned_actions():
    root = Path(__file__).resolve().parents[3]
    workflow = (root / ".github/workflows/drift.yml").read_text()
    actions = re.findall(r"uses:\s+(\S+)", workflow)
    assert actions and all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) for action in actions)
    assert "contents: read" in workflow
    assert "continue-on-error: true" in workflow
    assert "persist-credentials: false" in workflow
    assert "pull_request_target" not in workflow
    assert "gh " not in workflow
