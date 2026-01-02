"""
SPIRAL Protocol - Cross-Domain Alignment Verification
======================================================

This module exhaustively verifies alignment between:
1. Python consent_header.py (reference implementation)
2. HDL spiral_consent.v (hardware implementation)  
3. HDL stub positions (behavioral simulation)
4. Ra System constants (ra_constants_v2.json)

If any of these are misaligned, we risk costly redesign later.
"""

import json
import sys
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Tuple, Final

# =============================================================================
# Constants from ra_constants_v2.json that affect HDL
# =============================================================================

RA_CONSTANTS_AFFECTING_HDL = {
    "THETA_RANGE": (1, 27),       # 27 Repitans -> 5 bits needed
    "PHI_RANGE": (1, 6),          # 6 RAC levels -> 3 bits needed  
    "OMEGA_RANGE": (0, 4),        # 5 Omega formats -> 3 bits needed
    "RADIUS_BITS": 8,             # 256 levels
    "ANKH": 5.08938,              # Master constant
    "GREEN_PHI": 1.62,            # Access threshold
}


# =============================================================================
# Python Layout (from consent_header.py)
# =============================================================================

@dataclass
class PythonByteLayout:
    """18-byte layout from consent_header.py"""
    # Byte offsets
    OFF_RPP_ADDRESS: int = 0      # 4 bytes
    OFF_PACKET_ID: int = 4        # 4 bytes
    OFF_ORIGIN_REF: int = 8       # 2 bytes
    OFF_CONSENT: int = 10         # 1 byte
    OFF_ENTROPY: int = 11         # 1 byte
    OFF_TEMPORAL: int = 12        # 1 byte
    OFF_FALLBACK: int = 13        # 1 byte
    OFF_WINDOW_ID: int = 14       # 2 bytes
    OFF_PHASE_REF: int = 16       # 1 byte
    OFF_CRC: int = 17             # 1 byte
    
    @staticmethod
    def byte_to_bit_range(byte_offset: int, byte_count: int) -> Tuple[int, int]:
        """Convert byte offset to bit range in 144-bit header (big-endian)."""
        # Big-endian: byte 0 is MSB = bits [143:136]
        msb = 143 - (byte_offset * 8)
        lsb = msb - (byte_count * 8) + 1
        return (msb, lsb)


# Consent byte (byte 10) sub-fields
CONSENT_BYTE_LAYOUT = {
    "consent_verbal":    (7, 7, 1),    # bit 7, 1 bit
    "consent_somatic":   (6, 3, 4),    # bits 6:3, 4 bits
    "consent_ancestral": (2, 1, 2),    # bits 2:1, 2 bits
    "temporal_lock":     (0, 0, 1),    # bit 0, 1 bit
}

# Entropy byte (byte 11) sub-fields
ENTROPY_BYTE_LAYOUT = {
    "phase_entropy_index": (7, 3, 5),  # bits 7:3, 5 bits
    "complecount_trace":   (2, 0, 3),  # bits 2:0, 3 bits
}


# =============================================================================
# HDL Layout (from spiral_consent.v)
# =============================================================================

@dataclass
class HDLBitLayout:
    """Bit positions from spiral_consent.v (matches Python byte layout)"""
    
    # RPP Address (bytes 0-3) -> bits 143:112
    rpp_theta:    Tuple[int, int] = (143, 139)  # [31:27] of RPP = [143:139] of header
    rpp_phi:      Tuple[int, int] = (138, 136)  # [26:24] of RPP = [138:136] of header
    rpp_omega:    Tuple[int, int] = (135, 133)  # [23:21] of RPP = [135:133] of header
    rpp_radius:   Tuple[int, int] = (132, 125)  # [20:13] of RPP = [132:125] of header
    rpp_reserved: Tuple[int, int] = (124, 112)  # [12:0] of RPP = [124:112] of header
    
    # Packet ID (bytes 4-7) -> bits 111:80
    packet_id:    Tuple[int, int] = (111, 80)
    
    # Origin Ref (bytes 8-9) -> bits 79:64
    origin_ref:   Tuple[int, int] = (79, 64)
    
    # Consent (byte 10) -> bits 63:56
    consent_verbal:    Tuple[int, int] = (63, 63)   # byte10[7]
    consent_somatic:   Tuple[int, int] = (62, 59)   # byte10[6:3]
    consent_ancestral: Tuple[int, int] = (58, 57)   # byte10[2:1]
    temporal_lock:     Tuple[int, int] = (56, 56)   # byte10[0]
    
    # Entropy (byte 11) -> bits 55:48
    phase_entropy_index: Tuple[int, int] = (55, 51)  # byte11[7:3]
    complecount_trace:   Tuple[int, int] = (50, 48)  # byte11[2:0]
    
    # Temporal/Payload (byte 12) -> bits 47:40
    payload_type: Tuple[int, int] = (43, 40)  # byte12[3:0]
    
    # Fallback (byte 13) -> bits 39:32
    fallback_vector: Tuple[int, int] = (39, 32)
    
    # Window ID (bytes 14-15) -> bits 31:16
    coherence_window_id: Tuple[int, int] = (31, 16)
    
    # Target Phase (byte 16) -> bits 15:8
    target_phase_ref: Tuple[int, int] = (15, 8)
    
    # CRC (byte 17) -> bits 7:0
    header_crc: Tuple[int, int] = (7, 0)


