"""
RPP Consent Module

Implements the Avatar Consent State Protocol (ACSP) for RPP.

Consent States:
- FULL_CONSENT: All operations permitted
- DIMINISHED_CONSENT: Read-only, some sectors blocked
- SUSPENDED_CONSENT: Emergency read-only
- EMERGENCY_OVERRIDE: System override (requires justification)

Sector Requirements:
- Gene (theta 0-63): High sensitivity - requires full consent for writes
- Memory (theta 64-127): Medium sensitivity
- Guardian (theta 320-383): High sensitivity - protective data
- Meta (theta 448-511): System data - requires full consent
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List


class ConsentState(Enum):
    """
    Avatar Consent State Protocol states.

    Based on AVACHATTER ACSP specification.
    """

    FULL_CONSENT = "full"
    DIMINISHED_CONSENT = "diminished"
    SUSPENDED_CONSENT = "suspended"
    EMERGENCY_OVERRIDE = "emergency"

    @property
    def allows_write(self) -> bool:
        """Check if state allows write operations."""
        return self in (ConsentState.FULL_CONSENT, ConsentState.EMERGENCY_OVERRIDE)

    @property
    def allows_delete(self) -> bool:
        """Check if state allows delete operations."""
        return self == ConsentState.FULL_CONSENT

    @property
    def is_restricted(self) -> bool:
        """Check if state is restricted."""
        return self in (ConsentState.SUSPENDED_CONSENT, ConsentState.DIMINISHED_CONSENT)


class Sector(Enum):
    """
    Semantic sectors with consent requirements.

    Based on theta ranges (0-511 divided into 8 sectors of 64 each).
    """

    GENE = "gene"              # theta 0-63: Identity, biometric
    MEMORY = "memory"          # theta 64-127: Historical records
    WITNESS = "witness"        # theta 128-191: Attestation
    DREAM = "dream"            # theta 192-255: Creative
    BRIDGE = "bridge"          # theta 256-319: Shared
    GUARDIAN = "guardian"      # theta 320-383: Protective
    EMERGENCE = "emergence"    # theta 384-447: Transformational
    META = "meta"              # theta 448-511: System

    @classmethod
    def from_theta(cls, theta: int) -> "Sector":
        """Get sector from theta value."""
        if theta < 64:
            return cls.GENE
        elif theta < 128:
            return cls.MEMORY
        elif theta < 192:
            return cls.WITNESS
        elif theta < 256:
            return cls.DREAM
        elif theta < 320:
            return cls.BRIDGE
        elif theta < 384:
            return cls.GUARDIAN
        elif theta < 448:
            return cls.EMERGENCE
        else:
            return cls.META

    @property
    def sensitivity(self) -> str:
        """Get sensitivity level for sector."""
        high = {Sector.GENE, Sector.GUARDIAN, Sector.META}
        medium = {Sector.MEMORY, Sector.EMERGENCE}
        if self in high:
            return "high"
        elif self in medium:
            return "medium"
        else:
            return "low"

    @property
    def requires_full_consent_for_write(self) -> bool:
        """Check if sector requires full consent for writes."""
        return self.sensitivity == "high"


class GroundingZone(Enum):
    """
    Grounding zones based on phi value.

    Lower phi = more grounded (accessible)
    Higher phi = more ethereal (restricted)
    """

    GROUNDED = "grounded"        # phi 0-170
    TRANSITIONAL = "transitional" # phi 171-341
    ETHEREAL = "ethereal"        # phi 342-511

    @classmethod
    def from_phi(cls, phi: int) -> "GroundingZone":
        """Get grounding zone from phi value."""
        if phi <= 170:
            return cls.GROUNDED
        elif phi <= 341:
            return cls.TRANSITIONAL
        else:
            return cls.ETHEREAL

    @property
    def consent_threshold(self) -> ConsentState:
        """Minimum consent required for write operations."""
        if self == GroundingZone.GROUNDED:
            return ConsentState.DIMINISHED_CONSENT
        elif self == GroundingZone.TRANSITIONAL:
            return ConsentState.FULL_CONSENT
        else:
            return ConsentState.FULL_CONSENT  # Ethereal: full consent only


@dataclass(frozen=True)
class ConsentContext:
    """
    Context for consent-aware operations.

    Provides all information needed for consent checks.
    """

    state: ConsentState
    soul_id: Optional[str] = None
    session_id: Optional[str] = None
    coherence_score: float = 0.0
    emergency_justification: Optional[str] = None
    attestations: tuple = ()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for resolver context."""
        return {
            "consent": self.state.value,
            "consent_state": self.state,
            "soul_id": self.soul_id,
            "session_id": self.session_id,
            "coherence_score": self.coherence_score,
            "emergency_override": self.state == ConsentState.EMERGENCY_OVERRIDE,
            "emergency_justification": self.emergency_justification,
            "attestations": list(self.attestations),
        }

    @property
    def is_verified(self) -> bool:
        """Check if context has verified identity."""
        return self.soul_id is not None

    @property
    def is_coherent(self) -> bool:
        """Check if coherence score meets threshold (0.4)."""
        return self.coherence_score >= 0.4


