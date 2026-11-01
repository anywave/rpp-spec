"""Transcription characterization plus separately identified native Rust evidence.

The Python-transcription formulas do not independently validate the foreign
binding. Each docstring names a mutation; FOREIGN_BINDINGS distinguishes the
nine actually executed mutants from the remaining unexecuted examples.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import sys

import pytest

from tools.prove_out import foreign_reference
from tools.prove_out.evidence import evidence_bytes
from tools.prove_out.foreign_reference import (
    Avatar, SOURCE_HASHES, avatar_slots, clash_avatar_weight, clash_group, clash_rows,
    render_csv, rust_access, rust_floor, rust_rows, rust_threshold, verify_sources,
)


@pytest.fixture(autouse=True)
def in_memory_foreign_mutant(monkeypatch):
    """Apply only the named finite mutation; never edit source or evidence files."""
    mutation = os.environ.get("PROVE_OUT_MUTATION")
    module = sys.modules[__name__]

    def replace(name, implementation):
        monkeypatch.setattr(module, name, implementation)
        monkeypatch.setattr(foreign_reference, name, implementation)

    if mutation == "foreign_rust_alpha_reverse":
        original = foreign_reference.rust_access

        def reverse_alpha(coherence, level):
            kind, alpha = original(coherence, level)
            return kind, -alpha if kind == "partial" else alpha

        replace("rust_access", reverse_alpha)
    elif mutation == "foreign_rust_floor_strict":
        original = foreign_reference.rust_access

        def strict_floor(coherence, level):
            return ("blocked", 0.0) if coherence == rust_floor() else original(coherence, level)

        replace("rust_access", strict_floor)
    elif mutation == "foreign_clash_shift":
        replace("clash_avatar_weight", lambda coherence, depth: (coherence * depth) >> 7)
    elif mutation in {"foreign_clash_wrap", "foreign_clash_strict179",
                       "foreign_clash_inversion_denominator", "foreign_clash_unconditional_bonus"}:
        original = foreign_reference.clash_group

        def changed_group(avatars):
            result = dict(original(avatars))
            active = [avatar for avatar in avatars if avatar.active]
            aligned = result["dominant_size"] >= 3
            total = sum(clash_avatar_weight(a.coherence, a.depth) for a in active if not a.inverted)
            base = total // len(active) if active else 0
            if mutation == "foreign_clash_wrap":
                result["coherence"] = (base + (38 if aligned else 0)) % 256
                result["field_strength"] = (result["coherence"] + (77 if aligned else 0)) % 256
            elif mutation == "foreign_clash_strict179":
                if not result["inverted"] and result["coherence"] == 179:
                    result["status"] = "stable"
            elif mutation == "foreign_clash_inversion_denominator":
                contributors = sum(not avatar.inverted for avatar in active)
                base = total // contributors if contributors else 0
                result["coherence"] = min(255, base + (38 if aligned else 0))
            elif mutation == "foreign_clash_unconditional_bonus":
                result["coherence"] = min(255, base + 38)
            return result

        replace("clash_group", changed_group)
    elif mutation == "foreign_source_hash_guard":
        def unchecked_sources(source_root):
            return {name: hashlib.sha256(evidence_bytes(Path(source_root) / name)).hexdigest()
                    for name in foreign_reference.SOURCE_HASHES}

        replace("verify_sources", unchecked_sources)
    elif mutation == "foreign_native_artifact_row":
        original = Path.read_bytes

        def flipped_native_row(path):
            data = original(path)
            return data.replace(b"blocked", b"full", 1) if path.name == "rust-native.csv" else data

        monkeypatch.setattr(Path, "read_bytes", flipped_native_row)


def test_rust_transcription_grid_bounded_and_monotone_for_all_six_rac_levels():
    """Transcription evidence; executed mutant reverses the partial-alpha sign."""
    for level in range(1, 7):
        results = [rust_access(tick / 1000, level) for tick in range(1001)]
        alpha = [value for _, value in results]
        assert all(0 <= value <= 1 for value in alpha)
        assert alpha == sorted(alpha)
        assert results[0] == ("blocked", 0.0)
        assert results[-1] == ("full", 1.0)
        midpoint = (rust_floor() + rust_threshold(level)) / 2
        assert math.isclose(rust_access(midpoint, level)[1], 0.5, abs_tol=1e-15)


def test_rust_transcription_floor_and_threshold_branches_use_greater_or_equal():
    """Transcription evidence; executed floor >= to >, unexecuted threshold >= to >."""
    for level in range(1, 7):
        assert rust_access(math.nextafter(rust_floor(), -math.inf), level) == ("blocked", 0.0)
        assert rust_access(rust_floor(), level) == ("partial", 0.0)
        assert rust_access(math.nextafter(rust_floor(), math.inf), level)[1] > 0
        assert rust_access(math.nextafter(rust_threshold(level), -math.inf), level)[0] == "partial"
        assert rust_access(rust_threshold(level), level) == ("full", 1.0)


def test_rust_transcription_characterizes_nonfinite_input_without_adopting_it():
    """Transcription evidence; unexecuted mutation adds an unshipped finite guard."""
    assert rust_access(math.nan, 1) == ("blocked", 0.0)
    assert rust_access(math.inf, 1) == ("full", 1.0)
    assert rust_access(-math.inf, 1) == ("blocked", 0.0)


@pytest.mark.parametrize("level", [0, 7, True, 1.5])
def test_reference_harness_refuses_invalid_rac_indices(level):
    """Harness guard, not foreign evidence; unexecuted mutation removes index validation."""
    with pytest.raises(ValueError):
        rust_threshold(level)


def test_clash_transcription_all_65536_avatar_products_are_bounded_and_axis_monotone():
    """Transcription evidence; executed mutation shifts product by seven, not eight."""
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


def test_clash_transcription_fixed_three_aligned_group_is_bounded_and_axis_monotone():
    """Transcription evidence; executed mutation replaces saturation with wrapping."""
    for coherence in range(256):
        scores = []
        for depth in range(256):
            field = clash_group(avatar_slots(*(Avatar(coherence, depth),) * 3))
            expected = min(255, (coherence * depth) // 256 + 38)
            assert field["coherence"] == expected
            assert field["field_strength"] == min(255, expected + 77)
            scores.append(field["coherence"])
        assert scores == sorted(scores)


def test_clash_transcription_stability_is_strictly_above_179_without_inversion():
    """Transcription evidence; executed mutation changes >179 to >=179."""
    assert clash_group(avatar_slots(Avatar(180, 255)))["status"] == "transitioning"
    assert clash_group(avatar_slots(Avatar(181, 255)))["status"] == "stable"
    assert clash_group(avatar_slots(Avatar(255, 255, inverted=True)))["status"] == "unstable"


def test_clash_transcription_inverted_active_members_affect_denominator_and_cluster_bonus():
    """Transcription evidence; executed denominator exclusion, unexecuted cluster exclusion."""
    normal = clash_group(avatar_slots(Avatar(255, 255), Avatar(255, 255)))
    extra = clash_group(avatar_slots(Avatar(255, 255), Avatar(255, 255), Avatar(255, 255, inverted=True)))
    assert normal["coherence"] == 254
    assert extra["coherence"] == 207  # floor(508/3)+38, despite a third active slot.
    inverted = clash_group(avatar_slots(*(Avatar(255, 255, inverted=True),) * 3))
    assert inverted["coherence"] == 38 and inverted["field_strength"] == 115
    assert inverted["status"] == "collapsed"


def test_clash_transcription_empty_and_separate_clusters_have_no_alignment_bonus():
    """Transcription evidence; executed unconditional bonus, unexecuted merged clusters."""
    assert clash_group(avatar_slots())["coherence"] == 0
    field = clash_group(avatar_slots(*(Avatar(255, 255, harmonic_l=i) for i in (0, 2, 3, 4))))
    assert field["dominant_size"] == 1
    assert field["coherence"] == 254 and field["field_strength"] == 254


def test_reference_outputs_have_exact_counts_and_repeatable_utf8_bytes():
    """Transcription artifact integrity; unexecuted mutations drop row/add clock value."""
    rust = rust_rows()
    clash = clash_rows()
    assert len(rust) == 6042 and len(clash) == 65536
    assert render_csv(rust).encode("utf-8") == render_csv(rust_rows()).encode("utf-8")
    assert render_csv(clash).encode("utf-8") == render_csv(clash_rows()).encode("utf-8")


def test_source_hash_verification_refuses_changed_reviewed_file(tmp_path, monkeypatch):
    """Executed mutation skips source hash guard; CRLF conversion alone stays equal."""
    name = "source.txt"
    (tmp_path / name).write_bytes(b"reviewed\n")
    monkeypatch.setattr("tools.prove_out.foreign_reference.SOURCE_HASHES", {name: hashlib.sha256(b"reviewed\n").hexdigest()})
    assert verify_sources(tmp_path)[name] == hashlib.sha256(b"reviewed\n").hexdigest()
    (tmp_path / name).write_bytes(b"reviewed\r\n")
    assert verify_sources(tmp_path)[name] == hashlib.sha256(b"reviewed\n").hexdigest()
    (tmp_path / name).write_bytes(b"changed\n")
    rejected = False
    try:
        verify_sources(tmp_path)
    except ValueError:
        rejected = True
    assert rejected
    assert len(SOURCE_HASHES) == 5


def test_committed_native_rust_evidence_matches_all_6042_reference_rows():
    """Independent native artifact; executed row flip, unexecuted recorded-digest change."""
    directory = Path(__file__).resolve().parents[1] / "results/foreign"
    data = evidence_bytes(directory / "rust-native.csv")
    summary = json.loads(evidence_bytes(directory / "rust-native-summary.json").decode("utf-8"))
    assert data == render_csv(rust_rows()).encode("utf-8")
    assert summary["native_grid_rows"] == 6006 and summary["native_boundary_rows"] == 36
    assert summary["mismatches"] == 0
    assert summary["csv_sha256"] == hashlib.sha256(data).hexdigest()
