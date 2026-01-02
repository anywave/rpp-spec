"""
RPP Canonical Address Test Suite

Validates Ra-derived address implementation against specification.
Tests encoding/decoding, coherence calculations, and Ra alignment.

Reference: RPP v1.0-RaCanonical Specification
"""

import pytest
from typing import Final

# Import the module under test
from rpp.address_canonical import (
    RPPAddress,
    ThetaSector,
    RACBand,
    OmegaTier,
    create_address,
    create_from_sector,
    address_distance,
    coherence,
    same_sector,
    adjacent_sectors,
    compute_fallback,
    verify_roundtrip,
    verify_ra_alignment,
    THETA_MIN, THETA_MAX,
    PHI_MIN, PHI_MAX,
    OMEGA_MIN, OMEGA_MAX,
    ADDRESS_BITS,
    ADDRESS_BYTES,
)


# =============================================================================
# Ra Constants for Validation
# =============================================================================

ANKH: Final[float] = 5.08938
REPITAN_COUNT: Final[int] = 27
RAC_COUNT: Final[int] = 6
OMEGA_COUNT: Final[int] = 5


# =============================================================================
# Basic Construction Tests
# =============================================================================

class TestAddressConstruction:
    """Test basic address construction and validation."""
    
    def test_valid_address_creation(self):
        """Valid parameters should create an address."""
        addr = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        assert addr.theta == 14
        assert addr.phi == 3
        assert addr.omega == 2
        assert addr.radius == 0.5
    
    def test_minimum_valid_address(self):
        """Minimum valid values should work."""
        addr = RPPAddress(theta=1, phi=1, omega=0, radius=0.0)
        assert addr.is_valid()
        assert not addr.is_null
    
    def test_maximum_valid_address(self):
        """Maximum valid values should work."""
        addr = RPPAddress(theta=27, phi=6, omega=4, radius=1.0)
        assert addr.is_valid()
    
    def test_null_address(self):
        """Theta=0 should create null address."""
        addr = RPPAddress(theta=0, phi=1, omega=0, radius=0.0)
        assert addr.is_null
        assert not addr.is_valid()
    
    def test_invalid_theta_high(self):
        """Theta > 27 should be reserved but constructable."""
        addr = RPPAddress(theta=28, phi=1, omega=0, radius=0.0)
        assert not addr.is_valid()
        assert addr.is_reserved()
    
    def test_invalid_phi_high(self):
        """Phi > 6 should fail validation."""
        addr = RPPAddress(theta=14, phi=7, omega=2, radius=0.5)
        assert not addr.is_valid()
    
    def test_invalid_omega_high(self):
        """Omega > 4 should fail validation."""
        addr = RPPAddress(theta=14, phi=3, omega=5, radius=0.5)
        assert not addr.is_valid()
    
    def test_theta_out_of_range_raises(self):
        """Theta > 31 should raise ValueError."""
        with pytest.raises(ValueError):
            RPPAddress(theta=32, phi=1, omega=0, radius=0.0)
    
    def test_phi_out_of_range_raises(self):
        """Phi > 8 should raise ValueError."""
        with pytest.raises(ValueError):
            RPPAddress(theta=14, phi=9, omega=2, radius=0.5)
    
    def test_radius_out_of_range_raises(self):
        """Radius > 1.0 should raise ValueError."""
        with pytest.raises(ValueError):
            RPPAddress(theta=14, phi=3, omega=2, radius=1.5)
    
    def test_factory_function_valid(self):
        """create_address should return valid address."""
        addr = create_address(theta=14, phi=3, omega=2, radius=0.5)
        assert addr is not None
        assert addr.is_valid()
    
    def test_factory_function_invalid_returns_none(self):
        """create_address with validate=True returns None for invalid."""
        addr = create_address(theta=0, phi=3, omega=2, radius=0.5, validate=True)
        assert addr is None


# =============================================================================
# Encoding/Decoding Tests
# =============================================================================

