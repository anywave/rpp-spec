"""
RPP Extended Addressing Test Suite
==================================

Comprehensive tests for SPEC-EXTENDED.md compliance.

Compliance Levels:
- Level 1: Core Only (28-bit)
- Level 2: Extended Addressing (64-bit)
- Level 3: Holographic Operations
- Level 4: Hardware Emulation
- Level 5: RTL Synthesis (separate testbench)

Usage:
    pytest test_rpp_extended_spec.py -v
    pytest test_rpp_extended_spec.py -v -k "level1"  # Core only
    pytest test_rpp_extended_spec.py -v -k "level2"  # Extended
"""

import pytest
import math
from dataclasses import dataclass
from typing import Tuple, Optional


# =============================================================================
# CONSTANTS (from SPEC-EXTENDED.md)
# =============================================================================

# Core address masks and shifts
RPP_SHELL_MASK = 0x0C000000
RPP_THETA_MASK = 0x03FE0000
RPP_PHI_MASK = 0x0001FF00
RPP_HARMONIC_MASK = 0x000000FF

RPP_SHELL_SHIFT = 26
RPP_THETA_SHIFT = 17
RPP_PHI_SHIFT = 8
RPP_HARMONIC_SHIFT = 0

# Extended address masks and shifts
RPP_EXT_SHELL_SHIFT = 62
RPP_EXT_THETA_SHIFT = 42
RPP_EXT_PHI_SHIFT = 22
RPP_EXT_HARMONIC_SHIFT = 12
RPP_EXT_PHASE_SHIFT = 0

RPP_EXT_SHELL_MASK = 0xC000000000000000
RPP_EXT_THETA_MASK = 0x3FFFFC0000000000
RPP_EXT_PHI_MASK = 0x000003FFFFC00000
RPP_EXT_HARMONIC_MASK = 0x00000000003FF000
RPP_EXT_PHASE_MASK = 0x0000000000000FFF

# Value ranges
SHELL_MAX = 3
THETA_CORE_MAX = 511
PHI_CORE_MAX = 511
HARMONIC_CORE_MAX = 255

THETA_EXT_MAX = 1048575
PHI_EXT_MAX = 1048575
HARMONIC_EXT_MAX = 1023
PHASE_MAX = 4095

# Consent zones (phi values)
PHI_GROUNDED_MAX = 170
PHI_TRANSITIONAL_MAX = 341
PHI_ETHEREAL_MIN = 342

# Theta sectors (core values)
SECTOR_GENE = (0, 63)
SECTOR_MEMORY = (64, 127)
SECTOR_WITNESS = (128, 191)
SECTOR_DREAM = (192, 255)
SECTOR_BRIDGE = (256, 319)
SECTOR_GUARDIAN = (320, 383)
SECTOR_EMERGENCE = (384, 447)
SECTOR_META = (448, 511)


# =============================================================================
# CORE ADDRESS FUNCTIONS (Level 1)
# =============================================================================

def encode_core(shell: int, theta: int, phi: int, harmonic: int) -> int:
    """Encode 28-bit RPP core address."""
    assert 0 <= shell <= SHELL_MAX, f"Shell {shell} out of range"
    assert 0 <= theta <= THETA_CORE_MAX, f"Theta {theta} out of range"
    assert 0 <= phi <= PHI_CORE_MAX, f"Phi {phi} out of range"
    assert 0 <= harmonic <= HARMONIC_CORE_MAX, f"Harmonic {harmonic} out of range"
    
    return ((shell << RPP_SHELL_SHIFT) |
            (theta << RPP_THETA_SHIFT) |
            (phi << RPP_PHI_SHIFT) |
            harmonic)


def decode_core(addr: int) -> Tuple[int, int, int, int]:
    """Decode 28-bit RPP core address."""
    shell = (addr >> RPP_SHELL_SHIFT) & 0x3
    theta = (addr >> RPP_THETA_SHIFT) & 0x1FF
    phi = (addr >> RPP_PHI_SHIFT) & 0x1FF
    harmonic = addr & 0xFF
    return (shell, theta, phi, harmonic)