# =============================================================================
# HDL Stub Layout (from hdl_simulation.py - "canonical" per Architect)
# =============================================================================

@dataclass  
class StubBitLayout:
    """
    Bit positions from the 'canonical' stub.
    
    This layout places governance-critical fields at the MSB end,
    which is different from the byte-oriented Python layout.
    """
    coherence_window_id: Tuple[int, int] = (143, 132)  # 12 bits
    phase_entropy_index: Tuple[int, int] = (131, 126)  # 6 bits
    fallback_vector:     Tuple[int, int] = (125, 118)  # 8 bits
    complecount_trace:   Tuple[int, int] = (117, 113)  # 5 bits
    payload_type:        Tuple[int, int] = (112, 109)  # 4 bits
    consent_state:       Tuple[int, int] = (108, 107)  # 2 bits
    reserved:            Tuple[int, int] = (106, 0)    # 107 bits


# =============================================================================
# Alignment Verification
# =============================================================================

def verify_bit_widths() -> List[str]:
    """Verify bit widths match Ra System requirements."""
    issues = []
    
    # Theta: 27 values need ceil(log2(27)) = 5 bits
    hdl = HDLBitLayout()
    theta_width = hdl.rpp_theta[0] - hdl.rpp_theta[1] + 1
    if theta_width < 5:
        issues.append(f"THETA needs 5 bits for 27 Repitans, HDL has {theta_width}")
    
    # Phi: 6 values need ceil(log2(6)) = 3 bits  
    phi_width = hdl.rpp_phi[0] - hdl.rpp_phi[1] + 1
    if phi_width < 3:
        issues.append(f"PHI needs 3 bits for 6 RAC levels, HDL has {phi_width}")
    
    # Omega: 5 values need ceil(log2(5)) = 3 bits
    omega_width = hdl.rpp_omega[0] - hdl.rpp_omega[1] + 1
    if omega_width < 3:
        issues.append(f"OMEGA needs 3 bits for 5 formats, HDL has {omega_width}")
    
    return issues


def verify_python_hdl_alignment() -> List[str]:
    """Verify Python byte layout matches HDL bit layout."""
    issues = []
    py = PythonByteLayout()
    hdl = HDLBitLayout()
    
    # Check each major field
    checks = [
        ("RPP_ADDRESS", py.byte_to_bit_range(py.OFF_RPP_ADDRESS, 4), (143, 112)),
        ("PACKET_ID", py.byte_to_bit_range(py.OFF_PACKET_ID, 4), hdl.packet_id),
        ("ORIGIN_REF", py.byte_to_bit_range(py.OFF_ORIGIN_REF, 2), hdl.origin_ref),
        ("CONSENT_BYTE", py.byte_to_bit_range(py.OFF_CONSENT, 1), (63, 56)),
        ("ENTROPY_BYTE", py.byte_to_bit_range(py.OFF_ENTROPY, 1), (55, 48)),
        ("FALLBACK", py.byte_to_bit_range(py.OFF_FALLBACK, 1), hdl.fallback_vector),
        ("WINDOW_ID", py.byte_to_bit_range(py.OFF_WINDOW_ID, 2), hdl.coherence_window_id),
        ("CRC", py.byte_to_bit_range(py.OFF_CRC, 1), hdl.header_crc),
    ]
    
    for name, py_range, hdl_range in checks:
        if py_range != hdl_range:
            issues.append(f"{name}: Python={py_range}, HDL={hdl_range} - MISMATCH")
    
    return issues


