"""
RPP Mesh Test Suite
===================

Tests for the RPP Mesh consent-aware overlay network.
"""

import pytest
import struct
import asyncio
from unittest.mock import Mock, AsyncMock

from rpp_mesh import (
    RPPMeshHeader,
    RPPMeshPacket,
    RPPMeshTransport,
    ConsentState,
    MeshFlags,
    ConsentGate,
    DirectTransport,
    VPNTransport,
    derive_key,
    encrypt_payload,
    decrypt_payload,
    compress_payload,
    decompress_payload,
    compute_hmac,
    verify_hmac,
)
import rpp


# =============================================================================
# RPPMeshHeader Tests
# =============================================================================

class TestRPPMeshHeader:
    """Tests for mesh header serialization."""

    def test_header_size(self):
        """Header should always be 16 bytes."""
        header = RPPMeshHeader()
        packed = header.pack()
        assert len(packed) == 16

    def test_header_default_values(self):
        """Default header values should be sensible."""
        header = RPPMeshHeader()
        assert header.version == 1
        assert header.flags == 0
        assert header.consent_state == ConsentState.FULL_CONSENT
        assert header.soul_id == 0
        assert header.hop_count == 0
        assert header.ttl == 4

    def test_header_roundtrip(self):
        """Pack/unpack should preserve all fields."""
        header = RPPMeshHeader(
            version=1,
            flags=MeshFlags.ENCRYPTED | MeshFlags.PRIORITY,
            consent_state=ConsentState.DIMINISHED_CONSENT,
            soul_id=12345,
            hop_count=3,
            ttl=8,
            coherence_hash=0xABCD,
            reserved=0x1234,
        )

        packed = header.pack()
        unpacked = RPPMeshHeader.unpack(packed)

        assert unpacked.version == header.version
        assert unpacked.flags == header.flags
        assert unpacked.consent_state == header.consent_state
        assert unpacked.soul_id == header.soul_id
        assert unpacked.hop_count == header.hop_count
        assert unpacked.ttl == header.ttl
        assert unpacked.coherence_hash == header.coherence_hash
        assert unpacked.reserved == header.reserved

    def test_header_all_consent_states(self):
        """All consent states should roundtrip correctly."""
        for state in ConsentState:
            header = RPPMeshHeader(consent_state=state)
            packed = header.pack()
            unpacked = RPPMeshHeader.unpack(packed)
            assert unpacked.consent_state == state

    def test_header_all_flags(self):
        """All flag combinations should roundtrip correctly."""
        for flags in range(8):  # 3 bits = 8 combinations
            header = RPPMeshHeader(flags=flags)
            packed = header.pack()
            unpacked = RPPMeshHeader.unpack(packed)
            assert unpacked.flags == flags

    def test_header_max_values(self):
        """Maximum field values should work."""
        header = RPPMeshHeader(
            version=15,  # 4 bits max
            flags=15,    # 4 bits max
            consent_state=ConsentState.EMERGENCY_OVERRIDE,
            soul_id=65535,  # 16 bits max
            hop_count=255,  # 8 bits max
            ttl=255,        # 8 bits max
            coherence_hash=65535,
            reserved=65535,
        )

        packed = header.pack()
        unpacked = RPPMeshHeader.unpack(packed)

        assert unpacked.version == 15
        assert unpacked.flags == 15
        assert unpacked.soul_id == 65535
        assert unpacked.hop_count == 255
        assert unpacked.ttl == 255

    def test_header_too_short(self):
        """Unpack should raise on short data."""
        with pytest.raises(ValueError, match="too short"):
            RPPMeshHeader.unpack(b"\x00" * 10)

    def test_header_version_flags_byte(self):
        """Version and flags should pack into single byte correctly."""
        header = RPPMeshHeader(version=0xA, flags=0x5)
        packed = header.pack()
        # First byte: version (high nibble) | flags (low nibble)
        assert packed[0] == 0xA5


# =============================================================================
# RPPMeshPacket Tests
# =============================================================================

