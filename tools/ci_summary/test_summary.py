"""A failed flow can leave useful numbers; those numbers cannot prove completion."""

from pathlib import Path
import sys

from tools import ci_synth_summary as summary


LOG = """Info: TRELLIS_COMB: 124/1000
Info: TRELLIS_FF: 99/1000
Info: DP16KD: 1/100
Info: Max frequency for clock 'clk': 90.2 MHz
"""


def render(tmp_path, monkeypatch, capsys, status=None, log=None):
    if status is not None:
        (tmp_path / "flow_B.status").write_text(status, encoding="utf-8")
    if log is not None:
        (tmp_path / "pnr_B.log").write_text(log, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["ci_synth_summary.py", str(tmp_path), "2026-09-24"])
    summary.main()
    return capsys.readouterr().out


def test_failed_flow_with_partial_numbers_is_labeled_failed(tmp_path, monkeypatch, capsys):
    """Mutation: treat any parseable Flow B log as completed."""
    output = render(tmp_path, monkeypatch, capsys, "failed", LOG)
    assert "**failed**" in output
    assert "partial diagnostics" in output
    assert "| Max clock (MHz) | 90.2 | n/a | 90.2 |" in output
    assert "**completed**" not in output


def test_success_requires_status_and_log(tmp_path, monkeypatch, capsys):
    """Mutation: require missing data for completed status (inverts clean control)."""
    assert "**completed**" in render(tmp_path, monkeypatch, capsys, "ok", LOG)


def test_ok_marker_without_log_is_incomplete(tmp_path, monkeypatch, capsys):
    """Mutation: trust an ok marker without its evidence log."""
    output = render(tmp_path, monkeypatch, capsys, "ok")
    assert "**incomplete or unknown**" in output
    assert "**completed**" not in output


def test_log_without_marker_is_unknown(tmp_path, monkeypatch, capsys):
    """Mutation: accept a parseable log without the workflow success marker."""
    assert "**incomplete or unknown**" in render(tmp_path, monkeypatch, capsys, log=LOG)


def test_unknown_status_does_not_enter_markdown(tmp_path, monkeypatch, capsys):
    """Mutation: interpolate arbitrary status text into the report."""
    output = render(tmp_path, monkeypatch, capsys, "bad | injected\n# heading")
    assert "**incomplete or unknown**" in output
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
