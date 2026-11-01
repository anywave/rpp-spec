"""Execute seven named Rust policy/bookkeeping mutants in workspace copies.

This stdlib Python scaffold is outside the Rust crate and is never shipped by it.
Only a bounded, selected Rust test's assertion panic kills a mutant. Compiler
errors, arbitrary panics, signals, missing tests and broken clean controls fail
the runner rather than being reported as successful mutation evidence.
"""

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


TOOLCHAIN = "1.85.1"
REVIEWED_SOURCES = (
    "rpp-core/src/canonical.rs",
    "rpp-core/src/mobius32.rs",
    "rpp-core/src/overlay.rs",
    "rpp-core/tests/canonical.rs",
    "rpp-core/tests/overlay.rs",
    "rpp-core/tests/selection_preview.rs",
)


@dataclass(frozen=True)
class Test:
    target: str
    name: str


@dataclass(frozen=True)
class Mutation:
    name: str
    source: str
    before: str
    after: str
    positive: Test
    clean: Test


MUTATIONS = (
    Mutation(
        "address_field_shift", "rpp-core/src/canonical.rs",
        "((self.theta as u32) << 27)", "((self.theta as u32) << 26)",
        Test("canonical", "constructor_corpus_matches_python_words_and_bytes"),
        Test("lib", "mobius32::tests::golden_vectors_encode"),
    ),
    Mutation(
        "rounding_mode", "rpp-core/src/canonical.rs",
        "if fraction > 0.5 || (fraction == 0.5 && lower & 1 != 0) {", "if fraction >= 0.5 {",
        Test("canonical", "constructor_corpus_matches_python_words_and_bytes"),
        Test("lib", "mobius32::tests::golden_vectors_encode"),
    ),
    Mutation(
        "retry_after_first_token", "rpp-core/src/overlay.rs",
        "if tokens > 0 {", "if false {",
        Test("overlay", "retry_stops_after_first_token"),
        Test("overlay", "retry_before_token_preserves_meter_rows"),
    ),
    Mutation(
        "expired_billboard_applied", "rpp-core/src/overlay.rs",
        "&& tick < candidate.until", "&& true",
        Test("overlay", "billboard_expiry_and_clock_rollback"),
        Test("overlay", "billboard_unexpired_delivery"),
    ),
    Mutation(
        "latest_appends_history", "rpp-core/src/overlay.rs",
        "self.known_data_paths\n                .retain(|path| path.source != source || path.target != target);",
        "",
        Test("selection_preview", "latest_paths_bound_varying_snapshots_and_preserve_each_other_pair"),
        Test("selection_preview", "unavailable_or_invalid_latest_selection_preserves_historical_reference_without_new_ttl"),
    ),
    Mutation(
        "retention_noop", "rpp-core/src/overlay.rs",
        "self.rows.drain(..remove);", "let _ = remove;",
        Test("selection_preview", "retained_meter_window_stays_flat_and_preserves_global_ids_across_ten_thousand_controls"),
        Test("selection_preview", "ten_thousand_previews_do_not_spend_clock_sequence_requests_rows_or_references"),
    ),
    Mutation(
        "row_id_from_vector_length", "rpp-core/src/overlay.rs",
        "row: self.next_row,", "row: self.rows.len() as u64 + 1,",
        Test("selection_preview", "retention_preserves_retry_rows_with_one_request_and_default_history"),
        Test("selection_preview", "data_preview_preserves_validation_ranking_and_relay_outcomes"),
    ),
)


def one_test_summary(output, passed, failed):
    expression = (rf"^test result: {'ok' if failed == 0 else 'FAILED'}\. "
                  rf"{passed} passed; {failed} failed; 0 ignored; 0 measured; "
                  r"\d+ filtered out; finished in .+$")
    return (len(re.findall(r"^running 1 test$", output, re.MULTILINE)) == 1
            and len(re.findall(expression, output, re.MULTILINE)) == 1)