class TestEncodingDecoding:
    """Test encoding and decoding of addresses."""
    
    def test_to_int_basic(self):
        """Address should encode to 32-bit integer."""
        addr = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        raw = addr.to_int()
        assert isinstance(raw, int)
        assert 0 <= raw <= 0xFFFFFFFF
    
    def test_to_bytes_length(self):
        """Address should encode to exactly 4 bytes."""
        addr = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        data = addr.to_bytes()
        assert len(data) == ADDRESS_BYTES
    
    def test_roundtrip_int(self):
        """Encode to int and back should preserve fields."""
        original = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        raw = original.to_int()
        decoded = RPPAddress.from_int(raw)
        
        assert decoded.theta == original.theta
        assert decoded.phi == original.phi
        assert decoded.omega == original.omega
        # Radius has quantization error
        assert abs(decoded.radius - original.radius) < 0.005
    
    def test_roundtrip_bytes(self):
        """Encode to bytes and back should preserve fields."""
        original = RPPAddress(theta=27, phi=6, omega=4, radius=1.0)
        data = original.to_bytes()
        decoded = RPPAddress.from_bytes(data)
        
        assert decoded.theta == original.theta
        assert decoded.phi == original.phi
        assert decoded.omega == original.omega
        assert abs(decoded.radius - original.radius) < 0.005
    
    def test_roundtrip_all_corners(self):
        """Test roundtrip for corner cases."""
        test_cases = [
            (1, 1, 0, 0.0),
            (27, 6, 4, 1.0),
            (14, 3, 2, 0.5),
            (7, 4, 1, 0.75),
            (20, 5, 3, 0.33),
        ]
        
        for theta, phi, omega, radius in test_cases:
            original = RPPAddress(theta=theta, phi=phi, omega=omega, radius=radius)
            decoded = RPPAddress.from_int(original.to_int())
            
            assert decoded.theta == original.theta
            assert decoded.phi == original.phi
            assert decoded.omega == original.omega
            assert abs(decoded.radius - original.radius) < 0.005
    
    def test_bit_layout(self):
        """Verify exact bit positions match spec."""
        # theta=14 (0b01110), phi=3 (encoded as 2=0b010), omega=2 (0b010), radius=128 (0b10000000)
        addr = RPPAddress(theta=14, phi=3, omega=2, radius=0.502)  # ~128/255
        raw = addr.to_int()
        
        # Extract fields manually
        theta_extracted = (raw >> 27) & 0x1F
        phi_extracted = (raw >> 24) & 0x07
        omega_extracted = (raw >> 21) & 0x07
        radius_extracted = (raw >> 13) & 0xFF
        
        assert theta_extracted == 14
        assert phi_extracted == 2  # phi=3 encoded as 2
        assert omega_extracted == 2
        assert abs(radius_extracted - 128) <= 1
    
    def test_from_bytes_wrong_length_raises(self):
        """from_bytes with wrong length should raise."""
        with pytest.raises(ValueError):
            RPPAddress.from_bytes(b'\x00\x00\x00')  # 3 bytes


# =============================================================================
# Semantic Accessor Tests
# =============================================================================