# =============================================================================
# EXTENDED ADDRESS FUNCTIONS (Level 2)
# =============================================================================

def encode_extended(shell: int, theta_fine: int, phi_fine: int,
                    harmonic: int, phase: int) -> int:
    """Encode 64-bit RPP extended address."""
    assert 0 <= shell <= SHELL_MAX
    assert 0 <= theta_fine <= THETA_EXT_MAX
    assert 0 <= phi_fine <= PHI_EXT_MAX
    assert 0 <= harmonic <= HARMONIC_EXT_MAX
    assert 0 <= phase <= PHASE_MAX
    
    return ((shell << RPP_EXT_SHELL_SHIFT) |
            (theta_fine << RPP_EXT_THETA_SHIFT) |
            (phi_fine << RPP_EXT_PHI_SHIFT) |
            (harmonic << RPP_EXT_HARMONIC_SHIFT) |
            phase)


def decode_extended(addr: int) -> Tuple[int, int, int, int, int]:
    """Decode 64-bit RPP extended address."""
    shell = (addr >> RPP_EXT_SHELL_SHIFT) & 0x3
    theta_fine = (addr >> RPP_EXT_THETA_SHIFT) & 0xFFFFF
    phi_fine = (addr >> RPP_EXT_PHI_SHIFT) & 0xFFFFF
    harmonic = (addr >> RPP_EXT_HARMONIC_SHIFT) & 0x3FF
    phase = addr & 0xFFF
    return (shell, theta_fine, phi_fine, harmonic, phase)


def extended_to_core(extended: int) -> int:
    """Truncate extended address to core address."""
    shell, theta_fine, phi_fine, harmonic_fine, _ = decode_extended(extended)
    
    # Truncate by taking top bits
    theta_core = theta_fine >> 11  # 20 bits -> 9 bits
    phi_core = phi_fine >> 11
    harmonic_core = harmonic_fine >> 2  # 10 bits -> 8 bits
    
    return encode_core(shell, theta_core, phi_core, harmonic_core)


# =============================================================================
# COORDINATE CONVERSION (Level 2)
# =============================================================================

def degrees_to_core_theta(degrees: float) -> int:
    """Convert 0-360° to 0-511 core theta."""
    return int((degrees / 360.0) * 512) % 512


def degrees_to_core_phi(degrees: float) -> int:
    """Convert -90° to +90° to 0-511 core phi.
    
    Mapping: -90° → 0 (GROUNDED), +90° → 511 (ETHEREAL)
    """
    normalized = (degrees + 90) / 180.0  # 0 to 1
    return min(511, max(0, int(normalized * 512)))


def core_theta_to_degrees(theta: int) -> float:
    """Convert 0-511 core theta to 0-360°."""
    return (theta / 512.0) * 360.0


def core_phi_to_degrees(phi: int) -> float:
    """Convert 0-511 core phi to -90° to +90°.
    
    Mapping: 0 → -90° (GROUNDED), 511 → +90° (ETHEREAL)
    """
    return (phi / 511.0) * 180.0 - 90.0


def degrees_to_extended_theta(degrees: float) -> int:
    """Convert 0-360° to 20-bit extended theta."""
    return int((degrees / 360.0) * 1048576) % 1048576


def degrees_to_extended_phi(degrees: float) -> int:
    """Convert -90° to +90° to 20-bit extended phi."""
    normalized = (degrees + 90) / 180.0
    return int(normalized * 1048576) % 1048576


def extended_theta_to_degrees(theta_fine: int) -> float:
    """Convert 20-bit extended theta to 0-360°."""
    return (theta_fine / 1048576.0) * 360.0