def verify_stub_vs_production() -> List[str]:
    """Compare stub layout to production HDL layout."""
    issues = []
    stub = StubBitLayout()
    hdl = HDLBitLayout()
    
    # These fields exist in both but at different positions
    comparisons = [
        ("coherence_window_id", stub.coherence_window_id, hdl.coherence_window_id),
        ("phase_entropy_index", stub.phase_entropy_index, hdl.phase_entropy_index),
        ("fallback_vector", stub.fallback_vector, hdl.fallback_vector),
        ("complecount_trace", stub.complecount_trace, hdl.complecount_trace),
        ("payload_type", stub.payload_type, hdl.payload_type),
    ]
    
    for name, stub_pos, hdl_pos in comparisons:
        stub_width = stub_pos[0] - stub_pos[1] + 1
        hdl_width = hdl_pos[0] - hdl_pos[1] + 1
        
        if stub_width != hdl_width:
            issues.append(f"{name}: Stub width={stub_width}, HDL width={hdl_width} - WIDTH MISMATCH")
        
        if stub_pos != hdl_pos:
            issues.append(f"{name}: Stub={stub_pos}, HDL={hdl_pos} - POSITION DIFFERS")
    
    # Note: Different position is expected if stub uses a different layout
    # The question is: which is canonical?
    
    return issues


def verify_ra_constants_integration() -> List[str]:
    """Verify Ra constants are properly integrated."""
    issues = []
    
    # Check if rpp-spec has access to ra_system
    try:
        sys.path.insert(0, r'C:\Users\schmi\Documents\GitHub\ra-system\python')
        from ra_system import ANKH, Repitan, RacLevel, OmegaFormat
        from ra_system.repitans import all_repitans
        from ra_system.rac import all_rac_levels
        from ra_system.omega import all_omega_formats
        
        # Verify ranges match HDL expectations
        repitan_count = len(all_repitans())
        if repitan_count != 27:
            issues.append(f"Repitan count: Expected 27, got {repitan_count}")
        
        rac_count = len(all_rac_levels())
        if rac_count != 6:
            issues.append(f"RAC level count: Expected 6, got {rac_count}")
        
        omega_count = len(all_omega_formats())
        if omega_count < 5:
            issues.append(f"Omega format count: Expected >=5, got {omega_count}")
            
    except ImportError as e:
        issues.append(f"ra_system not available: {e}")
    
    return issues


def verify_coherence_score_formula() -> List[str]:
    """Verify coherence score calculation matches Ra constants."""
    issues = []
    
    # Current stub formula: score = (entropy << 1) + complecount
    # This needs to relate to Ra thresholds (1.62, 5.08938, etc.)
    
    # With 6-bit entropy (0-63) and 5-bit complecount (0-31):
    # Max score = (63 << 1) + 31 = 126 + 31 = 157 (needs 8 bits, but masked to 7)
    
    # This is arbitrary - should derive from Ra constants
    # GREEN_PHI = 1.62 as threshold base
    # Threshold scaling: coherence * 100 / 1.62 ?
    
    issues.append("WARNING: CoherenceEvaluator formula not derived from Ra constants")
    issues.append("  Current: score = (entropy << 1) + complecount")
    issues.append("  Should relate to: GREEN_PHI (1.62) or ANKH (5.08938)")
    
    return issues


def generate_canonical_test_vectors() -> Dict[str, int]:
    """Generate test vectors that should work with both layouts."""
    vectors = {}
    
    # All zeros (safe for both)
    vectors["all_zeros"] = 0
    
    # All ones in canonical fields
    vectors["all_ones_canonical"] = (
        (0xFFF << 132) |  # coherence_window_id (stub)
        (0x3F << 126) |   # phase_entropy_index (stub)
        (0xFF << 118) |   # fallback_vector (stub)
        (0x1F << 113) |   # complecount_trace (stub)
        (0xF << 109) |    # payload_type (stub)
        (0x3 << 107)      # consent_state (stub)
    )
    
    return vectors


# =============================================================================
# Main Verification Report
# =============================================================================

