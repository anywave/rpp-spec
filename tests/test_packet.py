"""Tests for RPP packet module."""

import pytest
from rpp.packet import (
    PayloadType,
    create_packet,
    parse_packet,
    parse_framed_packet,
    is_valid_packet,
    create_hash_packet,
    create_pointer_packet,
    create_framed_packet,
    extract_framed_content,
)
from rpp.address import encode


class TestCreatePacket:
    """Tests for packet creation."""

    def test_empty_packet(self):
        """Create packet with no payload."""
        addr = encode(0, 100, 200, 128)
        pkt = create_packet(addr)

        assert pkt.address.raw == addr
        assert pkt.payload == b""
        assert pkt.payload_type == PayloadType.EMPTY
        assert len(pkt) == 4

    def test_inline_packet(self):
        """Create packet with inline data."""
        addr = encode(1, 50, 100, 64)
        payload = b"hello world"
        pkt = create_packet(addr, payload)

        assert pkt.address.raw == addr
        assert pkt.payload == payload
        assert pkt.payload_type == PayloadType.INLINE
        assert len(pkt) == 4 + len(payload)

    def test_pointer_packet(self):
        """Create packet with 8-byte pointer."""
        addr = encode(2, 200, 300, 32)
        pointer = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        pkt = create_packet(addr, pointer)

        assert pkt.payload_type == PayloadType.POINTER
        assert len(pkt) == 12

    def test_hash_packet(self):
        """Create packet with 32-byte hash."""
        addr = encode(0, 0, 0, 0)
        hash_val = b"a" * 32
        pkt = create_packet(addr, hash_val)

        assert pkt.payload_type == PayloadType.HASH
        assert len(pkt) == 36

    def test_invalid_address(self):
        """Reject invalid address."""
        with pytest.raises(ValueError):
            create_packet(0x10000000)  # 28-bit overflow


class TestParsePacket:
    """Tests for packet parsing."""

    def test_parse_empty(self):
        """Parse empty packet."""
        data = bytes([0x05, 0xA4, 0x08, 0x80])
        pkt = parse_packet(data)

        assert pkt.address.raw == 0x05A40880
        assert pkt.payload == b""

    def test_parse_with_payload(self):
        """Parse packet with payload."""
        data = bytes([0x00, 0x18, 0x28, 0x01]) + b"test"
        pkt = parse_packet(data)

        assert pkt.payload == b"test"

    def test_parse_too_short(self):
        """Reject packet shorter than 4 bytes."""
        with pytest.raises(ValueError):
            parse_packet(b"\x00\x01\x02")

    def test_parse_reserved_bits(self):
        """Reject packet with non-zero reserved bits."""
        # First nibble should be 0, but we set bit 28
        data = bytes([0x10, 0x00, 0x00, 0x00])
        with pytest.raises(ValueError):
            parse_packet(data)


class TestRoundtrip:
    """Tests for encode/decode roundtrip."""

    def test_empty_roundtrip(self):
        """Roundtrip empty packet."""
        addr = encode(3, 511, 511, 255)
        pkt = create_packet(addr)
        data = pkt.to_bytes()
        parsed = parse_packet(data)

        assert parsed.address.raw == addr
        assert parsed.payload == b""

    def test_payload_roundtrip(self):
        """Roundtrip packet with payload."""
        addr = encode(1, 100, 200, 50)
        payload = b'{"key": "value"}'
        pkt = create_packet(addr, payload)
        data = pkt.to_bytes()
        parsed = parse_packet(data)

        assert parsed.address.raw == addr
        assert parsed.payload == payload

    def test_framed_roundtrip(self):
        """Roundtrip framed packet."""
        addr = encode(0, 50, 100, 200)
        pkt = create_packet(addr, b"data", PayloadType.INLINE)
        data = pkt.to_framed_bytes()
        parsed = parse_framed_packet(data)

        assert parsed.address.raw == addr
        assert parsed.payload == b"data"
        assert parsed.payload_type == PayloadType.INLINE


class TestIsValidPacket:
    """Tests for packet validation."""

    def test_valid_min(self):
        """Valid minimum packet."""
        assert is_valid_packet(bytes([0x00, 0x00, 0x00, 0x00]))

    def test_valid_max(self):
        """Valid maximum address."""
        assert is_valid_packet(bytes([0x0F, 0xFF, 0xFF, 0xFF]))

    def test_invalid_too_short(self):
        """Invalid: too short."""
        assert not is_valid_packet(b"\x00\x00\x00")

    def test_invalid_reserved_bits(self):
        """Invalid: reserved bits set."""
        assert not is_valid_packet(bytes([0x10, 0x00, 0x00, 0x00]))


class TestSpecialPackets:
    """Tests for specialized packet creators."""

    def test_hash_packet(self):
        """Create hash packet from content."""
        addr = encode(2, 160, 96, 128)
        content = b"Large document content..."
        pkt = create_hash_packet(addr, content)

        assert pkt.payload_type == PayloadType.HASH
        assert len(pkt.payload) == 32

        # Verify hash is correct
        import hashlib
        expected = hashlib.sha256(content).digest()
        assert pkt.payload == expected

    def test_pointer_packet(self):
        """Create pointer packet."""
        addr = encode(1, 100, 200, 64)
        pointer = 0xDEADBEEFCAFEBABE
        pkt = create_pointer_packet(addr, pointer)

        assert pkt.payload_type == PayloadType.POINTER
        assert len(pkt.payload) == 8
        assert int.from_bytes(pkt.payload, 'big') == pointer

    def test_framed_packet(self):
        """Create and extract framed content."""
        addr = encode(0, 50, 100, 200)
        content = b"Variable length content here"
        pkt = create_framed_packet(addr, content)

        assert pkt.payload_type == PayloadType.FRAMED
        assert len(pkt.payload) == 4 + len(content)

        extracted = extract_framed_content(pkt)
        assert extracted == content


class TestPacketMethods:
    """Tests for RPPPacket methods."""

    def test_content_hash(self):
        """Get SHA-256 hash of packet."""
        addr = encode(0, 0, 0, 0)
        pkt = create_packet(addr, b"test")

        assert len(pkt.content_hash) == 32

    def test_to_dict(self):
        """Convert packet to dict."""
        addr = encode(1, 100, 200, 50)
        pkt = create_packet(addr, b"data")
        d = pkt.to_dict()

        assert "address" in d
        assert d["payload_size"] == 4
        assert d["payload_type"] == "INLINE"
        assert d["total_size"] == 8

    def test_is_empty(self):
        """Check if packet has payload."""
        empty = create_packet(encode(0, 0, 0, 0))
        with_data = create_packet(encode(0, 0, 0, 0), b"x")

        assert empty.is_empty
        assert not with_data.is_empty
