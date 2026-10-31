"""Selected claim/proposal detector mutations, in test memory only."""

import os
from pathlib import Path
import subprocess
import sys


CASES = {
    "score_max": "test_weighted_score_formula_and_monotonicity",
    "binding_threshold": "test_binding_and_stage_all_raw_scores",
    "legacy_boundary": "test_v1_partition_is_total_disjoint_and_matches_consent_for_all_theta",
    "proposal_theta": "test_proposed_affinity_reaches_both_endpoints",
    "proposal_progress": "test_proposed_progress_has_explicit_counts_and_exact_endpoints",
    "complement": "test_complement_consistency_declines_with_one_input_drift",
    "spin_decay": "test_isolated_spin_site_implements_its_exponential_simulation",
}


def main():
    root = Path(__file__).resolve().parents[2]
    killed = 0
    for mutation, target in CASES.items():
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=",
                                 f"tools/prove_out/tests/test_properties.py::{target}"], cwd=root,
                                env=dict(os.environ, PROVE_OUT_MUTATION=mutation, PYTHONIOENCODING="utf-8"),
                                capture_output=True, encoding="utf-8")
        detected = result.returncode == 1 and "1 failed" in result.stdout and "AssertionError" in result.stdout
        killed += int(detected)
        print(f"{mutation}: {'KILLED' if detected else 'NOT KILLED'}")
        if not detected:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
    print(f"SUMMARY killed={killed} survived={len(CASES) - killed}")
    return int(killed != len(CASES))


if __name__ == "__main__":
    sys.exit(main())
