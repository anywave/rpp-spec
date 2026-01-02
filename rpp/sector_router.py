"""
Sector Router Module
====================

Consent-gated theta sector routing for SPIRAL protocol.
Implements the 8-sector model with VOID state and consent-based access control.

Reference: SPIRAL-Architecture.md Section 4 (Theta Sectors)
Version: 2.2.0-RaCanonical
"""

from __future__ import annotations

from enum import IntEnum
from typing import Final, FrozenSet, Dict

from rpp.consent_header import ConsentState


# =============================================================================
# Theta Sector Enum (Extended with VOID)
# =============================================================================

class RoutableSector(IntEnum):
    """
    8 semantic theta sectors plus VOID for phase collapse.

    The sectors form a chambered nautilus geometry with consent-gated access.
    VOID is a special state accessible only when coherence = 0.

    Sector Access by Consent State:
        FULL_CONSENT: All sectors (0-8)
        ATTENTIVE: MEMORY, WITNESS, BRIDGE, GUARDIAN (3, 4, 6, 7)
        DIMINISHED_CONSENT: BRIDGE, GUARDIAN, SHADOW (6, 7, 8)
        SUSPENDED_CONSENT: BRIDGE, GUARDIAN only (6, 7)
        EMERGENCY_OVERRIDE: GUARDIAN lockdown (7)
    """
    VOID = 0       # Reset/phase collapse (coherence=0 only)
    CORE = 1       # Essential identity (requires FULL)
    GENE = 2       # Biological/inherited (requires FULL)
    MEMORY = 3     # Experiential/learned (ATTENTIVE+)
    WITNESS = 4    # Present-moment awareness (ATTENTIVE+)
    DREAM = 5      # Aspirational/future (requires FULL)
    BRIDGE = 6     # Relational/connective (universal access)
    GUARDIAN = 7   # Protective/regulatory (universal access, fallback)
    SHADOW = 8     # Unintegrated/emergent (DIMINISHED+)


# =============================================================================
# Sector Access Matrix
# =============================================================================

# Define which sectors are accessible for each consent state
SECTOR_ACCESS: Final[Dict[ConsentState, FrozenSet[RoutableSector]]] = {
    ConsentState.FULL_CONSENT: frozenset([
        RoutableSector.VOID,
        RoutableSector.CORE,
        RoutableSector.GENE,
        RoutableSector.MEMORY,
        RoutableSector.WITNESS,
        RoutableSector.DREAM,
        RoutableSector.BRIDGE,
        RoutableSector.GUARDIAN,
        RoutableSector.SHADOW,
    ]),
    ConsentState.ATTENTIVE: frozenset([
        RoutableSector.MEMORY,
        RoutableSector.WITNESS,
        RoutableSector.BRIDGE,
        RoutableSector.GUARDIAN,
    ]),
    ConsentState.DIMINISHED_CONSENT: frozenset([
        RoutableSector.BRIDGE,
        RoutableSector.GUARDIAN,
        RoutableSector.SHADOW,
    ]),
    ConsentState.SUSPENDED_CONSENT: frozenset([
        RoutableSector.BRIDGE,
        RoutableSector.GUARDIAN,
    ]),
    ConsentState.EMERGENCY_OVERRIDE: frozenset([
        RoutableSector.GUARDIAN,  # Lockdown to GUARDIAN only
    ]),
}

# Sectors that are always accessible (universal access)
UNIVERSAL_SECTORS: Final[FrozenSet[RoutableSector]] = frozenset([
    RoutableSector.BRIDGE,
    RoutableSector.GUARDIAN,
])

# Sectors requiring full consent
RESTRICTED_SECTORS: Final[FrozenSet[RoutableSector]] = frozenset([
    RoutableSector.CORE,
    RoutableSector.GENE,
    RoutableSector.DREAM,
])


# =============================================================================
# Sector Properties
# =============================================================================

