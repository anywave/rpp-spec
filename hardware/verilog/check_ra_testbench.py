"""Compile/run the RA testbench and execute four named failure mutations.

Only disposable output copies are mutated. No protocol implementation is edited.
"""

import argparse
from pathlib import Path
import re
import subprocess


def summary(output: str) -> tuple[int, int, int]:
    """Reject a missing/ambiguous or inconsistent HDL summary."""
    counts = []
    for label in ("Total tests", "Passed", "Failed"):
        matches = re.findall(rf"^{label}:\s+(\d+)\s*$", output, re.MULTILINE)
        if len(matches) != 1:
            raise AssertionError(f"expected exactly one {label} summary")
        counts.append(int(matches[0]))
    total, passed, failed = counts
    if total != passed + failed:
        raise AssertionError("inconsistent testbench counts")
    if output.count("[PASS]") != passed or output.count("[FAIL]") != failed:
        raise AssertionError("summary disagrees with individual check rows")
    return total, passed, failed


def healthy(result: subprocess.CompletedProcess[str], expected: int) -> bool:
    """A printed success or process success alone is insufficient."""
    return result.returncode == 0 and summary(result.stdout) == (expected, expected, 0)


def require_failure_exit(result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode == 0 or summary(result.stdout)[2] == 0:
        raise AssertionError("failed checks must produce a nonzero process exit")


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise AssertionError(f"stale mutation anchor: {old}")
    return source.replace(old, new, 1)


def run_case(args, name: str, tb: str, rtl: str):
    root = args.output_dir / name
    root.mkdir(parents=True, exist_ok=True)
    tb_file = root / "spiral_testbench_ra.v"
    rtl_file = root / "spiral_ra_coherence.v"
    image = root / "ra.vvp"
    tb_file.write_text(tb, encoding="utf-8", newline="\n")
    rtl_file.write_text(rtl, encoding="utf-8", newline="\n")
    command = [str(args.iverilog)]
    if args.ivl_dir:
        command += ["-B", str(args.ivl_dir)]
    command += [
        "-g2012", "-s", "spiral_testbench_ra", "-o", str(image),
        str(tb_file), str(rtl_file), str(args.source_dir / "spiral_consent.v"),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    (root / "compile.log").write_text(
        compiled.stdout + compiled.stderr, encoding="utf-8", newline="\n"
    )
    if compiled.returncode:
        raise AssertionError(f"{name}: compile failed; see {root / 'compile.log'}")
    command = [str(args.vvp)]
    if args.ivl_dir:
        command += ["-M", str(args.ivl_dir)]
    command += [str(image)]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8")
    (root / "run.log").write_text(
        result.stdout + result.stderr, encoding="utf-8", newline="\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iverilog", type=Path, required=True)
    parser.add_argument("--vvp", type=Path, required=True)
    parser.add_argument("--ivl-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.iverilog = args.iverilog.resolve()
    args.vvp = args.vvp.resolve()
    args.output_dir = args.output_dir.resolve()
    if args.ivl_dir:
        args.ivl_dir = args.ivl_dir.resolve()
    args.source_dir = Path(__file__).resolve().parent
    tb = (args.source_dir / "spiral_testbench_ra.v").read_text(encoding="utf-8")
    rtl = (args.source_dir / "spiral_ra_coherence.v").read_text(encoding="utf-8")

    result = run_case(args, "control", tb, rtl)
    if not healthy(result, 33):
        raise AssertionError(f"control failed: exit={result.returncode} counts={summary(result.stdout)}")
    print("control checks=33 passed=33 failed=0 exit=0")

    # Each case names the single failing mutation and uses the clean compiled
    # control above. A compile error never counts as a killed mutation.
    wrong_mid = replace_once(tb, "coh_low && !coh_medium && !coh_high", "coh_medium")
    wrong_phi = replace_once(tb, "hdr_phi == 3'd1", "hdr_phi == 3'd3")
    no_medium = replace_once(
        rtl,
        "assign medium_coherence = (final_score >= 10'd300) && (final_score < 10'd500);",
        "assign medium_coherence = 1'b0;",
    )
    for name, mutant_tb, mutant_rtl in (
        ("restored-wrong-mid-band", wrong_mid, rtl),
        ("restored-wrong-encoded-phi", wrong_phi, rtl),
        ("medium-output-always-false", tb, no_medium),
    ):
        result = run_case(args, name, mutant_tb, mutant_rtl)
        if healthy(result, 33):
            raise AssertionError(f"survived mutation: {name}")
        require_failure_exit(result)
        print(f"killed {name} failed={summary(result.stdout)[2]} exit={result.returncode}")

    # The failing-phi positive control must exit nonzero. Removing only the fatal
    # behavior makes the same failed check exit zero, which this assertion kills.
    no_fatal = replace_once(wrong_phi, '$fatal(1, "RA testbench failed");', '$display("fatal removed");')
    result = run_case(args, "failure-exit-removed", no_fatal, rtl)
    if summary(result.stdout) != (33, 32, 1) or result.returncode != 0:
        raise AssertionError("stale failure-exit mutation: expected one failed row and exit zero")
    try:
        require_failure_exit(result)
    except AssertionError:
        pass
    else:
        raise AssertionError("failure-exit mutation survived the status assertion")
    print("killed failure-exit-removed failed=1 exit=0 (failure-status contract detects mutant)")
    print("mutations killed=4 survived=0 clean_controls=1 failed_controls=0")


if __name__ == "__main__":
    main()
