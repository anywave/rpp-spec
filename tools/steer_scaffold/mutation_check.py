"""Run bounded steering mutations in disposable Rust copies, never in production.

Run as ``python -m tools.steer_scaffold.mutation_check``. Only the selected
Rust test's assertion panic kills a mutant; compiler errors, missing tests,
arbitrary panics and broken clean controls fail this runner.
"""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from tools.esp32_scaffold.mutation_check import (
    Mutation, Test, assertion_failure, classifier_controls, passed_test, run_test, version,
)


RULE_CLEAN = Test("rules", "equal_scores_choose_smallest_id_in_either_input_order")
MTU_CLEAN = Test("rules", "mtu_means_atomic_payload_bytes_not_a_reassembled_control_frame")
RESTRICTION = "link.kind == LinkKind::Ble || link.cost == CostClass::ControlOnly"
RESTRICTED_TEST = Test("rules", "ble_and_control_only_never_carry_bulk_or_billboards")
BOUNDARY_TEST = Test("hysteresis", "hold_then_absolute_margin_switches_at_exact_boundaries")
ATOMIC_TEST = Test("hysteresis", "invalid_inputs_and_rollback_preserve_all_state_and_clock")


def mutation(name, source, before, after, positive, clean=RULE_CLEAN):
    return Mutation(name, "rpp-steer", f"rpp-steer/src/{source}.rs", before, after, positive, clean)


MUTATIONS = (
    mutation("down_eligible", "ranking",
             "link.reading.available && wire_bytes <= usize::from(link.mtu)",
             "true && wire_bytes <= usize::from(link.mtu)",
             Test("rules", "down_and_missing_links_never_win")),
    mutation("ble_bulk", "ranking", RESTRICTION,
             "(link.kind == LinkKind::Ble && class != MessageClass::Bulk) || link.cost == CostClass::ControlOnly",
             RESTRICTED_TEST),
    mutation("ble_billboard", "ranking", RESTRICTION,
             "(link.kind == LinkKind::Ble && class != MessageClass::Billboard) || link.cost == CostClass::ControlOnly",
             RESTRICTED_TEST),
    mutation("control_only_bulk", "ranking", RESTRICTION,
             "link.kind == LinkKind::Ble || (link.cost == CostClass::ControlOnly && class != MessageClass::Bulk)",
             RESTRICTED_TEST),
    mutation("control_only_billboard", "ranking", RESTRICTION,
             "link.kind == LinkKind::Ble || (link.cost == CostClass::ControlOnly && class != MessageClass::Billboard)",
             RESTRICTED_TEST),
    mutation("loss_reversed", "ranking", "left.reading.loss_ppm.cmp(&right.reading.loss_ppm)",
             "right.reading.loss_ppm.cmp(&left.reading.loss_ppm)",
             Test("rules", "control_and_billboard_prefer_loss_while_bulk_uses_measured_throughput")),
    mutation("throughput_reversed", "ranking", "right.throughput_kbps.cmp(&left.throughput_kbps)",
             "left.throughput_kbps.cmp(&right.throughput_kbps)",
             Test("rules", "full_width_metrics_compare_without_sum_or_negation_overflow")),
    mutation("id_reversed", "ranking", "left.id.cmp(&right.id)", "right.id.cmp(&left.id)",
             RULE_CLEAN, MTU_CLEAN),
    mutation("hold_omitted", "selector", "if tick - state.since < self.params.hold_ticks {",
             "if false && tick - state.since < self.params.hold_ticks {", BOUNDARY_TEST),
    mutation("margin_omitted", "selector", "else if improvement < margin {",
             "else if false && improvement < margin {", BOUNDARY_TEST),
    mutation("mtu_ignored", "ranking", "wire_bytes <= usize::from(link.mtu)", "wire_bytes > 0",
             Test("hysteresis", "down_missing_and_too_small_incumbents_bypass_hold_and_margin")),
    mutation("clock_before_validation", "selector", "ranking::validate(tick, wire_bytes, links)?;",
             "self.clock = Some(tick);\n        ranking::validate(tick, wire_bytes, links)?;", ATOMIC_TEST),
    mutation("zero_throughput_eligible", "ranking",
             "if class == MessageClass::Bulk && link.throughput_kbps == 0 {",
             "if false && class == MessageClass::Bulk && link.throughput_kbps == 0 {",
             Test("rules", "zero_throughput_is_bulk_ineligible_but_control_can_still_use_it")),
    mutation("shared_bulk_state", "selector", "MessageClass::Bulk => 1,", "MessageClass::Bulk => 0,",
             Test("hysteresis", "classes_have_independent_hold_state")),
    mutation("rollback_accepted", "selector", "if self.clock.is_some_and(|prior| tick < prior) {",
             "if false && self.clock.is_some_and(|prior| tick < prior) {", ATOMIC_TEST),
    mutation("outage_state_retained", "selector", "if decision.link_id != state.id {",
             "if decision.link_id.is_some() && decision.link_id != state.id {",
             Test("hysteresis", "no_channel_clears_hold_before_a_new_initial_selection")),
    mutation("margin_inclusive", "selector", "else if improvement < margin {",
             "else if improvement <= margin {",
             Test("hysteresis", "zero_and_maximum_margins_use_subtraction_without_overflow")),
)
MARKER = "CX-023 disposable steering mutation workspace\n"


