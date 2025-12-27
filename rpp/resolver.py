"""
RPP Resolver

The resolver translates RPP addresses into routing decisions.
It returns exactly: allowed (bool), route (str or null), reason (str).

This is the core of RPP's bridge architecture - it routes TO storage,
it does not provide storage itself.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Protocol
from rpp.address import from_raw, RPPAddress, is_valid_address


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
        Check consent requirements based on phi (grounding level).

        Low phi (0-127): Grounded - more accessible
        High phi (384-511): Ethereal - restricted

        Returns None if consent is sufficient, ResolveResult if denied.
        """
        # Emergency override bypasses all consent checks
        if context.get("emergency_override") is True:
            return None

        # Very high phi blocks all writes except with emergency override (checked above)
        if addr.phi >= 480 and operation == "write":
            return ResolveResult(
                allowed=False,
                route=None,
                reason=f"Write to high ethereal (phi={addr.phi}) blocked without emergency override",
            )

        # High phi requires explicit consent for writes
        if addr.phi >= 384 and operation == "write":
            consent = context.get("consent", "none")
            if consent not in ("full", "explicit"):
                return ResolveResult(
                    allowed=False,
                    route=None,
                    reason=f"Write to ethereal zone (phi={addr.phi}) requires explicit consent",
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
