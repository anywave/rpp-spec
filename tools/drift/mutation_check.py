"""Run each positive rule fixture with its detector deleted in memory."""

import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads(Path(__file__).with_name("catalog.json").read_text())
    killed = 0
    for rule in catalog["rules"]:
        rule_id = rule["rule_id"]
        target = f"tools/drift/tests/test_checker.py::test_rule_detects_drift[{rule_id}]"
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", target],
                                cwd=root, env=dict(os.environ, DRIFT_TEST_MUTANT=rule_id), capture_output=True)
        output = result.stdout.decode("utf-8", errors="replace")
        detected = result.returncode == 1 and "1 failed" in output and "AssertionError" in output
        killed += int(detected)
        print(f"{rule_id}: {'KILLED (expected assertion failure)' if detected else 'NOT KILLED'}")
        if not detected:
            sys.stdout.write(output)
            sys.stderr.buffer.write(result.stderr)
    print(f"SUMMARY killed={killed} survived={len(catalog['rules']) - killed}")
    return int(killed != len(catalog["rules"]))


if __name__ == "__main__":
    sys.exit(main())
