"""Bounded contract/parser witnesses; native evidence is produced separately."""
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.prove_out import verdict

KEY = (13, 5, 4, 255)
TERMINAL = "AFF,13,5,4,255,0,0,1,0,0,0,1,0\n"


@pytest.fixture(autouse=True)
def selected_python_mutation(monkeypatch):
    mutation = os.environ.get("CX017_MUTATION")
    if mutation == "python-score-zero":
        monkeypatch.setattr(verdict, "compute_coherence_score", lambda *_: 0)
    elif mutation == "reserved-influence":
        original = verdict.coherence
        monkeypatch.setattr(verdict, "coherence", lambda a, b: original(a, b) + b.reserved / 8192)
    elif mutation == "unknown-affinity-row":
        original = verdict.affinity_rows
        monkeypatch.setattr(verdict, "affinity_rows", lambda text: original("\n".join(line for line in text.splitlines() if line.startswith("AFF,"))))


@pytest.fixture
def terminal(monkeypatch):
    monkeypatch.setattr(verdict, "AFF_DOMAIN", {KEY})
    return TERMINAL


def test_python_ra_formula_and_driver_use_actual_function():
    """Executed mutant python-score-zero replaces the actual imported score function with zero."""
    for e in range(101):
        for c in range(101):
            actual = verdict.compute_coherence_score(e / 100, c / 100)
            assert actual == int(165 * (e / 100)) + int(509 * (c / 100))
            assert 0 <= actual <= 674
            if e:
                assert actual >= verdict.compute_coherence_score((e - 1) / 100, c / 100)
            if c:
                assert actual >= verdict.compute_coherence_score(e / 100, (c - 1) / 100)


def test_reserved_bits_do_not_change_actual_coordinate_affinity():
    """Executed mutant reserved-influence adds reserved/8192 to actual coordinate affinity."""
    expected = verdict.python_affinity(KEY)
    assert all(verdict.python_affinity(KEY, reserved) == expected for reserved in range(8192))


def test_production_python_contract_reports_complete_domains_and_separate_sentinel_caveats():
    """Failing mutation: omit a fraction/reserved probe or hide out-of-ordinary-domain caveats."""
    result = verdict.python_checks()
    assert result["ra_fraction_points"] == 10201 and result["ra_formula_driver_failures"] == 0
    assert result["affinity_reserved_probes"] == 8192 and result["affinity_irrelevance_failures"] == 0
    assert result["reserved_theta31_similarity"] > 1 and result["null_self_similarity"] == 0.7


def test_terminal_affinity_row_preserves_each_binding_contract_and_exact_disagreement(terminal):
    """Failing mutation: conflate the two bindings or conceal their exact disagreement with Python."""
    result = verdict.analyze_affinity(verdict.affinity_rows(terminal))
    verdict.require_affinity(result)
    assert result["points"] == 1 and result["adjacent_driver_pairs"] == 0
    assert result["minimum_python"] == 1 - (0.30 * (13 / 13.5) + 0.40 + 0.20 + 0.10)
    assert result["minimum_rtl_byte"] == {"consolidated": 0, "canonical": 0}
    assert all(value["exact_scaled_disagreements"] == 1 for value in result["bindings"].values())


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "malformed", "unknown-value", "outside"))
def test_affinity_parser_refuses_incomplete_duplicate_malformed_or_out_of_domain_rows(terminal, mutation):
    """Failing mutations: remove complete-domain, duplicate, row-width or integer parsing guards."""
    changed = {"missing": "", "duplicate": terminal * 2, "malformed": terminal.rstrip() + ",0\n",
               "unknown-value": terminal.replace(",0,0,1,0", ",x,0,1,0", 1),
               "outside": terminal.replace("AFF,13,", "AFF,14,", 1)}[mutation]
    with pytest.raises(ValueError):
        verdict.affinity_rows(changed)