class TestSemanticAccessors:
    """Test semantic field accessors."""
    
    def test_sector_core(self):
        """Theta 1-3 should map to CORE sector."""
        for theta in [1, 2, 3]:
            addr = RPPAddress(theta=theta, phi=1, omega=0, radius=0.5)
            assert addr.sector == ThetaSector.CORE
    
    def test_sector_gene(self):
        """Theta 4-6 should map to GENE sector."""
        for theta in [4, 5, 6]:
            addr = RPPAddress(theta=theta, phi=1, omega=0, radius=0.5)
            assert addr.sector == ThetaSector.GENE
    
    def test_sector_memory(self):
        """Theta 7-10 should map to MEMORY sector."""
        for theta in [7, 8, 9, 10]:
            addr = RPPAddress(theta=theta, phi=1, omega=0, radius=0.5)
            assert addr.sector == ThetaSector.MEMORY
    
    def test_sector_witness(self):
        """Theta 11-13 should map to WITNESS sector."""
        for theta in [11, 12, 13]:
            addr = RPPAddress(theta=theta, phi=1, omega=0, radius=0.5)
            assert addr.sector == ThetaSector.WITNESS
    
    def test_sector_dream(self):
        """Theta 14-17 should map to DREAM sector."""
        for theta in [14, 15, 16, 17]:
            addr = RPPAddress(theta=theta, phi=1, omega=0, radius=0.5)
            assert addr.sector == ThetaSector.DREAM
    
    def test_sector_bridge(self):
        """Theta 18-20 should map to BRIDGE sector."""
        for theta in [18, 19, 20]:
            addr = RPPAddress(theta=theta, phi=1, omega=0, radius=0.5)
            assert addr.sector == ThetaSector.BRIDGE
    
    def test_sector_guardian(self):
        """Theta 21-24 should map to GUARDIAN sector."""
        for theta in [21, 22, 23, 24]:
            addr = RPPAddress(theta=theta, phi=1, omega=0, radius=0.5)
            assert addr.sector == ThetaSector.GUARDIAN
    
    def test_sector_shadow(self):
        """Theta 25-27 should map to SHADOW sector."""
        for theta in [25, 26, 27]:
            addr = RPPAddress(theta=theta, phi=1, omega=0, radius=0.5)
            assert addr.sector == ThetaSector.SHADOW
    
    def test_rac_band(self):
        """Phi should map to correct RAC band."""
        for phi in range(1, 7):
            addr = RPPAddress(theta=14, phi=phi, omega=2, radius=0.5)
            assert addr.rac_band == RACBand(phi)
    
    def test_omega_tier(self):
        """Omega should map to correct tier."""
        for omega in range(5):
            addr = RPPAddress(theta=14, phi=3, omega=omega, radius=0.5)
            assert addr.omega_tier == OmegaTier(omega)
    
    def test_repitan_value(self):
        """Repitan value should be theta/27."""
        addr = RPPAddress(theta=9, phi=3, omega=2, radius=0.5)
        expected = 9 / 27.0
        assert abs(addr.repitan_value - expected) < 0.001
    
    def test_theta_degrees(self):
        """Theta degrees should be (theta/27) * 360."""
        addr = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        expected = (14 / 27.0) * 360.0
        assert abs(addr.theta_degrees - expected) < 0.1


# =============================================================================
# URI Format Tests
# =============================================================================

class TestURIFormat:
    """Test URI formatting and parsing."""
    
    def test_to_uri_format(self):
        """to_uri should produce correct format."""
        addr = RPPAddress(theta=14, phi=3, omega=2, radius=0.50)
        uri = addr.to_uri()
        assert uri == "spiral://θ:14/φ:3/h:2/r:0.50"
    
    def test_from_uri_basic(self):
        """from_uri should parse correctly."""
        uri = "spiral://θ:14/φ:3/h:2/r:0.50"
        addr = RPPAddress.from_uri(uri)
        assert addr.theta == 14
        assert addr.phi == 3
        assert addr.omega == 2
        assert abs(addr.radius - 0.50) < 0.01
    
    def test_uri_roundtrip(self):
        """URI encode/decode should roundtrip."""
        original = RPPAddress(theta=20, phi=5, omega=3, radius=0.75)
        decoded = RPPAddress.from_uri(original.to_uri())
        assert decoded.theta == original.theta
        assert decoded.phi == original.phi
        assert decoded.omega == original.omega
        assert abs(decoded.radius - original.radius) < 0.01
    
    def test_from_uri_invalid_raises(self):
        """Invalid URI should raise ValueError."""
        with pytest.raises(ValueError):
            RPPAddress.from_uri("invalid://format")


# =============================================================================
# Coherence Tests
# =============================================================================

