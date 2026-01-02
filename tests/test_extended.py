"""Tests for RPP extended addressing module."""

import pytest
import math
from rpp.extended import (
    encode_extended,
    decode_extended,
    from_extended_components,
    from_extended_raw,
    from_core_address,
    degrees_to_theta,
    degrees_to_phi,
    degrees_to_phase,
    phase_interference,
    MAX_THETA_FINE,
    MAX_PHI_FINE,
    MAX_HARMONIC_EXT,
    MAX_PHASE,
)
from rpp.address import encode as encode_core


class TestEncodeExtended:
    """Tests for extended address encoding."""

    def test_all_zeros(self):
        """Encode with all components at zero."""
        addr = encode_extended(0, 0, 0, 0, 0)
        assert addr == 0

    def test_all_max(self):
        """Encode with all components at maximum."""
        addr = encode_extended(3, MAX_THETA_FINE, MAX_PHI_FINE, MAX_HARMONIC_EXT, MAX_PHASE)
        # Shell: 11 at bits 63:62
        # Theta: 20 ones at bits 61:42
        # Phi: 20 ones at bits 41:22
        # Harmonic: 10 ones at bits 21:12
        # Phase: 12 ones at bits 11:0
        assert addr == 0xFFFFFFFFFFFFFFFF

    def test_shell_only(self):
        """Encode with shell only."""
        addr = encode_extended(3, 0, 0, 0, 0)
        assert addr == (3 << 62)

    def test_theta_only(self):
        """Encode with theta only."""
        addr = encode_extended(0, MAX_THETA_FINE, 0, 0, 0)
        assert addr == (MAX_THETA_FINE << 42)

    def test_phi_only(self):
        """Encode with phi only."""
        addr = encode_extended(0, 0, MAX_PHI_FINE, 0, 0)
        assert addr == (MAX_PHI_FINE << 22)

    def test_harmonic_only(self):
        """Encode with harmonic only."""
        addr = encode_extended(0, 0, 0, MAX_HARMONIC_EXT, 0)
        assert addr == (MAX_HARMONIC_EXT << 12)

    def test_phase_only(self):
        """Encode with phase only."""
        addr = encode_extended(0, 0, 0, 0, MAX_PHASE)
        assert addr == MAX_PHASE


class TestDecodeExtended:
    """Tests for extended address decoding."""

    def test_decode_zeros(self):
        """Decode all zeros."""
        shell, theta, phi, harmonic, phase = decode_extended(0)
        assert (shell, theta, phi, harmonic, phase) == (0, 0, 0, 0, 0)

    def test_decode_max(self):
        """Decode all maximum values."""
        shell, theta, phi, harmonic, phase = decode_extended(0xFFFFFFFFFFFFFFFF)
        assert shell == 3
        assert theta == MAX_THETA_FINE
        assert phi == MAX_PHI_FINE
        assert harmonic == MAX_HARMONIC_EXT
        assert phase == MAX_PHASE