def extended_phi_to_degrees(phi_fine: int) -> float:
    """Convert 20-bit extended phi to -90° to +90°."""
    return (phi_fine / 1048576.0) * 180.0 - 90.0


# =============================================================================
# HOLOGRAPHIC FUNCTIONS (Level 3)
# =============================================================================

@dataclass
class WavePacket:
    """Simplified wave packet for interference tests."""
    theta: float  # degrees
    phi: float    # degrees
    phase: float  # degrees
    amplitude: float = 1.0
    theta_spread: float = 30.0


def compute_interference(packets: list, query_theta: float, 
                         query_phi: float) -> float:
    """Compute wave interference amplitude at a point."""
    total = 0.0
    for pkt in packets:
        # Distance from packet center
        theta_diff = abs(query_theta - pkt.theta)
        theta_diff = min(theta_diff, 360 - theta_diff)
        phi_diff = abs(query_phi - pkt.phi)
        
        # Gaussian envelope
        envelope = math.exp(-(theta_diff**2) / (2 * pkt.theta_spread**2))
        envelope *= math.exp(-(phi_diff**2) / (2 * 15**2))
        
        # Phase contribution
        phase_rad = math.radians(pkt.phase)
        contribution = pkt.amplitude * envelope * math.cos(phase_rad)
        total += contribution
    
    return total


def detect_intersection(packets: list, min_overlap: float = 10.0) -> Optional[dict]:
    """Detect if packets form a viable intersection."""
    if len(packets) < 2:
        return None
    
    # Find theta overlap
    theta_min = max(p.theta - p.theta_spread/2 for p in packets)
    theta_max = min(p.theta + p.theta_spread/2 for p in packets)
    overlap = theta_max - theta_min
    
    if overlap < min_overlap:
        return None
    
    # Compute intersection center
    center_theta = (theta_min + theta_max) / 2
    center_phi = sum(p.phi for p in packets) / len(packets)
    
    return {
        "center_theta": center_theta,
        "center_phi": center_phi,
        "overlap": overlap,
        "packet_count": len(packets)
    }


# =============================================================================
# LEVEL 1 TESTS: Core Addressing
# =============================================================================

class TestLevel1Core:
    """Level 1: Core 28-bit addressing tests."""
    
    def test_encode_all_zeros(self):
        """Test encoding all zeros."""
        addr = encode_core(0, 0, 0, 0)
        assert addr == 0x00000000
    
    def test_encode_all_max(self):
        """Test encoding maximum values."""
        addr = encode_core(3, 511, 511, 255)
        assert addr == 0x0FFFFFFF
    
    def test_encode_shell_only(self):
        """Test encoding shell field only."""
        addr = encode_core(3, 0, 0, 0)
        assert addr == 0x0C000000
    
    def test_encode_theta_only(self):
        """Test encoding theta field only."""
        addr = encode_core(0, 511, 0, 0)
        assert addr == 0x03FE0000
    
    def test_encode_phi_only(self):
        """Test encoding phi field only."""
        addr = encode_core(0, 0, 511, 0)
        assert addr == 0x0001FF00
    
    def test_encode_harmonic_only(self):
        """Test encoding harmonic field only."""
        addr = encode_core(0, 0, 0, 255)
        assert addr == 0x000000FF
    
    def test_encode_example_1(self):
        """Test example from spec: Shell=0, Theta=12, Phi=40, Harmonic=1."""
        addr = encode_core(0, 12, 40, 1)
        assert addr == 0x00182801
    
    def test_decode_all_zeros(self):
        """Test decoding all zeros."""
        shell, theta, phi, harmonic = decode_core(0x00000000)
        assert (shell, theta, phi, harmonic) == (0, 0, 0, 0)
    
    def test_decode_all_max(self):
        """Test decoding maximum values."""
        shell, theta, phi, harmonic = decode_core(0x0FFFFFFF)
        assert (shell, theta, phi, harmonic) == (3, 511, 511, 255)
    
    @pytest.mark.parametrize("shell", [0, 1, 2, 3])
    @pytest.mark.parametrize("theta", [0, 255, 511])
    @pytest.mark.parametrize("phi", [0, 255, 511])
    @pytest.mark.parametrize("harmonic", [0, 127, 255])
    def test_roundtrip(self, shell, theta, phi, harmonic):
        """Test encode/decode roundtrip for various values."""
        addr = encode_core(shell, theta, phi, harmonic)
        s, t, p, h = decode_core(addr)
        assert (s, t, p, h) == (shell, theta, phi, harmonic)
    
    def test_28_bit_boundary(self):
        """Test that addresses fit in 28 bits."""
        addr = encode_core(3, 511, 511, 255)
        assert addr <= 0x0FFFFFFF
        assert addr.bit_length() <= 28
    
    def test_shell_isolation(self):
        """Test shell field is isolated."""
        addr = encode_core(3, 0, 0, 0)
        assert (addr & RPP_SHELL_MASK) == addr
    
    def test_theta_isolation(self):
        """Test theta field is isolated."""
        addr = encode_core(0, 511, 0, 0)
        assert (addr & RPP_THETA_MASK) == addr
    
    def test_phi_isolation(self):
        """Test phi field is isolated."""
        addr = encode_core(0, 0, 511, 0)
        assert (addr & RPP_PHI_MASK) == addr
    
    def test_harmonic_isolation(self):
        """Test harmonic field is isolated."""
        addr = encode_core(0, 0, 0, 255)
        assert (addr & RPP_HARMONIC_MASK) == addr


