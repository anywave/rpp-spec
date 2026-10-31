"""Exercise Unicode I/O with UTF-8 mode disabled, not just on a UTF-8 host."""

import ast
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]


def test_no_locale_dependent_text_io():
    for path in (ROOT / "tools/drift").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
            keywords = {k.arg: k.value for k in call.keywords}
            name = call.func.attr if isinstance(call.func, ast.Attribute) else None
            if name in {"read_text", "write_text"}:
                assert ast.literal_eval(keywords.get("encoding")) == "utf-8", (path, call.lineno)
            if name in {"run", "check_output"} and isinstance(call.func, ast.Attribute):
                if isinstance(call.func.value, ast.Name) and call.func.value.id == "subprocess":
                    binary = isinstance(keywords.get("text"), ast.Constant) and keywords["text"].value is False
                    assert binary or ast.literal_eval(keywords.get("encoding")) == "utf-8", (path, call.lineno)


def test_unicode_reports_with_pythonutf8_zero(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], encoding="utf-8", stderr=subprocess.PIPE).strip()

    git("init", "-q")
    git("config", "user.name", "Unicode fixture")
    git("config", "user.email", "fixture@example.invalid")
    (repo / "VERSION_POLICY.md").write_text("**RPP Specification Version:** 2.0.0\n", encoding="utf-8", newline="\n")
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-qm", "Before")
    base = git("rev-parse", "HEAD")
    (repo / "caf\u00e9.md").write_text("This is unhackable \u2014 caf\u00e9.\n", encoding="utf-8", newline="\n")
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-qm", "After")
    head = git("rev-parse", "HEAD")
    out = tmp_path / "reports"
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8="0", PYTHONCOERCECLOCALE="0",
               LC_ALL="C", PYTHONIOENCODING="utf-8")
    flags = [sys.executable, "-X", "utf8=0", "-X", "warn_default_encoding", "-W", "error::EncodingWarning"]
    program = "import sys; assert sys.flags.utf8_mode == 0; from tools.drift.__main__ import main; sys.exit(main())"
    result = subprocess.run(flags + ["-c", program, "check", "--base", base, "--head", head,
                                     "--output-dir", str(out)], cwd=repo, env=env,
                            capture_output=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    data = json.loads((out / "drift-report.json").read_text(encoding="utf-8"))
    assert data["findings"][0]["path"] == "caf\u00e9.md"
    assert "caf\u00e9" in (out / "drift-report.md").read_text(encoding="utf-8")

    # Exercise history.main's actual writers in the same non-UTF-8-default process.
    # Substitute a bounded local result, not a historical target's executable code.
    history_out = tmp_path / "history"
    history_finding = dict(data["findings"][0], severity="MEDIUM")
    fixture = dict(master_snapshot=head, commits=[dict(commit=head, parent=base,
                   summary=dict(data["summary"], low=0, medium=1), findings=[history_finding])])
    program = ("import sys; assert sys.flags.utf8_mode == 0; from tools.drift import history; "
               + "fixture = " + repr(fixture).encode("ascii", errors="backslashreplace").decode("ascii") + "; "
               + "history.run = lambda *_: fixture; history.main()")
    result = subprocess.run(flags + ["-c", program, "--master", head, "--output-dir", str(history_out)],
                            cwd=repo, env=env, capture_output=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert json.loads((history_out / "history.json").read_text(encoding="utf-8")) == fixture
    assert (history_out / "HISTORY.md").read_bytes().endswith(b"\n")
    assert "caf\u00e9" in (history_out / "HISTORY.md").read_text(encoding="utf-8")
