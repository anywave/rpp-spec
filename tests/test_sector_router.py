"""
Tests for Sector Router Module
===============================

Tests for consent-gated theta sector routing.
"""

import pytest

from rpp.sector_router import (
    RoutableSector,
    SECTOR_ACCESS,
    UNIVERSAL_SECTORS,
    RESTRICTED_SECTORS,
    SECTOR_SENSITIVITY,
    FALLBACK_CHAIN,
    can_access_sector,
    get_accessible_sectors,
    get_fallback_sector,
    get_sector_sensitivity,
    requires_full_consent,
    is_universal_access,
    route_to_sector,
    RoutingDecision,
    from_legacy_sector,
    to_legacy_sector,
)
from rpp.consent_header import ConsentState


# =============================================================================
# Test RoutableSector Enum
# =============================================================================

class TestRoutableSector:
    """Tests for RoutableSector enum."""

    def test_has_nine_sectors(self):
        """Should have 9 sectors (VOID + 8 semantic)."""
        assert len(RoutableSector) == 9

    def test_sector_values(self):
        """Sectors should have correct integer values."""
        assert RoutableSector.VOID == 0
        assert RoutableSector.CORE == 1
        assert RoutableSector.GENE == 2
        assert RoutableSector.MEMORY == 3
        assert RoutableSector.WITNESS == 4
        assert RoutableSector.DREAM == 5
        assert RoutableSector.BRIDGE == 6
        assert RoutableSector.GUARDIAN == 7
        assert RoutableSector.SHADOW == 8

    def test_void_is_zero(self):
        """VOID should be sector 0 (phase collapse state)."""
        assert RoutableSector.VOID == 0


# =============================================================================
# Test Sector Access Matrix
# =============================================================================

class TestSectorAccessMatrix:
    """Tests for sector access matrix."""

    def test_full_consent_all_sectors(self):
        """FULL_CONSENT should access all sectors."""
        accessible = SECTOR_ACCESS[ConsentState.FULL_CONSENT]
        assert len(accessible) == 9
        for sector in RoutableSector:
            assert sector in accessible

    def test_attentive_sectors(self):
        """ATTENTIVE should access MEMORY, WITNESS, BRIDGE, GUARDIAN."""
        accessible = SECTOR_ACCESS[ConsentState.ATTENTIVE]
        assert RoutableSector.MEMORY in accessible
        assert RoutableSector.WITNESS in accessible
        assert RoutableSector.BRIDGE in accessible
        assert RoutableSector.GUARDIAN in accessible
        # Should NOT access
        assert RoutableSector.CORE not in accessible
        assert RoutableSector.GENE not in accessible
        assert RoutableSector.DREAM not in accessible
        assert RoutableSector.VOID not in accessible

    def test_diminished_sectors(self):
        """DIMINISHED_CONSENT should access BRIDGE, GUARDIAN, SHADOW."""
        accessible = SECTOR_ACCESS[ConsentState.DIMINISHED_CONSENT]
        assert RoutableSector.BRIDGE in accessible
        assert RoutableSector.GUARDIAN in accessible
        assert RoutableSector.SHADOW in accessible
        assert len(accessible) == 3

    def test_suspended_sectors(self):
        """SUSPENDED_CONSENT should access BRIDGE, GUARDIAN only."""
        accessible = SECTOR_ACCESS[ConsentState.SUSPENDED_CONSENT]
        assert RoutableSector.BRIDGE in accessible
        assert RoutableSector.GUARDIAN in accessible
        assert len(accessible) == 2

    def test_emergency_override_guardian_only(self):
        """EMERGENCY_OVERRIDE should access GUARDIAN only (lockdown)."""
        accessible = SECTOR_ACCESS[ConsentState.EMERGENCY_OVERRIDE]
        assert RoutableSector.GUARDIAN in accessible
        assert len(accessible) == 1


