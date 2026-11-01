"""Execute seven bounded control-codec and adapter mutants in Rust copies.

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


@dataclass(frozen=True)
class Test:
    target: str
    name: str
    features: tuple[str, ...] = ()


@dataclass(frozen=True)
class Mutation:
    name: str
    package: str
    source: str
    before: str
    after: str
    positive: Test
    clean: Test


MUTATIONS = (
    Mutation(
        "control_unknown_kind", "rpp-control", "rpp-control/src/lib.rs",
        "other => Err(DecodeError::UnknownKind(other)),",
        "other => { let _ = other; Ok(Self::Alive) },",
        Test("codec", "unknown_kind_is_rejected_before_verification"),
        Test("codec", "valid_roundtrip_accepts_all_six_kinds"),
    ),
    Mutation(
        "strict_length", "rpp-control", "rpp-control/src/lib.rs",
        "if input.len() > FRAME_LEN {", "if false && input.len() > FRAME_LEN {",
        Test("codec", "strict_length_rejects_appended_payload"),
        Test("codec", "valid_roundtrip_accepts_all_six_kinds"),
    ),
    Mutation(
        "verifier_bypass", "rpp-control", "rpp-control/src/lib.rs",
        "if !verifier.verify(&sender, &header, &signature) {",
        "if false && !verifier.verify(&sender, &header, &signature) {",
        Test("codec", "opaque_signature_verdict_is_required"),
        Test("lib", "tests::round_trip_all_six"),
    ),
    Mutation(
        "recipient_binding", "rpp-control", "rpp-control/src/lib.rs",
        "if recipient != *expected_recipient {", "if false && recipient != *expected_recipient {",
        Test("codec", "frame_for_other_recipient_is_rejected_before_verification"),
        Test("codec", "valid_roundtrip_accepts_all_six_kinds"),
    ),
    Mutation(
        "control_on_data_path", "rpp-link", "rpp-link/src/lib.rs",
        "if path == TrafficPath::Data && matches!(frame, Outbound::Control(_)) {",
        "if false && path == TrafficPath::Data && matches!(frame, Outbound::Control(_)) {",
        Test("adapter", "control_on_data_path_is_rejected_before_adapter_callback"),
        Test("adapter", "valid_data_dispatch_succeeds"),
    ),
    Mutation(
        "separator_alias_dispatch", "rpp-link", "rpp-link/src/simulated.rs",
        "if adapters.iter().any(|adapter| adapter.name().contains('/')) {",
        "if false && adapters.iter().any(|adapter| adapter.name().contains('/')) {",
        Test("simulated", "separator_alias_names_fail_before_control_billboard_policy_or_callbacks", ("sim",)),
        Test("simulated", "adapter_driven_scenarios_match_three_python_artifacts", ("sim",)),
    ),
    Mutation(
        "default_simulation_feature_leak", "rpp-link", "rpp-link/src/lib.rs",
        '#[cfg(feature = "sim")]\npub mod simulated;', '#[cfg(feature = "std")]\npub mod simulated;',
        Test("feature_visibility", "production_consumers_cannot_import_simulation_fixture"),
        Test("adapter", "valid_data_dispatch_succeeds"),
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


def run_test(args, workspace, label, package, test, environment, target):
    command = [str(args.cargo), "test", "--manifest-path", str(workspace / "Cargo.toml"),
               "--offline", "--locked", "--package", package]
    command += ["--lib"] if test.target == "lib" else ["--test", test.target]
    if test.features:
        command += ["--features", ",".join(test.features)]
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
        raise RuntimeError("four codec mutations and three adapter/feature mutations must be configured")
    evidence = []
    for mutation in MUTATIONS:
        case = args.work_dir / mutation.name
        if case.exists():
            marker = case / ".rust-scaffold-mutation"
            if not marker.is_file() or marker.read_text(encoding="utf-8") != "CX-008 disposable mutation workspace\n":
                raise RuntimeError(f"refusing to replace an unowned workspace: {case}")
            shutil.rmtree(case)
        case.mkdir()
        (case / ".rust-scaffold-mutation").write_text(
            "CX-008 disposable mutation workspace\n", encoding="utf-8", newline="\n"
        )
        workspace = case / "rust"
        shutil.copytree(source_workspace, workspace, ignore=shutil.ignore_patterns("target", ".git"))
        path = workspace / mutation.source
        original = path.read_text(encoding="utf-8")
        if original.count(mutation.before) != 1:
            raise RuntimeError(f"stale or ambiguous source anchor for {mutation.name}")
        baseline = run_test(args, workspace, "baseline", mutation.package, mutation.positive, environment, case / "baseline-target")
        if not passed_test(baseline, mutation.positive):
            raise RuntimeError(f"baseline test failed for {mutation.name}; inspect {case}")
        changed = original.replace(mutation.before, mutation.after, 1)
        path.write_text(changed, encoding="utf-8", newline="\n")
        result = run_test(args, workspace, "mutant", mutation.package, mutation.positive, environment, case / "mutant-target")
        if not assertion_failure(result, mutation.positive):
            raise RuntimeError(f"{mutation.name} survived or failed without the required assertion; inspect {case}")
        control = run_test(args, workspace, "control", mutation.package, mutation.clean, environment, case / "mutant-target")
        if not passed_test(control, mutation.clean):
            raise RuntimeError(f"clean control failed for {mutation.name}; inspect {case}")
        evidence.append({"name": mutation.name, "package": mutation.package, "source": mutation.source,
                         "original_sha256": sha256(original.encode("utf-8")).hexdigest(),
                         "mutated_sha256": sha256(changed.encode("utf-8")).hexdigest(),
                         "positive_test": mutation.positive.name, "clean_test": mutation.clean.name,
                         "positive_features": list(mutation.positive.features),
                         "clean_features": list(mutation.clean.features),
                         "baseline_passed": True, "assertion_failed": True, "clean_control_passed": True})
        print(f"killed {mutation.name}; baseline=pass assertion=fail clean_control=pass")
    summary = {"toolchain": tools, "mutants": evidence, "killed": len(evidence), "survived": 0,
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
