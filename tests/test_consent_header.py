"""
Tests for Consent Packet Header v2.0
=====================================

Tests for 5-state ACSP with ATTENTIVE state and φ-based thresholds.
"""

import pytest

from rpp.consent_header import (
    ConsentState,
    AncestralConsent,
    PayloadType,
    ConsentPacketHeader,
    SpiralPacket,
    derive_consent_state,
    compute_crc8,
    HEADER_SIZE,
)
from rpp.ra_constants import (
    PHI_THRESHOLD_4BIT,
    ATTENTIVE_THRESHOLD_4BIT,
    DIMINISHED_THRESHOLD_4BIT,
)
from rpp.address_canonical import RPPAddress, ThetaSector, create_from_sector


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_address():
    """Create a sample RPP address for testing."""
    return create_from_sector(ThetaSector.MEMORY, phi=3, omega=2, radius=0.75)


@pytest.fixture
def full_consent_header(sample_address):
    """Create a header with full consent."""
    return ConsentPacketHeader.create(
        rpp_address=sample_address,
        consent_somatic_4bit=15,
        verbal_signal_strength=3,
    )


# =============================================================================
# Test ConsentState Enum
# =============================================================================

class TestConsentState:
    """Tests for 5-state ACSP enum."""

    def test_has_five_states(self):
        """Should have exactly 5 consent states."""
        assert len(ConsentState) == 5

    def test_state_values(self):
        """States should have correct integer values."""
        assert ConsentState.FULL_CONSENT == 0
        assert ConsentState.ATTENTIVE == 1
        assert ConsentState.DIMINISHED_CONSENT == 2
        assert ConsentState.SUSPENDED_CONSENT == 3
        assert ConsentState.EMERGENCY_OVERRIDE == 4

    def test_state_ordering(self):
        """States should be ordered by consent level (high to low)."""
        assert ConsentState.FULL_CONSENT < ConsentState.ATTENTIVE
        assert ConsentState.ATTENTIVE < ConsentState.DIMINISHED_CONSENT
        assert ConsentState.DIMINISHED_CONSENT < ConsentState.SUSPENDED_CONSENT
        assert ConsentState.SUSPENDED_CONSENT < ConsentState.EMERGENCY_OVERRIDE


# =============================================================================
# Test Standalone derive_consent_state
# =============================================================================

class TestDeriveConsentState:
    """Tests for standalone consent state derivation with φ-based thresholds."""

    def test_full_consent_at_threshold(self):
        """Somatic ≥ 10 should give FULL_CONSENT."""
        assert derive_consent_state(10) == ConsentState.FULL_CONSENT
        assert derive_consent_state(11) == ConsentState.FULL_CONSENT
        assert derive_consent_state(15) == ConsentState.FULL_CONSENT

    def test_full_consent_threshold_is_phi(self):
        """FULL threshold should be 10 (φ × 16 ≈ 9.89)."""
        assert PHI_THRESHOLD_4BIT == 10

    def test_attentive_in_zone(self):
        """Somatic 7-9 should give ATTENTIVE."""
        assert derive_consent_state(7) == ConsentState.ATTENTIVE
        assert derive_consent_state(8) == ConsentState.ATTENTIVE
        assert derive_consent_state(9) == ConsentState.ATTENTIVE

    def test_attentive_threshold(self):
        """ATTENTIVE threshold should be 7."""
        assert ATTENTIVE_THRESHOLD_4BIT == 7

    def test_diminished_at_boundary(self):
        """Somatic = 6 without verbal boost gives DIMINISHED."""
        assert derive_consent_state(6, verbal_signal_strength=0) == ConsentState.DIMINISHED_CONSENT
        assert derive_consent_state(6, verbal_signal_strength=1) == ConsentState.DIMINISHED_CONSENT

    def test_verbal_boost_at_boundary(self):
        """Somatic = 6 with strong verbal (≥2) boosts to ATTENTIVE."""
        assert derive_consent_state(6, verbal_signal_strength=2) == ConsentState.ATTENTIVE
        assert derive_consent_state(6, verbal_signal_strength=3) == ConsentState.ATTENTIVE

    def test_diminished_threshold(self):
        """DIMINISHED threshold should be 6 ((1-φ) × 16)."""
        assert DIMINISHED_THRESHOLD_4BIT == 6

    def test_suspended_below_threshold(self):
        """Somatic 0-5 should give SUSPENDED_CONSENT."""
        for somatic in range(6):
            assert derive_consent_state(somatic) == ConsentState.SUSPENDED_CONSENT

    def test_verbal_no_boost_below_threshold(self):
        """Verbal signal doesn't boost consent when somatic < 6."""
        for somatic in range(6):
            assert derive_consent_state(somatic, verbal_signal_strength=3) == ConsentState.SUSPENDED_CONSENT


