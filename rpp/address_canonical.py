"""
RPP Canonical Address v1.0-RaCanonical

Ra-derived address implementation for SPIRAL routing.
This module integrates with ra_system constants and provides
the foundational routing vector for all SPIRAL-based systems.

Reference: RPP v1.0-RaCanonical Specification
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Final, ClassVar
import struct

# =============================================================================
# Ra System Integration
# =============================================================================

try:
    from ra_system.repitans import Repitan, all_repitans  # noqa: F401
    from ra_system.rac import RacLevel, rac_value, all_rac_levels  # noqa: F401
    from ra_system.omega import OmegaFormat, all_omega_formats, harmonic_from_omega  # noqa: F401
    from ra_system.constants import ANKH
    RA_SYSTEM_AVAILABLE = True
except ImportError:
    RA_SYSTEM_AVAILABLE = False
    ANKH = 5.08938  # Fallback constant


# =============================================================================
# Constants (Ra-Derived)
# =============================================================================

# Bit field sizes
THETA_BITS: Final[int] = 5
PHI_BITS: Final[int] = 3
OMEGA_BITS: Final[int] = 3
RADIUS_BITS: Final[int] = 8
RESERVED_BITS: Final[int] = 13

# Total address size
ADDRESS_BITS: Final[int] = 32
ADDRESS_BYTES: Final[int] = 4

# Valid ranges (Ra-aligned)
THETA_MIN: Final[int] = 1
THETA_MAX: Final[int] = 27
THETA_RESERVED: Final[tuple[int, ...]] = (0, 28, 29, 30, 31)

PHI_MIN: Final[int] = 1  # RAC1
PHI_MAX: Final[int] = 6  # RAC6
PHI_RESERVED: Final[tuple[int, ...]] = (6, 7)  # As encoded (RAC7, RAC8 don't exist)

OMEGA_MIN: Final[int] = 0  # RED
OMEGA_MAX: Final[int] = 4  # BLUE
OMEGA_RESERVED: Final[tuple[int, ...]] = (5, 6, 7)

# Bit positions (from MSB)
THETA_SHIFT: Final[int] = 27  # bits [31:27]
PHI_SHIFT: Final[int] = 24    # bits [26:24]
OMEGA_SHIFT: Final[int] = 21  # bits [23:21]
RADIUS_SHIFT: Final[int] = 13 # bits [20:13]
RESERVED_SHIFT: Final[int] = 0 # bits [12:0]

# Masks
THETA_MASK: Final[int] = 0x1F << THETA_SHIFT
PHI_MASK: Final[int] = 0x07 << PHI_SHIFT
OMEGA_MASK: Final[int] = 0x07 << OMEGA_SHIFT
RADIUS_MASK: Final[int] = 0xFF << RADIUS_SHIFT
RESERVED_MASK: Final[int] = 0x1FFF


# =============================================================================
# Semantic Enumerations
# =============================================================================

class ThetaSector(IntEnum):
    """
    Semantic sectors mapped to Repitan ranges.
    
    The 27 Repitans divide into 8 symbolic domains,
    matching the Ra System's chambered nautilus geometry.
    """
    CORE = 0       # Repitans 1-3: Essential identity
    GENE = 1       # Repitans 4-6: Inherited/biological
    MEMORY = 2     # Repitans 7-10: Learned/experiential
    WITNESS = 3    # Repitans 11-13: Present-moment awareness
    DREAM = 4      # Repitans 14-17: Aspirational/future
    BRIDGE = 5     # Repitans 18-20: Relational/connective
    GUARDIAN = 6   # Repitans 21-24: Protective/regulatory
    SHADOW = 7     # Repitans 25-27: Unintegrated/emergent
    
    # Reserved
    INVERSE = 8    # Theta = 0 (inverted vector)
    META = 9       # Theta = 28-31 (meta-routing)
    
    @classmethod
    def from_theta(cls, theta: int) -> ThetaSector:
        """Map theta value to semantic sector."""
        if theta == 0:
            return cls.INVERSE
        if theta > 27:
            return cls.META
        if theta <= 3:
            return cls.CORE
        if theta <= 6:
            return cls.GENE
        if theta <= 10:
            return cls.MEMORY
        if theta <= 13:
            return cls.WITNESS
        if theta <= 17:
            return cls.DREAM
        if theta <= 20:
            return cls.BRIDGE
        if theta <= 24:
            return cls.GUARDIAN
        return cls.SHADOW
    
    @property
    def repitan_range(self) -> tuple[int, int]:
        """Get the Repitan range for this sector."""
        ranges = {
            self.CORE: (1, 3),
            self.GENE: (4, 6),
            self.MEMORY: (7, 10),
            self.WITNESS: (11, 13),
            self.DREAM: (14, 17),
            self.BRIDGE: (18, 20),
            self.GUARDIAN: (21, 24),
            self.SHADOW: (25, 27),
        }
        return ranges.get(self, (0, 0))
    
    @property
    def center_repitan(self) -> int:
        """Get center Repitan for this sector."""
        lo, hi = self.repitan_range
        return (lo + hi) // 2 if lo > 0 else 0


class RACBand(IntEnum):
    """
    Recursive Access Code bands (access sensitivity).
    
    RAC1 is highest access (least restrictive).
    RAC6 is lowest access (most restrictive).
    """
    RAC1 = 1  # 0.6362 Red Rams - Highest access
    RAC2 = 2  # 0.6283 Red Rams
    RAC3 = 3  # 0.5726 Red Rams
    RAC4 = 4  # 0.5236 Red Rams
    RAC5 = 5  # 0.4580 Red Rams
    RAC6 = 6  # 0.3999 Red Rams - Lowest access
    
    # Reserved
    OVERRIDE = 7   # System override (ETF)
    WILDCARD = 8   # Match any level
    
    @property
    def encoded(self) -> int:
        """Get encoded value (0-5 for RAC1-RAC6)."""
        if self.value <= 6:
            return self.value - 1
        return self.value - 1  # OVERRIDE=6, WILDCARD=7
    
    @classmethod
    def from_encoded(cls, encoded: int) -> RACBand:
        """Decode from 3-bit field."""
        if encoded <= 5:
            return cls(encoded + 1)
        if encoded == 6:
            return cls.OVERRIDE
        return cls.WILDCARD


class OmegaTier(IntEnum):
    """
    Omega format tiers (coherence/precision levels).
    
    Maps directly to Ra System's 5 Omega formats.
    """
    RED = 0          # Highest precision
    OMEGA_MAJOR = 1  # High precision (spectral)
    GREEN = 2        # Standard (default)
    OMEGA_MINOR = 3  # Reduced precision
    BLUE = 4         # Lowest precision (archive)
    
    # Reserved
    RESERVED_5 = 5
    RESERVED_6 = 6
    WILDCARD = 7     # Match any tier
    
    @property
    def is_valid(self) -> bool:
        """Check if this is a valid (non-reserved) tier."""
        return self.value <= 4


# =============================================================================
# Address Class
# =============================================================================

@dataclass(frozen=True, slots=True)
class RPPAddress:
    """
    RPP Canonical Address (Ra-Derived).
    
    This is not an address—it is a phase vector encoding positional
    resonance across the Ra topology.
    
    Attributes:
        theta: Repitan index 1-27 (semantic sector)
        phi: RAC level 1-6 (access sensitivity)
        omega: Omega tier 0-4 (coherence level)
        radius: Normalized intensity 0.0-1.0
        reserved: 13-bit CRC or future use
    
    Total: 32 bits (4 bytes)
    """
    
    theta: int
    phi: int
    omega: int
    radius: float
    reserved: int = 0
    
    # Class-level constants
    NULL: ClassVar[RPPAddress]
    WILDCARD: ClassVar[RPPAddress]
    
    def __post_init__(self) -> None:
        """Validate all fields against Ra constraints."""
        # Theta: 0-31 (5 bits), valid 1-27
        if not 0 <= self.theta <= 31:
            raise ValueError(f"theta must be 0-31, got {self.theta}")
        
        # Phi: 1-8, valid 1-6
        if not 1 <= self.phi <= 8:
            raise ValueError(f"phi must be 1-8, got {self.phi}")
        
        # Omega: 0-7, valid 0-4
        if not 0 <= self.omega <= 7:
            raise ValueError(f"omega must be 0-7, got {self.omega}")
        
        # Radius: 0.0-1.0
        if not 0.0 <= self.radius <= 1.0:
            raise ValueError(f"radius must be 0-1, got {self.radius}")
        
        # Reserved: 0-8191 (13 bits)
        if not 0 <= self.reserved <= 0x1FFF:
            raise ValueError(f"reserved must be 0-8191, got {self.reserved}")
    
    # -------------------------------------------------------------------------
    # Validity Checks
    # -------------------------------------------------------------------------
    
    def is_valid(self) -> bool:
        """Check if all fields are in Ra-valid ranges."""
        return (
            THETA_MIN <= self.theta <= THETA_MAX and
            PHI_MIN <= self.phi <= PHI_MAX and
            OMEGA_MIN <= self.omega <= OMEGA_MAX
        )
    
    def is_reserved(self) -> bool:
        """Check if any field uses a reserved value."""
        return (
            self.theta in THETA_RESERVED or
            (self.phi - 1) in PHI_RESERVED or
            self.omega in OMEGA_RESERVED
        )
    
    @property
    def is_null(self) -> bool:
        """Check if this is a null (theta=0) address."""
        return self.theta == 0
    
    @property
    def is_wildcard(self) -> bool:
        """Check if this is a wildcard address."""
        return self.theta == 31 or self.phi == 8 or self.omega == 7
    
    # -------------------------------------------------------------------------
    # Encoding / Decoding
    # -------------------------------------------------------------------------
    
    def to_int(self) -> int:
        """
        Encode to 32-bit integer.
        
        Layout:
            [31:27] theta (5 bits)
            [26:24] phi (3 bits, encoded as 0-7)
            [23:21] omega (3 bits)
            [20:13] radius (8 bits, scaled 0-255)
            [12:0]  reserved (13 bits)
        """
        theta_enc = (self.theta & 0x1F) << THETA_SHIFT
        phi_enc = ((self.phi - 1) & 0x07) << PHI_SHIFT
        omega_enc = (self.omega & 0x07) << OMEGA_SHIFT
        radius_enc = (round(self.radius * 255) & 0xFF) << RADIUS_SHIFT
        reserved_enc = self.reserved & RESERVED_MASK
        
        return theta_enc | phi_enc | omega_enc | radius_enc | reserved_enc
    
    def to_bytes(self) -> bytes:
        """Encode to 4-byte big-endian."""
        return struct.pack('>I', self.to_int())
    
    def to_hex(self) -> str:
        """Format as hex string."""
        return f"0x{self.to_int():08X}"
    
    @classmethod
    def from_int(cls, raw: int) -> RPPAddress:
        """Decode from 32-bit integer."""
        theta = (raw & THETA_MASK) >> THETA_SHIFT
        phi = ((raw & PHI_MASK) >> PHI_SHIFT) + 1
        omega = (raw & OMEGA_MASK) >> OMEGA_SHIFT
        radius = ((raw & RADIUS_MASK) >> RADIUS_SHIFT) / 255.0
        reserved = raw & RESERVED_MASK
        
        return cls(
            theta=theta,
            phi=phi,
            omega=omega,
            radius=radius,
            reserved=reserved
        )
    
    @classmethod
    def from_bytes(cls, data: bytes) -> RPPAddress:
        """Decode from 4-byte big-endian."""
        if len(data) != ADDRESS_BYTES:
            raise ValueError(f"Expected {ADDRESS_BYTES} bytes, got {len(data)}")
        raw = struct.unpack('>I', data)[0]
        return cls.from_int(raw)
    
    # -------------------------------------------------------------------------
    # Semantic Accessors
    # -------------------------------------------------------------------------
    
    @property
    def sector(self) -> ThetaSector:
        """Get semantic sector from theta."""
        return ThetaSector.from_theta(self.theta)
    
    @property
    def rac_band(self) -> RACBand:
        """Get RAC band from phi."""
        return RACBand(self.phi) if self.phi <= 6 else RACBand(self.phi)
    
    @property
    def omega_tier(self) -> OmegaTier:
        """Get Omega tier from omega field."""
        return OmegaTier(self.omega)
    
    @property
    def repitan_value(self) -> float:
        """Get Repitan fractional value (theta/27)."""
        return self.theta / 27.0 if self.theta > 0 else 0.0
    
    @property
    def theta_degrees(self) -> float:
        """Get theta as angle in degrees (0-360)."""
        return self.repitan_value * 360.0
    
    # -------------------------------------------------------------------------
    # Ra System Integration
    # -------------------------------------------------------------------------
    
    def to_ra_coordinate(self):
        """
        Convert to Ra System RaCoordinate (if ra_system available).
        
        Returns RaCoordinate or None if ra_system not installed.
        """
        if not RA_SYSTEM_AVAILABLE:
            return None
        
        from ra_system.spherical import RaCoordinate
        from ra_system.repitans import Repitan
        from ra_system.rac import RacLevel
        from ra_system.omega import OmegaFormat
        
        if not self.is_valid():
            return None
        
        return RaCoordinate(
            theta=Repitan(self.theta),
            phi=RacLevel(self.phi),
            harmonic=OmegaFormat(self.omega),
            radius=self.radius
        )
    
    @classmethod
    def from_ra_coordinate(cls, coord) -> RPPAddress:
        """Create from Ra System RaCoordinate."""
        return cls(
            theta=coord.theta.index,
            phi=coord.phi.value,
            omega=coord.harmonic.value,
            radius=coord.radius
        )
    
    # -------------------------------------------------------------------------
    # URI Format
    # -------------------------------------------------------------------------
    
    def to_uri(self) -> str:
        """
        Format as SPIRAL URI.
        
        Format: spiral://θ:<theta>/φ:<phi>/h:<omega>/r:<radius>
        """
        return f"spiral://θ:{self.theta}/φ:{self.phi}/h:{self.omega}/r:{self.radius:.2f}"
    
    @classmethod
    def from_uri(cls, uri: str) -> RPPAddress:
        """Parse from SPIRAL URI."""
        import re
        
        pattern = r"spiral://θ:(\d+)/φ:(\d+)/h:(\d+)/r:([\d.]+)"
        match = re.match(pattern, uri)
        
        if not match:
            raise ValueError(f"Invalid SPIRAL URI: {uri}")
        
        return cls(
            theta=int(match.group(1)),
            phi=int(match.group(2)),
            omega=int(match.group(3)),
            radius=float(match.group(4))
        )
    
    # -------------------------------------------------------------------------
    # String Representations
    # -------------------------------------------------------------------------
    
    def __str__(self) -> str:
        """Human-readable representation."""
        sector = self.sector.name
        rac = f"RAC{self.phi}" if self.phi <= 6 else self.rac_band.name
        tier = self.omega_tier.name
        
        return f"RPP(θ={self.theta}[{sector}], φ={rac}, h={tier}, r={self.radius:.2f})"
    
    def __repr__(self) -> str:
        return f"RPPAddress({self.to_hex()})"


# Initialize class-level constants
RPPAddress.NULL = RPPAddress(theta=0, phi=1, omega=0, radius=0.0)
RPPAddress.WILDCARD = RPPAddress(theta=31, phi=8, omega=7, radius=1.0)


# =============================================================================
# Factory Functions
# =============================================================================

def create_address(
    theta: int = 14,
    phi: int = 3,
    omega: int = 2,
    radius: float = 0.5,
    *,
    validate: bool = True
) -> RPPAddress | None:
    """
    Create an RPP address with optional validation.
    
    Args:
        theta: Repitan index 1-27 (default: 14, center of DREAM)
        phi: RAC level 1-6 (default: 3, RAC3)
        omega: Omega tier 0-4 (default: 2, GREEN)
        radius: Intensity 0.0-1.0 (default: 0.5)
        validate: If True, return None for invalid addresses
    
    Returns:
        RPPAddress or None if validation fails
    """
    try:
        addr = RPPAddress(theta=theta, phi=phi, omega=omega, radius=radius)
        if validate and not addr.is_valid():
            return None
        return addr
    except ValueError:
        return None


def create_from_sector(
    sector: ThetaSector,
    phi: int = 3,
    omega: int = 2,
    radius: float = 0.5
) -> RPPAddress:
    """
    Create address from semantic sector.
    
    Uses the center Repitan of the sector range.
    """
    theta = sector.center_repitan
    if theta == 0:
        theta = 14  # Default to DREAM center for invalid sectors
    
    return RPPAddress(theta=theta, phi=phi, omega=omega, radius=radius)


# =============================================================================
# Coherence Functions
# =============================================================================

def address_distance(a: RPPAddress, b: RPPAddress) -> float:
    """
    Calculate weighted distance between two addresses.
    
    Weights from Ra System:
        w_θ = 0.30 (semantic domain)
        w_φ = 0.40 (access sensitivity)
        w_h = 0.20 (coherence tier)
        w_r = 0.10 (intensity)
    
    Returns: Value in [0, 1], 0 = identical, 1 = maximum distance
    """
    # Theta: Circular distance (max = 13.5)
    theta_diff = abs(a.theta - b.theta)
    theta_dist = min(theta_diff, 27 - theta_diff) / 13.5 if a.theta > 0 and b.theta > 0 else 1.0
    
    # Phi: Linear distance (max = 5)
    phi_dist = abs(a.phi - b.phi) / 5.0
    
    # Omega: Linear distance (max = 4)
    omega_dist = abs(a.omega - b.omega) / 4.0
    
    # Radius: Linear distance (max = 1)
    radius_dist = abs(a.radius - b.radius)
    
    return 0.30 * theta_dist + 0.40 * phi_dist + 0.20 * omega_dist + 0.10 * radius_dist


def coherence(a: RPPAddress, b: RPPAddress) -> float:
    """
    Calculate coherence score between two addresses.
    
    Returns: Value in [0, 1], 1 = identical, 0 = maximum distance
    """
    return 1.0 - address_distance(a, b)


def same_sector(a: RPPAddress, b: RPPAddress) -> bool:
    """Check if two addresses are in the same semantic sector."""
    return a.sector == b.sector


def adjacent_sectors(a: RPPAddress, b: RPPAddress) -> bool:
    """Check if two addresses are in adjacent sectors."""
    # Sector adjacency based on Ra topology
    adjacency = {
        ThetaSector.CORE: {ThetaSector.GENE, ThetaSector.MEMORY},
        ThetaSector.GENE: {ThetaSector.CORE, ThetaSector.GUARDIAN, ThetaSector.BRIDGE},
        ThetaSector.MEMORY: {ThetaSector.CORE, ThetaSector.WITNESS, ThetaSector.BRIDGE},
        ThetaSector.WITNESS: {ThetaSector.MEMORY, ThetaSector.BRIDGE},
        ThetaSector.DREAM: {ThetaSector.BRIDGE, ThetaSector.SHADOW},
        ThetaSector.BRIDGE: {ThetaSector.GENE, ThetaSector.MEMORY, ThetaSector.WITNESS, 
                            ThetaSector.GUARDIAN, ThetaSector.DREAM},
        ThetaSector.GUARDIAN: {ThetaSector.GENE, ThetaSector.BRIDGE},
        ThetaSector.SHADOW: {ThetaSector.DREAM},
    }
    
    return b.sector in adjacency.get(a.sector, set())


# =============================================================================
# Fallback Vector
# =============================================================================

def compute_fallback(primary: RPPAddress, vector: int) -> RPPAddress:
    """
    Compute fallback address using XOR-based vector.
    
    Vector layout (8 bits):
        [7:5] theta offset (XOR with theta)
        [4:2] phi offset (XOR with phi)
        [1:0] omega offset (XOR with omega)
    """
    theta_off = (vector >> 5) & 0x07
    phi_off = (vector >> 2) & 0x07
    omega_off = vector & 0x03
    
    # XOR and wrap to valid ranges
    new_theta = ((primary.theta - 1) ^ theta_off) % 27 + 1
    new_phi = ((primary.phi - 1) ^ phi_off) % 6 + 1
    new_omega = (primary.omega ^ omega_off) % 5
    
    return RPPAddress(
        theta=new_theta,
        phi=new_phi,
        omega=new_omega,
        radius=primary.radius,
        reserved=primary.reserved
    )


# =============================================================================
# Verification
# =============================================================================

def verify_roundtrip() -> bool:
    """Verify encode/decode roundtrip identity."""
    test_cases = [
        (1, 1, 0, 0.0),
        (27, 6, 4, 1.0),
        (14, 3, 2, 0.5),
        (7, 4, 1, 0.75),
        (20, 5, 3, 0.33),
    ]
    
    for theta, phi, omega, radius in test_cases:
        original = RPPAddress(theta=theta, phi=phi, omega=omega, radius=radius)
        encoded = original.to_int()
        decoded = RPPAddress.from_int(encoded)
        
        if (decoded.theta != original.theta or
            decoded.phi != original.phi or
            decoded.omega != original.omega or
            abs(decoded.radius - original.radius) > 0.005):
            return False
    
    return True


def verify_ra_alignment() -> bool:
    """Verify alignment with Ra System constraints."""
    # 27 Repitans
    if THETA_MAX != 27:
        return False
    
    # 6 RAC levels
    if PHI_MAX != 6:
        return False
    
    # 5 Omega formats
    if OMEGA_MAX != 4:
        return False
    
    # Total 32 bits
    total_bits = THETA_BITS + PHI_BITS + OMEGA_BITS + RADIUS_BITS + RESERVED_BITS
    if total_bits != ADDRESS_BITS:
        return False
    
    return True


def verify_all() -> dict[str, bool]:
    """Run all verification checks."""
    return {
        'roundtrip': verify_roundtrip(),
        'ra_alignment': verify_ra_alignment(),
        'ra_system_available': RA_SYSTEM_AVAILABLE,
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("RPP Canonical Address v1.0-RaCanonical")
    print("=" * 60)
    
    # Verification
    results = verify_all()
    print("\nVerification:")
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
    
    # Examples
    print("\nExample Addresses:")
    
    # Create from components
    addr1 = create_address(theta=8, phi=3, omega=2, radius=0.7)
    print("\n  Memory sector address:")
    print(f"    {addr1}")
    print(f"    URI: {addr1.to_uri()}")
    print(f"    Hex: {addr1.to_hex()}")
    print(f"    Bytes: {addr1.to_bytes().hex()}")
    
    # Create from sector
    addr2 = create_from_sector(ThetaSector.GUARDIAN, phi=2, omega=1, radius=0.9)
    print("\n  Guardian sector address:")
    print(f"    {addr2}")
    print(f"    Valid: {addr2.is_valid()}")
    
    # Coherence
    print(f"\n  Coherence(addr1, addr2): {coherence(addr1, addr2):.4f}")
    print(f"  Same sector: {same_sector(addr1, addr2)}")
    print(f"  Adjacent: {adjacent_sectors(addr1, addr2)}")
    
    # Fallback
    fallback = compute_fallback(addr1, 0b10100101)
    print("\n  Fallback vector 0xA5:")
    print(f"    Primary: {addr1}")
    print(f"    Fallback: {fallback}")
    
    # Null and wildcard
    print("\n  Special addresses:")
    print(f"    NULL: {RPPAddress.NULL}")
    print(f"    WILDCARD: {RPPAddress.WILDCARD}")
