"""CX-004 A2 adversarial passage interactions in disposable Git repositories.

Mutation obligations: hunk/file-wide replacement borrowing breaks the removal
cases; dropping physical-passage pairing breaks the rewrite controls; forcing
removal for equal hashes breaks move/normalization controls; skipping anchor
guards breaks deletion while treating location as identity breaks anchor moves.
The fixed seed here is Git's fixture author/committer date, not random inputs.
"""

import json
import os
import subprocess
import textwrap
import unicodedata

import pytest

from tools.drift import checker
from tools.drift.passages import normalize


CATALOG = json.loads(checker.DATA.read_text(encoding="utf-8"))
PARAGRAPH = next(b for b in CATALOG["baselines"] if b["path"] == "spec/SPINTRONIC.md" and b["line"] == 21)
SECOND = next(b for b in CATALOG["baselines"] if b["path"] == "spec/SPINTRONIC.md" and b["line"] == 176)
FENCE = min((b for b in CATALOG["baselines"] if b["kind"] == "code_fence" and b["rule_id"] == "BND-F-2"), key=lambda b: len(b["text"]))
ROW = next(b for b in CATALOG["baselines"] if b["path"] == "BOUNDARIES.md" and b["line"] == 249)
DOCSTRING = next(b for b in CATALOG["baselines"] if b["path"] == "rpp/network.py" and b["line"] == 134)
COMMENT = next(b for b in CATALOG["baselines"] if b["path"] == "rpp/continuity.py" and b["line"] == 40)
NFC_BASELINE = next(b for b in CATALOG["baselines"] if unicodedata.normalize("NFD", b["text"]) != unicodedata.normalize("NFC", b["text"]))
ANCHOR = CATALOG["software_must_anchors"][0]