class TestRPPMeshPacket:
    """Tests for complete mesh packet serialization."""

    def test_packet_minimum_size(self):
        """Packet with empty payload should be 20 bytes (16 header + 4 address)."""
        packet = RPPMeshPacket(
            header=RPPMeshHeader(),
            rpp_address=0x0182801,
            payload=b""
        )
        packed = packet.pack()
        assert len(packed) == 20

    def test_packet_with_payload(self):
        """Packet size should include payload."""
        payload = b"Hello, Mesh!"
        packet = RPPMeshPacket(
            header=RPPMeshHeader(),
            rpp_address=0x0182801,
            payload=payload
        )
        packed = packet.pack()
        assert len(packed) == 20 + len(payload)

    def test_packet_roundtrip(self):
        """Pack/unpack should preserve all fields."""
        header = RPPMeshHeader(
            soul_id=9999,
            consent_state=ConsentState.FULL_CONSENT,
            hop_count=2
        )
        packet = RPPMeshPacket(
            header=header,
            rpp_address=0x0ABCDEF,
            payload=b"Test payload data"
        )

        packed = packet.pack()
        unpacked = RPPMeshPacket.unpack(packed)

        assert unpacked.rpp_address == packet.rpp_address
        assert unpacked.payload == packet.payload
        assert unpacked.header.soul_id == header.soul_id

    def test_packet_with_rpp_address(self):
        """Packet should preserve RPP address correctly."""
        addr = rpp.encode(shell=2, theta=200, phi=128, harmonic=32)
        packet = RPPMeshPacket(
            header=RPPMeshHeader(),
            rpp_address=addr,
            payload=b"data"
        )

        packed = packet.pack()
        unpacked = RPPMeshPacket.unpack(packed)

        assert unpacked.rpp_address == addr

        # Verify we can decode the RPP address
        # decode() returns tuple: (shell, theta, phi, harmonic)
        shell, theta, phi, harmonic = rpp.decode(unpacked.rpp_address)
        assert shell == 2
        assert theta == 200
        assert phi == 128
        assert harmonic == 32

    def test_packet_large_payload(self):
        """Large payloads should work."""
        payload = b"X" * 10000
        packet = RPPMeshPacket(
            header=RPPMeshHeader(),
            rpp_address=0x0182801,
            payload=payload
        )

        packed = packet.pack()
        unpacked = RPPMeshPacket.unpack(packed)

        assert unpacked.payload == payload

    def test_packet_binary_payload(self):
        """Binary payloads with all byte values should work."""
        payload = bytes(range(256))
        packet = RPPMeshPacket(
            header=RPPMeshHeader(),
            rpp_address=0x0182801,
            payload=payload
        )

        packed = packet.pack()
        unpacked = RPPMeshPacket.unpack(packed)

        assert unpacked.payload == payload


# =============================================================================
# ConsentState Tests
# =============================================================================

class TestConsentState:
    """Tests for consent state enumeration."""

    def test_consent_values(self):
        """Consent states should have expected values."""
        assert ConsentState.FULL_CONSENT == 0x00
        assert ConsentState.DIMINISHED_CONSENT == 0x01
        assert ConsentState.SUSPENDED_CONSENT == 0x02
        assert ConsentState.EMERGENCY_OVERRIDE == 0xFF

    def test_consent_from_int(self):
        """Should be able to create from int."""
        assert ConsentState(0) == ConsentState.FULL_CONSENT
        assert ConsentState(1) == ConsentState.DIMINISHED_CONSENT
        assert ConsentState(2) == ConsentState.SUSPENDED_CONSENT
        assert ConsentState(255) == ConsentState.EMERGENCY_OVERRIDE

    def test_consent_names(self):
        """Consent states should have readable names."""
        assert ConsentState.FULL_CONSENT.name == "FULL_CONSENT"
        assert ConsentState.DIMINISHED_CONSENT.name == "DIMINISHED_CONSENT"
        assert ConsentState.SUSPENDED_CONSENT.name == "SUSPENDED_CONSENT"
        assert ConsentState.EMERGENCY_OVERRIDE.name == "EMERGENCY_OVERRIDE"


# =============================================================================
# MeshFlags Tests
# =============================================================================

class TestMeshFlags:
    """Tests for mesh packet flags."""

    def test_flag_values(self):
        """Flags should be powers of 2."""
        assert MeshFlags.ENCRYPTED == 0x01
        assert MeshFlags.COMPRESSED == 0x02
        assert MeshFlags.PRIORITY == 0x04

    def test_flag_combinations(self):
        """Flags should combine with OR."""
        combined = MeshFlags.ENCRYPTED | MeshFlags.PRIORITY
        assert combined == 0x05
        assert combined & MeshFlags.ENCRYPTED
        assert combined & MeshFlags.PRIORITY
        assert not (combined & MeshFlags.COMPRESSED)


# =============================================================================
# ConsentGate Tests
# =============================================================================