# Sector sensitivity levels (higher = more restricted)
SECTOR_SENSITIVITY: Final[Dict[RoutableSector, int]] = {
    RoutableSector.VOID: 0,      # Special state, no sensitivity
    RoutableSector.BRIDGE: 1,    # Universal access
    RoutableSector.GUARDIAN: 1,  # Universal access (fallback)
    RoutableSector.SHADOW: 2,    # Diminished+ access
    RoutableSector.MEMORY: 3,    # Attentive+ access
    RoutableSector.WITNESS: 3,   # Attentive+ access
    RoutableSector.DREAM: 4,     # Full consent required
    RoutableSector.GENE: 5,      # Full consent required (biological)
    RoutableSector.CORE: 5,      # Full consent required (identity)
}

# Fallback sector chain (when access denied, try these in order)
FALLBACK_CHAIN: Final[tuple[RoutableSector, ...]] = (
    RoutableSector.GUARDIAN,
    RoutableSector.BRIDGE,
)


# =============================================================================
# Access Control Functions
# =============================================================================

def can_access_sector(
    consent_state: ConsentState,
    sector: RoutableSector,
    coherence: int = 674,
) -> bool:
    """
    Check if a sector is accessible given the consent state.

    Args:
        consent_state: Current ACSP consent state
        sector: Target sector to access
        coherence: Current coherence score (0-674)

    Returns:
        True if sector is accessible

    Special Cases:
        - VOID sector requires coherence = 0
        - GUARDIAN is always accessible (emergency fallback)
    """
    # VOID is only accessible at coherence = 0
    if sector == RoutableSector.VOID:
        return coherence == 0

    # GUARDIAN is always accessible (emergency fallback)
    if sector == RoutableSector.GUARDIAN:
        return True

    # Check sector access matrix
    accessible = SECTOR_ACCESS.get(consent_state, frozenset())
    return sector in accessible


def get_accessible_sectors(consent_state: ConsentState) -> FrozenSet[RoutableSector]:
    """
    Get all sectors accessible for a given consent state.

    Args:
        consent_state: Current ACSP consent state

    Returns:
        Frozenset of accessible sectors
    """
    return SECTOR_ACCESS.get(consent_state, frozenset([RoutableSector.GUARDIAN]))


def get_fallback_sector(
    consent_state: ConsentState,
    requested_sector: RoutableSector,
) -> RoutableSector:
    """
    Get fallback sector when requested sector is not accessible.

    Args:
        consent_state: Current ACSP consent state
        requested_sector: Originally requested sector

    Returns:
        Fallback sector (GUARDIAN or BRIDGE)
    """
    if can_access_sector(consent_state, requested_sector):
        return requested_sector

    # Try fallback chain
    accessible = get_accessible_sectors(consent_state)
    for fallback in FALLBACK_CHAIN:
        if fallback in accessible:
            return fallback

    # Ultimate fallback is always GUARDIAN
    return RoutableSector.GUARDIAN


def get_sector_sensitivity(sector: RoutableSector) -> int:
    """
    Get sensitivity level for a sector (0-5).

    Higher values indicate more restricted sectors.

    Args:
        sector: Target sector

    Returns:
        Sensitivity level (0-5)
    """
    return SECTOR_SENSITIVITY.get(sector, 5)


def requires_full_consent(sector: RoutableSector) -> bool:
    """
    Check if sector requires FULL_CONSENT for access.

    Args:
        sector: Target sector

    Returns:
        True if FULL_CONSENT required
    """
    return sector in RESTRICTED_SECTORS


def is_universal_access(sector: RoutableSector) -> bool:
    """
    Check if sector has universal access (all consent states).

    Args:
        sector: Target sector

    Returns:
        True if universally accessible
    """
    return sector in UNIVERSAL_SECTORS


# =============================================================================
# Routing Decision
# =============================================================================