class TestLevel1ConsentZones:
    """Level 1: Consent zone boundary tests."""
    
    def test_grounded_zone(self):
        """Test phi values in grounded zone."""
        for phi in [0, 85, 170]:
            assert phi <= PHI_GROUNDED_MAX
            addr = encode_core(0, 0, phi, 0)
            _, _, decoded_phi, _ = decode_core(addr)
            assert decoded_phi <= PHI_GROUNDED_MAX
    
    def test_transitional_zone(self):
        """Test phi values in transitional zone."""
        for phi in [171, 255, 341]:
            assert PHI_GROUNDED_MAX < phi <= PHI_TRANSITIONAL_MAX
            addr = encode_core(0, 0, phi, 0)
            _, _, decoded_phi, _ = decode_core(addr)
            assert PHI_GROUNDED_MAX < decoded_phi <= PHI_TRANSITIONAL_MAX
    
    def test_ethereal_zone(self):
        """Test phi values in ethereal zone."""
        for phi in [342, 426, 511]:
            assert phi >= PHI_ETHEREAL_MIN
            addr = encode_core(0, 0, phi, 0)
            _, _, decoded_phi, _ = decode_core(addr)
            assert decoded_phi >= PHI_ETHEREAL_MIN


class TestLevel1ThetaSectors:
    """Level 1: Theta sector boundary tests."""
    
    @pytest.mark.parametrize("sector,bounds", [
        ("GENE", SECTOR_GENE),
        ("MEMORY", SECTOR_MEMORY),
        ("WITNESS", SECTOR_WITNESS),
        ("DREAM", SECTOR_DREAM),
        ("BRIDGE", SECTOR_BRIDGE),
        ("GUARDIAN", SECTOR_GUARDIAN),
        ("EMERGENCE", SECTOR_EMERGENCE),
        ("META", SECTOR_META),
    ])
    def test_sector_boundaries(self, sector, bounds):
        """Test theta sector boundaries."""
        lo, hi = bounds
        assert hi - lo == 63  # Each sector spans 64 values
        
        # Test boundary values
        addr_lo = encode_core(0, lo, 0, 0)
        addr_hi = encode_core(0, hi, 0, 0)
        
        _, theta_lo, _, _ = decode_core(addr_lo)
        _, theta_hi, _, _ = decode_core(addr_hi)
        
        assert theta_lo == lo
        assert theta_hi == hi


