"""Exercise summary status regressions in memory; never edit source files."""

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from tools import ci_synth_summary
from tools.ci_summary.workflow_fixture import flow_a_fragment, run_flow_a


def output(source, status, log, flow):
    namespace = {"__name__": "summary_mutation"}
    exec(compile(source, "summary_mutation", "exec"), namespace)
    with TemporaryDirectory() as directory:
        path = Path(directory)
        if status is not None:
            (path / f"flow_{flow}.status").write_text(status, encoding="utf-8")
        if log is not None:
            (path / f"pnr_{flow}.log").write_text(log, encoding="utf-8")
        original = sys.argv
        try:
            sys.argv = ["summary", directory, "2026-09-24"]
            stream = io.StringIO()
            with redirect_stdout(stream):
                namespace["main"]()
            return stream.getvalue()
        finally:
            sys.argv = original


def main():
    source = Path(ci_synth_summary.__file__).read_text(encoding="utf-8")
    success = 'st == "ok" and has_values'
    parsed = 'any(value != "?" for value in values.values())'
    log = "TRELLIS_COMB: 124/1000\n"
    cases = [
        ("ignore_failed", 'elif st == "failed":', "elif False:", "failed", log, "A", "**failed**"),
        ("trust_marker_without_log", success, 'st == "ok"', "ok", None, "A", "**incomplete or unknown**"),
        ("trust_log_without_marker", success, "has_values", None, log, "B", "**incomplete or unknown**"),
        ("reject_success", success, "False", "ok", log, "B", "**completed**"),
        ("trust_empty_log", parsed, "True", "ok", "", "A", "**incomplete or unknown**"),
        ("trust_unparseable_log", parsed, "True", "ok", "not a resource line\n", "B", "**incomplete or unknown**"),
        ("omit_flow_a", '(("A", a), ("B", b))', '(("B", b),)', "failed", log, "A", "**failed**"),
    ]
    killed = 0
    for name, old, new, status, log, flow, label in cases:
        assert source.count(old) == 1, name
        expected = f"Flow {flow} status: {label}"
        assert expected in output(source, status, log, flow), name + " clean control"
        assert expected not in output(source.replace(old, new), status, log, flow), name + " survived"
        killed += 1
    workflow_cases = [
        ("hide_flow_a_failure", "            exit 1\n", "            exit 0\n", 0, 1, "failed", 1),
        ("flow_a_failure_marked_ok", 'echo failed > "$out/flow_A.status"',
         'echo ok > "$out/flow_A.status"', 0, 1, "failed", 1),
        ("omit_flow_a_success_marker", 'echo ok > "$out/flow_A.status"',
         'echo incomplete > "$out/flow_A.status"', 0, 0, "ok", 0),
        ("reuse_stale_flow_b_success", 'echo incomplete > "$out/flow_B.status"', ":", 1, 0, "failed", 1),
    ]
    skipped = 0
    for name, old, new, ys, pn, marker, code in workflow_cases:
        if os.name == "nt":
            skipped += 1
            continue
        fragment = flow_a_fragment()
        # De-dented workflow text is executed, not a separately maintained shell copy.
        old, new = old.lstrip(), new.lstrip()
        assert fragment.count(old) == 1, name

        def matches(script):
            with TemporaryDirectory() as directory:
                path = Path(directory)
                result = run_flow_a(path, ys, pn, script)
                return (result.returncode == code
                        and (path / "flow_A.status").read_text(encoding="utf-8").strip() == marker
                        and (path / "flow_B.status").read_text(encoding="utf-8").strip() == "incomplete"
                        and "status-at-yosys:\nincomplete\nincomplete\n" in result.stdout)

        assert matches(fragment), name + " clean control"
        assert not matches(fragment.replace(old, new)), name + " survived"
        killed += 1
    print(f"killed={killed} survived=0 controls={killed}/0 skipped={skipped}")


if __name__ == "__main__":
    main()