# =============================================================================
# Test ConsentPacketHeader
# =============================================================================

class TestConsentPacketHeader:
    """Tests for consent packet header encoding/decoding."""

    def test_header_size(self):
        """Header should be 18 bytes."""
        assert HEADER_SIZE == 18

    def test_create_full_consent(self, sample_address):
        """Create header with full consent."""
        header = ConsentPacketHeader.create(
            rpp_address=sample_address,
            consent_somatic_4bit=15,
            verbal_signal_strength=3,
        )
        assert header.consent_state == ConsentState.FULL_CONSENT
        assert header.consent_somatic_4bit == 15
        assert header.verbal_signal_strength == 3

    def test_create_attentive(self, sample_address):
        """Create header with attentive consent."""
        header = ConsentPacketHeader.create(
            rpp_address=sample_address,
            consent_somatic_4bit=8,
            verbal_signal_strength=2,
        )
        assert header.consent_state == ConsentState.ATTENTIVE

    def test_create_diminished(self, sample_address):
        """Create header with diminished consent."""
        header = ConsentPacketHeader.create(
            rpp_address=sample_address,
            consent_somatic_4bit=6,
            verbal_signal_strength=1,
        )
        assert header.consent_state == ConsentState.DIMINISHED_CONSENT

    def test_create_suspended(self, sample_address):
        """Create header with suspended consent."""
        header = ConsentPacketHeader.create(
            rpp_address=sample_address,
            consent_somatic_4bit=3,
            verbal_signal_strength=0,
        )
        assert header.consent_state == ConsentState.SUSPENDED_CONSENT

    def test_encode_decode_roundtrip(self, full_consent_header):
        """Encoding then decoding should preserve all fields."""
        encoded = full_consent_header.to_bytes()
        decoded = ConsentPacketHeader.from_bytes(encoded)

        assert decoded.consent_somatic_4bit == full_consent_header.consent_somatic_4bit
        assert decoded.verbal_signal_strength == full_consent_header.verbal_signal_strength
        assert decoded.consent_ancestral == full_consent_header.consent_ancestral
        assert decoded.consent_state == full_consent_header.consent_state

    def test_encode_size(self, full_consent_header):
        """Encoded header should be exactly 18 bytes."""
        encoded = full_consent_header.to_bytes()
        assert len(encoded) == HEADER_SIZE

    def test_crc_validation(self, full_consent_header):
        """CRC should be computed correctly."""
        encoded = full_consent_header.to_bytes()
        # Tamper with a byte
        tampered = bytearray(encoded)
        tampered[5] ^= 0xFF
        with pytest.raises(ValueError, match="CRC mismatch"):
            ConsentPacketHeader.from_bytes(bytes(tampered))


class TestConsentPacketHeaderValidation:
    """Tests for header validation rules."""

    def test_valid_header(self, full_consent_header):
        """Valid header should pass validation."""
        valid, errors = full_consent_header.validate()
        assert valid is True
        assert len(errors) == 0

    def test_c1_rule_low_somatic_no_complecount(self, sample_address):
        """C1: Low somatic (< 6) requires complecount > 0."""
        header = ConsentPacketHeader(
            rpp_address=sample_address,
            consent_somatic_4bit=4,
            verbal_signal_strength=1,
            complecount_trace=0,  # Violates C1
        )
        valid, errors = header.validate()
        assert valid is False
        assert any("C1" in e for e in errors)

    def test_c1_rule_low_somatic_with_complecount(self, sample_address):
        """C1: Low somatic with complecount > 0 is valid."""
        header = ConsentPacketHeader(
            rpp_address=sample_address,
            consent_somatic_4bit=4,
            verbal_signal_strength=1,
            complecount_trace=3,  # Satisfies C1
        )
        valid, errors = header.validate()
        # Should pass C1 (may fail other checks)
        assert not any("C1" in e for e in errors)