class TestUniversalSectors:
    """Tests for universal access sectors."""

    def test_bridge_is_universal(self):
        """BRIDGE should have universal access."""
        assert RoutableSector.BRIDGE in UNIVERSAL_SECTORS

    def test_guardian_is_universal(self):
        """GUARDIAN should have universal access."""
        assert RoutableSector.GUARDIAN in UNIVERSAL_SECTORS

    def test_only_two_universal(self):
        """Only BRIDGE and GUARDIAN should be universal."""
        assert len(UNIVERSAL_SECTORS) == 2


class TestRestrictedSectors:
    """Tests for restricted (FULL_CONSENT required) sectors."""

    def test_core_is_restricted(self):
        """CORE should require FULL_CONSENT."""
        assert RoutableSector.CORE in RESTRICTED_SECTORS

    def test_gene_is_restricted(self):
        """GENE should require FULL_CONSENT."""
        assert RoutableSector.GENE in RESTRICTED_SECTORS

    def test_dream_is_restricted(self):
        """DREAM should require FULL_CONSENT."""
        assert RoutableSector.DREAM in RESTRICTED_SECTORS

    def test_only_three_restricted(self):
        """Only CORE, GENE, DREAM should be restricted."""
        assert len(RESTRICTED_SECTORS) == 3


# =============================================================================
# Test can_access_sector
# =============================================================================

class TestCanAccessSector:
    """Tests for can_access_sector function."""

    def test_void_requires_zero_coherence(self):
        """VOID sector requires coherence = 0."""
        assert can_access_sector(ConsentState.FULL_CONSENT, RoutableSector.VOID, coherence=0)
        assert not can_access_sector(ConsentState.FULL_CONSENT, RoutableSector.VOID, coherence=1)
        assert not can_access_sector(ConsentState.FULL_CONSENT, RoutableSector.VOID, coherence=674)

    def test_guardian_always_accessible(self):
        """GUARDIAN should always be accessible."""
        for state in ConsentState:
            assert can_access_sector(state, RoutableSector.GUARDIAN)

    def test_full_consent_all_sectors(self):
        """FULL_CONSENT can access all sectors (except VOID needs coherence=0)."""
        for sector in RoutableSector:
            if sector == RoutableSector.VOID:
                continue
            assert can_access_sector(ConsentState.FULL_CONSENT, sector)

    def test_attentive_limited_sectors(self):
        """ATTENTIVE has limited sector access."""
        # Accessible
        assert can_access_sector(ConsentState.ATTENTIVE, RoutableSector.MEMORY)
        assert can_access_sector(ConsentState.ATTENTIVE, RoutableSector.WITNESS)
        assert can_access_sector(ConsentState.ATTENTIVE, RoutableSector.BRIDGE)
        assert can_access_sector(ConsentState.ATTENTIVE, RoutableSector.GUARDIAN)
        # Not accessible
        assert not can_access_sector(ConsentState.ATTENTIVE, RoutableSector.CORE)
        assert not can_access_sector(ConsentState.ATTENTIVE, RoutableSector.GENE)
        assert not can_access_sector(ConsentState.ATTENTIVE, RoutableSector.DREAM)

    def test_suspended_minimal_access(self):
        """SUSPENDED_CONSENT has minimal access."""
        assert can_access_sector(ConsentState.SUSPENDED_CONSENT, RoutableSector.BRIDGE)
        assert can_access_sector(ConsentState.SUSPENDED_CONSENT, RoutableSector.GUARDIAN)
        assert not can_access_sector(ConsentState.SUSPENDED_CONSENT, RoutableSector.MEMORY)
        assert not can_access_sector(ConsentState.SUSPENDED_CONSENT, RoutableSector.SHADOW)

    def test_emergency_guardian_only(self):
        """EMERGENCY_OVERRIDE only accesses GUARDIAN."""
        assert can_access_sector(ConsentState.EMERGENCY_OVERRIDE, RoutableSector.GUARDIAN)
        assert not can_access_sector(ConsentState.EMERGENCY_OVERRIDE, RoutableSector.BRIDGE)
        assert not can_access_sector(ConsentState.EMERGENCY_OVERRIDE, RoutableSector.CORE)


# =============================================================================
# Test get_accessible_sectors
# =============================================================================