class TestCoherence:
    """Test coherence and distance calculations."""
    
    def test_identical_addresses_coherence_one(self):
        """Identical addresses should have coherence 1.0."""
        addr = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        assert coherence(addr, addr) == 1.0
    
    def test_identical_addresses_distance_zero(self):
        """Identical addresses should have distance 0.0."""
        addr = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        assert address_distance(addr, addr) == 0.0
    
    def test_coherence_symmetry(self):
        """Coherence should be symmetric."""
        addr1 = RPPAddress(theta=5, phi=2, omega=1, radius=0.3)
        addr2 = RPPAddress(theta=20, phi=5, omega=4, radius=0.8)
        assert coherence(addr1, addr2) == coherence(addr2, addr1)
    
    def test_distance_symmetry(self):
        """Distance should be symmetric."""
        addr1 = RPPAddress(theta=5, phi=2, omega=1, radius=0.3)
        addr2 = RPPAddress(theta=20, phi=5, omega=4, radius=0.8)
        assert address_distance(addr1, addr2) == address_distance(addr2, addr1)
    
    def test_coherence_in_range(self):
        """Coherence should always be in [0, 1]."""
        for _ in range(100):
            import random
            addr1 = RPPAddress(
                theta=random.randint(1, 27),
                phi=random.randint(1, 6),
                omega=random.randint(0, 4),
                radius=random.random()
            )
            addr2 = RPPAddress(
                theta=random.randint(1, 27),
                phi=random.randint(1, 6),
                omega=random.randint(0, 4),
                radius=random.random()
            )
            c = coherence(addr1, addr2)
            assert 0.0 <= c <= 1.0
    
    def test_distance_in_range(self):
        """Distance should always be in [0, 1]."""
        for _ in range(100):
            import random
            addr1 = RPPAddress(
                theta=random.randint(1, 27),
                phi=random.randint(1, 6),
                omega=random.randint(0, 4),
                radius=random.random()
            )
            addr2 = RPPAddress(
                theta=random.randint(1, 27),
                phi=random.randint(1, 6),
                omega=random.randint(0, 4),
                radius=random.random()
            )
            d = address_distance(addr1, addr2)
            assert 0.0 <= d <= 1.0
    
    def test_theta_circular_distance(self):
        """Theta distance should be circular (max 13)."""
        # Theta 1 and 27 should be close (distance 1 in circular)
        addr1 = RPPAddress(theta=1, phi=3, omega=2, radius=0.5)
        addr2 = RPPAddress(theta=27, phi=3, omega=2, radius=0.5)
        addr3 = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        
        # 1↔27 should be closer than 1↔14
        dist_1_27 = address_distance(addr1, addr2)
        dist_1_14 = address_distance(addr1, addr3)
        assert dist_1_27 < dist_1_14


# =============================================================================
# Sector Tests
# =============================================================================

class TestSectors:
    """Test sector comparison functions."""
    
    def test_same_sector_true(self):
        """Addresses in same Repitan range should be same sector."""
        addr1 = RPPAddress(theta=7, phi=3, omega=2, radius=0.5)   # MEMORY
        addr2 = RPPAddress(theta=10, phi=1, omega=4, radius=0.1)  # MEMORY
        assert same_sector(addr1, addr2)
    
    def test_same_sector_false(self):
        """Addresses in different ranges should not be same sector."""
        addr1 = RPPAddress(theta=5, phi=3, omega=2, radius=0.5)   # GENE
        addr2 = RPPAddress(theta=25, phi=3, omega=2, radius=0.5)  # SHADOW
        assert not same_sector(addr1, addr2)
    
    def test_adjacent_sectors(self):
        """Known adjacent sectors should return True."""
        # CORE ↔ GENE
        addr_core = create_from_sector(ThetaSector.CORE)
        addr_gene = create_from_sector(ThetaSector.GENE)
        assert adjacent_sectors(addr_core, addr_gene)
        
        # BRIDGE is hub - adjacent to many
        addr_bridge = create_from_sector(ThetaSector.BRIDGE)
        addr_memory = create_from_sector(ThetaSector.MEMORY)
        assert adjacent_sectors(addr_bridge, addr_memory)
    
    def test_non_adjacent_sectors(self):
        """Non-adjacent sectors should return False."""
        # CORE and SHADOW are not adjacent
        addr_core = create_from_sector(ThetaSector.CORE)
        addr_shadow = create_from_sector(ThetaSector.SHADOW)
        assert not adjacent_sectors(addr_core, addr_shadow)


# =============================================================================
# Fallback Vector Tests
# =============================================================================