class TestConsentPacketHeaderFields:
    """Tests for individual field encoding/decoding."""

    def test_verbal_signal_strength_encoding(self, sample_address):
        """Verbal signal strength should encode/decode correctly."""
        for verbal in range(4):
            header = ConsentPacketHeader.create(
                rpp_address=sample_address,
                consent_somatic_4bit=10,
                verbal_signal_strength=verbal,
            )
            encoded = header.to_bytes()
            decoded = ConsentPacketHeader.from_bytes(encoded)
            assert decoded.verbal_signal_strength == verbal

    def test_consent_somatic_4bit_encoding(self, sample_address):
        """Consent somatic 4-bit should encode/decode correctly."""
        for somatic in range(16):
            header = ConsentPacketHeader.create(
                rpp_address=sample_address,
                consent_somatic_4bit=somatic,
                verbal_signal_strength=2,
            )
            encoded = header.to_bytes()
            decoded = ConsentPacketHeader.from_bytes(encoded)
            assert decoded.consent_somatic_4bit == somatic

    def test_ancestral_consent_encoding(self, sample_address):
        """Ancestral consent should encode/decode correctly."""
        for ancestral in AncestralConsent:
            header = ConsentPacketHeader(
                rpp_address=sample_address,
                consent_somatic_4bit=10,
                verbal_signal_strength=2,
                consent_ancestral=ancestral,
            )
            encoded = header.to_bytes()
            decoded = ConsentPacketHeader.from_bytes(encoded)
            assert decoded.consent_ancestral == ancestral

    def test_temporal_lock_encoding(self, sample_address):
        """Temporal lock should encode/decode correctly."""
        for lock in [True, False]:
            header = ConsentPacketHeader(
                rpp_address=sample_address,
                consent_somatic_4bit=10,
                verbal_signal_strength=2,
                temporal_lock=lock,
            )
            encoded = header.to_bytes()
            decoded = ConsentPacketHeader.from_bytes(encoded)
            assert decoded.temporal_lock == lock


# =============================================================================
# Test SpiralPacket
# =============================================================================

class TestSpiralPacket:
    """Tests for complete SPIRAL packet."""

    def test_packet_with_payload(self, full_consent_header):
        """Packet should include header and payload."""
        payload = b"Hello, SPIRAL!"
        packet = SpiralPacket(header=full_consent_header, payload=payload)

        assert packet.total_size == HEADER_SIZE + len(payload)

    def test_packet_roundtrip(self, full_consent_header):
        """Encoding then decoding packet should preserve data."""
        payload = b"Test payload data"
        packet = SpiralPacket(header=full_consent_header, payload=payload)

        encoded = packet.to_bytes()
        decoded = SpiralPacket.from_bytes(encoded)

        assert decoded.payload == payload
        assert decoded.header.consent_state == full_consent_header.consent_state


# =============================================================================
# Test Threshold Values
# =============================================================================

class TestPhiThresholds:
    """Tests for φ-derived threshold values."""

    def test_phi_threshold_value(self):
        """PHI_THRESHOLD should be 10 (φ × 16 ≈ 9.89)."""
        assert PHI_THRESHOLD_4BIT == 10

    def test_attentive_threshold_value(self):
        """ATTENTIVE_THRESHOLD should be 7."""
        assert ATTENTIVE_THRESHOLD_4BIT == 7

    def test_diminished_threshold_value(self):
        """DIMINISHED_THRESHOLD should be 6 ((1-φ) × 16 ≈ 6.11)."""
        assert DIMINISHED_THRESHOLD_4BIT == 6

    def test_threshold_ordering(self):
        """Thresholds should be in descending order."""
        assert PHI_THRESHOLD_4BIT > ATTENTIVE_THRESHOLD_4BIT > DIMINISHED_THRESHOLD_4BIT


# =============================================================================
# Test State Transitions
# =============================================================================

class TestStateTransitionBoundaries:
    """Tests for consent state transition boundaries."""

    def test_full_to_attentive_boundary(self):
        """Transition from FULL to ATTENTIVE at somatic = 9."""
        assert derive_consent_state(10) == ConsentState.FULL_CONSENT
        assert derive_consent_state(9) == ConsentState.ATTENTIVE

    def test_attentive_to_diminished_boundary(self):
        """Transition from ATTENTIVE to DIMINISHED at somatic = 6."""
        assert derive_consent_state(7) == ConsentState.ATTENTIVE
        assert derive_consent_state(6) == ConsentState.DIMINISHED_CONSENT

    def test_diminished_to_suspended_boundary(self):
        """Transition from DIMINISHED to SUSPENDED at somatic = 5."""
        assert derive_consent_state(6) == ConsentState.DIMINISHED_CONSENT
        assert derive_consent_state(5) == ConsentState.SUSPENDED_CONSENT

    def test_verbal_boost_boundary(self):
        """Verbal boost only works at DIMINISHED boundary (somatic = 6)."""
        # At boundary: verbal boost works
        assert derive_consent_state(6, verbal_signal_strength=2) == ConsentState.ATTENTIVE

        # Below boundary: verbal boost doesn't help
        assert derive_consent_state(5, verbal_signal_strength=3) == ConsentState.SUSPENDED_CONSENT

        # Above boundary (ATTENTIVE zone): verbal doesn't change state
        assert derive_consent_state(7, verbal_signal_strength=0) == ConsentState.ATTENTIVE
        assert derive_consent_state(7, verbal_signal_strength=3) == ConsentState.ATTENTIVE