class TestGetAccessibleSectors:
    """Tests for get_accessible_sectors function."""

    def test_full_consent_returns_all(self):
        """FULL_CONSENT should return all 9 sectors."""
        sectors = get_accessible_sectors(ConsentState.FULL_CONSENT)
        assert len(sectors) == 9

    def test_attentive_returns_four(self):
        """ATTENTIVE should return 4 sectors."""
        sectors = get_accessible_sectors(ConsentState.ATTENTIVE)
        assert len(sectors) == 4

    def test_returns_frozenset(self):
        """Should return immutable frozenset."""
        sectors = get_accessible_sectors(ConsentState.FULL_CONSENT)
        assert isinstance(sectors, frozenset)


# =============================================================================
# Test get_fallback_sector
# =============================================================================

class TestGetFallbackSector:
    """Tests for get_fallback_sector function."""

    def test_accessible_sector_returns_self(self):
        """If sector is accessible, return it unchanged."""
        result = get_fallback_sector(ConsentState.FULL_CONSENT, RoutableSector.CORE)
        assert result == RoutableSector.CORE

    def test_inaccessible_falls_back_to_guardian(self):
        """Inaccessible sector should fallback to GUARDIAN."""
        result = get_fallback_sector(ConsentState.ATTENTIVE, RoutableSector.CORE)
        assert result == RoutableSector.GUARDIAN

    def test_emergency_always_guardian(self):
        """EMERGENCY_OVERRIDE should always fallback to GUARDIAN."""
        for sector in RoutableSector:
            if sector != RoutableSector.GUARDIAN:
                result = get_fallback_sector(ConsentState.EMERGENCY_OVERRIDE, sector)
                assert result == RoutableSector.GUARDIAN


# =============================================================================
# Test Sector Properties
# =============================================================================

class TestSectorSensitivity:
    """Tests for sector sensitivity levels."""

    def test_sensitivity_range(self):
        """Sensitivity should be 0-5."""
        for sector in RoutableSector:
            sens = get_sector_sensitivity(sector)
            assert 0 <= sens <= 5

    def test_core_high_sensitivity(self):
        """CORE should have high sensitivity (5)."""
        assert get_sector_sensitivity(RoutableSector.CORE) == 5

    def test_bridge_low_sensitivity(self):
        """BRIDGE should have low sensitivity (1)."""
        assert get_sector_sensitivity(RoutableSector.BRIDGE) == 1

    def test_void_zero_sensitivity(self):
        """VOID should have zero sensitivity."""
        assert get_sector_sensitivity(RoutableSector.VOID) == 0


class TestRequiresFullConsent:
    """Tests for requires_full_consent function."""

    def test_core_requires_full(self):
        """CORE requires FULL_CONSENT."""
        assert requires_full_consent(RoutableSector.CORE)

    def test_gene_requires_full(self):
        """GENE requires FULL_CONSENT."""
        assert requires_full_consent(RoutableSector.GENE)

    def test_dream_requires_full(self):
        """DREAM requires FULL_CONSENT."""
        assert requires_full_consent(RoutableSector.DREAM)

    def test_bridge_does_not_require_full(self):
        """BRIDGE does not require FULL_CONSENT."""
        assert not requires_full_consent(RoutableSector.BRIDGE)

    def test_memory_does_not_require_full(self):
        """MEMORY does not require FULL_CONSENT (ATTENTIVE is enough)."""
        assert not requires_full_consent(RoutableSector.MEMORY)


class TestIsUniversalAccess:
    """Tests for is_universal_access function."""

    def test_bridge_is_universal(self):
        """BRIDGE is universal."""
        assert is_universal_access(RoutableSector.BRIDGE)

    def test_guardian_is_universal(self):
        """GUARDIAN is universal."""
        assert is_universal_access(RoutableSector.GUARDIAN)

    def test_core_not_universal(self):
        """CORE is not universal."""
        assert not is_universal_access(RoutableSector.CORE)


# =============================================================================
# Test RoutingDecision
# =============================================================================