def test_affinity_parser_rejects_unknown_rows(terminal):
    """Executed mutant unknown-affinity-row filters unknown lines instead of rejecting them."""
    rejected = False
    try:
        verdict.affinity_rows(terminal + "UNKNOWN,0\n")
    except ValueError:
        rejected = True
    assert rejected, "unknown native affinity row was accepted"


@pytest.mark.parametrize("mutation", ("formula", "threshold", "score-dependence", "bounds"))
def test_affinity_contract_rejects_changed_native_binding_outputs(terminal, mutation):
    """Failing mutation: drop a native formula, threshold, threshold-irrelevance or range contract check."""
    row = list(verdict.affinity_rows(terminal)[0])
    row[{"formula": 4, "threshold": 6, "score-dependence": 5, "bounds": 4}[mutation]] = {"formula": 1, "threshold": 0, "score-dependence": 1, "bounds": 256}[mutation]
    with pytest.raises(AssertionError, match="contract"):
        verdict.require_affinity(verdict.analyze_affinity([tuple(row)]))


def test_orientation_parser_requires_complete_unique_typed_grid_and_declared_formula():
    """Failing mutations: accept missing/duplicate/unknown orientation rows or skip wrap/reverse formula checks."""
    rows = [(a, b, m, *(verdict.rtl_affinity((min(abs(a - b), 27 - abs(a - b)), 5, 4, 255), name) for name in ("consolidated", "canonical"))) for a in range(1, 28) for b in range(1, 28) for m in range(8)]
    text = "\n".join("ORI," + ",".join(map(str, row)) for row in rows) + "\n"
    assert len(verdict.orientation(text)) == 5832  # Synthetic parser control, not native evidence.
    first, rest = text.split("\n", 1)
    for changed in (rest, text + first + "\n", "UNKNOWN\n" + text, text.replace(first, first + ",0", 1), text.replace(first, first.rsplit(",", 1)[0] + ",x", 1), text.replace("ORI,1,1,0", "ORI,28,1,0", 1)):
        with pytest.raises(ValueError):
            verdict.orientation(changed)
    with pytest.raises(AssertionError, match="wrap/reverse"):
        verdict.orientation(text.replace(first, first.rsplit(",", 1)[0] + ",0", 1))


def test_native_helper_preserves_utf8_bench_and_logs_under_simulated_windows_acp(tmp_path, monkeypatch):
    """Failing mutation drop-explicit-UTF8 lets simulated cp1252 corrupt bench/log text or subprocess capture."""
    repo, work = tmp_path / "repo", tmp_path / "work"
    repo.mkdir()
    (repo / "bench.v").write_bytes("// café\n$finish;\n".encode("utf-8"))
    read, write = Path.read_text, Path.write_text
    def acp_read(path, *args, **kwargs):
        if not args and kwargs.get("encoding") is None:
            kwargs["encoding"] = "cp1252"
        return read(path, *args, **kwargs)
    def acp_write(path, text, *args, **kwargs):
        if not args and kwargs.get("encoding") is None:
            kwargs["encoding"] = "cp1252"
        return write(path, text, *args, **kwargs)
    calls = []
    def capture(command, **kwargs):
        assert kwargs.get("encoding") == "utf-8"
        calls.append(command)
        return SimpleNamespace(stdout="café\n", stderr="")
    monkeypatch.setattr(Path, "read_text", acp_read)
    monkeypatch.setattr(Path, "write_text", acp_write)
    monkeypatch.setattr(verdict.subprocess, "run", capture)
    args = SimpleNamespace(repo=repo, work_dir=work, iverilog="iverilog", vvp="vvp", ivl_dir=None)
    assert verdict.native(args, "acp", "bench.v", "Test", {"source.v": "// café\n"}) == "café\n"
    assert len(calls) == 2
    assert (work / "acp/bench.v").read_bytes() == "// café\n$finish(0);\n".encode("utf-8")
    assert (work / "acp/source.v").read_bytes() == "// café\n".encode("utf-8")
    for name in ("compile.log", "run.log"):
        assert (work / "acp" / name).read_bytes() == "café\n".encode("utf-8")
