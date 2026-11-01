"""Execute thirteen bounded fleet path-policy and boundary mutants in Rust copies.

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
REUSED_SOURCES = (
    "rust/rpp-core/src/canonical.rs",
    "rust/rpp-core/src/overlay.rs",
    "rust/rpp-core/src/resolver.rs",
    "rust/rpp-link/src/lib.rs",
    "rust/rpp-control/src/lib.rs",
)


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
        "wrong_failover_order", "rpp-fleet", "rpp-fleet/src/resolver.rs",
        "routes.push(Self::resolved(&selected.0, chosen.clone()));",
        "routes.insert(0, Self::resolved(&selected.0, chosen.clone()));",
        Test("scenarios", "reading_changes_reorder_routes_using_existing_core_policy"),
        Test("scenarios", "xiaozhi_websocket_gateway_uses_lan_policy"),
    ),
    Mutation(
        "data_on_ble", "rpp-fleet", "rpp-fleet/src/endpoint.rs",
        "LinkKind::Ble => Underlay::Bluetooth,", "LinkKind::Ble => Underlay::Lan,",
        Test("scenarios", "unreviewed_ble_is_not_data_route"),
        Test("scenarios", "xiaozhi_websocket_gateway_uses_lan_policy"),
    ),
    Mutation(
        "control_on_data_path", "rpp-fleet", "rpp-fleet/src/resolver.rs",
        "if path == TrafficPath::Data {", "if false && path == TrafficPath::Data {",
        Test("scenarios", "control_resolution_rejects_data_path_without_consuming_sequence"),
        Test("scenarios", "verified_control_route_dispatch_uses_control_hook_only"),
    ),
    Mutation(
        "node_capacity_bypass", "rpp-fleet", "rpp-fleet/src/registry.rs",
        "if self.nodes.len() >= MAX_NODES {", "if false && self.nodes.len() >= MAX_NODES {",
        Test("capacity", "exactly_sixteen_nodes_fit_and_seventeenth_rejection_preserves_all_registry_indices"),
        Test("scenarios", "xiaozhi_websocket_gateway_uses_lan_policy"),
    ),
    Mutation(
        "endpoint_registration_capacity_bypass", "rpp-fleet", "rpp-fleet/src/registry.rs",
        "if endpoints.len() > MAX_ENDPOINTS_PER_NODE {\n            return Err(RegistryError::Capacity);\n        }\n        let identity",
        "if false && endpoints.len() > MAX_ENDPOINTS_PER_NODE {\n            return Err(RegistryError::Capacity);\n        }\n        let identity",
        Test("capacity", "registration_accepts_four_endpoints_and_five_is_an_atomic_capacity_error"),
        Test("scenarios", "xiaozhi_websocket_gateway_uses_lan_policy"),
    ),
    Mutation(
        "endpoint_replacement_capacity_bypass", "rpp-fleet", "rpp-fleet/src/registry.rs",
        "if endpoints.len() > MAX_ENDPOINTS_PER_NODE {\n            return Err(RegistryError::Capacity);\n        }\n        if !self.nodes.contains_key(identity)",
        "if false && endpoints.len() > MAX_ENDPOINTS_PER_NODE {\n            return Err(RegistryError::Capacity);\n        }\n        if !self.nodes.contains_key(identity)",
        Test("capacity", "replacement_accepts_four_endpoints_and_five_keeps_the_entire_registry_unchanged"),
        Test("scenarios", "xiaozhi_websocket_gateway_uses_lan_policy"),
    ),
    Mutation(
        "uri_capacity_bypass", "rpp-fleet", "rpp-fleet/src/endpoint.rs",
        "if uri.len() > MAX_URI_LEN {", "if false && uri.len() > MAX_URI_LEN {",
        Test("negative", "uri_byte_limit_accepts_exactly_limit_and_rejects_plus_one_atomically"),
        Test("scenarios", "xiaozhi_websocket_gateway_uses_lan_policy"),
    ),
    Mutation(
        "uri_ascii_bypass", "rpp-fleet", "rpp-fleet/src/endpoint.rs",
        "if uri.is_empty() || !uri.bytes().all(|byte| (0x20..=0x7e).contains(&byte)) {",
        "if uri.is_empty() {",
        Test("negative", "hostile_uri_characters_and_empty_websocket_authorities_are_rejected"),
        Test("scenarios", "xiaozhi_websocket_gateway_uses_lan_policy"),
    ),
    Mutation(
        "silent_invalid_reference", "rpp-fleet", "rpp-fleet/src/resolver.rs",
        ".ok_or(FleetResolveError::InvalidDataReference)?\n            .as_slice();",
        ".map(Vec::as_slice)\n            .unwrap_or(&[]);",
        Test("negative", "invalid_reference_errors_precede_all_policy_state_changes"),
        Test("scenarios", "verified_control_route_dispatch_uses_control_hook_only"),
    ),
    Mutation(
        "non_clock_invalid_input_mislabeled", "rpp-fleet", "rpp-fleet/src/resolver.rs",
        "Status::InvalidInput => return Err(FleetResolveError::InvalidInput),\n            Status::NoChannel => {",
        "Status::InvalidInput => return Err(FleetResolveError::ClockRollback),\n            Status::NoChannel => {",
        Test("lib", "resolver::tests::current_tick_with_malformed_core_input_remains_invalid_input"),
        Test("lib", "identity::tests::explicit_binding_preserves_core_encoding_and_checks_full_identity"),
    ),
    Mutation(
        "data_rollback_guard_bypassed", "rpp-fleet", "rpp-fleet/src/resolver.rs",
        ") -> Result<DataResolution, FleetResolveError> {\n        // Rollback is checked first, before validation or core state changes.\n        if tick < self.policy.clock() {",
        ") -> Result<DataResolution, FleetResolveError> {\n        // Rollback is checked first, before validation or core state changes.\n        if false && tick < self.policy.clock() {",
        Test("clock", "rollback_tick_with_valid_input_is_rejected_without_spending_state"),
        Test("scenarios", "xiaozhi_websocket_gateway_uses_lan_policy"),
    ),
    Mutation(
        "control_rollback_after_path_validation", "rpp-fleet", "rpp-fleet/src/resolver.rs",
        ") -> Result<ControlResolution<'frame>, FleetResolveError> {\n        // Rollback is checked first, before validation or core state changes.\n        if tick < self.policy.clock() {",
        ") -> Result<ControlResolution<'frame>, FleetResolveError> {\n        // Mutant: inspect the path before checking rollback.\n        if path == TrafficPath::Data {\n            return Err(FleetResolveError::ControlOnDataPath);\n        }\n        if tick < self.policy.clock() {",
        Test("clock", "rollback_tick_with_invalid_input_is_checked_first_and_preserves_state"),
        Test("scenarios", "xiaozhi_websocket_gateway_uses_lan_policy"),
    ),
    Mutation(
        "sentinel_reading_bypass", "rpp-fleet", "rpp-fleet/src/endpoint.rs",
        "if !reading.valid() || reading.latency_ms == u64::MAX || reading.jitter_ms == u64::MAX {",
        "if !reading.valid() {",
        Test("negative", "rejected_reading_updates_preserve_good_data_control_and_registry_state"),
        Test("scenarios", "xiaozhi_websocket_gateway_uses_lan_policy"),
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


def source_fingerprints(repository):
    return {name: sha256((repository / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in REUSED_SOURCES}


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
    fingerprints = source_fingerprints(repository)
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
    if len(MUTATIONS) != 13:
        raise RuntimeError("thirteen fleet policy and boundary mutations must be configured")
    evidence = []
    for mutation in MUTATIONS:
        case = args.work_dir / mutation.name
        if case.exists():
            marker = case / ".rust-scaffold-mutation"
            if not marker.is_file() or marker.read_text(encoding="utf-8") != "CX-010 disposable mutation workspace\n":
                raise RuntimeError(f"refusing to replace an unowned workspace: {case}")
            shutil.rmtree(case)
        case.mkdir()
        (case / ".rust-scaffold-mutation").write_text(
            "CX-010 disposable mutation workspace\n", encoding="utf-8", newline="\n"
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
    if source_fingerprints(repository) != fingerprints:
        raise RuntimeError("reused source changed during the mutation run; re-review and repeat")
    summary = {"toolchain": tools, "mutants": evidence, "killed": len(evidence), "survived": 0,
               "reused_sources_sha256_lf": fingerprints,
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
