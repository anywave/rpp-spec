"""
RPP Address Encoding/Decoding

Implements the 28-bit RPP address format:
  [31:28] Reserved (must be 0)
  [27:26] Shell (2 bits, 0-3)
  [25:17] Theta (9 bits, 0-511)
  [16:8]  Phi (9 bits, 0-511)
  [7:0]   Harmonic (8 bits, 0-255)

This module is pure Python with no external dependencies.
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
        shell: Radial depth / storage tier (0-3)
        theta: Angular sector (0-511)
        phi: Grounding level (0-511)
        harmonic: Frequency / mode (0-255)
        raw: Original 28-bit integer
    """

    shell: int
    theta: int
    phi: int
    harmonic: int
    raw: int

    def __post_init__(self) -> None:
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
        return f"RPP(shell={self.shell}, theta={self.theta}, phi={self.phi}, harmonic={self.harmonic}) = {self.to_hex()}"

    def __repr__(self) -> str:
        return f"RPPAddress(shell={self.shell}, theta={self.theta}, phi={self.phi}, harmonic={self.harmonic}, raw={hex(self.raw)})"

    def to_hex(self) -> str:
        """Return address as zero-padded hex string."""
        return f"0x{self.raw:07X}"

    def to_dict(self) -> dict:
        """Return address as dictionary (JSON-serializable)."""
        return {
            "shell": self.shell,
            "theta": self.theta,
            "phi": self.phi,
            "harmonic": self.harmonic,
            "address": self.to_hex(),
        }

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
        theta: Angular sector (0-511)
        phi: Grounding level (0-511)
        harmonic: Frequency/mode (0-255)

    Returns:
        28-bit unsigned integer

    Raises:
        ValueError: If any component is out of range
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
        theta: Angular sector (0-511)
        phi: Grounding level (0-511)
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


def is_valid_address(address: int) -> bool:
    """
    Check if an integer is a valid 28-bit RPP address.

    Args:
        address: Integer to validate

    Returns:
        True if valid, False otherwise
    """
    return isinstance(address, int) and 0 <= address <= MAX_ADDRESS


def parse_address(value: str) -> int:
    """
    Parse an address from string (hex or decimal).

    Args:
        value: String like "0x1234ABC" or "19141308"

    Returns:
        Integer address

    Raises:
        ValueError: If parsing fails or address is invalid
    """
    value = value.strip()
    try:
        if value.lower().startswith("0x"):
            address = int(value, 16)
        else:
            address = int(value)
    except ValueError:
        raise ValueError(f"Cannot parse address: {value}")

    if not is_valid_address(address):
        raise ValueError(f"Address out of range: {hex(address)}")

    return address
