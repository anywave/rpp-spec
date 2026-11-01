"""Exercise summary status regressions in memory; never edit source files."""

from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from tools import ci_synth_summary


def output(source, status, has_log):
    namespace = {"__name__": "summary_mutation"}
    exec(compile(source, "summary_mutation", "exec"), namespace)
    with TemporaryDirectory() as directory:
        path = Path(directory)
        if status is not None:
            (path / "flow_B.status").write_text(status, encoding="utf-8")
        if has_log:
            (path / "pnr_B.log").write_text("TRELLIS_COMB: 124/1000\n", encoding="utf-8")
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
    cases = [
        ("ignore_failed", 'elif st == "failed":', "elif False:", "failed", True, "**failed**"),
        ("trust_marker_without_log", 'st == "ok" and b is not None', 'st == "ok"', "ok", False,
         "**incomplete or unknown**"),
        ("trust_log_without_marker", 'st == "ok" and b is not None', 'b is not None', None, True,
         "**incomplete or unknown**"),
        ("reject_success", 'st == "ok" and b is not None', "False", "ok", True, "**completed**"),
    ]
    killed = 0
    for name, old, new, status, log, expected in cases:
        assert source.count(old) == 1, name
        assert expected in output(source, status, log), name + " clean control"
        assert expected not in output(source.replace(old, new), status, log), name + " survived"
        killed += 1
    print(f"killed={killed} survived=0 controls={len(cases)}/0")


if __name__ == "__main__":
    main()
