"""Run twelve in-memory policy mutants and clean controls; source is never modified."""

import os
from pathlib import Path
import re
import subprocess
import sys

CASES = (
    ("unavailable", "test_available_channel_all_masks_and_live_measurements", "test_available_control_clean"),
    ("start", "test_control_start_forbidden_even_when_signed", "test_control_allowlist_and_independent_channel_clean"),
    ("expiry", "test_billboard_half_open_expiry_and_future_hold", "test_billboard_unexpired_clean"),
    ("after_token", "test_after_first_token_never_retries", "test_before_token_retry_preserves_every_meter_row"),
    ("meter", "test_before_token_retry_preserves_every_meter_row", "test_success_meter_clean"),
    ("unstable", "test_byte_identical_reruns_and_stable_tiebreak", "test_available_control_clean"),
    ("independence", "test_control_requires_known_path_and_disjoint_verified_tunnel", "test_control_valid_independent_fixture_clean"),
    ("known_path", "test_control_requires_known_path_and_disjoint_verified_tunnel", "test_control_valid_independent_fixture_clean"),
    ("issuer_replay", "test_billboard_receipts_are_per_issuer_and_cannot_burn_another_id", "test_billboard_unexpired_clean"),
    ("delivery_expiry", "test_billboard_delivery_rejects_expired_before_storage", "test_billboard_unexpired_clean"),
    ("tunnel_bypass", "test_control_requires_known_path_and_disjoint_verified_tunnel", "test_control_valid_independent_fixture_clean"),
    ("premature_clock", "test_invalid_far_future_calls_do_not_lock_out_later_valid_work", "test_success_meter_clean"),
)


def is_assertion_failure(result):
    """Count one actual pytest AssertionError, never runtime/collection failures."""
    return (result.returncode == 1 and "1 failed" in result.stdout
            and re.search(r"(?m)^E\s+AssertionError(?:[:\s]|$)", result.stdout) is not None)


def main():
    root = Path(__file__).resolve().parents[2]
    killed = survived = controls_passed = controls_failed = 0
    for mutation, positive, control in CASES:
        env = dict(os.environ, OVERLAY_MUTATION=mutation, PYTHONPATH=str(root))
        for test, expected_failure in ((positive, True), (control, False)):
            command = [sys.executable, "-m", "pytest", f"tools/overlay_sim/tests/test_properties.py::{test}",
                       "-q", "-o", "addopts="]
            result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, encoding="utf-8")
            # Only an assertion failure in one collected test is a killed mutant.
            correct = (is_assertion_failure(result) if expected_failure
                       else result.returncode == 0 and "1 passed" in result.stdout)
            if expected_failure:
                killed += correct
                survived += not correct
            else:
                controls_passed += correct
                controls_failed += not correct
            if not correct:
                print(f"unexpected mutation={mutation} test={test} exit={result.returncode}")
                print(result.stdout)
                print(result.stderr)
    print(f"killed={killed} survived={survived} controls_passed={controls_passed} controls_failed={controls_failed}")
    return int(bool(survived or controls_failed))


if __name__ == "__main__":
    raise SystemExit(main())
