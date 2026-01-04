"""
RPP Extended Addressing (64-bit) - LEGACY

Implements the extended address format from SPEC-EXTENDED.md:
- 2-bit shell (same as core)
- 20-bit theta (fine precision)
- 20-bit phi (fine precision)
- 10-bit harmonic
- 12-bit phase angle

Provides 2048x higher angular resolution than core addressing.

DEPRECATION NOTICE (v2.0):
  This module implements a legacy 64-bit extended format.
  The current canonical format is Ra-Canonical v2.0 (32-bit):
      [θ:5][φ:3][h:3][r:8][reserved:13]
  See spec/RPP-CANONICAL-v2.md for authoritative format.
  Use rpp.address_canonical for new implementations.
"""

from dataclasses import dataclass
from typing import Tuple

# Extended address constants
MAX_EXTENDED_ADDRESS = 0xFFFFFFFFFFFFFFFF  # 64 bits
MAX_THETA_FINE = 1048575  # 20 bits
MAX_PHI_FINE = 1048575  # 20 bits
MAX_HARMONIC_EXT = 1023  # 10 bits
MAX_PHASE = 4095  # 12 bits

# Bit positions for 64-bit extended format
EXT_SHELL_SHIFT = 62
EXT_THETA_SHIFT = 42
EXT_PHI_SHIFT = 22
EXT_HARMONIC_SHIFT = 12
EXT_PHASE_SHIFT = 0

# Masks
EXT_SHELL_MASK = 0x3
EXT_THETA_MASK = 0xFFFFF  # 20 bits
EXT_PHI_MASK = 0xFFFFF  # 20 bits
EXT_HARMONIC_MASK = 0x3FF  # 10 bits
EXT_PHASE_MASK = 0xFFF  # 12 bits


@dataclass(frozen=True)
class RPPExtendedAddress:
    """
    Immutable extended RPP address with high-precision components.

    Attributes:
        shell: Radial depth / storage tier (0-3)
        theta: Angular sector, fine precision (0-1048575)
        phi: Grounding level, fine precision (0-1048575)
        harmonic: Frequency / mode (0-1023)
        phase: Phase angle for interference (0-4095)
        raw: Original 64-bit integer
    """

    shell: int
    theta: int
    phi: int
    harmonic: int
    phase: int
    raw: int

    def __post_init__(self) -> None:
        """Validate components are in range."""
        if not (0 <= self.shell <= 3):
            raise ValueError(f"Shell must be 0-3, got {self.shell}")
        if not (0 <= self.theta <= MAX_THETA_FINE):
            raise ValueError(f"Theta must be 0-{MAX_THETA_FINE}, got {self.theta}")
        if not (0 <= self.phi <= MAX_PHI_FINE):
            raise ValueError(f"Phi must be 0-{MAX_PHI_FINE}, got {self.phi}")
        if not (0 <= self.harmonic <= MAX_HARMONIC_EXT):
            raise ValueError(f"Harmonic must be 0-{MAX_HARMONIC_EXT}, got {self.harmonic}")
        if not (0 <= self.phase <= MAX_PHASE):
            raise ValueError(f"Phase must be 0-{MAX_PHASE}, got {self.phase}")

    def __str__(self) -> str:
        return (
            f"RPPExt(shell={self.shell}, theta={self.theta}, phi={self.phi}, "
            f"harmonic={self.harmonic}, phase={self.phase}) = {self.to_hex()}"
        )

    def __repr__(self) -> str:
        return (
            f"RPPExtendedAddress(shell={self.shell}, theta={self.theta}, "
            f"phi={self.phi}, harmonic={self.harmonic}, phase={self.phase}, "
            f"raw={hex(self.raw)})"
        )

    def to_hex(self) -> str:
        """Return address as zero-padded hex string."""
        return f"0x{self.raw:016X}"

    def to_dict(self) -> dict:
        """Return address as dictionary (JSON-serializable)."""
        return {
            "shell": self.shell,
            "theta": self.theta,
            "phi": self.phi,
            "harmonic": self.harmonic,
            "phase": self.phase,
            "address": self.to_hex(),
            "theta_degrees": self.theta_degrees,
            "phi_degrees": self.phi_degrees,
            "phase_degrees": self.phase_degrees,
        }

    @property
    def theta_degrees(self) -> float:
        """Convert theta to degrees (0-360)."""
        return (self.theta / 1048576.0) * 360.0

    @property
    def phi_degrees(self) -> float:
        """Convert phi to degrees (-90 to +90)."""
        return (self.phi / 1048576.0) * 180.0 - 90.0

    @property
    def phase_degrees(self) -> float:
        """Convert phase to degrees (0-360)."""
        return (self.phase / 4096.0) * 360.0

    def to_core(self) -> int:
        """
        Truncate to 28-bit core address.

        Loses precision but maintains routing compatibility.
        """
        # Truncate 20-bit to 9-bit (take top 9 bits)
        core_theta = self.theta >> 11
        core_phi = self.phi >> 11
        # Truncate 10-bit to 8-bit
        core_harmonic = self.harmonic >> 2

        return (
            (self.shell << 26) |
            (core_theta << 17) |
            (core_phi << 8) |
            core_harmonic
        )

    @property
    def sector_name(self) -> str:
        """Return canonical sector name for theta (using core resolution)."""
        core_theta = self.theta >> 11
        if core_theta < 64:
            return "Gene"
        elif core_theta < 128:
            return "Memory"
        elif core_theta < 192:
            return "Witness"
        elif core_theta < 256:
            return "Dream"
        elif core_theta < 320:
            return "Bridge"
        elif core_theta < 384:
            return "Guardian"
        elif core_theta < 448:
            return "Emergence"
        else:
            return "Meta"

    @property
    def grounding_level(self) -> str:
        """Return grounding level name for phi (using core resolution)."""
        core_phi = self.phi >> 11
        if core_phi < 128:
            return "Grounded"
        elif core_phi < 256:
            return "Transitional"
        elif core_phi < 384:
            return "Abstract"
        else:
            return "Ethereal"


