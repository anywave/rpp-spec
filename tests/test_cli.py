"""
RPP CLI Test Suite

Subprocess-based tests that verify CLI behavior.
These tests ensure PuTTY/emulator compatibility by:
- Invoking CLI via subprocess
- Capturing stdout/stderr
- Asserting exact text output (no ANSI, no color)

All tests must pass on Windows, Linux, and macOS.
"""

import subprocess
import sys
import json
import pytest


def run_rpp(*args, input_data=None):
    """
    Run the rpp CLI command and return (returncode, stdout, stderr).

    Uses subprocess for cross-platform compatibility.
    """
    cmd = [sys.executable, "-m", "rpp.cli"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=input_data,
    )
    return result.returncode, result.stdout, result.stderr


class TestCLIEncode:
    """Test the encode command."""

    def test_encode_basic(self):
        """Test basic encoding."""
        code, stdout, stderr = run_rpp(
            "encode",
            "--shell", "0",
            "--theta", "12",
            "--phi", "40",
            "--harmonic", "1",
        )

        assert code == 0
        # New visual output format includes hex address and component values
        assert "0x" in stdout  # Address is shown
        assert "shell:" in stdout.lower()
        assert stderr == ""

    def test_encode_no_ansi(self):
        """Verify output contains no ANSI escape codes."""
        code, stdout, stderr = run_rpp(
            "encode", "--shell", "0", "--theta", "100", "--phi", "200", "--harmonic", "50"
        )

        # ANSI codes start with ESC (0x1B) or \x1b
        assert "\x1b" not in stdout
        assert "\x1b" not in stderr
        # Also check for common ANSI patterns
        assert "[0m" not in stdout
        assert "[1m" not in stdout

    def test_encode_json_output(self):
        """Test JSON output format."""
        code, stdout, stderr = run_rpp(
            "encode",
            "--shell", "1",
            "--theta", "100",
            "--phi", "200",
            "--harmonic", "50",
            "--json",
        )

        assert code == 0
        data = json.loads(stdout.strip())
        assert data["shell"] == 1
        assert data["theta"] == 100
        assert data["phi"] == 200
        assert data["harmonic"] == 50
        assert "address" in data

    def test_encode_invalid_shell(self):
        """Test encoding with invalid shell."""
        code, stdout, stderr = run_rpp(
            "encode", "--shell", "5", "--theta", "0", "--phi", "0", "--harmonic", "0"
        )

        assert code == 1
        assert "error" in stderr.lower()

    def test_encode_invalid_theta(self):
        """Test encoding with invalid theta."""
        code, stdout, stderr = run_rpp(
            "encode", "--shell", "0", "--theta", "600", "--phi", "0", "--harmonic", "0"
        )

        assert code == 1
        assert "error" in stderr.lower()

    def test_encode_missing_args(self):
        """Test encoding with missing arguments."""
        code, stdout, stderr = run_rpp("encode", "--shell", "0")

        assert code != 0  # Should fail


class TestCLIDecode:
    """Test the decode command."""

    def test_decode_hex(self):
        """Test decoding a hex address."""
        code, stdout, stderr = run_rpp("decode", "--address", "0x0018281")

        assert code == 0
        assert "shell:" in stdout.lower()
        assert "theta:" in stdout.lower()
        assert "phi:" in stdout.lower()
        assert "harmonic:" in stdout.lower()
        assert stderr == ""

    def test_decode_decimal(self):
        """Test decoding a decimal address."""
        code, stdout, stderr = run_rpp("decode", "--address", "99329")

        assert code == 0
        # New visual output format shows address in header
        assert "0x" in stdout

    def test_decode_no_ansi(self):
        """Verify decode output contains no ANSI codes."""
        code, stdout, stderr = run_rpp("decode", "--address", "0x1234567")

        assert "\x1b" not in stdout
        assert "\x1b" not in stderr

    def test_decode_json_output(self):
        """Test JSON decode output."""
        code, stdout, stderr = run_rpp("decode", "--address", "0x0018281", "--json")

        assert code == 0
        data = json.loads(stdout.strip())
        assert "shell" in data
        assert "theta" in data
        assert "phi" in data
        assert "harmonic" in data
        assert "address" in data

    def test_decode_invalid_address(self):
        """Test decoding invalid address."""
        code, stdout, stderr = run_rpp("decode", "--address", "not_an_address")

        assert code == 1
        assert "error" in stderr.lower()

    def test_decode_out_of_range(self):
        """Test decoding address out of 28-bit range."""
        code, stdout, stderr = run_rpp("decode", "--address", "0x10000000")

        assert code == 1
        assert "error" in stderr.lower()


class TestCLIResolve:
    """Test the resolve command."""

    def test_resolve_read(self):
        """Test resolving a read operation."""
        code, stdout, stderr = run_rpp("resolve", "--address", "0x0018281")

        assert code == 0
        # New visual output format shows allowed/route/reason
        assert "allowed:" in stdout.lower() or "[allowed]" in stdout.lower()
        assert "route:" in stdout.lower()
        assert "reason:" in stdout.lower()

    def test_resolve_no_ansi(self):
        """Verify resolve output contains no ANSI codes."""
        code, stdout, stderr = run_rpp("resolve", "--address", "0x1234567")

        assert "\x1b" not in stdout
        assert "\x1b" not in stderr

    def test_resolve_json_output(self):
        """Test JSON resolve output."""
        code, stdout, stderr = run_rpp("resolve", "--address", "0x0018281", "--json")

        assert code == 0
        data = json.loads(stdout.strip())
        assert "allowed" in data
        assert "route" in data
        assert "reason" in data

    def test_resolve_denied_returns_exit_2(self):
        """Test that denied resolution returns exit code 2."""
        # High phi write should be denied
        # First encode a high-phi address
        code1, stdout1, _ = run_rpp(
            "encode", "--shell", "0", "--theta", "100", "--phi", "450", "--harmonic", "64", "--json"
        )
        data = json.loads(stdout1.strip())
        addr = data["address"]

        # Now resolve with write
        code, stdout, stderr = run_rpp("resolve", "--address", addr, "--operation", "write")

        assert code == 2  # EXIT_DENIED
        # New visual output format uses "allowed: false" in compact mode
        assert "allowed: false" in stdout.lower() or "[denied]" in stdout.lower()