class TestConsentGate:
    """Tests for consent gate node logic."""

    @pytest.fixture
    def gate(self):
        """Create a consent gate for testing."""
        return ConsentGate(hnc_public_key=b"test-key")

    @pytest.fixture
    def mock_forward(self):
        """Create mock forward function."""
        async def forward(packet):
            return b"response"
        return AsyncMock(side_effect=forward)

    @pytest.mark.asyncio
    async def test_full_consent_passes(self, gate, mock_forward):
        """FULL_CONSENT packets should pass through."""
        packet = RPPMeshPacket(
            header=RPPMeshHeader(consent_state=ConsentState.FULL_CONSENT),
            rpp_address=0x0182801,
            payload=b"data"
        )

        result = await gate.process_packet(packet, mock_forward)

        assert result == b"response"
        mock_forward.assert_called_once()

    @pytest.mark.asyncio
    async def test_suspended_consent_drops(self, gate, mock_forward):
        """SUSPENDED_CONSENT packets should be dropped."""
        packet = RPPMeshPacket(
            header=RPPMeshHeader(consent_state=ConsentState.SUSPENDED_CONSENT),
            rpp_address=0x0182801,
            payload=b"data"
        )

        result = await gate.process_packet(packet, mock_forward)

        assert result is None
        mock_forward.assert_not_called()

    @pytest.mark.asyncio
    async def test_emergency_override_drops(self, gate, mock_forward):
        """EMERGENCY_OVERRIDE packets should be dropped and alerted."""
        packet = RPPMeshPacket(
            header=RPPMeshHeader(consent_state=ConsentState.EMERGENCY_OVERRIDE),
            rpp_address=0x0182801,
            payload=b"data"
        )

        result = await gate.process_packet(packet, mock_forward)

        assert result is None
        mock_forward.assert_not_called()

    @pytest.mark.asyncio
    async def test_diminished_consent_delays(self, gate, mock_forward):
        """DIMINISHED_CONSENT packets should be delayed."""
        packet = RPPMeshPacket(
            header=RPPMeshHeader(consent_state=ConsentState.DIMINISHED_CONSENT),
            rpp_address=0x0182801,
            payload=b"data"
        )

        # Mock _query_consent to return FULL_CONSENT after delay
        gate._query_consent = AsyncMock(return_value=ConsentState.FULL_CONSENT)

        start = asyncio.get_event_loop().time()
        result = await gate.process_packet(packet, mock_forward)
        elapsed = asyncio.get_event_loop().time() - start

        # Should have delayed ~2 seconds
        assert elapsed >= 1.5
        assert result == b"response"


# =============================================================================
# RPPMeshTransport Tests
# =============================================================================