class TestRoutingDecision:
    """Tests for RoutingDecision class."""

    def test_granted_decision(self):
        """Test granted routing decision."""
        decision = RoutingDecision(
            granted=True,
            sector=RoutableSector.CORE,
            original_sector=RoutableSector.CORE,
            reason="access granted",
        )
        assert decision.granted
        assert decision.sector == RoutableSector.CORE
        assert not decision.was_redirected

    def test_redirected_decision(self):
        """Test redirected routing decision."""
        decision = RoutingDecision(
            granted=True,
            sector=RoutableSector.GUARDIAN,
            original_sector=RoutableSector.CORE,
            reason="fallback",
        )
        assert decision.granted
        assert decision.was_redirected
        assert decision.sector == RoutableSector.GUARDIAN
        assert decision.original_sector == RoutableSector.CORE

    def test_denied_decision(self):
        """Test denied routing decision."""
        decision = RoutingDecision(
            granted=False,
            sector=RoutableSector.CORE,
            original_sector=RoutableSector.CORE,
            reason="access denied",
        )
        assert not decision.granted


# =============================================================================
# Test route_to_sector
# =============================================================================

class TestRouteToSector:
    """Tests for route_to_sector function."""

    def test_direct_access_granted(self):
        """Direct access should be granted when allowed."""
        decision = route_to_sector(ConsentState.FULL_CONSENT, RoutableSector.CORE)
        assert decision.granted
        assert decision.sector == RoutableSector.CORE
        assert not decision.was_redirected

    def test_fallback_routing(self):
        """Fallback routing when direct access denied."""
        decision = route_to_sector(ConsentState.ATTENTIVE, RoutableSector.CORE)
        assert decision.granted
        assert decision.was_redirected
        assert decision.sector == RoutableSector.GUARDIAN
        assert decision.original_sector == RoutableSector.CORE

    def test_fallback_disabled(self):
        """Should deny when fallback disabled."""
        decision = route_to_sector(
            ConsentState.ATTENTIVE,
            RoutableSector.CORE,
            allow_fallback=False,
        )
        assert not decision.granted
        assert not decision.was_redirected

    def test_void_with_zero_coherence(self):
        """VOID accessible with coherence=0."""
        decision = route_to_sector(
            ConsentState.FULL_CONSENT,
            RoutableSector.VOID,
            coherence=0,
        )
        assert decision.granted
        assert decision.sector == RoutableSector.VOID

    def test_void_redirects_without_zero_coherence(self):
        """VOID redirects to fallback without coherence=0."""
        decision = route_to_sector(
            ConsentState.FULL_CONSENT,
            RoutableSector.VOID,
            coherence=100,
        )
        assert decision.granted
        assert decision.was_redirected
        assert decision.sector in FALLBACK_CHAIN


# =============================================================================
# Test Legacy Conversion
# =============================================================================

class TestLegacyConversion:
    """Tests for legacy sector conversion."""

    def test_from_legacy_sector(self):
        """Convert legacy 0-7 to new 1-8."""
        assert from_legacy_sector(0) == RoutableSector.CORE
        assert from_legacy_sector(1) == RoutableSector.GENE
        assert from_legacy_sector(2) == RoutableSector.MEMORY
        assert from_legacy_sector(7) == RoutableSector.SHADOW

    def test_from_legacy_invalid(self):
        """Invalid legacy values should raise."""
        with pytest.raises(ValueError):
            from_legacy_sector(-1)
        with pytest.raises(ValueError):
            from_legacy_sector(8)

    def test_to_legacy_sector(self):
        """Convert new 1-8 to legacy 0-7."""
        assert to_legacy_sector(RoutableSector.CORE) == 0
        assert to_legacy_sector(RoutableSector.GENE) == 1
        assert to_legacy_sector(RoutableSector.SHADOW) == 7

    def test_to_legacy_void_returns_negative(self):
        """VOID has no legacy equivalent, returns -1."""
        assert to_legacy_sector(RoutableSector.VOID) == -1

    def test_roundtrip_conversion(self):
        """Legacy→new→legacy should preserve value."""
        for i in range(8):
            sector = from_legacy_sector(i)
            back = to_legacy_sector(sector)
            assert back == i
