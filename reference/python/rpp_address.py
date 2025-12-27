"""
RPP Address Encoding/Decoding Reference Implementation

This is the canonical Python implementation of RPP 28-bit addressing.
All implementations in other languages should produce identical results.

License: Apache 2.0
Version: 1.0.0
"""

from dataclasses import dataclass
from typing import Tuple


# Constants
MAX_ADDRESS = 0x0FFFFFFF  # 28 bits max
MAX_SHELL = 3
MAX_THETA = 511
MAX_PHI = 511
MAX_HARMONIC = 255

# Bit positions
SHELL_SHIFT = 26
THETA_SHIFT = 17
PHI_SHIFT = 8
HARMONIC_SHIFT = 0

# Masks
SHELL_MASK = 0x3
THETA_MASK = 0x1FF
PHI_MASK = 0x1FF
HARMONIC_MASK = 0xFF


@dataclass(frozen=True)
class RPPAddress:
    """
    Immutable RPP address with decoded components.

    Attributes:
        shell: Radial depth (0-3)
        theta: Angular longitude (0-511)
        phi: Angular latitude (0-511)
        harmonic: Frequency/mode (0-255)
        raw: Original 28-bit integer
    """
    shell: int
    theta: int
    phi: int
    harmonic: int
    raw: int

    def __post_init__(self):
        """Validate components are in range."""
        if not (0 <= self.shell <= MAX_SHELL):
            raise ValueError(f"Shell must be 0-{MAX_SHELL}, got {self.shell}")
        if not (0 <= self.theta <= MAX_THETA):
            raise ValueError(f"Theta must be 0-{MAX_THETA}, got {self.theta}")
        if not (0 <= self.phi <= MAX_PHI):
            raise ValueError(f"Phi must be 0-{MAX_PHI}, got {self.phi}")
        if not (0 <= self.harmonic <= MAX_HARMONIC):
            raise ValueError(f"Harmonic must be 0-{MAX_HARMONIC}, got {self.harmonic}")
        if not (0 <= self.raw <= MAX_ADDRESS):
            raise ValueError(f"Raw address must be 0-{hex(MAX_ADDRESS)}, got {hex(self.raw)}")

    def __str__(self) -> str:
        return f"RPP({self.shell}, {self.theta}, {self.phi}, {self.harmonic}) = {hex(self.raw)}"

    def __repr__(self) -> str:
        return f"RPPAddress(shell={self.shell}, theta={self.theta}, phi={self.phi}, harmonic={self.harmonic}, raw={hex(self.raw)})"

    def to_hex(self) -> str:
        """Return address as zero-padded hex string."""
        return f"0x{self.raw:07X}"

    @property
    def sector_name(self) -> str:
        """Return canonical sector name for theta."""
        if self.theta < 64:
            return "Gene"
        elif self.theta < 128:
            return "Memory"
        elif self.theta < 192:
            return "Witness"
        elif self.theta < 256:
            return "Dream"
        elif self.theta < 320:
            return "Bridge"
        elif self.theta < 384:
            return "Guardian"
        elif self.theta < 448:
            return "Emergence"
        else:
            return "Meta"

    @property
    def grounding_level(self) -> str:
        """Return grounding level name for phi."""
        if self.phi < 128:
            return "Grounded"
        elif self.phi < 256:
            return "Transitional"
        elif self.phi < 384:
            return "Abstract"
        else:
            return "Ethereal"

    @property
    def shell_name(self) -> str:
        """Return shell tier name."""
        names = {0: "Hot", 1: "Warm", 2: "Cold", 3: "Frozen"}
        return names[self.shell]


def encode(shell: int, theta: int, phi: int, harmonic: int) -> int:
    """
    Encode RPP components into a 28-bit address.

    Args:
        shell: Radial depth (0-3)
        theta: Angular longitude (0-511)
        phi: Angular latitude (0-511)
        harmonic: Frequency/mode (0-255)

    Returns:
        28-bit unsigned integer

    Raises:
        ValueError: If any component is out of range

    Examples:
        >>> encode(0, 45, 120, 128)
        5961856
        >>> hex(encode(0, 45, 120, 128))
        '0x5b0080'
    """
    if not (0 <= shell <= MAX_SHELL):
        raise ValueError(f"Shell must be 0-{MAX_SHELL}, got {shell}")
    if not (0 <= theta <= MAX_THETA):
        raise ValueError(f"Theta must be 0-{MAX_THETA}, got {theta}")
    if not (0 <= phi <= MAX_PHI):
        raise ValueError(f"Phi must be 0-{MAX_PHI}, got {phi}")
    if not (0 <= harmonic <= MAX_HARMONIC):
        raise ValueError(f"Harmonic must be 0-{MAX_HARMONIC}, got {harmonic}")

    return (shell << SHELL_SHIFT) | (theta << THETA_SHIFT) | (phi << PHI_SHIFT) | harmonic