class TestRoundtrip:
    """Tests for encode/decode roundtrip."""

    def test_roundtrip_corners(self):
        """Roundtrip corner cases."""
        test_cases = [
            (0, 0, 0, 0, 0),
            (3, MAX_THETA_FINE, MAX_PHI_FINE, MAX_HARMONIC_EXT, MAX_PHASE),
            (1, 500000, 750000, 512, 2048),
            (2, 1, 1, 1, 1),
        ]

        for shell, theta, phi, harmonic, phase in test_cases:
            addr = encode_extended(shell, theta, phi, harmonic, phase)
            s, t, p, h, ph = decode_extended(addr)
            assert (s, t, p, h, ph) == (shell, theta, phi, harmonic, phase)

    def test_roundtrip_many(self):
        """Roundtrip many values."""
        for shell in range(4):
            for theta in [0, MAX_THETA_FINE // 2, MAX_THETA_FINE]:
                for phi in [0, MAX_PHI_FINE // 2, MAX_PHI_FINE]:
                    for harmonic in [0, MAX_HARMONIC_EXT]:
                        for phase in [0, MAX_PHASE]:
                            addr = encode_extended(shell, theta, phi, harmonic, phase)
                            s, t, p, h, ph = decode_extended(addr)
                            assert (s, t, p, h, ph) == (shell, theta, phi, harmonic, phase)


class TestExtendedAddress:
    """Tests for RPPExtendedAddress class."""

    def test_from_components(self):
        """Create from components."""
        addr = from_extended_components(1, 100000, 200000, 500, 1000)

        assert addr.shell == 1
        assert addr.theta == 100000
        assert addr.phi == 200000
        assert addr.harmonic == 500
        assert addr.phase == 1000

    def test_from_raw(self):
        """Create from raw value."""
        raw = encode_extended(2, 300000, 400000, 800, 2000)
        addr = from_extended_raw(raw)

        assert addr.shell == 2
        assert addr.theta == 300000
        assert addr.phi == 400000
        assert addr.harmonic == 800
        assert addr.phase == 2000

    def test_to_core(self):
        """Convert to core address."""
        # Create extended with values that map cleanly
        addr = from_extended_components(
            shell=1,
            theta=100 << 11,  # Maps to core theta=100
            phi=200 << 11,    # Maps to core phi=200
            harmonic=50 << 2,  # Maps to core harmonic=50
            phase=0,
        )

        core = addr.to_core()
        expected = encode_core(1, 100, 200, 50)
        assert core == expected

    def test_to_hex(self):
        """Format as hex string."""
        addr = from_extended_components(0, 0, 0, 0, 0)
        assert addr.to_hex() == "0x0000000000000000"

    def test_theta_degrees(self):
        """Convert theta to degrees."""
        addr = from_extended_components(0, 524288, 0, 0, 0)  # Half of max
        assert addr.theta_degrees == pytest.approx(180.0, abs=0.001)

    def test_phi_degrees(self):
        """Convert phi to degrees."""
        addr = from_extended_components(0, 0, 0, 0, 0)  # Min phi
        assert addr.phi_degrees == pytest.approx(-90.0, abs=0.001)

        addr = from_extended_components(0, 0, MAX_PHI_FINE, 0, 0)  # Max phi
        assert addr.phi_degrees == pytest.approx(90.0, abs=0.001)

    def test_phase_degrees(self):
        """Convert phase to degrees."""
        addr = from_extended_components(0, 0, 0, 0, 2048)  # Half of max
        assert addr.phase_degrees == pytest.approx(180.0, abs=0.1)


class TestCoreConversion:
    """Tests for core to extended conversion."""

    def test_upconvert(self):
        """Upconvert core to extended."""
        core = encode_core(2, 256, 128, 64)
        ext = from_core_address(core)

        assert ext.shell == 2
        # 9-bit theta shifted to 20-bit position
        assert ext.theta == 256 << 11
        assert ext.phi == 128 << 11
        assert ext.harmonic == 64 << 2
        assert ext.phase == 0

    def test_roundtrip_via_core(self):
        """Roundtrip: core -> extended -> core."""
        original = encode_core(1, 200, 300, 100)
        ext = from_core_address(original)
        back = ext.to_core()

        assert back == original


class TestDegreeConversions:
    """Tests for degree conversion functions."""

    def test_degrees_to_theta(self):
        """Convert degrees to theta."""
        assert degrees_to_theta(0) == 0
        assert degrees_to_theta(180) == 524288
        assert degrees_to_theta(360) == 0  # Wraps

    def test_degrees_to_phi(self):
        """Convert degrees to phi."""
        assert degrees_to_phi(-90) == 0
        assert degrees_to_phi(0) == 524288
        assert degrees_to_phi(90) == MAX_PHI_FINE

    def test_degrees_to_phase(self):
        """Convert degrees to phase."""
        assert degrees_to_phase(0) == 0
        assert degrees_to_phase(180) == 2048
        assert degrees_to_phase(360) == 0  # Wraps


class TestPhaseInterference:
    """Tests for phase interference calculation."""

    def test_constructive(self):
        """Same phase = constructive interference."""
        amp = phase_interference(0, 0)
        assert amp == pytest.approx(2.0, abs=0.001)

        amp = phase_interference(1000, 1000)
        assert amp == pytest.approx(2.0, abs=0.001)

    def test_destructive(self):
        """180 degrees apart = destructive interference."""
        amp = phase_interference(0, 2048)  # 0 vs 180 degrees
        assert amp == pytest.approx(0.0, abs=0.001)

    def test_quadrature(self):
        """90 degrees apart = quadrature."""
        amp = phase_interference(0, 1024)  # 0 vs 90 degrees
        assert amp == pytest.approx(math.sqrt(2), abs=0.01)


class TestValidation:
    """Tests for validation."""

    def test_invalid_shell(self):
        """Reject invalid shell."""
        with pytest.raises(ValueError):
            encode_extended(4, 0, 0, 0, 0)

    def test_invalid_theta(self):
        """Reject invalid theta."""
        with pytest.raises(ValueError):
            encode_extended(0, MAX_THETA_FINE + 1, 0, 0, 0)

    def test_invalid_phi(self):
        """Reject invalid phi."""
        with pytest.raises(ValueError):
            encode_extended(0, 0, MAX_PHI_FINE + 1, 0, 0)

    def test_invalid_harmonic(self):
        """Reject invalid harmonic."""
        with pytest.raises(ValueError):
            encode_extended(0, 0, 0, MAX_HARMONIC_EXT + 1, 0)

    def test_invalid_phase(self):
        """Reject invalid phase."""
        with pytest.raises(ValueError):
            encode_extended(0, 0, 0, 0, MAX_PHASE + 1)