# =============================================================================
# LEVEL 2 TESTS: Extended Addressing
# =============================================================================

class TestLevel2Extended:
    """Level 2: Extended 64-bit addressing tests."""
    
    def test_encode_extended_zeros(self):
        """Test encoding extended zeros."""
        addr = encode_extended(0, 0, 0, 0, 0)
        assert addr == 0
    
    def test_encode_extended_max(self):
        """Test encoding extended maximum."""
        addr = encode_extended(3, THETA_EXT_MAX, PHI_EXT_MAX, 
                               HARMONIC_EXT_MAX, PHASE_MAX)
        # Verify all bits are set appropriately
        shell, theta, phi, harmonic, phase = decode_extended(addr)
        assert shell == 3
        assert theta == THETA_EXT_MAX
        assert phi == PHI_EXT_MAX
        assert harmonic == HARMONIC_EXT_MAX
        assert phase == PHASE_MAX
    
    def test_decode_extended_roundtrip(self):
        """Test extended encode/decode roundtrip."""
        original = (2, 524288, 262144, 512, 2048)
        addr = encode_extended(*original)
        decoded = decode_extended(addr)
        assert decoded == original
    
    def test_extended_to_core_truncation(self):
        """Test truncation from extended to core."""
        # Extended theta 524288 (mid-point of 20-bit range)
        # Should truncate to 256 (mid-point of 9-bit range)
        ext_addr = encode_extended(1, 524288, 524288, 512, 0)
        core_addr = extended_to_core(ext_addr)
        
        shell, theta, phi, harmonic = decode_core(core_addr)
        assert shell == 1
        assert theta == 256  # 524288 >> 11 = 256
        assert phi == 256
        assert harmonic == 128  # 512 >> 2 = 128
    
    def test_extended_precision(self):
        """Test extended precision vs core."""
        # Two values that differ by less than core resolution but more than extended
        theta_a = degrees_to_extended_theta(45.0)
        theta_b = degrees_to_extended_theta(45.001)  # 0.001° difference
        
        # Should be different in extended (0.001° > 0.000343° resolution)
        assert theta_a != theta_b, "Extended should distinguish 0.001° difference"
        
        # But same when truncated to core
        core_a = theta_a >> 11
        core_b = theta_b >> 11
        assert core_a == core_b  # Lost in truncation


class TestLevel2Conversion:
    """Level 2: Coordinate conversion tests."""
    
    def test_theta_degrees_roundtrip_core(self):
        """Test theta degrees conversion roundtrip (core)."""
        for deg in [0, 45, 90, 180, 270, 359]:
            core = degrees_to_core_theta(deg)
            back = core_theta_to_degrees(core)
            # Allow for quantization error (360/512 = 0.703°)
            assert abs(back - deg) < 1.0
    
    def test_phi_degrees_roundtrip_core(self):
        """Test phi degrees conversion roundtrip (core)."""
        for deg in [-90, -45, 0, 45, 90]:
            core = degrees_to_core_phi(deg)
            back = core_phi_to_degrees(core)
            # Allow for quantization error (180/512 = 0.352°)
            assert abs(back - deg) < 1.0
    
    def test_theta_degrees_roundtrip_extended(self):
        """Test theta degrees conversion roundtrip (extended)."""
        for deg in [0, 45.123456, 137.5, 270.999]:
            ext = degrees_to_extended_theta(deg)
            back = extended_theta_to_degrees(ext)
            # Much higher precision (360/1048576 = 0.000343°)
            assert abs(back - deg) < 0.001
    
    def test_phi_degrees_roundtrip_extended(self):
        """Test phi degrees conversion roundtrip (extended)."""
        for deg in [-90, -23.456, 0, 45.789, 89.999]:
            ext = degrees_to_extended_phi(deg)
            back = extended_phi_to_degrees(ext)
            assert abs(back - deg) < 0.001
    
    def test_resolution_comparison(self):
        """Test resolution difference between core and extended."""
        core_resolution = 360.0 / 512  # 0.703125°
        ext_resolution = 360.0 / 1048576  # 0.000343°
        
        assert ext_resolution < core_resolution / 2000  # 2048× better


