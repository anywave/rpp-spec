"""
RPP Address Test Suite

Tests for the rpp.address module.
"""

import json
import pytest
from pathlib import Path

from rpp.address import (
    encode,
    decode,
    from_components,
    from_raw,
    parse_address,
    is_valid_address,
    MAX_ADDRESS,
)


# Load test vectors
TEST_VECTORS_PATH = Path(__file__).parent / "test_vectors.json"
with open(TEST_VECTORS_PATH) as f:
    TEST_DATA = json.load(f)


class TestEncoding:
    """Test encoding from components to address."""

    @pytest.mark.parametrize("test_case", TEST_DATA["test_vectors"]["encoding"])
    def test_encoding(self, test_case):
        """Test that encoding produces expected addresses."""
        inp = test_case["input"]
        expected = test_case["expected"]

        result = encode(inp["shell"], inp["theta"], inp["phi"], inp["harmonic"])

        assert result == expected["decimal"], (
            f"Encoding {inp} failed: expected {expected['decimal']}, got {result}"
        )

    def test_minimum_address(self):
        """Test minimum address (all zeros)."""
        assert encode(0, 0, 0, 0) == 0x0000000

    def test_maximum_address(self):
        """Test maximum address (all max values)."""
        assert encode(3, 511, 511, 255) == 0x0FFFFFFF

    def test_shell_isolation(self):
        """Test that shell field is properly isolated."""
        for shell in range(4):
            addr = encode(shell, 0, 0, 0)
            assert addr == (shell << 26)

    def test_theta_isolation(self):
        """Test that theta field is properly isolated."""
        for theta in [0, 128, 255, 511]:
            addr = encode(0, theta, 0, 0)
            assert addr == (theta << 17)

    def test_phi_isolation(self):
        """Test that phi field is properly isolated."""
        for phi in [0, 128, 255, 511]:
            addr = encode(0, 0, phi, 0)
            assert addr == (phi << 8)

    def test_harmonic_isolation(self):
        """Test that harmonic field is properly isolated."""
        for harmonic in [0, 64, 128, 255]:
            addr = encode(0, 0, 0, harmonic)
            assert addr == harmonic


class TestDecoding:
    """Test decoding from address to components."""

    @pytest.mark.parametrize("test_case", TEST_DATA["test_vectors"]["decoding"])
    def test_decoding(self, test_case):
        """Test that decoding produces expected components."""
        expected = test_case["expected"]
        address = test_case["input"]["decimal"]

        shell, theta, phi, harmonic = decode(address)

        assert shell == expected["shell"]
        assert theta == expected["theta"]
        assert phi == expected["phi"]
        assert harmonic == expected["harmonic"]

    def test_decode_zero(self):
        """Test decoding zero address."""
        assert decode(0) == (0, 0, 0, 0)

    def test_decode_max(self):
        """Test decoding maximum address."""
        assert decode(0x0FFFFFFF) == (3, 511, 511, 255)


class TestRoundtrip:
    """Test roundtrip encode/decode identity."""

    @pytest.mark.parametrize("test_case", TEST_DATA["test_vectors"]["roundtrip"])
    def test_roundtrip(self, test_case):
        """Test that encode followed by decode returns original values."""
        s, t, p, h = test_case["shell"], test_case["theta"], test_case["phi"], test_case["harmonic"]

        address = encode(s, t, p, h)
        decoded = decode(address)

        assert decoded == (s, t, p, h), (
            f"Roundtrip failed: ({s},{t},{p},{h}) -> {hex(address)} -> {decoded}"
        )

    def test_full_space_sample(self):
        """Test roundtrip for sampled addresses across entire space."""
        for shell in range(4):
            for theta in [0, 128, 256, 384, 511]:
                for phi in [0, 128, 256, 384, 511]:
                    for harmonic in [0, 64, 128, 192, 255]:
                        addr = encode(shell, theta, phi, harmonic)
                        result = decode(addr)
                        assert result == (shell, theta, phi, harmonic)


class TestInvalidInputs:
    """Test rejection of invalid inputs."""

    def test_shell_out_of_range(self):
        """Test that shell > 3 raises error."""
        with pytest.raises(ValueError, match="[Ss]hell"):
            encode(4, 0, 0, 0)

    def test_shell_negative(self):
        """Test that negative shell raises error."""
        with pytest.raises(ValueError, match="[Ss]hell"):
            encode(-1, 0, 0, 0)

    def test_theta_out_of_range(self):
        """Test that theta > 511 raises error."""
        with pytest.raises(ValueError, match="[Tt]heta"):
            encode(0, 512, 0, 0)

    def test_phi_out_of_range(self):
        """Test that phi > 511 raises error."""
        with pytest.raises(ValueError, match="[Pp]hi"):
            encode(0, 0, 512, 0)

    def test_harmonic_out_of_range(self):
        """Test that harmonic > 255 raises error."""
        with pytest.raises(ValueError, match="[Hh]armonic"):
            encode(0, 0, 0, 256)

    def test_address_exceeds_28_bits(self):
        """Test that address > 0x0FFFFFFF raises error on decode."""
        with pytest.raises(ValueError):
            decode(0x10000000)


