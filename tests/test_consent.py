"""Tests for RPP consent module."""

from rpp.consent import (
    ConsentState,
    ConsentContext,
    Sector,
    GroundingZone,
    check_consent,
    create_consent_context,
)


class TestConsentState:
    """Tests for ConsentState enum."""

    def test_allows_write(self):
        """Check write permission for each state."""
        assert ConsentState.FULL_CONSENT.allows_write
        assert not ConsentState.DIMINISHED_CONSENT.allows_write
        assert not ConsentState.SUSPENDED_CONSENT.allows_write
        assert ConsentState.EMERGENCY_OVERRIDE.allows_write

    def test_allows_delete(self):
        """Check delete permission for each state."""
        assert ConsentState.FULL_CONSENT.allows_delete
        assert not ConsentState.DIMINISHED_CONSENT.allows_delete
        assert not ConsentState.SUSPENDED_CONSENT.allows_delete
        assert not ConsentState.EMERGENCY_OVERRIDE.allows_delete

    def test_is_restricted(self):
        """Check restricted states."""
        assert not ConsentState.FULL_CONSENT.is_restricted
        assert ConsentState.DIMINISHED_CONSENT.is_restricted
        assert ConsentState.SUSPENDED_CONSENT.is_restricted
        assert not ConsentState.EMERGENCY_OVERRIDE.is_restricted


class TestSector:
    """Tests for Sector enum."""

    def test_from_theta(self):
        """Map theta to sectors."""
        assert Sector.from_theta(0) == Sector.GENE
        assert Sector.from_theta(63) == Sector.GENE
        assert Sector.from_theta(64) == Sector.MEMORY
        assert Sector.from_theta(127) == Sector.MEMORY
        assert Sector.from_theta(128) == Sector.WITNESS
        assert Sector.from_theta(192) == Sector.DREAM
        assert Sector.from_theta(256) == Sector.BRIDGE
        assert Sector.from_theta(320) == Sector.GUARDIAN
        assert Sector.from_theta(384) == Sector.EMERGENCE
        assert Sector.from_theta(448) == Sector.META
        assert Sector.from_theta(511) == Sector.META

    def test_sensitivity(self):
        """Check sector sensitivity levels."""
        assert Sector.GENE.sensitivity == "high"
        assert Sector.GUARDIAN.sensitivity == "high"
        assert Sector.META.sensitivity == "high"
        assert Sector.MEMORY.sensitivity == "medium"
        assert Sector.EMERGENCE.sensitivity == "medium"
        assert Sector.DREAM.sensitivity == "low"
        assert Sector.BRIDGE.sensitivity == "low"
        assert Sector.WITNESS.sensitivity == "low"

    def test_requires_full_consent(self):
        """Check which sectors require full consent for writes."""
        assert Sector.GENE.requires_full_consent_for_write
        assert Sector.GUARDIAN.requires_full_consent_for_write
        assert Sector.META.requires_full_consent_for_write
        assert not Sector.DREAM.requires_full_consent_for_write


class TestGroundingZone:
    """Tests for GroundingZone enum."""

    def test_from_phi(self):
        """Map phi to zones."""
        assert GroundingZone.from_phi(0) == GroundingZone.GROUNDED
        assert GroundingZone.from_phi(170) == GroundingZone.GROUNDED
        assert GroundingZone.from_phi(171) == GroundingZone.TRANSITIONAL
        assert GroundingZone.from_phi(341) == GroundingZone.TRANSITIONAL
        assert GroundingZone.from_phi(342) == GroundingZone.ETHEREAL
        assert GroundingZone.from_phi(511) == GroundingZone.ETHEREAL

    def test_consent_threshold(self):
        """Check consent thresholds for zones."""
        assert GroundingZone.GROUNDED.consent_threshold == ConsentState.DIMINISHED_CONSENT
        assert GroundingZone.TRANSITIONAL.consent_threshold == ConsentState.FULL_CONSENT
        assert GroundingZone.ETHEREAL.consent_threshold == ConsentState.FULL_CONSENT


class TestConsentContext:
    """Tests for ConsentContext."""

    def test_to_dict(self):
        """Convert context to dict."""
        ctx = ConsentContext(
            state=ConsentState.FULL_CONSENT,
            soul_id="soul-123",
            coherence_score=0.7,
        )
        d = ctx.to_dict()

        assert d["consent"] == "full"
        assert d["soul_id"] == "soul-123"
        assert d["coherence_score"] == 0.7
        assert d["emergency_override"] is False

    def test_is_verified(self):
        """Check verified status."""
        verified = ConsentContext(state=ConsentState.FULL_CONSENT, soul_id="soul-123")
        unverified = ConsentContext(state=ConsentState.FULL_CONSENT)

        assert verified.is_verified
        assert not unverified.is_verified

    def test_is_coherent(self):
        """Check coherence threshold."""
        coherent = ConsentContext(state=ConsentState.FULL_CONSENT, coherence_score=0.5)
        incoherent = ConsentContext(state=ConsentState.FULL_CONSENT, coherence_score=0.3)

        assert coherent.is_coherent
        assert not incoherent.is_coherent


