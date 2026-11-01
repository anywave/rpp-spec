"""A failed flow can leave useful numbers; those numbers cannot prove completion."""

from pathlib import Path
import os
import sys

import pytest

from tools import ci_synth_summary as summary
from tools.ci_summary.workflow_fixture import run_flow_a


LOG = """Info: TRELLIS_COMB: 124/1000
Info: TRELLIS_FF: 99/1000
Info: DP16KD: 1/100
Info: Max frequency for clock 'clk': 90.2 MHz
"""


def render(tmp_path, monkeypatch, capsys, status=None, log=None, flow="B"):
    if status is not None:
        (tmp_path / f"flow_{flow}.status").write_text(status, encoding="utf-8")
    if log is not None:
        (tmp_path / f"pnr_{flow}.log").write_text(log, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["ci_synth_summary.py", str(tmp_path), "2026-09-24"])
    summary.main()
    return capsys.readouterr().out


@pytest.mark.parametrize("flow", ["A", "B"])
def test_failed_flow_with_partial_numbers_is_labeled_failed(tmp_path, monkeypatch, capsys, flow):
    """Mutation: treat any parseable flow log as completed or omit Flow A status."""
    output = render(tmp_path, monkeypatch, capsys, "failed", LOG, flow)
    assert f"Flow {flow} status: **failed**" in output
    assert "partial diagnostics" in output
    row = "| Max clock (MHz) | 90.2 | " + ("90.2 | n/a |" if flow == "A" else "n/a | 90.2 |")
    assert row in output
    assert "**completed**" not in output


@pytest.mark.parametrize("flow", ["A", "B"])
def test_success_requires_status_and_log(tmp_path, monkeypatch, capsys, flow):
    """Mutation: require missing data for completed status (inverts clean control)."""
    assert f"Flow {flow} status: **completed**" in render(tmp_path, monkeypatch, capsys, "ok", LOG, flow)


@pytest.mark.parametrize("flow", ["A", "B"])
def test_ok_marker_without_log_is_incomplete(tmp_path, monkeypatch, capsys, flow):
    """Mutation: trust an ok marker without its evidence log."""
    output = render(tmp_path, monkeypatch, capsys, "ok", flow=flow)
    assert f"Flow {flow} status: **incomplete or unknown**" in output
    assert "**completed**" not in output


@pytest.mark.parametrize("flow", ["A", "B"])
def test_log_without_marker_is_unknown(tmp_path, monkeypatch, capsys, flow):
    """Mutation: accept a parseable log without the workflow success marker."""
    assert f"Flow {flow} status: **incomplete or unknown**" in render(tmp_path, monkeypatch, capsys, log=LOG, flow=flow)


@pytest.mark.parametrize("flow", ["A", "B"])
def test_unknown_status_does_not_enter_markdown(tmp_path, monkeypatch, capsys, flow):
    """Mutation: interpolate arbitrary status text into the report."""
    output = render(tmp_path, monkeypatch, capsys, "bad | injected\n# heading", flow=flow)
    assert f"Flow {flow} status: **incomplete or unknown**" in output
    assert "injected" not in output


def test_log_decoder_is_utf8_with_replacement(tmp_path, monkeypatch):
    """Mutation: use the platform default decoder for synthesis logs."""
    log_path = tmp_path / "pnr_A.log"
    log_path.write_bytes(b"\xff" + LOG.encode("utf-8"))
    original = Path.read_text

    def audited_read(path, *args, **kwargs):
        assert kwargs.get("encoding") == "utf-8"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", audited_read)
    assert summary.parse(log_path)["Fmax"] == "90.2"


@pytest.mark.parametrize("flow", ["A", "B"])
@pytest.mark.parametrize("log", ["", "not a nextpnr resource or timing line\n"], ids=["empty", "unparseable"])
def test_ok_marker_without_any_parsed_value_is_incomplete(tmp_path, monkeypatch, capsys, flow, log):
    """Mutation: consider an existing empty/unparseable log sufficient for completion."""
    output = render(tmp_path, monkeypatch, capsys, "ok", log, flow)
    assert f"Flow {flow} status: **incomplete or unknown**" in output
    assert "**completed**" not in output


@pytest.mark.parametrize("flow", ["A", "B"])
def test_status_decoder_is_utf8_with_replacement(tmp_path, monkeypatch, capsys, flow):
    """Mutation: omit explicit UTF-8 or replacement decoding on a status-file read."""
    (tmp_path / f"flow_{flow}.status").write_bytes(b"\xfffailed")
    original = Path.read_text
    reads = []

    def audited_read(path, *args, **kwargs):
        if path.suffix == ".status":
            reads.append(path.name)
            assert kwargs.get("encoding") == "utf-8"
            assert kwargs.get("errors") == "replace"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", audited_read)
    output = render(tmp_path, monkeypatch, capsys)
    assert reads == [f"flow_{flow}.status"]
    assert f"Flow {flow} status: **incomplete or unknown**" in output


@pytest.mark.skipif(os.name == "nt", reason="GitHub Linux workflow fragment requires POSIX mock executables")
@pytest.mark.parametrize(
    "yosys_status,nextpnr_status,expected_status,expected_exit",
    [(1, 0, "failed", 1), (0, 1, "failed", 1), (0, 0, "ok", 0)],
    ids=["yosys-failure", "nextpnr-failure", "success"],
)
def test_flow_a_workflow_records_status_without_hiding_failure(
    tmp_path, yosys_status, nextpnr_status, expected_status, expected_exit,
):
    """Mutation: keep a stale ok, mark failure ok, omit success marker, or suppress exit 1."""
    result = run_flow_a(tmp_path, yosys_status, nextpnr_status)
    assert result.returncode == expected_exit, result.stderr
    assert (tmp_path / "flow_A.status").read_text(encoding="utf-8").strip() == expected_status
    assert (tmp_path / "flow_B.status").read_text(encoding="utf-8").strip() == "incomplete"
    assert "status-at-yosys:\nincomplete\nincomplete\n" in result.stdout
    assert (tmp_path / "pnr_A.log").exists() == (yosys_status == 0)
