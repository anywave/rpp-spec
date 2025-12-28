"""
RPP - Rotational Packet Protocol

A 28-bit semantic addressing system for consent-aware routing.

RPP IS:
- A deterministic 28-bit semantic address
- A resolver that returns allow / deny / route
- A bridge to existing storage backends

RPP IS NOT:
- A storage system
- A database
- An identity provider
- A policy DSL
- An AI system
"""

__version__ = "0.1.3"

from rpp.address import (
    RPPAddress,
    encode,
    decode,
    from_components,
    from_raw,
    is_valid_address,
    MAX_ADDRESS,
    MAX_SHELL,
    MAX_THETA,
    MAX_PHI,
    MAX_HARMONIC,
)

from rpp.resolver import (
    RPPResolver,
    ResolveResult,
    resolve,
)

__all__ = [
    # Version
    "__version__",
    # Address
    "RPPAddress",
    "encode",
    "decode",
    "from_components",
    "from_raw",
    "is_valid_address",
    "MAX_ADDRESS",
    "MAX_SHELL",
    "MAX_THETA",
    "MAX_PHI",
    "MAX_HARMONIC",
    # Resolver
    "RPPResolver",
    "ResolveResult",
    "resolve",
]
