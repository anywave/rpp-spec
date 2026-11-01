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

COMPLETION_CASES = {
    "completion_binding": "test_all_raw_score_thresholds_and_stages",
    "completion_matrix": "test_all_sector_access_states_and_void_exception",
    "completion_projection": "test_sector_projection_table_has_every_theta_once",
    "completion_grid_guard": "test_rtl_grid_rejects_missing_rows",
}

FOREIGN_CASES = {
    "foreign_rust_alpha_reverse": "test_rust_transcription_grid_bounded_and_monotone_for_all_six_rac_levels",
    "foreign_rust_floor_strict": "test_rust_transcription_floor_and_threshold_branches_use_greater_or_equal",
    "foreign_clash_shift": "test_clash_transcription_all_65536_avatar_products_are_bounded_and_axis_monotone",
    "foreign_clash_wrap": "test_clash_transcription_fixed_three_aligned_group_is_bounded_and_axis_monotone",
    "foreign_clash_strict179": "test_clash_transcription_stability_is_strictly_above_179_without_inversion",
    "foreign_clash_inversion_denominator": "test_clash_transcription_inverted_active_members_affect_denominator_and_cluster_bonus",
    "foreign_clash_unconditional_bonus": "test_clash_transcription_empty_and_separate_clusters_have_no_alignment_bonus",
    "foreign_source_hash_guard": "test_source_hash_verification_refuses_changed_reviewed_file",
    "foreign_native_artifact_row": "test_committed_native_rust_evidence_matches_all_6042_reference_rows",
}

EVIDENCE_CASES = {
    "evidence_crlf_missing": "test_all_completion_and_foreign_snapshot_hashes_accept_crlf_only",
    "evidence_attributes_missing": "test_autocrlf_checkout_preserves_all_evidence_paths_and_overlay_rules",
}


def main():
    root = Path(__file__).resolve().parents[2]
    killed = 0
    cases = [(mutation, "test_properties.py", target) for mutation, target in CASES.items()]
    cases += [(mutation, "test_completion.py", target) for mutation, target in COMPLETION_CASES.items()]
    cases += [(mutation, "test_foreign_reference.py", target) for mutation, target in FOREIGN_CASES.items()]
    cases += [(mutation, "test_evidence_bytes.py", target) for mutation, target in EVIDENCE_CASES.items()]
    for mutation, filename, target in cases:
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=",
                                 f"tools/prove_out/tests/{filename}::{target}"], cwd=root,
                                env=dict(os.environ, PROVE_OUT_MUTATION=mutation, PYTHONIOENCODING="utf-8"),
                                capture_output=True, encoding="utf-8")
        detected = result.returncode == 1 and "1 failed" in result.stdout and "AssertionError" in result.stdout
        killed += int(detected)
        print(f"{mutation}: {'KILLED' if detected else 'NOT KILLED'}")
        if not detected:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
    print(f"SUMMARY killed={killed} survived={len(cases) - killed}")
    return int(killed != len(cases))


if __name__ == "__main__":
    sys.exit(main())