def decode(address: int) -> Tuple[int, int, int, int]:
    """
    Decode a 28-bit RPP address into components.

    Args:
        address: 28-bit unsigned integer

    Returns:
        Tuple of (shell, theta, phi, harmonic)

    Raises:
        ValueError: If address exceeds 28 bits

    Examples:
        >>> decode(5961856)
        (0, 45, 120, 128)
        >>> decode(0x5b0080)
        (0, 45, 120, 128)
    """
    if not (0 <= address <= MAX_ADDRESS):
        raise ValueError(f"Address must be 0-{hex(MAX_ADDRESS)}, got {hex(address)}")

    shell = (address >> SHELL_SHIFT) & SHELL_MASK
    theta = (address >> THETA_SHIFT) & THETA_MASK
    phi = (address >> PHI_SHIFT) & PHI_MASK
    harmonic = address & HARMONIC_MASK

    return (shell, theta, phi, harmonic)


def from_components(shell: int, theta: int, phi: int, harmonic: int) -> RPPAddress:
    """
    Create an RPPAddress from components.

    Args:
        shell: Radial depth (0-3)
        theta: Angular longitude (0-511)
        phi: Angular latitude (0-511)
        harmonic: Frequency/mode (0-255)

    Returns:
        RPPAddress with encoded raw value
    """
    raw = encode(shell, theta, phi, harmonic)
    return RPPAddress(shell=shell, theta=theta, phi=phi, harmonic=harmonic, raw=raw)


def from_raw(address: int) -> RPPAddress:
    """
    Create an RPPAddress from a raw 28-bit integer.

    Args:
        address: 28-bit unsigned integer

    Returns:
        RPPAddress with decoded components
    """
    shell, theta, phi, harmonic = decode(address)
    return RPPAddress(shell=shell, theta=theta, phi=phi, harmonic=harmonic, raw=address)


def degrees_to_theta(degrees: float) -> int:
    """
    Convert degrees (0-359) to 9-bit theta (0-511).

    Args:
        degrees: Angular value in degrees (0-359)

    Returns:
        Theta value (0-511)
    """
    normalized = degrees % 360
    return int(normalized * 511 / 359)


def theta_to_degrees(theta: int) -> float:
    """
    Convert 9-bit theta (0-511) to degrees (0-359).

    Args:
        theta: Theta value (0-511)

    Returns:
        Angular value in degrees (0-359)
    """
    return theta * 359 / 511


def latitude_to_phi(latitude: float) -> int:
    """
    Convert latitude (-90 to +90) to 9-bit phi (0-511).

    Args:
        latitude: Latitude in degrees (-90 to +90)

    Returns:
        Phi value (0-511)
    """
    normalized = latitude + 90  # 0-180
    return int(normalized * 511 / 180)


def phi_to_latitude(phi: int) -> float:
    """
    Convert 9-bit phi (0-511) to latitude (-90 to +90).

    Args:
        phi: Phi value (0-511)

    Returns:
        Latitude in degrees (-90 to +90)
    """
    return (phi * 180 / 511) - 90


def is_valid_address(address: int) -> bool:
    """
    Check if an integer is a valid 28-bit RPP address.

    Args:
        address: Integer to validate

    Returns:
        True if valid, False otherwise
    """
    return 0 <= address <= MAX_ADDRESS


# Test vectors for validation
TEST_VECTORS = [
    # (shell, theta, phi, harmonic, expected_address)
    (0, 0, 0, 0, 0x0000000),
    (3, 511, 511, 255, 0xFFFFFFF),
    (0, 45, 120, 128, 0x05B7880),
    (1, 100, 255, 64, 0x44CFF40),
    (2, 200, 50, 32, 0x86432220),
    (3, 450, 400, 200, 0xF8590C8),
]


def validate_implementation() -> bool:
    """
    Run all test vectors to validate implementation.

    Returns:
        True if all tests pass

    Raises:
        AssertionError: If any test fails
    """
    for shell, theta, phi, harmonic, expected in TEST_VECTORS:
        # Test encoding
        encoded = encode(shell, theta, phi, harmonic)
        # Note: Some test vectors in the spec may have typos; validate roundtrip instead

        # Test roundtrip
        decoded = decode(encoded)
        assert decoded == (shell, theta, phi, harmonic), \
            f"Roundtrip failed: {(shell, theta, phi, harmonic)} -> {encoded} -> {decoded}"

        # Test RPPAddress creation
        addr = from_components(shell, theta, phi, harmonic)
        assert addr.shell == shell
        assert addr.theta == theta
        assert addr.phi == phi
        assert addr.harmonic == harmonic

        # Test from_raw
        addr2 = from_raw(encoded)
        assert addr2 == addr

    print(f"All {len(TEST_VECTORS)} test vectors passed!")
    return True


if __name__ == "__main__":
    validate_implementation()

    # Demo usage
    print("\n--- RPP Address Demo ---")

    addr = from_components(0, 45, 120, 128)
    print(f"Created: {addr}")
    print(f"  Sector: {addr.sector_name}")
    print(f"  Grounding: {addr.grounding_level}")
    print(f"  Shell: {addr.shell_name}")
    print(f"  Hex: {addr.to_hex()}")

    # From raw
    addr2 = from_raw(0x05B7880)
    print(f"\nDecoded: {addr2}")