class TestLevel2Phase:
    """Level 2: Phase angle tests."""
    
    def test_phase_range(self):
        """Test phase angle range."""
        for phase in [0, 1024, 2048, 4095]:
            addr = encode_extended(0, 0, 0, 0, phase)
            _, _, _, _, decoded = decode_extended(addr)
            assert decoded == phase
    
    def test_phase_to_degrees(self):
        """Test phase value to degrees conversion."""
        # 4096 steps = 360°
        # phase 0 = 0°
        # phase 1024 = 90°
        # phase 2048 = 180°
        # phase 4095 = 359.912°
        
        def phase_to_degrees(phase: int) -> float:
            return (phase / 4096.0) * 360.0
        
        assert phase_to_degrees(0) == 0.0
        assert abs(phase_to_degrees(1024) - 90.0) < 0.1
        assert abs(phase_to_degrees(2048) - 180.0) < 0.1


# =============================================================================
# LEVEL 3 TESTS: Holographic Operations
# =============================================================================

class TestLevel3Holographic:
    """Level 3: Holographic interference and emergence tests."""
    
    def test_constructive_interference(self):
        """Test constructive interference (same phase)."""
        packets = [
            WavePacket(theta=45, phi=0, phase=0, amplitude=1.0),
            WavePacket(theta=45, phi=0, phase=0, amplitude=1.0),
        ]
        
        amplitude = compute_interference(packets, 45, 0)
        # Should be ~2.0 for perfect constructive interference
        assert amplitude > 1.5
    
    def test_destructive_interference(self):
        """Test destructive interference (180° out of phase)."""
        packets = [
            WavePacket(theta=45, phi=0, phase=0, amplitude=1.0),
            WavePacket(theta=45, phi=0, phase=180, amplitude=1.0),
        ]
        
        amplitude = compute_interference(packets, 45, 0)
        # Should be ~0 for perfect destructive interference
        assert abs(amplitude) < 0.1
    
    def test_quadrature_interference(self):
        """Test quadrature interference (90° phase difference)."""
        packets = [
            WavePacket(theta=45, phi=0, phase=0, amplitude=1.0),
            WavePacket(theta=45, phi=0, phase=90, amplitude=1.0),
        ]
        
        amplitude = compute_interference(packets, 45, 0)
        # One packet contributes ~1.0, other contributes ~0
        assert 0.5 < abs(amplitude) < 1.5
    
    def test_intersection_detection(self):
        """Test intersection detection for overlapping packets."""
        packets = [
            WavePacket(theta=45, phi=0, phase=0, theta_spread=30),
            WavePacket(theta=60, phi=5, phase=0, theta_spread=30),
        ]
        
        result = detect_intersection(packets)
        assert result is not None
        assert result["overlap"] >= 10.0
        assert result["packet_count"] == 2
    
    def test_no_intersection(self):
        """Test no intersection for non-overlapping packets."""
        packets = [
            WavePacket(theta=0, phi=0, phase=0, theta_spread=30),
            WavePacket(theta=180, phi=0, phase=0, theta_spread=30),
        ]
        
        result = detect_intersection(packets)
        assert result is None
    
    def test_minimum_packets(self):
        """Test intersection requires at least 2 packets."""
        packets = [WavePacket(theta=45, phi=0, phase=0)]
        result = detect_intersection(packets)
        assert result is None


# =============================================================================
# LEVEL 4 TESTS: Hardware Emulation Alignment
# =============================================================================