class RoutingDecision:
    """Result of a sector routing decision."""

    __slots__ = ('granted', 'sector', 'original_sector', 'reason')

    def __init__(
        self,
        granted: bool,
        sector: RoutableSector,
        original_sector: RoutableSector,
        reason: str,
    ):
        self.granted = granted
        self.sector = sector
        self.original_sector = original_sector
        self.reason = reason

    @property
    def was_redirected(self) -> bool:
        """Check if request was redirected to fallback sector."""
        return self.sector != self.original_sector

    def __repr__(self) -> str:
        status = "GRANTED" if self.granted else "DENIED"
        if self.was_redirected:
            return (
                f"RoutingDecision({status}: {self.original_sector.name} → "
                f"{self.sector.name}, reason={self.reason!r})"
            )
        return f"RoutingDecision({status}: {self.sector.name}, reason={self.reason!r})"


def route_to_sector(
    consent_state: ConsentState,
    requested_sector: RoutableSector,
    coherence: int = 674,
    allow_fallback: bool = True,
) -> RoutingDecision:
    """
    Make a routing decision for sector access.

    Args:
        consent_state: Current ACSP consent state
        requested_sector: Desired sector
        coherence: Current coherence score (0-674)
        allow_fallback: Whether to allow fallback routing

    Returns:
        RoutingDecision with access result
    """
    # Check VOID special case
    if requested_sector == RoutableSector.VOID:
        if coherence == 0:
            return RoutingDecision(
                granted=True,
                sector=RoutableSector.VOID,
                original_sector=RoutableSector.VOID,
                reason="coherence=0 enables VOID access",
            )
        else:
            if allow_fallback:
                fallback = get_fallback_sector(consent_state, requested_sector)
                return RoutingDecision(
                    granted=True,
                    sector=fallback,
                    original_sector=RoutableSector.VOID,
                    reason=f"VOID requires coherence=0, redirected to {fallback.name}",
                )
            return RoutingDecision(
                granted=False,
                sector=requested_sector,
                original_sector=requested_sector,
                reason="VOID requires coherence=0",
            )

    # Check direct access
    if can_access_sector(consent_state, requested_sector, coherence):
        return RoutingDecision(
            granted=True,
            sector=requested_sector,
            original_sector=requested_sector,
            reason=f"{consent_state.name} grants access to {requested_sector.name}",
        )

    # Handle fallback
    if allow_fallback:
        fallback = get_fallback_sector(consent_state, requested_sector)
        return RoutingDecision(
            granted=True,
            sector=fallback,
            original_sector=requested_sector,
            reason=(
                f"{consent_state.name} denies {requested_sector.name}, "
                f"redirected to {fallback.name}"
            ),
        )

    # Access denied, no fallback
    return RoutingDecision(
        granted=False,
        sector=requested_sector,
        original_sector=requested_sector,
        reason=f"{consent_state.name} denies access to {requested_sector.name}",
    )


# =============================================================================
# Sector Conversion Utilities
# =============================================================================

def from_legacy_sector(legacy_value: int) -> RoutableSector:
    """
    Convert legacy ThetaSector value (0-7) to RoutableSector (1-8).

    Legacy mapping:
        0 (CORE) → 1 (CORE)
        1 (GENE) → 2 (GENE)
        ... etc

    Args:
        legacy_value: Legacy ThetaSector value (0-7)

    Returns:
        Corresponding RoutableSector
    """
    if not 0 <= legacy_value <= 7:
        raise ValueError(f"Legacy sector must be 0-7, got {legacy_value}")
    return RoutableSector(legacy_value + 1)


def to_legacy_sector(sector: RoutableSector) -> int:
    """
    Convert RoutableSector to legacy ThetaSector value.

    Args:
        sector: RoutableSector value

    Returns:
        Legacy ThetaSector value (0-7), or -1 for VOID

    Raises:
        ValueError: If sector is VOID (no legacy equivalent)
    """
    if sector == RoutableSector.VOID:
        return -1  # VOID has no legacy equivalent
    return sector.value - 1
