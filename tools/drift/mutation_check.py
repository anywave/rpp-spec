"""Run each positive rule fixture with its detector deleted in memory."""

import json
import os
from pathlib import Path
import subprocess
import sys

from .branch_mutations import BRANCH_MUTANTS


def run_case(root, target, environment):
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", target],
                          cwd=root, env=environment, capture_output=True, encoding="utf-8")


def expected_assertion_failure(result):
    # A syntax error, collection/setup error or arbitrary tool exception is not
    # evidence that a fixture caught the intended algorithm mutation.
    return (result.returncode == 1 and "1 failed" in result.stdout and
            "AssertionError" in result.stdout and "1 error" not in result.stdout)


def expected_clean_control(result):
    return result.returncode == 0 and "1 passed" in result.stdout


def show_failure(result):
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)


def main():
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))
    killed = 0
    controls = 0
    baseline_environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    baseline_environment.pop("DRIFT_TEST_MUTANT", None)
    baseline_environment.pop("DRIFT_TEST_BRANCH_MUTANT", None)
    for rule in catalog["rules"]:
        rule_id = rule["rule_id"]
        target = f"tools/drift/tests/test_checker.py::test_rule_detects_drift[{rule_id}]"
        control_target = f"tools/drift/tests/test_checker.py::test_rule_clean_control[{rule_id}]"
        environment = dict(baseline_environment, DRIFT_TEST_MUTANT=rule_id)
        result = run_case(root, target, environment)
        control = run_case(root, control_target, environment)
        control_ok = expected_clean_control(control)
        controls += int(control_ok)
        detected = expected_assertion_failure(result) and control_ok
        killed += int(detected)
        print(f"{rule_id}: {'KILLED (positive assertion failed; clean control passed)' if detected else 'NOT KILLED'}")
        if not detected:
            show_failure(result)
            show_failure(control)
    for name, spec in BRANCH_MUTANTS.items():
        environment = dict(baseline_environment, DRIFT_TEST_BRANCH_MUTANT=name)
        result = run_case(root, spec["positive"], environment)
        control = run_case(root, spec["control"], environment)
        control_ok = expected_clean_control(control)
        controls += int(control_ok)
        detected = expected_assertion_failure(result) and control_ok
        killed += int(detected)
        print(f"branch:{name}: {'KILLED (positive assertion failed; clean control passed)' if detected else 'NOT KILLED'}")
        if not detected:
            show_failure(result)
            show_failure(control)
    total = len(catalog["rules"]) + len(BRANCH_MUTANTS)
    print(f"SUMMARY killed={killed} survived={total - killed} rule_mutants={len(catalog['rules'])} branch_mutants={len(BRANCH_MUTANTS)}")
    print(f"CONTROLS passed={controls} failed={total - controls}")
    return int(killed != total)


if __name__ == "__main__":
    sys.exit(main())