def run_full_verification() -> None:
    """Run all alignment checks and report."""
    print("=" * 70)
    print("SPIRAL Protocol - Cross-Domain Alignment Verification")
    print("=" * 70)
    
    all_issues = []
    
    # Check 1: Bit widths match Ra requirements
    print("\n[1] Ra System Bit Width Requirements:")
    issues = verify_bit_widths()
    if issues:
        for i in issues:
            print(f"    ❌ {i}")
        all_issues.extend(issues)
    else:
        print("    ✅ All bit widths match Ra System requirements")
    
    # Check 2: Python/HDL alignment
    print("\n[2] Python consent_header.py ↔ HDL spiral_consent.v:")
    issues = verify_python_hdl_alignment()
    if issues:
        for i in issues:
            print(f"    ❌ {i}")
        all_issues.extend(issues)
    else:
        print("    ✅ Python and HDL layouts are aligned")
    
    # Check 3: Stub vs Production
    print("\n[3] Stub Layout vs Production HDL Layout:")
    issues = verify_stub_vs_production()
    if issues:
        for i in issues:
            print(f"    ⚠️  {i}")
        all_issues.extend(issues)
    else:
        print("    ✅ Stub and production layouts match")
    
    # Check 4: Ra constants integration
    print("\n[4] Ra Constants Integration:")
    issues = verify_ra_constants_integration()
    if issues:
        for i in issues:
            if "not available" in i.lower():
                print(f"    ⚠️  {i}")
            else:
                print(f"    ❌ {i}")
        all_issues.extend(issues)
    else:
        print("    ✅ Ra System properly integrated")
    
    # Check 5: Coherence formula
    print("\n[5] Coherence Score Formula:")
    issues = verify_coherence_score_formula()
    for i in issues:
        print(f"    ⚠️  {i}")
    
    # Summary
    print("\n" + "=" * 70)
    print("ALIGNMENT SUMMARY")
    print("=" * 70)
    
    critical = [i for i in all_issues if "MISMATCH" in i or "needs" in i.lower()]
    warnings = [i for i in all_issues if i not in critical]
    
    print(f"\n  Critical Issues: {len(critical)}")
    print(f"  Warnings:        {len(warnings)}")
    
    if critical:
        print("\n⛔ CRITICAL ISSUES THAT WILL CAUSE REDESIGN:")
        for i in critical:
            print(f"    • {i}")
    
    print("\n" + "=" * 70)
    print("LAYOUT COMPARISON TABLE")
    print("=" * 70)
    
    stub = StubBitLayout()
    hdl = HDLBitLayout()
    
    print(f"\n{'Field':<25} {'Stub [MSB:LSB]':<20} {'HDL [MSB:LSB]':<20} {'Match?'}")
    print("-" * 70)
    
    comparisons = [
        ("coherence_window_id", stub.coherence_window_id, hdl.coherence_window_id),
        ("phase_entropy_index", stub.phase_entropy_index, hdl.phase_entropy_index),
        ("fallback_vector", stub.fallback_vector, hdl.fallback_vector),
        ("complecount_trace", stub.complecount_trace, hdl.complecount_trace),
        ("payload_type", stub.payload_type, hdl.payload_type),
    ]
    
    for name, s, h in comparisons:
        s_str = f"[{s[0]}:{s[1]}]"
        h_str = f"[{h[0]}:{h[1]}]"
        match = "✅" if s == h else "❌"
        print(f"{name:<25} {s_str:<20} {h_str:<20} {match}")
    
    # Additional HDL-only fields
    print(f"\n{'HDL-Only Fields':<25} {'Position [MSB:LSB]':<20} {'Width'}")
    print("-" * 50)
    hdl_only = [
        ("rpp_theta", hdl.rpp_theta),
        ("rpp_phi", hdl.rpp_phi),
        ("rpp_omega", hdl.rpp_omega),
        ("rpp_radius", hdl.rpp_radius),
        ("packet_id", hdl.packet_id),
        ("origin_ref", hdl.origin_ref),
        ("consent_verbal", hdl.consent_verbal),
        ("consent_somatic", hdl.consent_somatic),
        ("consent_ancestral", hdl.consent_ancestral),
        ("header_crc", hdl.header_crc),
    ]
    
    for name, pos in hdl_only:
        width = pos[0] - pos[1] + 1
        print(f"{name:<25} [{pos[0]}:{pos[1]}]{'':>10} {width} bits")


if __name__ == "__main__":
    run_full_verification()