class TestCLIDemo:
    """Test the demo command."""

    def test_demo_runs(self):
        """Test that demo command runs successfully."""
        code, stdout, stderr = run_rpp("demo")

        assert code == 0
        # New visual output includes "demonstration complete" in summary
        assert "demonstration" in stdout.lower() or "rpp" in stdout.lower()

    def test_demo_shows_three_scenarios(self):
        """Test that demo shows all three scenarios."""
        code, stdout, stderr = run_rpp("demo")

        assert "scenario 1" in stdout.lower()
        assert "scenario 2" in stdout.lower()
        assert "scenario 3" in stdout.lower()

    def test_demo_no_ansi(self):
        """Verify demo output contains no ANSI codes."""
        code, stdout, stderr = run_rpp("demo")

        assert "\x1b" not in stdout
        assert "\x1b" not in stderr

    def test_demo_allowed_read(self):
        """Test demo shows allowed read scenario."""
        code, stdout, stderr = run_rpp("demo")

        # New visual format shows [ALLOWED] in routing diagram
        assert "[allowed]" in stdout.lower()

    def test_demo_denied_write(self):
        """Test demo shows denied write scenario."""
        code, stdout, stderr = run_rpp("demo")

        # New visual format shows [DENIED] in routing diagram
        assert "[denied]" in stdout.lower()

    def test_demo_archive_route(self):
        """Test demo shows archive routing."""
        code, stdout, stderr = run_rpp("demo")

        # Scenario 3 should route to archive
        assert "archive" in stdout.lower()


class TestCLIVersion:
    """Test version output."""

    def test_version_command(self):
        """Test version subcommand."""
        code, stdout, stderr = run_rpp("version")

        assert code == 0
        assert "rpp" in stdout.lower()

    def test_version_flag(self):
        """Test --version flag."""
        code, stdout, stderr = run_rpp("--version")

        assert code == 0
        assert "rpp" in stdout.lower()


class TestCLIHelp:
    """Test help output."""

    def test_help_no_args(self):
        """Test help with no arguments."""
        code, stdout, stderr = run_rpp()

        assert code == 0
        # Should show help or usage

    def test_help_flag(self):
        """Test --help flag."""
        code, stdout, stderr = run_rpp("--help")

        assert code == 0
        assert "encode" in stdout.lower() or "usage" in stdout.lower()


class TestCLILineOriented:
    """Test that CLI output is line-oriented (one value per line)."""

    def test_encode_output_lines(self):
        """Test that encode output has one field per line."""
        code, stdout, stderr = run_rpp(
            "encode", "--shell", "0", "--theta", "100", "--phi", "200", "--harmonic", "50"
        )

        lines = [line for line in stdout.strip().split("\n") if line]
        # New visual output has header, address line, and field lines
        assert len(lines) >= 4  # at least status, address, and some fields

    def test_resolve_output_lines(self):
        """Test that resolve output has one field per line."""
        code, stdout, stderr = run_rpp("resolve", "--address", "0x0018281")

        lines = [line for line in stdout.strip().split("\n") if line]
        # New visual output has status line plus allowed/route/reason
        assert len(lines) >= 3  # status + at least allowed, route, reason


class TestCLIRoundtrip:
    """Test encode-decode roundtrip via CLI."""

    @pytest.mark.parametrize("shell,theta,phi,harmonic", [
        (0, 0, 0, 0),
        (3, 511, 511, 255),
        (1, 100, 200, 128),
        (2, 300, 400, 64),
    ])
    def test_roundtrip(self, shell, theta, phi, harmonic):
        """Test that encode then decode returns original values."""
        # Encode
        code1, stdout1, _ = run_rpp(
            "encode",
            "--shell", str(shell),
            "--theta", str(theta),
            "--phi", str(phi),
            "--harmonic", str(harmonic),
            "--json",
        )
        assert code1 == 0
        encoded = json.loads(stdout1.strip())
        address = encoded["address"]

        # Decode
        code2, stdout2, _ = run_rpp("decode", "--address", address, "--json")
        assert code2 == 0
        decoded = json.loads(stdout2.strip())

        # Verify roundtrip
        assert decoded["shell"] == shell
        assert decoded["theta"] == theta
        assert decoded["phi"] == phi
        assert decoded["harmonic"] == harmonic


class TestCLICrossPlatform:
    """Tests for cross-platform compatibility."""

    def test_no_platform_specific_paths(self):
        """Verify output doesn't contain platform-specific paths."""
        code, stdout, stderr = run_rpp("resolve", "--address", "0x0018281")

        # Should not contain backslashes (Windows paths)
        assert "\\" not in stdout  # Only forward slashes in routes

    def test_utf8_output(self):
        """Verify output is valid UTF-8."""
        code, stdout, stderr = run_rpp("demo")

        # If we got here, the output was valid UTF-8
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
