"""Git presentation/configuration must not hide review predicates or change reports."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools.drift import checker


ROOT = Path(__file__).resolve().parents[3]
COMMIT_ENV = dict(os.environ, GIT_AUTHOR_DATE="2000-01-01T00:00:00+0000",
                  GIT_COMMITTER_DATE="2000-01-01T00:00:00+0000")


class Repo:
    def __init__(self, directory):
        self.path = directory
        directory.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Git boundary fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.write("VERSION_POLICY.md", "**RPP Specification Version:** 2.0.0\n")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.path), *args],
                                       stderr=subprocess.PIPE, env=COMMIT_ENV, encoding="utf-8").strip()

    def write(self, path, text):
        target = self.path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")

    def commit(self):
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "Fixture")
        return self.git("rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path / "repo")


def test_color_cannot_hide_storage_boundary(repo):
    repo.write("spec/SPEC.md", "An ordinary note.\n")
    base = repo.commit()
    repo.write("spec/SPEC.md", "RPP stores encrypted blobs.\n")
    head = repo.commit()
    repo.git("config", "color.ui", "never")
    expected = checker.check(repo.path, base, head)
    assert any(f["rule_id"] == "BND-A-1" for f in expected["findings"])
    repo.git("config", "color.ui", "always")
    assert checker.check(repo.path, base, head) == expected


@pytest.mark.parametrize("key,value", [
    ("color.ui", "always"), ("diff.algorithm", "histogram"),
    ("diff.indentHeuristic", "true"), ("diff.interHunkContext", "100"),
    ("diff.mnemonicPrefix", "true"), ("diff.noprefix", "true"),
    ("diff.relative", "true"), ("core.quotePath", "true"), ("core.abbrev", "4"),
    ("diff.suppressBlankEmpty", "true"),
])
def test_git_display_settings_do_not_change_report(repo, key, value):
    path = "docs/caf\u00e9 notes.md"
    before = "\n\n".join(f"Note {i}." for i in range(25)) + "\n"
    repo.write(path, before)
    base = repo.commit()
    repo.write(path, before.replace("Note 2.", "This is unhackable.").replace("Note 22.", "This is guaranteed."))
    head = repo.commit()
    expected = checker.check(repo.path, base, head)
    assert len(expected["findings"]) == 2
    repo.git("config", key, value)
    actual = checker.check(repo.path, base, head)
    assert actual == expected
    assert checker.markdown(actual) == checker.markdown(expected)


def test_vector_mode_evidence_has_stable_unicode_paths(repo):
    path = "tests/golden caf\u00e9.md"
    repo.write(path, "Vector fixture.\n")
    base = repo.commit()
    repo.git("config", "core.filemode", "false")
    repo.git("update-index", "--chmod=+x", path)
    head = repo.commit()
    repo.git("config", "core.quotePath", "false")
    expected = checker.check(repo.path, base, head)
    assert any(f["rule_id"] == "VEC-1" for f in expected["findings"])
    repo.git("config", "core.quotePath", "true")
    assert checker.check(repo.path, base, head) == expected


def test_binary_diff_attribute_cannot_hide_word_claim(repo):
    repo.write(".gitattributes", "docs/*.md -diff\n")
    repo.write("docs/claim.md", "Ordinary note.\n")
    base = repo.commit()
    repo.write("docs/claim.md", "This is unhackable.\n")
    head = repo.commit()
    findings = checker.check(repo.path, base, head)["findings"]
    assert any(f["rule_id"] == "WORD-CLAIM-1" for f in findings)


@pytest.mark.parametrize("kind", ["binary", "invalid_utf8", "symlink", "oversized"])
def test_all_reviewed_markdown_is_validated_and_cli_errors(repo, tmp_path, kind):
    repo.write("docs/claim.md", "Ordinary note.\n")
    base = repo.commit()
    path = repo.path / "docs/claim.md"
    if kind == "binary":
        path.write_bytes(b"\0This is unhackable.\n")
    elif kind == "invalid_utf8":
        path.write_bytes(b"\xffThis is unhackable.\n")
    elif kind == "oversized":
        path.write_bytes(b"#" * (checker.MAX_BLOB + 1))
    else:
        # An added link used to bypass blob validation without even triggering a
        # file-type transition in the patch parser. Never follow its destination.
        target = repo.path / "docs/new-link.md"
        try:
            target.symlink_to("../claim.md")
        except OSError as exc:
            if os.name == "nt":
                pytest.skip(f"Windows symlink creation is unavailable: {exc}")
            raise
    head = repo.commit()
    output = tmp_path / "output"
    result = subprocess.run([sys.executable, "-m", "tools.drift", "check", "--base", base, "--head", head,
                             "--output-dir", str(output)], cwd=repo.path,
                            env=dict(os.environ, PYTHONPATH=str(ROOT)), capture_output=True, encoding="utf-8")
    assert result.returncode == 2, result.stderr
    assert not (output / "drift-report.json").exists()


@pytest.mark.parametrize("separator", ["\u2028", "\u2029", "\v", "\f"])
def test_unicode_separators_are_not_git_line_boundaries(repo, separator):
    repo.write("docs/claim.md", "Ordinary note.\n")
    base = repo.commit()
    repo.write("docs/claim.md", "This is unhackable." + separator + "Continuation.\n")
    findings = checker.check(repo.path, base, repo.commit())["findings"]
    finding = next(f for f in findings if f["rule_id"] == "WORD-CLAIM-1")
    assert finding["line"] == 1
    assert separator in finding["evidence"]


def test_atomic_edit_spans_are_passage_inputs_not_hunk_scope(repo):
    repo.write("README.md", "Before one.\n\nContext.\n\nBefore two.\n")
    base = repo.commit()
    repo.write("README.md", "After one.\n\nContext.\n\nAfter two.\n")
    head = repo.commit()
    catalog = json.loads(checker.DATA.read_text(encoding="utf-8"))
    edits = checker.changes(repo.path, base, head, catalog)["README.md"]
    # One Git hunk contains two independent replacements separated by context.
    assert {e.edit for e in edits} == {(1, 2, 1, 2), (5, 6, 5, 6)}
    assert {e.evidence.split("\n", 1)[0] for e in edits} == {"@@ -1,5 +1,5 @@"}


def test_added_file_edit_coordinates_are_one_based(repo):
    base = repo.commit()
    repo.write("README.md", "One.\nTwo.\n")
    head = repo.commit()
    catalog = json.loads(checker.DATA.read_text(encoding="utf-8"))
    edits = checker.changes(repo.path, base, head, catalog)["README.md"]
    assert len(edits) == 2
    assert {e.edit for e in edits} == {(1, 1, 1, 3)}


def test_function_captions_do_not_depend_on_diff_attributes(repo):
    path = "docs/code.md"
    before = "def before():\n" + "\n".join(f"    note_{i} = {i}" for i in range(12)) + "\n    return 'ordinary'\n"
    repo.write(path, before)
    base = repo.commit()
    repo.write(path, before.replace("'ordinary'", "'unhackable'"))
    head = repo.commit()
    expected = checker.check(repo.path, base, head)
    assert all(f["evidence"].split("\n", 1)[0].endswith(" @@") for f in expected["findings"])
    repo.write(".gitattributes", "docs/*.md diff=fixture\n")
    repo.git("config", "diff.fixture.xfuncname", "^NOTHINGMATCHES$")
    assert checker.check(repo.path, base, head) == expected


def test_repository_root_preserves_trailing_space():
    expected = Path("/tmp/project with trailing space ")
    assert checker.parse_repository_root(b"/tmp/project with trailing space \n") == expected


def test_repository_root_normal_control():
    expected = Path("/tmp/ordinary-project")
    assert checker.parse_repository_root(b"/tmp/ordinary-project\n") == expected


def test_actual_posix_repository_root_preserves_whitespace(tmp_path):
    if os.name == "nt":
        pytest.skip("Trailing whitespace in Windows filesystem component names is not supported by normal Win32 paths")
    repo = Repo(tmp_path / "project with trailing space ")
    repo.write("spec/SPEC.md", "An ordinary note.\n")
    base = repo.commit()
    repo.write("spec/SPEC.md", "RPP stores encrypted blobs.\n")
    findings = checker.check(repo.path, base, repo.commit())["findings"]
    assert any(f["rule_id"] == "BND-A-1" for f in findings)


def test_posix_repository_root_preserves_carriage_return():
    if os.name == "nt":
        pytest.skip("Windows Git may use CRLF records and CR is not a legal Win32 filename character")
    assert checker.parse_repository_root(b"/tmp/project\r\n") == Path("/tmp/project\r")
