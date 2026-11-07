"""Bounded offline mutations in disposable copies; compile errors never kill."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.esp32_scaffold.mutation_check import (  # noqa: E402
    Test, assertion_failure, classifier_controls, passed_test,
)

VALID = "valid_update_replaces_all_grants_and_dispatches"
WEAK = "weak_pin_is_rejected_and_modes_have_distinct_visible_labels"
SEQUENCE = "equal_lower_and_zero_sequences_preserve_the_last_good"
UPDATE_EXPIRY = "expired_update_and_expiry_boundary_preserve_the_last_good"
CLOCK = "invalid_future_update_cannot_poison_clock_and_rollback_is_refused"
APP = "enforce_never_calls_the_operation_on_missing_stale_or_denied_list"
MUTANTS = (
    ("signature_removed", ".map_err(|_| Refusal::BadSignature)?;", ".unwrap_or(());",
     "bad_signature_is_refused_without_replacing_last_good"),
    ("pin_removed", "if list.signer != self.pin.to_bytes() {",
     "if false && list.signer != self.pin.to_bytes() {",
     "unknown_key_is_refused_without_replacing_last_good"),
    ("sequence_removed", "if list.sequence <= self.sequence {",
     "if false && list.sequence <= self.sequence {", SEQUENCE),
    ("equal_sequence_allowed", "if list.sequence <= self.sequence {",
     "if list.sequence < self.sequence {", SEQUENCE),
    ("update_expiry_removed", "if list.expires_at <= now {",
     "if false && list.expires_at <= now {", UPDATE_EXPIRY),
    ("expiry_boundary_inclusive", "if list.expires_at <= now {",
     "if list.expires_at < now {", UPDATE_EXPIRY),
    ("audience_removed", "if list.audience != self.audience {",
     "if false && list.audience != self.audience {",
     "malformed_domain_length_and_wrong_audience_are_refused"),
    ("domain_removed", "|| &bytes[..16] != DOMAIN", "|| false",
     "malformed_domain_length_and_wrong_audience_are_refused"),
    ("weak_pin_allowed", "if pin.is_weak() {", "if false && pin.is_weak() {", WEAK),
    ("floor_ignored", "sequence: sequence_floor,", "sequence: 0,",
     "restart_floor_and_max_sequence_cannot_be_rolled_back"),
    ("update_rollback_allowed", "if now < self.last_now {",
     "if false && now < self.last_now {", CLOCK),
    ("admission_rollback_allowed", "if request.now < self.last_now {",
     "if false && request.now < self.last_now {", CLOCK),
    ("admission_expiry_removed", "if list.expires_at <= request.now {",
     "if false && list.expires_at <= request.now {", APP),
    ("sector_guard_removed", "if list.grants[theta / 8] & (1 << (theta % 8)) == 0 {",
     "if false && list.grants[theta / 8] & (1 << (theta % 8)) == 0 {", APP),
    ("missing_list_allowed", "let list = self.last_good.as_ref().ok_or(Refusal::NoList)?;",
     "let Some(list) = self.last_good.as_ref() else { return Ok(()); };", APP),
    ("enforce_bypassed", "let dispatched = refusal.is_none()",
     "let dispatched = self.mode == Mode::Enforce || refusal.is_none()", APP),
    ("request_update_failure_hidden", "update_result.and_then(|()| self.check(&request)).err()",
     "{ let _ = update_result; self.check(&request).err() }",
     "enforce_refuses_each_bad_update_at_the_operation_boundary"),
    ("consent_bypassed_in_log_only", "refusal != Some(Refusal::NoConsent)", "true",
     "neither_mode_bypasses_current_consent"),
    ("audit_failure_ignored", "if !audit(admission) {", "if !audit(admission) && false {",
     "unavailable_audit_refuses_dispatch_in_both_modes"),
    ("last_good_not_replaced", "self.last_good = Some(list);", "let _ = list;", VALID),
    ("log_only_mode_hidden", "mode: self.mode,", "mode: Mode::Enforce,",
     "log_only_is_explicit_visible_and_does_not_accept_bad_updates"),
    ("phi_as_consent_axis", "request.address.theta()", "request.address.phi()",
     "only_theta_selects_grants_including_both_bitmap_edges"),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    environment = dict(os.environ, CARGO_INCREMENTAL="0")
    rows = []
    controls = classifier_controls()
    with tempfile.TemporaryDirectory(prefix="rpp-gatelist-mutants-") as directory:
        work = Path(directory)
        shutil.copytree(root / "rust/rpp-gatelist", work / "rpp-gatelist",
                        ignore=shutil.ignore_patterns("target"))
        shutil.copytree(root / "rust/rpp-core/src", work / "rpp-core/src")
        shutil.copy2(root / "rust/rpp-core/Cargo.toml", work / "rpp-core/Cargo.toml")
        (work / "Cargo.toml").write_text(
            '[workspace]\nmembers=["rpp-core"]\n[workspace.package]\n'
            'version="0.1.0"\nedition="2021"\nrust-version="1.85.1"\n'
            'license="Apache-2.0"\n', encoding="utf-8")
        manifest = work / "rpp-gatelist/Cargo.toml"
        source = work / "rpp-gatelist/src/lib.rs"
        original = source.read_text(encoding="utf-8")

        def run(name):
            return subprocess.run(
                ["cargo", "test", "--manifest-path", str(manifest), "--offline",
                 "--locked", "--test", "admission", name, "--", "--exact",
                 "--color", "never"], env=environment, capture_output=True,
                text=True, encoding="utf-8", timeout=180)

        for name, before, after, test in MUTANTS:
            if original.count(before) != 1:
                raise RuntimeError(f"{name}: mutation anchor is not unique")
            positive = Test("admission", test)
            clean = Test("admission", VALID if test == WEAK else WEAK)
            source.write_text(original, encoding="utf-8", newline="\n")
            for case in (positive, clean):
                result = run(case.name)
                if not passed_test(result, case):
                    raise RuntimeError(f"{name}: clean test failed\n{result.stdout}{result.stderr}")
            source.write_text(original.replace(before, after), encoding="utf-8", newline="\n")
            failure, control = run(positive.name), run(clean.name)
            if not assertion_failure(failure, positive) or not passed_test(control, clean):
                raise RuntimeError(f"{name}: invalid kill/control\n"
                                   f"{failure.stdout}{failure.stderr}{control.stdout}{control.stderr}")
            rows.append({"mutation": name, "test": test, "killed": True,
                         "clean_control": clean.name})
            print(f"KILLED {name}", flush=True)
    report = {"source_sha256": sha256(original.encode()).hexdigest(),
              "killed": len(rows), "survived": 0, "classifier_controls": controls,
              "mutations": rows}
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    print(f"killed={len(rows)} survived=0 classifier_controls={controls}")


if __name__ == "__main__":
    main()