def encode_extended(
    shell: int,
    theta: int,
    phi: int,
    harmonic: int,
    phase: int = 0,
) -> int:
    """
    Encode extended RPP components into a 64-bit address.

    Args:
        shell: Radial depth (0-3)
        theta: Angular sector, fine (0-1048575)
        phi: Grounding level, fine (0-1048575)
        harmonic: Frequency/mode (0-1023)
        phase: Phase angle (0-4095)

    Returns:
        64-bit unsigned integer

    Raises:
        ValueError: If any component is out of range
    """
    if not (0 <= shell <= 3):
        raise ValueError(f"Shell must be 0-3, got {shell}")
    if not (0 <= theta <= MAX_THETA_FINE):
        raise ValueError(f"Theta must be 0-{MAX_THETA_FINE}, got {theta}")
    if not (0 <= phi <= MAX_PHI_FINE):
        raise ValueError(f"Phi must be 0-{MAX_PHI_FINE}, got {phi}")
    if not (0 <= harmonic <= MAX_HARMONIC_EXT):
        raise ValueError(f"Harmonic must be 0-{MAX_HARMONIC_EXT}, got {harmonic}")
    if not (0 <= phase <= MAX_PHASE):
        raise ValueError(f"Phase must be 0-{MAX_PHASE}, got {phase}")

    return (
        (shell << EXT_SHELL_SHIFT) |
        (theta << EXT_THETA_SHIFT) |
        (phi << EXT_PHI_SHIFT) |
        (harmonic << EXT_HARMONIC_SHIFT) |
        phase
    )


def decode_extended(address: int) -> Tuple[int, int, int, int, int]:
    """
    Decode a 64-bit extended RPP address into components.

    Args:
        address: 64-bit unsigned integer

    Returns:
        Tuple of (shell, theta, phi, harmonic, phase)
    """
    shell = (address >> EXT_SHELL_SHIFT) & EXT_SHELL_MASK
    theta = (address >> EXT_THETA_SHIFT) & EXT_THETA_MASK
    phi = (address >> EXT_PHI_SHIFT) & EXT_PHI_MASK
    harmonic = (address >> EXT_HARMONIC_SHIFT) & EXT_HARMONIC_MASK
    phase = address & EXT_PHASE_MASK

    return (shell, theta, phi, harmonic, phase)


