"""Foreign source-transcription properties, with a named failing mutation per test."""

import hashlib
import json
import math
from pathlib import Path

import pytest

from tools.prove_out.foreign_reference import (
    Avatar, SOURCE_HASHES, avatar_slots, clash_avatar_weight, clash_group, clash_rows,
    render_csv, rust_access, rust_floor, rust_rows, rust_threshold, verify_sources,
)


def test_rust_grid_bounded_and_monotone_for_all_six_rac_levels():
    """Failing mutation: change alpha numerator to floor minus coherence."""
    for level in range(1, 7):
        results = [rust_access(tick / 1000, level) for tick in range(1001)]
        alpha = [value for _, value in results]
        assert all(0 <= value <= 1 for value in alpha)
        assert alpha == sorted(alpha)
        assert results[0] == ("blocked", 0.0)
        assert results[-1] == ("full", 1.0)


def test_rust_floor_and_threshold_branches_use_greater_or_equal():
    """Failing mutation: replace either >= comparison with >."""
    for level in range(1, 7):
        assert rust_access(math.nextafter(rust_floor(), -math.inf), level) == ("blocked", 0.0)
        assert rust_access(rust_floor(), level) == ("partial", 0.0)
        assert rust_access(math.nextafter(rust_floor(), math.inf), level)[1] > 0
        assert rust_access(math.nextafter(rust_threshold(level), -math.inf), level)[0] == "partial"
        assert rust_access(rust_threshold(level), level) == ("full", 1.0)


def test_rust_transcription_characterizes_nonfinite_input_without_adopting_it():
    """Failing mutation: add an unshipped finite-input guard to this transcription."""
    assert rust_access(math.nan, 1) == ("blocked", 0.0)
    assert rust_access(math.inf, 1) == ("full", 1.0)
    assert rust_access(-math.inf, 1) == ("blocked", 0.0)


@pytest.mark.parametrize("level", [0, 7, True, 1.5])
def test_reference_harness_refuses_invalid_rac_indices(level):
    """Failing mutation: remove explicit ordinary-index validation."""
    with pytest.raises(ValueError):
        rust_threshold(level)


def test_clash_all_65536_avatar_products_are_bounded_and_axis_monotone():
    """Failing mutation: shift product by seven instead of eight bits."""
    for coherence in range(256):
        for depth in range(256):
            actual = clash_avatar_weight(coherence, depth)
            assert actual == (coherence * depth) // 256
            assert 0 <= actual <= 254
            if coherence:
                assert actual >= clash_avatar_weight(coherence - 1, depth)
            if depth:
                assert actual >= clash_avatar_weight(coherence, depth - 1)
    assert clash_avatar_weight(255, 255) == 254


def test_clash_fixed_three_aligned_group_is_bounded_and_axis_monotone():
    """Failing mutation: use wrapping addition instead of saturating addition."""
    for coherence in range(256):
        scores = []
        for depth in range(256):
            field = clash_group(avatar_slots(*(Avatar(coherence, depth),) * 3))
            expected = min(255, (coherence * depth) // 256 + 38)
            assert field["coherence"] == expected
            assert field["field_strength"] == min(255, expected + 77)
            scores.append(field["coherence"])
        assert scores == sorted(scores)


def test_clash_stability_is_strictly_above_179_without_inversion():
    """Failing mutation: change >179 to >=179 in stability classification."""
    assert clash_group(avatar_slots(Avatar(180, 255)))["status"] == "transitioning"
    assert clash_group(avatar_slots(Avatar(181, 255)))["status"] == "stable"
    assert clash_group(avatar_slots(Avatar(255, 255, inverted=True)))["status"] == "unstable"


def test_clash_inverted_active_members_affect_denominator_and_cluster_bonus():
    """Failing mutation: exclude inverted avatars from active count or clusters."""
    normal = clash_group(avatar_slots(Avatar(255, 255), Avatar(255, 255)))
    extra = clash_group(avatar_slots(Avatar(255, 255), Avatar(255, 255), Avatar(255, 255, inverted=True)))
    assert normal["coherence"] == 254
    assert extra["coherence"] == 207  # floor(508/3)+38, despite a third active slot.
    inverted = clash_group(avatar_slots(*(Avatar(255, 255, inverted=True),) * 3))
    assert inverted["coherence"] == 38 and inverted["field_strength"] == 115
    assert inverted["status"] == "collapsed"


def test_clash_empty_and_separate_clusters_have_no_alignment_bonus():
    """Failing mutation: add bonuses unconditionally or merge all L clusters."""
    assert clash_group(avatar_slots())["coherence"] == 0
    field = clash_group(avatar_slots(*(Avatar(255, 255, harmonic_l=i) for i in (0, 2, 3, 4))))
    assert field["dominant_size"] == 1
    assert field["coherence"] == 254 and field["field_strength"] == 254


def test_reference_outputs_have_exact_counts_and_repeatable_utf8_bytes():
    """Failing mutation: drop a probe row or add a time-dependent output value."""
    rust = rust_rows()
    clash = clash_rows()
    assert len(rust) == 6042 and len(clash) == 65536
    assert render_csv(rust).encode("utf-8") == render_csv(rust_rows()).encode("utf-8")
    assert render_csv(clash).encode("utf-8") == render_csv(clash_rows()).encode("utf-8")


def test_source_hash_verification_refuses_changed_reviewed_file(tmp_path, monkeypatch):
    """Failing mutation: skip comparison of actual source hash with reviewed hash."""
    name = "source.txt"
    (tmp_path / name).write_bytes(b"reviewed\n")
    monkeypatch.setattr("tools.prove_out.foreign_reference.SOURCE_HASHES", {name: hashlib.sha256(b"reviewed\n").hexdigest()})
    assert verify_sources(tmp_path)[name] == hashlib.sha256(b"reviewed\n").hexdigest()
    (tmp_path / name).write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="unreviewed source"):
        verify_sources(tmp_path)
    assert len(SOURCE_HASHES) == 5


def test_committed_native_rust_evidence_matches_all_6042_reference_rows():
    """Failing mutation: flip one native CSV result/alpha row or alter its digest."""
    directory = Path(__file__).resolve().parents[1] / "results/foreign"
    data = (directory / "rust-native.csv").read_bytes()
    summary = json.loads((directory / "rust-native-summary.json").read_text(encoding="utf-8"))
    assert data == render_csv(rust_rows()).encode("utf-8")
    assert summary["native_grid_rows"] == 6006 and summary["native_boundary_rows"] == 36
    assert summary["mismatches"] == 0
    assert summary["csv_sha256"] == hashlib.sha256(data).hexdigest()