class TestFallbackVector:
    """Test fallback address computation."""
    
    def test_fallback_zero_vector(self):
        """Zero fallback vector should return (nearly) same address."""
        primary = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        fallback = compute_fallback(primary, 0b00000000)
        # XOR with 0 should wrap to same position
        assert fallback.radius == primary.radius
    
    def test_fallback_changes_theta(self):
        """Fallback vector should modify theta."""
        primary = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        fallback = compute_fallback(primary, 0b11100000)  # theta offset = 7
        assert fallback.theta != primary.theta
    
    def test_fallback_changes_phi(self):
        """Fallback vector should modify phi."""
        primary = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        fallback = compute_fallback(primary, 0b00011100)  # phi offset = 7
        assert fallback.phi != primary.phi
    
    def test_fallback_changes_omega(self):
        """Fallback vector should modify omega."""
        primary = RPPAddress(theta=14, phi=3, omega=2, radius=0.5)
        fallback = compute_fallback(primary, 0b00000011)  # omega offset = 3
        assert fallback.omega != primary.omega
    
    def test_fallback_preserves_validity(self):
        """Fallback should always produce valid addresses."""
        for _ in range(100):
            import random
            primary = RPPAddress(
                theta=random.randint(1, 27),
                phi=random.randint(1, 6),
                omega=random.randint(0, 4),
                radius=random.random()
            )
            vector = random.randint(0, 255)
            fallback = compute_fallback(primary, vector)
            assert fallback.is_valid()


# =============================================================================
# Ra Alignment Tests
# =============================================================================

class TestRaAlignment:
    """Test alignment with Ra System constants."""
    
    def test_repitan_count(self):
        """Should support exactly 27 Repitans."""
        assert THETA_MAX == REPITAN_COUNT
        assert THETA_MIN == 1
    
    def test_rac_count(self):
        """Should support exactly 6 RAC levels."""
        assert PHI_MAX == RAC_COUNT
        assert PHI_MIN == 1
    
    def test_omega_count(self):
        """Should support exactly 5 Omega formats."""
        assert OMEGA_MAX == OMEGA_COUNT - 1  # 0-indexed
        assert OMEGA_MIN == 0
    
    def test_address_size(self):
        """Address should be exactly 32 bits."""
        assert ADDRESS_BITS == 32
        assert ADDRESS_BYTES == 4
    
    def test_verify_roundtrip(self):
        """Built-in roundtrip verification should pass."""
        assert verify_roundtrip()
    
    def test_verify_ra_alignment(self):
        """Built-in Ra alignment verification should pass."""
        assert verify_ra_alignment()
    
    def test_sector_coverage(self):
        """All 27 Repitans should map to exactly 8 sectors."""
        sectors_seen = set()
        for theta in range(1, 28):
            addr = RPPAddress(theta=theta, phi=1, omega=0, radius=0.5)
            sectors_seen.add(addr.sector)
        assert len(sectors_seen) == 8


# =============================================================================
# Special Address Tests
# =============================================================================

class TestSpecialAddresses:
    """Test special address constants."""
    
    def test_null_address(self):
        """NULL constant should exist and be null."""
        assert RPPAddress.NULL.is_null
        assert RPPAddress.NULL.theta == 0
    
    def test_wildcard_address(self):
        """WILDCARD constant should exist and be wildcard."""
        assert RPPAddress.WILDCARD.is_wildcard
        assert RPPAddress.WILDCARD.theta == 31


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_create_route_validate(self):
        """Full workflow: create, encode, decode, validate."""
        # Create from semantic
        addr = create_from_sector(
            ThetaSector.MEMORY,
            phi=3,
            omega=2,
            radius=0.7
        )
        
        # Encode to wire format
        wire_bytes = addr.to_bytes()
        wire_hex = addr.to_hex()
        assert wire_hex.startswith("0x") and len(wire_hex) == 10  # 4 bytes = 8 hex chars + 0x prefix

        # Decode
        decoded = RPPAddress.from_bytes(wire_bytes)
        
        # Validate
        assert decoded.is_valid()
        assert decoded.sector == ThetaSector.MEMORY
        assert decoded.rac_band == RACBand.RAC3
        assert decoded.omega_tier == OmegaTier.GREEN
    
    def test_coherence_based_routing(self):
        """Simulate coherence-based route selection."""
        destination = RPPAddress(theta=12, phi=3, omega=2, radius=0.8)
        
        candidates = [
            RPPAddress(theta=11, phi=3, omega=2, radius=0.7),  # Close
            RPPAddress(theta=25, phi=6, omega=4, radius=0.2),  # Far
            RPPAddress(theta=12, phi=4, omega=2, radius=0.8),  # Same theta, diff phi
        ]
        
        # Rank by coherence
        ranked = sorted(candidates, key=lambda c: coherence(c, destination), reverse=True)
        
        # Closest should be first
        assert ranked[0].theta == 11  # Same sector, very close
        assert ranked[-1].theta == 25  # Different sector, low coherence


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