def source_text(path):
    """Hash exactly UTF-8 bytes after CRLF-to-LF; retain other source bytes."""
    return path.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")


def digest(text):
    return sha256(text.encode("utf-8")).hexdigest()


def test_hash(workspace, test):
    relative = "src/lib.rs" if test.target == "lib" else f"tests/{test.target}.rs"
    return digest(source_text(workspace / "rpp-steer" / relative))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cargo", "rustc", "work-dir", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--library-dir", type=Path)
    args = parser.parse_args()
    for name, value in vars(args).items():
        if value is not None:
            setattr(args, name, value.resolve())
    repository = Path(__file__).resolve().parents[2]
    if any(path.is_relative_to(repository) for path in (args.work_dir, args.output_dir)):
        parser.error("mutation work/output directories must be outside the source checkout")
    source_workspace = repository / "rust"
    if not (source_workspace / "Cargo.lock").is_file():
        parser.error("the committed Rust lockfile is required")
    if not 1 <= len(MUTATIONS) <= 24 or len({case.name for case in MUTATIONS}) != len(MUTATIONS):
        raise RuntimeError("configure one to twenty-four uniquely named steering mutations")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "mutation-summary.json"
    summary_path.unlink(missing_ok=True)
    environment = dict(os.environ, RUSTC=str(args.rustc), CARGO_TERM_COLOR="never",
                       RUST_BACKTRACE="0", CARGO_HOME=str(args.work_dir / "cargo-home"),
                       CARGO_BUILD_JOBS="1", CARGO_NET_OFFLINE="true")
    if args.library_dir:
        previous = environment.get("LD_LIBRARY_PATH")
        environment["LD_LIBRARY_PATH"] = str(args.library_dir) + (os.pathsep + previous if previous else "")
    tools = {name: version(getattr(args, name), name, environment) for name in ("cargo", "rustc")}
    rejected = classifier_controls()
    evidence = []
    for mutation in MUTATIONS:
        case = args.work_dir / mutation.name
        if case.exists():
            marker = case / ".steer-mutation"
            if case.is_symlink() or not marker.is_file() or marker.read_text(encoding="utf-8") != MARKER:
                raise RuntimeError(f"refusing to replace an unowned workspace: {case}")
            shutil.rmtree(case)
        case.mkdir()
        (case / ".steer-mutation").write_text(MARKER, encoding="utf-8", newline="\n")
        workspace = case / "rust"
        shutil.copytree(source_workspace, workspace, ignore=shutil.ignore_patterns("target", ".git"))
        path = workspace / mutation.source
        original = source_text(path)
        if original.count(mutation.before) != 1:
            raise RuntimeError(f"stale or ambiguous source anchor for {mutation.name}")
        baseline = run_test(args, workspace, "baseline", mutation.package, mutation.positive,
                            environment, case / "baseline-target")
        if not passed_test(baseline, mutation.positive):
            raise RuntimeError(f"baseline failed for {mutation.name}; inspect {case}")
        changed = original.replace(mutation.before, mutation.after, 1)
        if changed == original:
            raise RuntimeError(f"mutation {mutation.name} did not change its source")
        path.write_text(changed, encoding="utf-8", newline="\n")
        result = run_test(args, workspace, "mutant", mutation.package, mutation.positive,
                          environment, case / "mutant-target")
        if not assertion_failure(result, mutation.positive):
            raise RuntimeError(f"{mutation.name} survived or failed without its named assertion; inspect {case}")
        control = run_test(args, workspace, "control", mutation.package, mutation.clean,
                           environment, case / "mutant-target")
        if not passed_test(control, mutation.clean):
            raise RuntimeError(f"clean control failed for {mutation.name}; inspect {case}")
        evidence.append({"name": mutation.name, "package": mutation.package, "source": mutation.source,
                         "original_sha256": digest(original), "mutated_sha256": digest(changed),
                         "positive_test": mutation.positive.name, "clean_test": mutation.clean.name,
                         "positive_test_sha256": test_hash(workspace, mutation.positive),
                         "clean_test_sha256": test_hash(workspace, mutation.clean),
                         "positive_features": list(mutation.positive.features),
                         "clean_features": list(mutation.clean.features),
                         "baseline_passed": True, "assertion_failed": True, "clean_control_passed": True})
        print(f"killed {mutation.name}; baseline=pass assertion=fail clean_control=pass", flush=True)
        for target_name in ("baseline-target", "mutant-target"):
            shutil.rmtree(case / target_name)
    summary = {"schema_version": 1, "toolchain": tools, "hash_scope": "UTF-8 after CRLF-to-LF only",
               "runner_sha256": digest(source_text(Path(__file__))),
               "classifier_sha256": digest(source_text(Path(run_test.__code__.co_filename))),
               "mutants": evidence, "killed": len(evidence), "survived": 0,
               "baseline_controls_passed": len(evidence), "clean_controls_passed": len(evidence),
               "controls_failed": 0, "nonassertion_classifier_controls_rejected": rejected}
    encoded = (json.dumps(summary, sort_keys=True, indent=2) + "\n").encode("utf-8")
    summary_path.write_bytes(encoded)
    print(f"killed={len(evidence)} survived=0 baseline_controls={len(evidence)} clean_controls={len(evidence)}")
    print(f"mutation-summary.json sha256={sha256(encoded).hexdigest()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, UnicodeError, subprocess.SubprocessError) as error:
        print(f"mutation_check: tool error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