class TestCheckConsent:
    """Tests for check_consent function."""

    def test_full_consent_read(self):
        """Full consent allows all reads."""
        ctx = ConsentContext(state=ConsentState.FULL_CONSENT)
        check = check_consent(theta=50, phi=100, operation="read", context=ctx)

        assert check.allowed
        assert check.sector == Sector.GENE

    def test_full_consent_write_low_sensitivity(self):
        """Full consent allows writes to low-sensitivity sectors."""
        ctx = ConsentContext(state=ConsentState.FULL_CONSENT, soul_id="soul-123")
        check = check_consent(theta=200, phi=100, operation="write", context=ctx)

        assert check.allowed
        assert check.sector == Sector.DREAM

    def test_full_consent_write_high_sensitivity_no_soul(self):
        """High-sensitivity writes need verified identity."""
        ctx = ConsentContext(state=ConsentState.FULL_CONSENT)  # No soul_id
        check = check_consent(theta=50, phi=100, operation="write", context=ctx)

        assert not check.allowed
        assert "verified identity" in check.reason

    def test_full_consent_write_high_sensitivity_with_soul(self):
        """High-sensitivity writes allowed with verified identity."""
        ctx = ConsentContext(state=ConsentState.FULL_CONSENT, soul_id="soul-123")
        check = check_consent(theta=50, phi=100, operation="write", context=ctx)

        assert check.allowed

    def test_full_consent_write_ethereal_low_coherence(self):
        """Ethereal zone writes need high coherence."""
        ctx = ConsentContext(
            state=ConsentState.FULL_CONSENT,
            soul_id="soul-123",
            coherence_score=0.2,
        )
        check = check_consent(theta=200, phi=400, operation="write", context=ctx)

        assert not check.allowed
        assert "coherence" in check.reason

    def test_full_consent_write_ethereal_high_coherence(self):
        """Ethereal zone writes allowed with high coherence."""
        ctx = ConsentContext(
            state=ConsentState.FULL_CONSENT,
            soul_id="soul-123",
            coherence_score=0.8,
        )
        check = check_consent(theta=200, phi=400, operation="write", context=ctx)

        assert check.allowed

    def test_diminished_consent_read(self):
        """Diminished consent allows reads to low/medium sectors."""
        ctx = ConsentContext(state=ConsentState.DIMINISHED_CONSENT)
        check = check_consent(theta=200, phi=100, operation="read", context=ctx)

        assert check.allowed

    def test_diminished_consent_read_high_sensitivity(self):
        """Diminished consent blocks high-sensitivity reads."""
        ctx = ConsentContext(state=ConsentState.DIMINISHED_CONSENT)
        check = check_consent(theta=50, phi=100, operation="read", context=ctx)

        assert not check.allowed
        assert "full consent" in check.reason.lower()

    def test_diminished_consent_write(self):
        """Diminished consent blocks all writes."""
        ctx = ConsentContext(state=ConsentState.DIMINISHED_CONSENT)
        check = check_consent(theta=200, phi=100, operation="write", context=ctx)

        assert not check.allowed
        assert "not permitted" in check.reason

    def test_suspended_consent_read_grounded(self):
        """Suspended consent allows reads in grounded zone."""
        ctx = ConsentContext(state=ConsentState.SUSPENDED_CONSENT)
        check = check_consent(theta=200, phi=50, operation="read", context=ctx)

        assert check.allowed

    def test_suspended_consent_read_not_grounded(self):
        """Suspended consent blocks reads outside grounded zone."""
        ctx = ConsentContext(state=ConsentState.SUSPENDED_CONSENT)
        check = check_consent(theta=200, phi=300, operation="read", context=ctx)

        assert not check.allowed
        assert "grounded" in check.reason.lower()

    def test_suspended_consent_write(self):
        """Suspended consent blocks all writes."""
        ctx = ConsentContext(state=ConsentState.SUSPENDED_CONSENT)
        check = check_consent(theta=200, phi=50, operation="write", context=ctx)

        assert not check.allowed

    def test_emergency_override_with_justification(self):
        """Emergency override allows all operations with justification."""
        ctx = ConsentContext(
            state=ConsentState.EMERGENCY_OVERRIDE,
            emergency_justification="Medical emergency",
        )
        check = check_consent(theta=50, phi=500, operation="write", context=ctx)

        assert check.allowed
        assert "Medical emergency" in check.reason

    def test_emergency_override_without_justification(self):
        """Emergency override requires justification."""
        ctx = ConsentContext(state=ConsentState.EMERGENCY_OVERRIDE)
        check = check_consent(theta=50, phi=500, operation="write", context=ctx)

        assert not check.allowed
        assert "justification" in check.reason.lower()

    def test_delete_requires_verified_identity(self):
        """Delete operations require verified identity."""
        ctx = ConsentContext(state=ConsentState.FULL_CONSENT)  # No soul_id
        check = check_consent(theta=200, phi=100, operation="delete", context=ctx)

        assert not check.allowed
        assert "verified identity" in check.reason


class TestCreateConsentContext:
    """Tests for create_consent_context helper."""

    def test_create_full(self):
        """Create full consent context."""
        ctx = create_consent_context(state="full", soul_id="soul-123")

        assert ctx.state == ConsentState.FULL_CONSENT
        assert ctx.soul_id == "soul-123"

    def test_create_diminished(self):
        """Create diminished consent context."""
        ctx = create_consent_context(state="diminished")

        assert ctx.state == ConsentState.DIMINISHED_CONSENT

    def test_create_with_coherence(self):
        """Create context with coherence score."""
        ctx = create_consent_context(state="full", coherence=0.75)

        assert ctx.coherence_score == 0.75
        assert ctx.is_coherent

    def test_create_emergency(self):
        """Create emergency context."""
        ctx = create_consent_context(
            state="emergency",
            emergency_justification="Test override",
        )

        assert ctx.state == ConsentState.EMERGENCY_OVERRIDE
        assert ctx.emergency_justification == "Test override"