def passed_test(result, test):
    return (result.returncode == 0 and one_test_summary(result.stdout, 1, 0)
            and re.search(rf"^test {re.escape(test.name)} \.\.\. ok$", result.stdout, re.MULTILINE)
            is not None)


def assertion_failure(result, test):
    diagnostic = result.stdout + result.stderr
    return (
        result.returncode == 101 and one_test_summary(result.stdout, 0, 1)
        and re.search(rf"^test {re.escape(test.name)} \.\.\. FAILED$", result.stdout, re.MULTILINE)
        is not None
        and "panicked at " in diagnostic
        and re.search(r"^assertion (?:`.*` failed|failed:)", diagnostic, re.MULTILINE) is not None
        and re.search(r"^error(?:\[|: could not compile)", diagnostic, re.MULTILINE) is None
    )


def classifier_controls():
    """Mutation false-kill: compile errors/arbitrary panics/empty runs must fail."""
    test = Test("fixture", "bounded_assertion_case")
    output = ("running 1 test\ntest bounded_assertion_case ... FAILED\n\n"
              "thread 'bounded_assertion_case' panicked at tests/fixture.rs:1:1:\n"
              "assertion `left == right` failed\n  left: 1\n right: 2\n\n"
              "test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; "
              "0 filtered out; finished in 0.00s\n")
    good = subprocess.CompletedProcess([], 101, output, "error: test failed\n")
    if not assertion_failure(good, test):
        raise RuntimeError("assertion-failure classifier rejected its clean fixture")
    bad = (
        subprocess.CompletedProcess([], 101, "", "error[E0308]: mismatched types\n"),
        subprocess.CompletedProcess([], 101, output.replace("assertion `left == right` failed", "explicit panic"), ""),
        subprocess.CompletedProcess([], -6, output, "process aborted"),
        subprocess.CompletedProcess([], 0, output, ""),
        subprocess.CompletedProcess([], 101, output.replace("running 1 test", "running 0 tests"), ""),
        subprocess.CompletedProcess([], 101, output.replace("bounded_assertion_case ... FAILED", "another_case ... FAILED"), ""),
    )
    if any(assertion_failure(result, test) for result in bad):
        raise RuntimeError("non-assertion failure counted as a killed mutant")
    return len(bad)


def run_test(args, workspace, label, test, environment, target):
    command = [str(args.cargo), "test", "--manifest-path", str(workspace / "Cargo.toml"),
               "--offline", "--locked", "--package", "rpp-core"]
    command += ["--lib"] if test.target == "lib" else ["--test", test.target]
    command += [test.name, "--", "--exact", "--color", "never"]
    result = subprocess.run(command, cwd=workspace, env=dict(environment, CARGO_TARGET_DIR=str(target)),
                            capture_output=True, text=True, encoding="utf-8", timeout=180)
    (workspace.parent / f"{label}.stdout.log").write_text(result.stdout, encoding="utf-8", newline="\n")
    (workspace.parent / f"{label}.stderr.log").write_text(result.stderr, encoding="utf-8", newline="\n")
    return result


def version(executable, program, environment):
    result = subprocess.run([str(executable), "--version"], env=environment, capture_output=True,
                            text=True, encoding="utf-8", check=True, timeout=30)
    value = result.stdout.strip()
    if not re.match(rf"^{program} {re.escape(TOOLCHAIN)}(?: |$)", value):
        raise RuntimeError(f"{program} must be pinned to {TOOLCHAIN}; observed {value}")
    return value