class TestRPPMeshTransport:
    """Tests for mesh transport layer."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock()
        config.ingress_nodes = ["localhost:7700"]
        config.soul_key_path = "/nonexistent/key"
        config.consent_update_endpoint = "wss://test/consent"
        config.encrypt_payload = False
        config.compress_payload = False
        config.sector_ttl = 4
        config.log_routing_decisions = False
        config.fallback_mode = "fail"
        return config

    def test_transport_init(self, mock_config):
        """Transport should initialize with config."""
        transport = RPPMeshTransport(mock_config)

        assert transport.config == mock_config
        assert transport.ingress_nodes == ["localhost:7700"]
        assert transport._consent_state == ConsentState.FULL_CONSENT

    def test_soul_id_truncation(self, mock_config):
        """Soul ID should be truncated to 16 bits."""
        transport = RPPMeshTransport(mock_config)

        # Should be a 16-bit value
        assert 0 <= transport.soul_id_truncated <= 65535

    def test_coherence_hash(self, mock_config):
        """Coherence hash should be deterministic."""
        transport = RPPMeshTransport(mock_config)

        hash1 = transport._compute_coherence_hash(b"test")
        hash2 = transport._compute_coherence_hash(b"test")
        hash3 = transport._compute_coherence_hash(b"different")

        assert hash1 == hash2
        assert hash1 != hash3
        assert 0 <= hash1 <= 65535


# =============================================================================
# Integration Tests
# =============================================================================

class TestMeshIntegration:
    """Integration tests combining multiple components."""

    def test_full_packet_flow(self):
        """Test complete packet creation and parsing."""
        # Encode an RPP address
        addr = rpp.encode(shell=0, theta=44, phi=160, harmonic=7)

        # Create header with consent
        header = RPPMeshHeader(
            version=1,
            flags=MeshFlags.ENCRYPTED,
            consent_state=ConsentState.FULL_CONSENT,
            soul_id=42,
            hop_count=0,
            ttl=4,
            coherence_hash=0x1234,
        )

        # Create packet
        packet = RPPMeshPacket(
            header=header,
            rpp_address=addr,
            payload=b'{"action": "recall", "target": "memory"}'
        )

        # Serialize
        wire_data = packet.pack()

        # Deserialize
        received = RPPMeshPacket.unpack(wire_data)

        # Verify
        assert received.header.consent_state == ConsentState.FULL_CONSENT
        assert received.header.soul_id == 42
        assert received.rpp_address == addr
        assert b"recall" in received.payload

        # Decode RPP address (returns tuple: shell, theta, phi, harmonic)
        shell, theta, phi, harmonic = rpp.decode(received.rpp_address)
        assert theta == 44
        assert phi == 160

    def test_consent_state_in_header(self):
        """Consent state should be visible in wire format."""
        for state in ConsentState:
            header = RPPMeshHeader(consent_state=state)
            packed = header.pack()

            # Consent state is byte 1
            assert packed[1] == state.value


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_payload(self):
        """Empty payload should work."""
        packet = RPPMeshPacket(
            header=RPPMeshHeader(),
            rpp_address=0,
            payload=b""
        )
        packed = packet.pack()
        unpacked = RPPMeshPacket.unpack(packed)
        assert unpacked.payload == b""

    def test_zero_address(self):
        """Zero RPP address should work."""
        packet = RPPMeshPacket(
            header=RPPMeshHeader(),
            rpp_address=0,
            payload=b"test"
        )
        packed = packet.pack()
        unpacked = RPPMeshPacket.unpack(packed)
        assert unpacked.rpp_address == 0

    def test_max_address(self):
        """Maximum 28-bit address should work."""
        max_addr = 0x0FFFFFFF
        packet = RPPMeshPacket(
            header=RPPMeshHeader(),
            rpp_address=max_addr,
            payload=b"test"
        )
        packed = packet.pack()
        unpacked = RPPMeshPacket.unpack(packed)
        assert unpacked.rpp_address == max_addr


# =============================================================================
# Crypto Tests
# =============================================================================

class TestCrypto:
    """Tests for crypto utilities."""

    def test_key_derivation(self):
        """Key derivation should be deterministic."""
        key1 = derive_key(b"secret")
        key2 = derive_key(b"secret")
        key3 = derive_key(b"different")

        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 32

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypt/decrypt should preserve data."""
        key = derive_key(b"test-key")
        plaintext = b"Hello, encrypted world!"

        encrypted = encrypt_payload(plaintext, key)
        decrypted = decrypt_payload(encrypted, key)

        assert decrypted == plaintext
        assert encrypted != plaintext

    def test_encrypt_different_nonces(self):
        """Each encryption should use a different nonce."""
        key = derive_key(b"test-key")
        plaintext = b"same data"

        enc1 = encrypt_payload(plaintext, key)
        enc2 = encrypt_payload(plaintext, key)

        # Different nonces mean different ciphertext
        assert enc1 != enc2

        # But both decrypt to same plaintext
        assert decrypt_payload(enc1, key) == plaintext
        assert decrypt_payload(enc2, key) == plaintext

    def test_compress_decompress_roundtrip(self):
        """Compress/decompress should preserve data."""
        data = b"Hello world! " * 100  # Compressible data

        compressed = compress_payload(data)
        decompressed = decompress_payload(compressed)

        assert decompressed == data
        # Compressed should be smaller for repetitive data
        assert len(compressed) < len(data)

    def test_compress_small_data(self):
        """Small data shouldn't be compressed (overhead)."""
        data = b"tiny"

        compressed = compress_payload(data)
        decompressed = decompress_payload(compressed)

        assert decompressed == data
        # First 4 bytes should be 0 (not compressed indicator)
        assert struct.unpack(">I", compressed[:4])[0] == 0

    def test_hmac_verification(self):
        """HMAC should verify correctly."""
        key = b"hmac-key"
        data = b"message to authenticate"

        hmac_tag = compute_hmac(key, data)
        assert len(hmac_tag) == 16

        assert verify_hmac(key, data, hmac_tag) is True
        assert verify_hmac(key, b"different", hmac_tag) is False
        assert verify_hmac(b"wrong-key", data, hmac_tag) is False

    def test_encrypt_empty(self):
        """Empty data should encrypt/decrypt correctly."""
        key = derive_key(b"key")

        encrypted = encrypt_payload(b"", key)
        decrypted = decrypt_payload(encrypted, key)

        assert decrypted == b""

    def test_compress_binary_data(self):
        """Binary data should compress/decompress correctly."""
        data = bytes(range(256)) * 10

        compressed = compress_payload(data)
        decompressed = decompress_payload(compressed)

        assert decompressed == data


# =============================================================================
# Fallback Transport Tests
# =============================================================================

class TestDirectTransport:
    """Tests for direct transport fallback."""

    def test_init(self):
        """Should initialize with config."""
        config = Mock()
        config.direct_endpoints = ["localhost:8080"]

        transport = DirectTransport(config)

        assert transport.config == config
        assert transport.direct_endpoints == ["localhost:8080"]


class TestVPNTransport:
    """Tests for VPN transport fallback."""

    def test_init(self):
        """Should initialize with config."""
        config = Mock()
        config.vpn_gateway = "vpn.example.com:443"
        config.vpn_credentials = {"user": "test"}

        transport = VPNTransport(config)

        assert transport.config == config
        assert transport.vpn_gateway == "vpn.example.com:443"