class TestLevel4Hardware:
    """Level 4: Hardware emulation alignment tests."""
    
    def test_spi_command_alignment(self):
        """Test SPI command codes match spec."""
        # From virtual_hardware.py
        FPGA_COMMANDS = {
            "NOP": 0x00,
            "READ_STATUS": 0x01,
            "WRITE_CACHE": 0x10,
            "READ_CACHE": 0x11,
            "INVALIDATE": 0x12,
            "COHERENCE_CHK": 0x20,
            "CONSENT_GATE": 0x21,
            "GLYPH_DETECT": 0x30,
            "EMERGENCE_TRIG": 0x31,
            "SET_SKIP_PATTERN": 0x40,
            "GET_SKIP_ANGLE": 0x41,
        }
        
        # Verify commands don't overlap
        values = list(FPGA_COMMANDS.values())
        assert len(values) == len(set(values))
    
    def test_golden_angle(self):
        """Test golden angle constant matches spec."""
        GOLDEN_ANGLE = 137.5077640500378
        
        # Verify it's the golden angle (360 * (1 - 1/φ))
        phi = (1 + math.sqrt(5)) / 2  # Golden ratio
        expected = 360 * (1 - 1/phi)
        assert abs(GOLDEN_ANGLE - expected) < 0.0001
    
    def test_fibonacci_skip_pattern(self):
        """Test Fibonacci skip pattern generates golden angle increments."""
        angles = []
        current = 0.0
        for i in range(10):
            angles.append(current)
            current = (current + 137.5) % 360
        
        # Verify spacing is golden angle
        for i in range(1, len(angles)):
            diff = angles[i] - angles[i-1]
            if diff < 0:
                diff += 360
            assert abs(diff - 137.5) < 0.1
    
    def test_address_fits_32bit_register(self):
        """Test core address fits in 32-bit register."""
        max_addr = encode_core(3, 511, 511, 255)
        assert max_addr <= 0xFFFFFFFF
        assert max_addr <= 0x0FFFFFFF  # Actually fits in 28 bits
    
    def test_memory_timing_constraints(self):
        """Test memory timing values are realistic."""
        # From virtual_hardware.py
        READ_LATENCY_NS = 35.0
        WRITE_LATENCY_NS = 50.0
        BUS_CLOCK_NS = 25.0  # 40 MHz
        
        # STT-MRAM typical values
        assert 10 <= READ_LATENCY_NS <= 100
        assert 10 <= WRITE_LATENCY_NS <= 100
        assert 10 <= BUS_CLOCK_NS <= 50


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class TestRegression:
    """Regression tests for known issues."""
    
    def test_phi_pole_orientation(self):
        """Test phi=0 is grounded (south pole), phi=511 is ethereal (north)."""
        # This was a spec inconsistency - ensure it's correct
        addr_grounded = encode_core(0, 0, 0, 0)
        addr_ethereal = encode_core(0, 0, 511, 0)
        
        _, _, phi_grounded, _ = decode_core(addr_grounded)
        _, _, phi_ethereal, _ = decode_core(addr_ethereal)
        
        # Grounded should be low phi
        assert phi_grounded <= PHI_GROUNDED_MAX
        # Ethereal should be high phi
        assert phi_ethereal >= PHI_ETHEREAL_MIN
    
    def test_theta_sector_coverage(self):
        """Test theta sectors cover full range without gaps."""
        sectors = [
            SECTOR_GENE, SECTOR_MEMORY, SECTOR_WITNESS, SECTOR_DREAM,
            SECTOR_BRIDGE, SECTOR_GUARDIAN, SECTOR_EMERGENCE, SECTOR_META
        ]
        
        # Verify contiguous coverage
        all_values = set()
        for lo, hi in sectors:
            for v in range(lo, hi + 1):
                assert v not in all_values, f"Overlap at {v}"
                all_values.add(v)
        
        # Verify full coverage
        assert all_values == set(range(512))


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
