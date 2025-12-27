#!/usr/bin/env python3
"""
RPP Basic Usage Examples
========================

Demonstrates fundamental RPP address encoding, decoding, and interpretation.

Usage:
    python examples/basic_usage.py
"""

import sys
from pathlib import Path

# Add reference implementation to path
sys.path.insert(0, str(Path(__file__).parent.parent / "reference" / "python"))

from rpp_address import (
    encode,
    decode,
    from_components,
    from_raw,
    degrees_to_theta,
    latitude_to_phi,
    RPPAddress,
)


def example_basic_encoding():
    """Basic encoding and decoding."""
    print("=" * 60)
    print("Example 1: Basic Encoding and Decoding")
    print("=" * 60)

    # Encode an address
    shell = 0      # Hot cache
    theta = 45     # Gene sector region
    phi = 128      # Transitional grounding
    harmonic = 64  # Summary resolution

    address = encode(shell, theta, phi, harmonic)
    print(f"\nInput: shell={shell}, theta={theta}, phi={phi}, harmonic={harmonic}")
    print(f"Encoded: {hex(address)} (decimal: {address})")

    # Decode it back
    s, t, p, h = decode(address)
    print(f"Decoded: shell={s}, theta={t}, phi={p}, harmonic={h}")

    # Verify roundtrip
    assert (s, t, p, h) == (shell, theta, phi, harmonic)
    print("✓ Roundtrip verified")


def example_rpp_address_object():
    """Using the RPPAddress dataclass."""
    print("\n" + "=" * 60)
    print("Example 2: RPPAddress Object")
    print("=" * 60)

    # Create from components
    addr = from_components(shell=1, theta=100, phi=256, harmonic=128)
    print(f"\nCreated: {addr}")
    print(f"  Hex: {addr.to_hex()}")
    print(f"  Sector: {addr.sector_name}")
    print(f"  Grounding: {addr.grounding_level}")
    print(f"  Shell: {addr.shell_name}")

    # Create from raw address
    addr2 = from_raw(0x05A8040)
    print(f"\nFrom raw 0x05A8040: {addr2}")
    print(f"  Sector: {addr2.sector_name}")
    print(f"  Grounding: {addr2.grounding_level}")


def example_sector_mapping():
    """Demonstrate sector classification."""
    print("\n" + "=" * 60)
    print("Example 3: Sector Classification")
    print("=" * 60)

    sectors = [
        (32, "Gene - Core identity"),
        (96, "Memory - Experiences"),
        (160, "Witness - Observations"),
        (224, "Dream - Speculation"),
        (288, "Bridge - Integration"),
        (352, "Guardian - Protection"),
        (416, "Emergence - Discovery"),
        (480, "Meta - Self-reference"),
    ]

    print("\nSector mapping by theta value:")
    print("-" * 40)

    for theta, description in sectors:
        addr = from_components(shell=0, theta=theta, phi=256, harmonic=128)
        print(f"  theta={theta:3d} → {addr.sector_name:10s} ({description})")


def example_grounding_levels():
    """Demonstrate grounding level interpretation."""
    print("\n" + "=" * 60)
    print("Example 4: Grounding Levels")
    print("=" * 60)

    levels = [
        (64, "Physical sensor data"),
        (192, "Behavioral patterns"),
        (320, "Conceptual inference"),
        (448, "Emergent speculation"),
    ]

    print("\nGrounding levels by phi value:")
    print("-" * 40)

    for phi, description in levels:
        addr = from_components(shell=0, theta=128, phi=phi, harmonic=128)
        print(f"  phi={phi:3d} → {addr.grounding_level:12s} ({description})")


def example_shell_tiers():
    """Demonstrate shell/tier interpretation."""
    print("\n" + "=" * 60)
    print("Example 5: Storage Tiers (Shell)")
    print("=" * 60)

    tiers = [
        (0, "Immediate access, cache"),
        (1, "Working memory, session"),
        (2, "Persistent, database"),
        (3, "Archive, cold storage"),
    ]

    print("\nStorage tiers by shell value:")
    print("-" * 40)

    for shell, description in tiers:
        addr = from_components(shell=shell, theta=128, phi=256, harmonic=128)
        print(f"  shell={shell} → {addr.shell_name:6s} ({description})")


def example_angular_conversion():
    """Demonstrate degree to theta/phi conversion."""
    print("\n" + "=" * 60)
    print("Example 6: Angular Conversions")
    print("=" * 60)

    print("\nDegrees to Theta (longitude):")
    for deg in [0, 45, 90, 180, 270, 359]:
        theta = degrees_to_theta(deg)
        print(f"  {deg:3d}° → theta={theta}")

    print("\nLatitude to Phi (elevation):")
    for lat in [-90, -45, 0, 45, 90]:
        phi = latitude_to_phi(lat)
        print(f"  {lat:+3d}° → phi={phi}")


def example_address_space_coverage():
    """Show address space coverage."""
    print("\n" + "=" * 60)
    print("Example 7: Address Space Overview")
    print("=" * 60)

    print("\nRPP Address Space:")
    print(f"  Total addresses: 2^28 = {2**28:,}")
    print(f"  Maximum address: 0x{0x0FFFFFFF:07X}")
    print()
    print("  Field breakdown:")
    print(f"    Shell:    4 values (2 bits)")
    print(f"    Theta:  512 values (9 bits)")
    print(f"    Phi:    512 values (9 bits)")
    print(f"    Harmonic: 256 values (8 bits)")
    print()
    print(f"  Total: 4 × 512 × 512 × 256 = {4 * 512 * 512 * 256:,}")


def example_practical_addresses():
    """Show practical address examples."""
    print("\n" + "=" * 60)
    print("Example 8: Practical Address Examples")
    print("=" * 60)

    examples = [
        ("User identity hash", 0, 32, 64, 128, "Gene/Grounded/Standard"),
        ("Conversation memory", 1, 96, 192, 64, "Memory/Transitional/Summary"),
        ("Audit log entry", 2, 160, 96, 128, "Witness/Grounded/Standard"),
        ("Prediction model", 0, 224, 384, 192, "Dream/Ethereal/Extended"),
        ("API translation", 0, 288, 256, 64, "Bridge/Abstract/Summary"),
        ("Consent rules", 0, 352, 64, 128, "Guardian/Grounded/Standard"),
        ("Anomaly detected", 0, 416, 448, 255, "Emergence/Ethereal/Maximum"),
        ("System metrics", 0, 480, 128, 32, "Meta/Transitional/Minimal"),
    ]

    print("\nPractical address examples:")
    print("-" * 70)
    print(f"{'Description':<22} {'Address':>12} {'Interpretation':<30}")
    print("-" * 70)

    for desc, shell, theta, phi, harmonic, interp in examples:
        addr = from_components(shell, theta, phi, harmonic)
        print(f"{desc:<22} {addr.to_hex():>12} {interp:<30}")


def main():
    """Run all examples."""
    print("\n" + "#" * 60)
    print("#" + " RPP (Rotational Packet Protocol) Examples ".center(58) + "#")
    print("#" * 60)

    example_basic_encoding()
    example_rpp_address_object()
    example_sector_mapping()
    example_grounding_levels()
    example_shell_tiers()
    example_angular_conversion()
    example_address_space_coverage()
    example_practical_addresses()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