def from_extended_components(
    shell: int,
    theta: int,
    phi: int,
    harmonic: int,
    phase: int = 0,
) -> RPPExtendedAddress:
    """
    Create an RPPExtendedAddress from components.

    Args:
        shell: Radial depth (0-3)
        theta: Angular sector, fine (0-1048575)
        phi: Grounding level, fine (0-1048575)
        harmonic: Frequency/mode (0-1023)
        phase: Phase angle (0-4095)

    Returns:
        RPPExtendedAddress with encoded raw value
    """
    raw = encode_extended(shell, theta, phi, harmonic, phase)
    return RPPExtendedAddress(
        shell=shell,
        theta=theta,
        phi=phi,
        harmonic=harmonic,
        phase=phase,
        raw=raw,
    )


def from_extended_raw(address: int) -> RPPExtendedAddress:
    """
    Create an RPPExtendedAddress from a raw 64-bit integer.

    Args:
        address: 64-bit unsigned integer

    Returns:
        RPPExtendedAddress with decoded components
    """
    shell, theta, phi, harmonic, phase = decode_extended(address)
    return RPPExtendedAddress(
        shell=shell,
        theta=theta,
        phi=phi,
        harmonic=harmonic,
        phase=phase,
        raw=address,
    )


def from_core_address(core_address: int) -> RPPExtendedAddress:
    """
    Upconvert a 28-bit core address to extended format.

    Fills extended precision bits with zeros (no interpolation).

    Args:
        core_address: 28-bit core RPP address

    Returns:
        RPPExtendedAddress with core precision only
    """
    from rpp.address import decode as decode_core

    shell, theta, phi, harmonic = decode_core(core_address)

    # Upconvert by shifting to extended bit positions
    theta_ext = theta << 11  # 9-bit to 20-bit
    phi_ext = phi << 11
    harmonic_ext = harmonic << 2  # 8-bit to 10-bit

    return from_extended_components(shell, theta_ext, phi_ext, harmonic_ext, phase=0)


def degrees_to_theta(degrees: float) -> int:
    """
    Convert 0-360 degrees to extended theta value.

    Args:
        degrees: Angle in degrees (0-360)

    Returns:
        Theta value (0-1048575)
    """
    normalized = degrees % 360.0
    return int((normalized / 360.0) * 1048576) % 1048576


def degrees_to_phi(degrees: float) -> int:
    """
    Convert -90 to +90 degrees to extended phi value.

    Args:
        degrees: Angle in degrees (-90 to +90)

    Returns:
        Phi value (0-1048575)
    """
    clamped = max(-90.0, min(90.0, degrees))
    normalized = (clamped + 90.0) / 180.0
    # Clamp to valid range to avoid wrap-around at exactly 90 degrees
    return min(int(normalized * 1048576), MAX_PHI_FINE)


def degrees_to_phase(degrees: float) -> int:
    """
    Convert 0-360 degrees to phase value.

    Args:
        degrees: Angle in degrees (0-360)

    Returns:
        Phase value (0-4095)
    """
    normalized = degrees % 360.0
    return int((normalized / 360.0) * 4096) % 4096


def phase_interference(phase_a: int, phase_b: int) -> float:
    """
    Calculate interference amplitude for two phase angles.

    Args:
        phase_a: First phase (0-4095)
        phase_b: Second phase (0-4095)

    Returns:
        Amplitude factor (0.0 to 2.0)
        - 2.0: Constructive (same phase)
        - 0.0: Destructive (180 degrees apart)
        - 1.414: Quadrature (90 degrees apart)
    """
    import math

    # Convert to radians
    angle_a = (phase_a / 4096.0) * 2 * math.pi
    angle_b = (phase_b / 4096.0) * 2 * math.pi

    # Phase difference
    diff = angle_a - angle_b

    # Amplitude: 2 * cos(diff/2) for two unit vectors
    # At 0 diff: 2.0, at pi diff: 0.0, at pi/2 diff: sqrt(2)
    amplitude = abs(2.0 * math.cos(diff / 2.0))

    return amplitude