class InteractionRepo:
    """Only fixture files below tmp_path are ever written."""

    def __init__(self, path):
        self.path = path
        path.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Boundary interaction fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.write("VERSION_POLICY.md", "**RPP Specification Version:** 2.0.0\n")

    def git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_DATE="2026-10-31T00:00:00+0000", GIT_COMMITTER_DATE="2026-10-31T00:00:00+0000")
        return subprocess.check_output(["git", "-C", str(self.path), *args], encoding="utf-8", stderr=subprocess.PIPE, env=env).strip()

    def write(self, path, text):
        target = self.path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")

    def commit(self):
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "Interaction fixture")
        return self.git("rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    return InteractionRepo(tmp_path / "repo")


def checked(repo, base, head):
    """Single integration hook for mutation-runner variants."""
    return checker.check(repo.path, base, head)


def removal_ids(report):
    return {b["id"] for b in CATALOG["baselines"] for f in report["findings"]
            if f["rule_id"] == "BND-F-BASELINE-REMOVED" and b["id"] in f["evidence"]}


def f_findings(report, rule_id):
    return [f for f in report["findings"] if f["rule_id"] == rule_id]


@pytest.mark.parametrize("independent_physics", [False, True], ids=["control", "cx001_003_repro"])
def test_removed_baseline_not_hidden_by_independent_same_hunk_physics(repo, independent_physics):
    """Mutation: restoring hunk-wide physics_replacement hides the positive case."""
    path = PARAGRAPH["path"]
    repo.write(path, "## Baseline claim\n\n" + PARAGRAPH["text"] + "\n\n## Independent feature\n\nA routing detail.\n")
    base = repo.commit()
    extra = "The T2 measurement is optional." if independent_physics else "A routing detail."
    repo.write(path, "## Baseline claim\n\nAn ordinary routing statement.\n\n## Independent feature\n\n" + extra + "\n")
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == {PARAGRAPH["id"]}
    assert len(f_findings(report, "BND-F-2")) == int(independent_physics)
    assert report["summary"]["medium"] == 1 + int(independent_physics)


def test_removed_baseline_not_hidden_by_other_hunk_physics(repo):
    """Mutation: file-wide replacement borrowing suppresses the removal."""
    spacer = "\n".join(f"Unchanged line {n}." for n in range(20))
    before = PARAGRAPH["text"] + "\n\n" + spacer + "\n\nA routing detail.\n"
    after = "An ordinary routing statement.\n\n" + spacer + "\n\nThe T2 measurement is optional.\n"
    repo.write(PARAGRAPH["path"], before)
    base = repo.commit()
    repo.write(PARAGRAPH["path"], after)
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == {PARAGRAPH["id"]}
    assert len(f_findings(report, "BND-F-2")) == 1
    headers = {f["evidence"].split("\n", 1)[0] for f in report["findings"]}
    assert len(headers) == 2


def test_two_baselines_one_hunk_removed_and_physical_rewrite(repo):
    """Mutation: shared replacement sets make both baselines appear rewritten."""
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"] + "\n\n" + SECOND["text"] + "\n")
    base = repo.commit()
    rewritten = SECOND["text"].replace("thermodynamics", "thermalization")
    assert rewritten != SECOND["text"]
    repo.write(PARAGRAPH["path"], "An ordinary routing statement.\n\n" + rewritten + "\n")
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == {PARAGRAPH["id"]}
    assert len(f_findings(report, "BND-F-2")) == 1
    assert {e["baseline_id"] for e in report["baseline_events"]} == {PARAGRAPH["id"], SECOND["id"]}


def test_same_passage_physical_rewrite_is_not_baseline_removal(repo):
    """Clean control for removal: forcing every lost hash to removal fails here."""
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"] + "\n")
    base = repo.commit()
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"].replace("25 ns", "24 ns") + "\n")
    report = checked(repo, base, repo.commit())
    assert not removal_ids(report)
    assert len(f_findings(report, "BND-F-2")) == 1


def test_physics_sentence_appended_to_same_passage_is_physical_rewrite(repo):
    """Mutation: ignoring unchanged-line ownership misreads zero-delete insertions."""
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"] + "\n")
    base = repo.commit()
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"] + "\nA T2 value is also recorded.\n")
    report = checked(repo, base, repo.commit())
    assert not removal_ids(report)
    assert len(f_findings(report, "BND-F-2")) == 1


def test_baseline_split_is_conservative_identity_loss(repo):
    """IMPOSED split policy; allowing 1-to-many pairing loses the tombstone."""
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"] + "\n")
    base = repo.commit()
    first, second = PARAGRAPH["text"].split(" The statement", 1)
    repo.write(PARAGRAPH["path"], first + "\n\nThe statement" + second + "\n")
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == {PARAGRAPH["id"]}
    assert len(f_findings(report, "BND-F-2")) == 2


def test_two_baselines_merged_is_conservative_identity_loss(repo):
    """IMPOSED merge policy; removing component-cardinality guards fails this."""
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"] + "\n\n" + SECOND["text"] + "\n")
    base = repo.commit()
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"] + " " + SECOND["text"] + "\n")
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == {PARAGRAPH["id"], SECOND["id"]}
    assert len(f_findings(report, "BND-F-2")) == 1


@pytest.mark.parametrize("change_word", [False, True], ids=["rewrap_only", "rewrap_and_change"])
def test_rewrapped_passage_with_optional_word_change(repo, change_word):
    """Mutation: using raw text as identity or refusing unique physical pairs fails."""
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"] + "\n")
    base = repo.commit()
    after = PARAGRAPH["text"].replace(" The statement", "\nThe statement")
    if change_word:
        after = after.replace("25 ns", "24 ns")
    repo.write(PARAGRAPH["path"], after + "\n")
    report = checked(repo, base, repo.commit())
    assert not removal_ids(report)
    assert len(f_findings(report, "BND-F-2")) == int(change_word)
    events = [e for e in report["baseline_events"] if e["baseline_id"] == PARAGRAPH["id"]]
    assert len(events) == 1
    event = events[0]
    assert event["change"] == ("changed" if change_word else "moved")


def test_crlf_lf_nfc_nfd_preserve_baseline_identity(repo):
    """Mutation: omitting LF/NFC/whitespace normalization produces false drift."""
    b = NFC_BASELINE
    repo.write(b["path"], unicodedata.normalize("NFC", b["text"]) + "\n")
    base = repo.commit()
    target = repo.path / b["path"]
    changed = unicodedata.normalize("NFD", b["text"]).replace(" ", "  ") + "\r\n"
    target.write_bytes(changed.encode("utf-8"))
    report = checked(repo, base, repo.commit())
    assert not removal_ids(report)
    assert not f_findings(report, "BND-F-1") and not f_findings(report, "BND-F-2")
    events = [e for e in report["baseline_events"] if e["baseline_id"] == b["id"]]
    assert len(events) == 1
    event = events[0]
    assert event["change"] == "moved" and event["new_sha256"] == event["old_sha256"]


def test_deleted_file_baseline_is_reported(repo):
    """Mutation: skipping deleted-path blobs suppresses the Q1 finding."""
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"] + "\n")
    base = repo.commit()
    (repo.path / PARAGRAPH["path"]).unlink()
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == {PARAGRAPH["id"]}
    assert next(e for e in report["baseline_events"] if e["baseline_id"] == PARAGRAPH["id"])["change"] == "removed"


@pytest.mark.parametrize("change_text", [False, True], ids=["same_text_move", "changed_rename"])
def test_renamed_file_baseline_identity(repo, change_text):
    """Dropping hash moves or lending changed text across paths breaks a variant."""
    repo.write(PARAGRAPH["path"], PARAGRAPH["text"] + "\n")
    base = repo.commit()
    (repo.path / PARAGRAPH["path"]).unlink()
    destination = "spec/Renamed baseline \u00e9.md"
    after = PARAGRAPH["text"].replace("25 ns", "24 ns") if change_text else PARAGRAPH["text"]
    repo.write(destination, after + "\n")
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == ({PARAGRAPH["id"]} if change_text else set())
    assert len(f_findings(report, "BND-F-2")) == int(change_text)
    events = [e for e in report["baseline_events"] if e["baseline_id"] == PARAGRAPH["id"]]
    assert len(events) == 1
    event = events[0]
    if not change_text:
        assert event["change"] == "moved" and event["new_path"] == destination


@pytest.mark.parametrize("delete", [False, True], ids=["move_inside_file", "delete_anchor"])
def test_software_anchor_move_versus_loss(repo, delete):
    """Mutation: tying anchors to old coordinates or omitting the loss guard fails."""
    text = ANCHOR["text"]
    repo.write(ANCHOR["path"], "## TTL\n\n" + text + "\n\n## Policy\n\nAn ordinary policy.\n")
    base = repo.commit()
    after = "## Policy\n\nAn ordinary policy.\n" + ("" if delete else "\n## TTL\n\n" + text + "\n")
    repo.write(ANCHOR["path"], after)
    report = checked(repo, base, repo.commit())
    hits = [f for f in f_findings(report, "BND-F-1") if "Software-MUST anchor" in f["evidence"]]
    assert bool(hits) == delete


@pytest.mark.parametrize("physics", [False, True], ids=["ordinary_control", "term_twice"])
def test_repeated_physics_term_is_one_passage_finding(repo, physics):
    """Per-term emission duplicates F2; emitting for ordinary prose breaks control."""
    repo.write("README.md", "")
    base = repo.commit()
    text = "The T2 label repeats T2." if physics else "An ordinary routing label."
    repo.write("README.md", text + "\n")
    report = checked(repo, base, repo.commit())
    assert len(f_findings(report, "BND-F-2")) == int(physics)


@pytest.mark.parametrize("kind", ["code_fence", "table_row"])
@pytest.mark.parametrize("remove_physics", [False, True], ids=["physical_rewrite", "nonphysics_rewrite"])
def test_fence_and_table_are_individual_replacement_units(repo, kind, remove_physics):
    """Mutation: grouping a whole table/fence neighborhood lends unrelated physics."""
    b = FENCE if kind == "code_fence" else ROW
    repo.write(b["path"], b["text"] + "\n")
    base = repo.commit()
    if remove_physics:
        after = "```\nAn ordinary example.\n```" if kind == "code_fence" else "| RPP | Ordinary routing |"
    elif kind == "code_fence":
        after = b["text"].replace("T2", "T2 value", 1)
    else:
        after = b["text"].replace("physically", "physically today")
    assert after != b["text"]
    repo.write(b["path"], after + "\n")
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == ({b["id"]} if remove_physics else set())
    assert len(f_findings(report, "BND-F-2")) == int(not remove_physics)


@pytest.mark.parametrize("kind", ["docstring", "comment"])
@pytest.mark.parametrize("change_kind", [False, True], ids=["same_kind_rewrite", "changed_kind"])
def test_docstring_and_comment_replacement_kinds(repo, kind, change_kind):
    """IMPOSED kind-loss policy; deleting the kind guard loses its tombstone."""
    b = DOCSTRING if kind == "docstring" else COMMENT
    repo.write(b["path"], b["text"] + "\n")
    base = repo.commit()
    if change_kind:
        content = normalize(b["text"].strip('"#\n '))
        after = "# " + content if kind == "docstring" else '\"\"\"' + content + '\"\"\"'
    elif kind == "docstring":
        after = b["text"].replace("Emitted", "Produced", 1)
    else:
        after = b["text"].replace("literal", "explicit", 1)
    assert after != b["text"]
    repo.write(b["path"], after + "\n")
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == ({b["id"]} if change_kind else set())
    assert len(f_findings(report, "BND-F-2")) == 1


def test_python_sibling_docstring_cannot_borrow_replacement(repo):
    """Mutation: per-file/per-hunk Python pairing lends a sibling's physics claim."""
    before = "def claim():\n" + textwrap.indent(DOCSTRING["text"], "    ") + "\n    pass\n\ndef independent():\n    \"\"\"An ordinary detail.\"\"\"\n    pass\n"
    after = 'def claim():\n    """An ordinary detail."""\n    pass\n\ndef independent():\n    """The T2 measurement is optional."""\n    pass\n'
    repo.write(DOCSTRING["path"], before)
    base = repo.commit()
    repo.write(DOCSTRING["path"], after)
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == {DOCSTRING["id"]}
    assert len(f_findings(report, "BND-F-2")) == 1


@pytest.mark.parametrize("owner", ["heading", "function"])
def test_changed_owner_and_changed_text_are_conservative_identity_loss(repo, owner):
    """IMPOSED owner-loss policy; deleting the owner guard loses its tombstone."""
    if owner == "heading":
        b = PARAGRAPH
        before = "## Original owner\n\n" + b["text"] + "\n"
        after = "## Different owner\n\n" + b["text"].replace("25 ns", "24 ns") + "\n"
    else:
        b = DOCSTRING
        before = "def original():\n" + textwrap.indent(b["text"], "    ") + "\n    pass\n"
        after = "def different():\n" + textwrap.indent(b["text"].replace("Emitted", "Produced"), "    ") + "\n    pass\n"
    repo.write(b["path"], before)
    base = repo.commit()
    repo.write(b["path"], after)
    report = checked(repo, base, repo.commit())
    assert removal_ids(report) == {b["id"]}
    assert len(f_findings(report, "BND-F-2")) == 1


def test_unchanged_docstring_owner_rename_is_hash_move(repo):
    """Checking owner before exact hash wrongly removes an unchanged unit."""
    before = "def original():\n" + textwrap.indent(DOCSTRING["text"], "    ") + "\n    pass\n"
    repo.write(DOCSTRING["path"], before)
    base = repo.commit()
    repo.write(DOCSTRING["path"], before.replace("def original", "def renamed"))
    report = checked(repo, base, repo.commit())
    assert not removal_ids(report) and not f_findings(report, "BND-F-2")
    events = [e for e in report["baseline_events"] if e["baseline_id"] == DOCSTRING["id"]]
    assert len(events) == 1 and events[0]["change"] == "moved"


def test_word_only_markdown_binary_is_tool_error_in_process(repo):
    """Mutation: removing both blob validations formerly made this a clean scan."""
    repo.write("docs/claim.md", "An ordinary note.\n")
    base = repo.commit()
    (repo.path / "docs/claim.md").write_bytes(b"\0This is unhackable.\n")
    error = None
    try:
        checked(repo, base, repo.commit())
    except checker.ToolError as exc:
        error = exc
    assert error is not None


def test_valid_word_only_markdown_is_reviewed(repo):
    """Unconditional I/O rejection or deleting WORD-CLAIM-1 breaks this control."""
    repo.write("docs/claim.md", "An ordinary note.\n")
    base = repo.commit()
    repo.write("docs/claim.md", "This is unhackable.\n")
    error = None
    report = None
    try:
        report = checked(repo, base, repo.commit())
    except checker.ToolError as exc:
        error = exc
    assert error is None
    assert len(f_findings(report, "WORD-CLAIM-1")) == 1


def test_unicode_separator_keeps_valid_review_in_process(repo):
    """Mutation: splitlines() reads Unicode separators as Git LF boundaries."""
    repo.write("docs/claim.md", "An ordinary note.\n")
    base = repo.commit()
    repo.write("docs/claim.md", "This is unhackable.\u2028Still the same Git line.\n")
    error = None
    report = None
    try:
        report = checked(repo, base, repo.commit())
    except checker.ToolError as exc:
        error = exc
    assert error is None
    hits = f_findings(report, "WORD-CLAIM-1")
    assert len(hits) == 1 and hits[0]["line"] == 1
    assert "\u2028" in hits[0]["evidence"]


def test_blank_context_config_does_not_break_valid_review(repo):
    """Mutation: letting local suppressBlankEmpty alter Git's line grammar fails."""
    repo.write("docs/claim.md", "An ordinary note.\n\nAnother note.\n")
    base = repo.commit()
    repo.write("docs/claim.md", "This is unhackable.\n\nAnother note.\n")
    head = repo.commit()
    repo.git("config", "diff.suppressBlankEmpty", "true")
    error = None
    report = None
    try:
        report = checked(repo, base, head)
    except checker.ToolError as exc:
        error = exc
    assert error is None
    assert len(f_findings(report, "WORD-CLAIM-1")) == 1