@dataclass(frozen=True)
class ConsentCheck:
    """
    Result of a consent check.

    Includes detailed information about why access was allowed or denied.
    """

    allowed: bool
    state: ConsentState
    sector: Sector
    zone: GroundingZone
    reason: str
    required_state: Optional[ConsentState] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allowed": self.allowed,
            "state": self.state.value,
            "sector": self.sector.value,
            "zone": self.zone.value,
            "reason": self.reason,
            "required_state": self.required_state.value if self.required_state else None,
        }


def check_consent(
    theta: int,
    phi: int,
    operation: str,
    context: ConsentContext,
) -> ConsentCheck:
    """
    Check if an operation is allowed based on consent context.

    Args:
        theta: Angular sector (0-511)
        phi: Grounding level (0-511)
        operation: "read", "write", or "delete"
        context: Consent context with state and metadata

    Returns:
        ConsentCheck with allowed status and reason
    """
    sector = Sector.from_theta(theta)
    zone = GroundingZone.from_phi(phi)

    # Emergency override allows all operations (with justification)
    if context.state == ConsentState.EMERGENCY_OVERRIDE:
        if context.emergency_justification:
            return ConsentCheck(
                allowed=True,
                state=context.state,
                sector=sector,
                zone=zone,
                reason=f"Emergency override: {context.emergency_justification}",
            )
        else:
            return ConsentCheck(
                allowed=False,
                state=context.state,
                sector=sector,
                zone=zone,
                reason="Emergency override requires justification",
                required_state=ConsentState.EMERGENCY_OVERRIDE,
            )

    # Suspended consent: read-only, grounded zone only
    if context.state == ConsentState.SUSPENDED_CONSENT:
        if operation != "read":
            return ConsentCheck(
                allowed=False,
                state=context.state,
                sector=sector,
                zone=zone,
                reason=f"Suspended consent: {operation} not permitted",
                required_state=ConsentState.FULL_CONSENT,
            )
        if zone != GroundingZone.GROUNDED:
            return ConsentCheck(
                allowed=False,
                state=context.state,
                sector=sector,
                zone=zone,
                reason="Suspended consent: only grounded zone accessible",
                required_state=ConsentState.DIMINISHED_CONSENT,
            )

    # Diminished consent: read-only, excludes high-sensitivity sectors
    if context.state == ConsentState.DIMINISHED_CONSENT:
        if operation != "read":
            return ConsentCheck(
                allowed=False,
                state=context.state,
                sector=sector,
                zone=zone,
                reason=f"Diminished consent: {operation} not permitted",
                required_state=ConsentState.FULL_CONSENT,
            )
        if sector.sensitivity == "high":
            return ConsentCheck(
                allowed=False,
                state=context.state,
                sector=sector,
                zone=zone,
                reason=f"Diminished consent: {sector.value} sector requires full consent",
                required_state=ConsentState.FULL_CONSENT,
            )

    # Full consent: check sector and zone requirements for writes
    if context.state == ConsentState.FULL_CONSENT:
        if operation == "write":
            # High-sensitivity sectors need verified identity
            if sector.requires_full_consent_for_write and not context.is_verified:
                return ConsentCheck(
                    allowed=False,
                    state=context.state,
                    sector=sector,
                    zone=zone,
                    reason=f"Write to {sector.value} requires verified identity",
                )

            # Ethereal zone needs high coherence
            if zone == GroundingZone.ETHEREAL and not context.is_coherent:
                return ConsentCheck(
                    allowed=False,
                    state=context.state,
                    sector=sector,
                    zone=zone,
                    reason="Write to ethereal zone requires coherence >= 0.4",
                )

        if operation == "delete":
            # Delete always needs verified identity
            if not context.is_verified:
                return ConsentCheck(
                    allowed=False,
                    state=context.state,
                    sector=sector,
                    zone=zone,
                    reason="Delete requires verified identity",
                )

    # Default: allowed
    return ConsentCheck(
        allowed=True,
        state=context.state,
        sector=sector,
        zone=zone,
        reason=f"{operation} permitted in {sector.value}/{zone.value}",
    )


def create_consent_context(
    state: str = "full",
    soul_id: Optional[str] = None,
    coherence: float = 0.0,
    **kwargs: Any,
) -> ConsentContext:
    """
    Create a ConsentContext from simple parameters.

    Args:
        state: Consent state string ("full", "diminished", "suspended", "emergency")
               Also accepts legacy values: "explicit" (maps to "full"), "none" (maps to "suspended")
        soul_id: Optional verified soul ID
        coherence: Coherence score (0.0-1.0)
        **kwargs: Additional context fields

    Returns:
        ConsentContext instance
    """
    # Map legacy consent strings to new enum values
    legacy_mapping = {
        "explicit": "full",
        "none": "suspended",
        "partial": "diminished",
    }
    normalized_state = legacy_mapping.get(state, state)
    consent_state = ConsentState(normalized_state)

    return ConsentContext(
        state=consent_state,
        soul_id=soul_id,
        coherence_score=coherence,
        session_id=kwargs.get("session_id"),
        emergency_justification=kwargs.get("emergency_justification"),
        attestations=tuple(kwargs.get("attestations", [])),
    )