def source_fingerprints(workspace):
    return {name: sha256((workspace / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in REVIEWED_SOURCES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cargo", type=Path, required=True)
    parser.add_argument("--rustc", type=Path, required=True)
    parser.add_argument("--library-dir", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for name in ("cargo", "rustc", "library_dir", "work_dir", "output_dir"):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    repository = Path(__file__).resolve().parents[2]
    source_workspace = repository / "rust"
    if args.work_dir.is_relative_to(repository) or args.output_dir.is_relative_to(repository):
        parser.error("mutation work/output directories must be outside the repository worktree")
    if not (source_workspace / "Cargo.lock").is_file():
        parser.error("the committed Rust lockfile is required")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "mutation-summary.json"
    summary_path.unlink(missing_ok=True)
    environment = dict(os.environ, RUSTC=str(args.rustc), CARGO_TERM_COLOR="never",
                       RUST_BACKTRACE="0", CARGO_HOME=str(args.work_dir / "cargo-home"), CARGO_BUILD_JOBS="1")
    if args.library_dir:
        previous = environment.get("LD_LIBRARY_PATH")
        environment["LD_LIBRARY_PATH"] = str(args.library_dir) + (os.pathsep + previous if previous else "")
    tools = {"cargo": version(args.cargo, "cargo", environment), "rustc": version(args.rustc, "rustc", environment)}
    rejected = classifier_controls()
    if len(MUTATIONS) != 7:
        raise RuntimeError("seven core policy/bookkeeping mutations must be configured")
    fingerprints = source_fingerprints(source_workspace)
    evidence = []
    for mutation in MUTATIONS:
        case = args.work_dir / mutation.name
        if case.exists():
            marker = case / ".rust-scaffold-mutation"
            if not marker.is_file() or marker.read_text(encoding="utf-8") != "CX-007 disposable mutation workspace\n":
                raise RuntimeError(f"refusing to replace an unowned workspace: {case}")
            shutil.rmtree(case)
        case.mkdir()
        (case / ".rust-scaffold-mutation").write_text(
            "CX-007 disposable mutation workspace\n", encoding="utf-8", newline="\n"
        )
        workspace = case / "rust"
        shutil.copytree(source_workspace, workspace, ignore=shutil.ignore_patterns("target", ".git"))
        path = workspace / mutation.source
        original = path.read_text(encoding="utf-8")
        if original.count(mutation.before) != 1:
            raise RuntimeError(f"stale or ambiguous source anchor for {mutation.name}")
        baseline = run_test(args, workspace, "baseline", mutation.positive, environment, case / "baseline-target")
        if not passed_test(baseline, mutation.positive):
            raise RuntimeError(f"baseline test failed for {mutation.name}; inspect {case}")
        changed = original.replace(mutation.before, mutation.after, 1)
        path.write_text(changed, encoding="utf-8", newline="\n")
        result = run_test(args, workspace, "mutant", mutation.positive, environment, case / "mutant-target")
        if not assertion_failure(result, mutation.positive):
            raise RuntimeError(f"{mutation.name} survived or failed without the required assertion; inspect {case}")
        control = run_test(args, workspace, "control", mutation.clean, environment, case / "mutant-target")
        if not passed_test(control, mutation.clean):
            raise RuntimeError(f"clean control failed for {mutation.name}; inspect {case}")
        evidence.append({"name": mutation.name, "source": mutation.source,
                         "original_sha256": sha256(original.encode("utf-8")).hexdigest(),
                         "mutated_sha256": sha256(changed.encode("utf-8")).hexdigest(),
                         "positive_test": mutation.positive.name, "clean_test": mutation.clean.name,
                         "baseline_passed": True, "assertion_failed": True, "clean_control_passed": True})
        print(f"killed {mutation.name}; baseline=pass assertion=fail clean_control=pass")
    if source_fingerprints(source_workspace) != fingerprints:
        raise RuntimeError("reviewed source changed during the mutation run; re-review and repeat")
    summary = {"toolchain": tools, "mutants": evidence, "killed": len(evidence), "survived": 0,
               "reviewed_sources_sha256_lf": fingerprints,
               "baseline_controls_passed": len(evidence), "clean_controls_passed": len(evidence),
               "controls_failed": 0, "nonassertion_classifier_controls_rejected": rejected}
    encoded = (json.dumps(summary, sort_keys=True, indent=2) + "\n").encode("utf-8")
    summary_path.write_bytes(encoded)
    print(f"killed={len(evidence)} survived=0 baseline_controls={len(evidence)} clean_controls={len(evidence)} controls_failed=0")
    print(f"mutation-summary.json sha256={sha256(encoded).hexdigest()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"mutation_check: tool error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
