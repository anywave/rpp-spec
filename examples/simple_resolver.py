#!/usr/bin/env python3
"""
RPP Simple Resolver Example
============================

Demonstrates a minimal resolver implementation that maps RPP addresses
to filesystem paths, showing the bridge architecture concept.

Usage:
    python examples/simple_resolver.py
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional

# Add reference implementation to path
sys.path.insert(0, str(Path(__file__).parent.parent / "reference" / "python"))

from rpp_address import decode, from_components, RPPAddress


class ConsentState(Enum):
    """Consent states for access control."""
    FULL_CONSENT = "full"
    DIMINISHED_CONSENT = "diminished"
    SUSPENDED_CONSENT = "suspended"
    EMERGENCY_OVERRIDE = "emergency"


@dataclass
class ResolvedPath:
    """Result of resolving an RPP address."""
    backend: str
    path: str
    readable: bool
    writable: bool
    reason: Optional[str] = None


class SimpleResolver:
    """
    Minimal RPP resolver demonstrating the bridge architecture.

    This resolver maps RPP addresses to filesystem paths based on
    shell (storage tier) and theta (sector).
    """

    def __init__(self, base_path: str = "/data"):
        self.base_path = Path(base_path)

        # Shell to directory mapping
        self.shell_dirs = {
            0: "hot",      # Fast cache
            1: "warm",     # Working storage
            2: "cold",     # Persistent storage
            3: "frozen",   # Archive
        }

        # Theta ranges to sector names
        self.sectors = [
            (0, 64, "gene"),
            (64, 128, "memory"),
            (128, 192, "witness"),
            (192, 256, "dream"),
            (256, 320, "bridge"),
            (320, 384, "guardian"),
            (384, 448, "emergence"),
            (448, 512, "meta"),
        ]

        # Consent requirements by sector
        self.sector_consent = {
            "gene": ConsentState.FULL_CONSENT,
            "memory": ConsentState.DIMINISHED_CONSENT,
            "witness": ConsentState.DIMINISHED_CONSENT,
            "dream": ConsentState.DIMINISHED_CONSENT,
            "bridge": ConsentState.DIMINISHED_CONSENT,
            "guardian": ConsentState.FULL_CONSENT,
            "emergence": ConsentState.FULL_CONSENT,
            "meta": ConsentState.DIMINISHED_CONSENT,
        }

    def get_sector_name(self, theta: int) -> str:
        """Get sector name from theta value."""
        for start, end, name in self.sectors:
            if start <= theta < end:
                return name
        return "unknown"

    def check_consent(
        self,
        sector: str,
        current_consent: ConsentState,
        operation: str
    ) -> tuple[bool, str]:
        """
        Check if current consent level allows operation.

        Returns (allowed, reason).
        """
        required = self.sector_consent.get(sector, ConsentState.FULL_CONSENT)

        consent_levels = {
            ConsentState.SUSPENDED_CONSENT: 0,
            ConsentState.DIMINISHED_CONSENT: 1,
            ConsentState.FULL_CONSENT: 2,
            ConsentState.EMERGENCY_OVERRIDE: 3,
        }

        current_level = consent_levels[current_consent]
        required_level = consent_levels[required]

        # Writes require higher consent
        if operation == "write":
            required_level += 1

        if current_level >= required_level:
            return True, "Consent sufficient"
        else:
            return False, f"Requires {required.value}, have {current_consent.value}"

    def resolve(
        self,
        address: int,
        consent: ConsentState,
        operation: str = "read"
    ) -> ResolvedPath:
        """
        Resolve an RPP address to a filesystem path.

        Args:
            address: 28-bit RPP address
            consent: Current consent state
            operation: "read" or "write"

        Returns:
            ResolvedPath with backend, path, and access permissions
        """
        # Decode address
        shell, theta, phi, harmonic = decode(address)

        # Get mappings
        tier = self.shell_dirs.get(shell, "unknown")
        sector = self.get_sector_name(theta)

        # Build path
        # Format: /data/{tier}/{sector}/{theta}_{phi}_{harmonic}.dat
        filename = f"{theta}_{phi}_{harmonic}.dat"
        path = self.base_path / tier / sector / filename

        # Check consent
        allowed, reason = self.check_consent(sector, consent, operation)

        return ResolvedPath(
            backend="filesystem",
            path=str(path),
            readable=allowed if operation == "read" else False,
            writable=allowed if operation == "write" else False,
            reason=reason if not allowed else None,
        )


def demo_resolver():
    """Demonstrate the simple resolver."""
    print("=" * 60)
    print("RPP Simple Resolver Demonstration")
    print("=" * 60)

    resolver = SimpleResolver(base_path="/data/rpp")

    # Test addresses
    test_cases = [
        ("User identity", from_components(0, 32, 64, 128)),
        ("Conversation log", from_components(1, 96, 192, 64)),
        ("Audit record", from_components(2, 160, 96, 128)),
        ("Guardian rules", from_components(0, 352, 64, 128)),
    ]

    print("\n--- With FULL_CONSENT ---\n")

    for desc, addr in test_cases:
        result = resolver.resolve(addr.raw, ConsentState.FULL_CONSENT, "read")
        print(f"{desc}:")
        print(f"  Address: {addr.to_hex()}")
        print(f"  Resolved: {result.path}")
        print(f"  Readable: {result.readable}")
        print()

    print("--- With DIMINISHED_CONSENT ---\n")

    for desc, addr in test_cases:
        result = resolver.resolve(addr.raw, ConsentState.DIMINISHED_CONSENT, "read")
        status = "✓" if result.readable else f"✗ ({result.reason})"
        print(f"{desc}: {status}")

    print("\n--- Write Operations with DIMINISHED_CONSENT ---\n")

    for desc, addr in test_cases:
        result = resolver.resolve(addr.raw, ConsentState.DIMINISHED_CONSENT, "write")
        status = "✓" if result.writable else f"✗ ({result.reason})"
        print(f"{desc}: {status}")


def demo_address_routing():
    """Show how different addresses route to different locations."""
    print("\n" + "=" * 60)
    print("Address Routing Examples")
    print("=" * 60)

    resolver = SimpleResolver(base_path="/storage")

    print("\nShowing how shell affects storage tier:\n")

    # Same logical data, different shells
    theta, phi, harmonic = 100, 200, 128

    for shell in range(4):
        addr = from_components(shell, theta, phi, harmonic)
        result = resolver.resolve(addr.raw, ConsentState.FULL_CONSENT)
        print(f"Shell {shell} ({addr.shell_name:6s}): {result.path}")

    print("\nShowing how theta affects sector:\n")

    # Same shell, different sectors
    shell, phi, harmonic = 0, 200, 128

    for theta in [32, 96, 160, 352, 480]:
        addr = from_components(shell, theta, phi, harmonic)
        result = resolver.resolve(addr.raw, ConsentState.FULL_CONSENT)
        sector = resolver.get_sector_name(theta)
        print(f"Theta {theta:3d} ({sector:10s}): {result.path}")


def main():
    """Run resolver demonstrations."""
    demo_resolver()
    demo_address_routing()

    print("\n" + "=" * 60)
    print("Resolver demonstration complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
