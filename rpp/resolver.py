"""
RPP Resolver (Legacy v1.0)

DEPRECATED: This module implements the legacy 28-bit address format.
For new implementations, use resolver_canonical.py which implements
the Ra-Canonical v2.0 (32-bit) format.

See: rpp/resolver_canonical.py for the current format.
See: spec/RESOLVER.md for resolver architecture documentation.

The resolver translates RPP addresses into routing decisions.
It returns exactly: allowed (bool), route (str or null), reason (str).

This is the core of RPP's bridge architecture - it routes TO storage,
it does not provide storage itself.

Consent integration:
- Uses ACSP (Avatar Consent State Protocol) states
- Checks sector sensitivity and grounding zone
- Requires verified identity for high-sensitivity operations
"""

import warnings

warnings.warn(
    "rpp.resolver uses legacy 28-bit format. Use rpp.resolver_canonical for Ra-Canonical v2.0.",
    DeprecationWarning,
    stacklevel=2
)

from dataclasses import dataclass
from typing import Optional, Dict, Any, Protocol
from rpp.address import from_raw, RPPAddress, is_valid_address
from rpp.consent import (
    ConsentState,
    ConsentContext,
    check_consent,
    create_consent_context,
)


@dataclass(frozen=True)
class ResolveResult:
    """
    Result of resolving an RPP address.

    Attributes:
        allowed: Whether the operation is permitted
        route: Backend route path (null if denied or no route)
        reason: Human-readable explanation
    """

    allowed: bool
    route: Optional[str]
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        """Return as JSON-serializable dictionary."""
        return {
            "allowed": self.allowed,
            "route": self.route,
            "reason": self.reason,
        }

    def to_line(self) -> str:
        """Return as single-line plain text."""
        route_str = self.route if self.route else "null"
        return f"allowed={self.allowed} route={route_str} reason={self.reason}"


class BackendAdapter(Protocol):
    """Protocol for storage backend adapters."""

    name: str

    def is_available(self) -> bool:
        """Check if backend is available."""
        ...


class RPPResolver:
    """
    RPP address resolver.

    Resolves addresses to allow/deny/route decisions based on:
    - Shell (storage tier)
    - Theta (sector - determines consent requirements)
    - Phi (grounding level - determines access restrictions)
    - Registered backend adapters
    """

    def __init__(self) -> None:
        self._adapters: Dict[int, BackendAdapter] = {}
        self._default_shell_routes = {
            0: "memory",      # Hot: in-memory
            1: "filesystem",  # Warm: local disk
            2: "archive",     # Cold: archive storage
            3: "glacier",     # Frozen: deep archive
        }

    def register_adapter(self, shell: int, adapter: BackendAdapter) -> None:
        """Register a backend adapter for a shell tier."""
        if not (0 <= shell <= 3):
            raise ValueError(f"Shell must be 0-3, got {shell}")
        self._adapters[shell] = adapter

    def resolve(
        self,
        address: int,
        operation: str = "read",
        context: Optional[Dict[str, Any]] = None,
    ) -> ResolveResult:
        """
        Resolve an RPP address to a routing decision.

        Args:
            address: 28-bit RPP address
            operation: "read", "write", "delete"
            context: Optional context (consent level, etc.)

        Returns:
            ResolveResult with allowed, route, and reason
        """
        context = context or {}

        # Validate address
        if not is_valid_address(address):
            return ResolveResult(
                allowed=False,
                route=None,
                reason="Invalid address: must be 0-0x0FFFFFFF",
            )

        # Decode address
        addr = from_raw(address)

        # Check consent requirements based on phi
        consent_result = self._check_consent(addr, operation, context)
        if consent_result is not None:
            return consent_result

        # Determine route based on shell
        route = self._get_route(addr)
        if route is None:
            return ResolveResult(
                allowed=False,
                route=None,
                reason=f"No backend available for shell {addr.shell}",
            )

        # Build full path
        path = self._build_path(addr, route)

        return ResolveResult(
            allowed=True,
            route=path,
            reason=f"{operation} permitted via {route}",
        )

    def _check_consent(
        self,
        addr: RPPAddress,
        operation: str,
        context: Dict[str, Any],
    ) -> Optional[ResolveResult]:
        """
        Check consent requirements using ACSP consent state protocol.

        Uses the consent module for comprehensive checks:
        - Consent state (full, diminished, suspended, emergency)
        - Sector sensitivity (gene, guardian, meta = high)
        - Grounding zone (grounded, transitional, ethereal)
        - Identity verification for high-sensitivity operations

        Returns None if consent is sufficient, ResolveResult if denied.
        """
        # Build consent context from raw context dict
        if "consent_state" in context and isinstance(context["consent_state"], ConsentState):
            # Already have a ConsentState object
            consent_ctx = ConsentContext(
                state=context["consent_state"],
                soul_id=context.get("soul_id"),
                coherence_score=context.get("coherence_score", 0.0),
                session_id=context.get("session_id"),
                emergency_justification=context.get("emergency_justification"),
            )
        else:
            # Parse from string consent value
            consent_str = context.get("consent", "full")
            consent_ctx = create_consent_context(
                state=consent_str,
                soul_id=context.get("soul_id"),
                coherence=context.get("coherence_score", 0.0),
                session_id=context.get("session_id"),
                emergency_justification=context.get("emergency_justification"),
            )

        # Legacy emergency override handling
        if context.get("emergency_override") is True:
            consent_ctx = ConsentContext(
                state=ConsentState.EMERGENCY_OVERRIDE,
                soul_id=consent_ctx.soul_id,
                coherence_score=consent_ctx.coherence_score,
                emergency_justification=context.get("emergency_justification", "Legacy override"),
            )

        # Perform consent check
        check = check_consent(addr.theta, addr.phi, operation, consent_ctx)

        if not check.allowed:
            return ResolveResult(
                allowed=False,
                route=None,
                reason=check.reason,
            )

        return None

    def _get_route(self, addr: RPPAddress) -> Optional[str]:
        """Get the backend route for an address based on shell."""
        # Check for registered adapter
        if addr.shell in self._adapters:
            adapter = self._adapters[addr.shell]
            if adapter.is_available():
                return adapter.name

        # Fall back to default route
        return self._default_shell_routes.get(addr.shell)

    def _build_path(self, addr: RPPAddress, backend: str) -> str:
        """Build the full route path."""
        return f"{backend}://{addr.sector_name.lower()}/{addr.grounding_level.lower()}/{addr.theta}_{addr.phi}_{addr.harmonic}"


# Module-level convenience function
_default_resolver: Optional[RPPResolver] = None


def get_resolver() -> RPPResolver:
    """Get or create the default resolver instance."""
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = RPPResolver()
    return _default_resolver


def resolve(
    address: int,
    operation: str = "read",
    context: Optional[Dict[str, Any]] = None,
) -> ResolveResult:
    """
    Resolve an RPP address using the default resolver.

    Args:
        address: 28-bit RPP address
        operation: "read", "write", "delete"
        context: Optional context (consent level, etc.)

    Returns:
        ResolveResult with allowed, route, and reason
    """
    return get_resolver().resolve(address, operation, context)