class TestRPPAddressObject:
    """Test the RPPAddress dataclass."""

    def test_from_components(self):
        """Test creating RPPAddress from components."""
        addr = from_components(1, 96, 192, 128)
        assert addr.shell == 1
        assert addr.theta == 96
        assert addr.phi == 192
        assert addr.harmonic == 128

    def test_from_raw(self):
        """Test creating RPPAddress from raw address."""
        addr = from_raw(0x005A8040)
        assert addr.shell == 0
        assert addr.theta == 45
        assert addr.phi == 128
        assert addr.harmonic == 64

    def test_sector_names(self):
        """Test sector name interpretation."""
        sectors = [
            (32, "Gene"),
            (96, "Memory"),
            (160, "Witness"),
            (224, "Dream"),
            (288, "Bridge"),
            (352, "Guardian"),
            (416, "Emergence"),
            (480, "Meta"),
        ]
        for theta, expected_sector in sectors:
            addr = from_components(0, theta, 256, 128)
            assert addr.sector_name == expected_sector

    def test_grounding_levels(self):
        """Test grounding level interpretation."""
        levels = [
            (64, "Grounded"),
            (192, "Transitional"),
            (320, "Abstract"),
            (448, "Ethereal"),
        ]
        for phi, expected_level in levels:
            addr = from_components(0, 256, phi, 128)
            assert addr.grounding_level == expected_level

    def test_shell_names(self):
        """Test shell name interpretation."""
        names = [(0, "Hot"), (1, "Warm"), (2, "Cold"), (3, "Frozen")]
        for shell, expected_name in names:
            addr = from_components(shell, 256, 256, 128)
            assert addr.shell_name == expected_name

    def test_to_hex(self):
        """Test hex representation."""
        addr = from_components(0, 45, 128, 64)
        assert "0x" in addr.to_hex().lower()

    def test_to_dict(self):
        """Test dictionary representation."""
        addr = from_components(1, 100, 200, 50)
        d = addr.to_dict()
        assert d["shell"] == 1
        assert d["theta"] == 100
        assert d["phi"] == 200
        assert d["harmonic"] == 50
        assert "address" in d


class TestParseAddress:
    """Test address parsing."""

    def test_parse_hex(self):
        """Test parsing hex address."""
        assert parse_address("0x1234567") == 0x1234567

    def test_parse_hex_lowercase(self):
        """Test parsing lowercase hex."""
        assert parse_address("0xabcdef") == 0xabcdef

    def test_parse_hex_uppercase(self):
        """Test parsing uppercase hex."""
        assert parse_address("0xABCDEF") == 0xABCDEF

    def test_parse_decimal(self):
        """Test parsing decimal address."""
        assert parse_address("12345678") == 12345678

    def test_parse_with_whitespace(self):
        """Test parsing with leading/trailing whitespace."""
        assert parse_address("  0x1234  ") == 0x1234

    def test_parse_invalid(self):
        """Test parsing invalid string."""
        with pytest.raises(ValueError):
            parse_address("not_a_number")

    def test_parse_out_of_range(self):
        """Test parsing address out of 28-bit range."""
        with pytest.raises(ValueError):
            parse_address("0x10000000")


class TestIsValidAddress:
    """Test address validation."""

    def test_valid_zero(self):
        """Test zero is valid."""
        assert is_valid_address(0) is True

    def test_valid_max(self):
        """Test max address is valid."""
        assert is_valid_address(MAX_ADDRESS) is True

    def test_invalid_negative(self):
        """Test negative is invalid."""
        assert is_valid_address(-1) is False

    def test_invalid_too_large(self):
        """Test too large is invalid."""
        assert is_valid_address(MAX_ADDRESS + 1) is False

    def test_invalid_type(self):
        """Test non-integer is invalid."""
        assert is_valid_address("0x1234") is False
        assert is_valid_address(1.5) is False


class TestBitMasks:
    """Test that bit masks are correctly defined."""

    def test_shell_mask(self):
        """Test shell mask covers bits 27:26."""
        assert 0x0C000000 == (3 << 26)

    def test_theta_mask(self):
        """Test theta mask covers bits 25:17."""
        assert 0x03FE0000 == (511 << 17)

    def test_phi_mask(self):
        """Test phi mask covers bits 16:8."""
        assert 0x0001FF00 == (511 << 8)

    def test_harmonic_mask(self):
        """Test harmonic mask covers bits 7:0."""
        assert 0x000000FF == 255

    def test_masks_no_overlap(self):
        """Test that field masks don't overlap."""
        masks = [0x0C000000, 0x03FE0000, 0x0001FF00, 0x000000FF]
        for i, m1 in enumerate(masks):
            for m2 in masks[i + 1:]:
                assert (m1 & m2) == 0, f"Masks overlap: {hex(m1)} & {hex(m2)}"

    def test_masks_cover_28_bits(self):
        """Test that all masks together cover exactly 28 bits."""
        combined = 0x0C000000 | 0x03FE0000 | 0x0001FF00 | 0x000000FF
        assert combined == 0x0FFFFFFF


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
