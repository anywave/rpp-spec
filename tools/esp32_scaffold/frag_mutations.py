"""Execute twelve bounded fragmentation counterfactuals in disposable Rust copies.

Only the named test's assertion panic counts; compilation and arbitrary panic
failures are tool errors. Baseline and unaffected mutated controls must pass.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil

from tools.esp32_scaffold.mutation_check import (
    Mutation, Test, assertion_failure, classifier_controls, passed_test, run_test, version,
)

SOURCE = "rpp-frag/src/reassembly.rs"
CLEAN = Test("reassembly", "out_of_order_valid_and_forged_frames_require_caller_verifier")


def mutation(name, before, after, positive, clean=CLEAN):
    return Mutation(name, "rpp-frag", SOURCE, before, after, Test("reassembly", positive), clean)


MUTATIONS = (
    Mutation("scenario_data_over_ble", "rpp-link", "rpp-link/src/simulated.rs",
             "if self.kind() == LinkKind::Ble {", "if false {",
             Test("ble", "data_over_simulated_ble_is_refused_without_fragments", ("sim",)),
             Test("simulated", "adapter_driven_scenarios_match_three_python_artifacts", ("sim",))),
    mutation("duplicate_advances_clock", "if !added {", "if false {",
             "identical_duplicate_does_not_advance_remembered_tick"),
    Mutation("scenario_ble_bypass", "rpp-link", "rpp-link/src/simulated.rs",
             "if self.metadata.underlay == Underlay::Bluetooth {", "if false {",
             Test("simulated", "adapter_driven_scenarios_match_three_python_artifacts", ("sim",)),
             Test("ble", "simulated_ble_fragments_control_at_mtu20_and_decodes_again", ("sim",))),
    mutation("overlap_accepted", "return Err(Error::Overlap);", "continue;",
             "different_byte_overlap_is_rejected_without_poisoning_uncovered_prefix"),
    mutation("bounds_accepted", "end > total", "end > MAX_LEN",
             "offset_plus_length_beyond_total_is_rejected_before_any_copy"),
    mutation("duplicate_counted_twice", "if !slot.seen[offset + i] {", "if true {",
             "duplicates_do_not_count_twice_or_complete_without_last_fragment"),
    mutation("timeout_never_fires", "if tick >= self.slots[index].deadline {", "if false {",
             "timeout_is_half_open_and_duplicates_never_refresh_deadline"),
    mutation("slots_full_evicts", ".ok_or(Error::SlotsFull)?", ".unwrap_or(0)",
             "slots_full_refuses_new_tag_without_eviction"),
    mutation("peer_key_omitted", "s.active && s.peer == peer && s.tag == tag", "s.active && s.tag == tag",
             "two_peers_with_same_tag_never_merge_coverage"),
    Mutation("fragment_exceeds_mtu", "rpp-frag", "rpp-frag/src/lib.rs",
             "self.mtu - HEADER_LEN", "self.mtu",
             Test("fragmenter", "emitted_fragments_never_exceed_mtu_and_reconstruct_exact_bytes"),
             Test("fragmenter", "constructors_reject_empty_or_oversize_datagrams")),
    mutation("missing_last_completes", "slot.covered == slot.total", "slot.covered >= slot.total - 7",
             "missing_last_fragment_never_completes",
             Test("reassembly", "offset_plus_length_beyond_total_is_rejected_before_any_copy")),
    Mutation("data_over_ble", "rpp-link", "rpp-link/src/simulated/ble.rs",
             "Err(Error::DataUnsupported)", "Ok(DataOutcome::Sent)",
             Test("ble", "data_over_simulated_ble_is_refused_without_fragments", ("sim",)),
             Test("ble", "simulated_ble_fragments_control_at_mtu20_and_decodes_again", ("sim",))),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cargo", "rustc", "library-dir", "work-dir", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    for name in ("cargo", "rustc", "library_dir", "work_dir", "output_dir"):
        setattr(args, name, getattr(args, name).resolve())
    for path in (args.work_dir, args.output_dir):
        if path == repo or repo in path.parents:
            parser.error("work/output must be outside checkout")
        path.mkdir(parents=True, exist_ok=True)
    receipt = args.output_dir / "frag-mutations.json"
    receipt.unlink(missing_ok=True)
    environment = dict(os.environ, RUSTC=str(args.rustc), LD_LIBRARY_PATH=str(args.library_dir),
                       CARGO_HOME=str(args.work_dir / "cargo-home"), CARGO_BUILD_JOBS="1",
                       CARGO_TERM_COLOR="never", RUST_BACKTRACE="0")
    tools = {"cargo": version(args.cargo, "cargo", environment),
             "rustc": version(args.rustc, "rustc", environment)}
    rejected = classifier_controls()
    evidence = []
    for item in MUTATIONS:
        case = args.work_dir / item.name
        case.mkdir()  # Existing evidence is never silently replaced.
        (case / ".cx021-owned").write_text(item.name + "\n", encoding="ascii")
        workspace = case / "rust"
        shutil.copytree(repo / "rust", workspace, ignore=shutil.ignore_patterns("target", ".git"))
        source = workspace / item.source
        original = source.read_text(encoding="utf-8")
        if original.count(item.before) != 1:
            raise RuntimeError(f"stale or ambiguous anchor: {item.name}")
        baseline = run_test(args, workspace, "baseline", item.package, item.positive, environment, case / "target")
        if not passed_test(baseline, item.positive):
            raise RuntimeError(f"baseline failed: {item.name}")
        changed = original.replace(item.before, item.after, 1)
        source.write_text(changed, encoding="utf-8", newline="\n")
        result = run_test(args, workspace, "mutant", item.package, item.positive, environment, case / "target")
        if not assertion_failure(result, item.positive):
            raise RuntimeError(f"not an assertion kill: {item.name}")
        control = run_test(args, workspace, "control", item.package, item.clean, environment, case / "target")
        if not passed_test(control, item.clean):
            raise RuntimeError(f"mutated clean control failed: {item.name}")
        evidence.append({"name": item.name, "source": item.source,
                         "source_sha256": sha256(original.encode()).hexdigest(),
                         "mutant_sha256": sha256(changed.encode()).hexdigest(),
                         "positive": item.positive.name, "clean": item.clean.name,
                         "baseline": "pass", "mutant": "assertion", "control": "pass"})
        # Only this run's completed target is removed; sources and logs remain.
        if (case / ".cx021-owned").read_text(encoding="ascii") != item.name + "\n":
            raise RuntimeError("owned scratch marker changed")
        shutil.rmtree(case / "target")
        print(f"killed {item.name}; baseline=pass assertion=fail clean=pass", flush=True)
    payload = {"toolchain": tools, "killed": len(evidence), "survived": 0,
               "classifier_rejections": rejected, "cases": evidence}
    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
    receipt.write_bytes(encoded)
    print(f"killed={len(evidence)} receipt_sha256={sha256(encoded).hexdigest()}")


if __name__ == "__main__":
    main()
