"""
SPIRAL Protocol - HDL Behavioral Simulation & Verification (Canonical Production)
==================================================================================

CANONICAL LAYOUT: Production byte-oriented format (matches consent_header.py)

This module provides cycle-accurate behavioral models matching:
- spiral_consent.v (production HDL)
- consent_header.py (Python reference)

Field widths (CANONICAL):
- coherence_window_id: 16 bits (bytes 14-15)
- phase_entropy_index: 5 bits (byte 11[7:3])
- complecount_trace: 3 bits (byte 11[2:0])

Coherence formula (Ra-derived):
- GREEN_PHI ≈ 1.618 → scaled to 165 (×100)
- ANKH ≈ 5.089 → scaled to 509 (×100)
- E = phase_entropy_index / 31 (normalized 0.0-1.0)
- C = complecount_trace / 7 (normalized 0.0-1.0)
- coherence_score = (φ × E) + (𝔄 × C)
"""

from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Final
from enum import IntEnum
import time

# =============================================================================
# Ra System Constants (Fixed-Point Scaled ×100)
# =============================================================================

GREEN_PHI_SCALED: Final[int] = 165      # 1.618 × 100 (truncated to 165)
ANKH_SCALED: Final[int] = 509           # 5.089 × 100
SCALE_FACTOR: Final[int] = 100

# Normalization divisors
ENTROPY_MAX: Final[int] = 31
COMPLECOUNT_MAX: Final[int] = 7


# =============================================================================
# Canonical Field Positions (Production Layout)
# =============================================================================

class CanonicalLayout:
    """
    Production byte-oriented layout (18 bytes = 144 bits).
    Big-endian: byte 0 = MSB = header[143:136]
    """
    # Byte offsets
    OFF_RPP_ADDRESS = 0      # bytes 0-3 (32 bits)
    OFF_PACKET_ID = 4        # bytes 4-7 (32 bits)
    OFF_ORIGIN_REF = 8       # bytes 8-9 (16 bits)
    OFF_CONSENT = 10         # byte 10 (8 bits)
    OFF_ENTROPY = 11         # byte 11 (8 bits)
    OFF_TEMPORAL = 12        # byte 12 (8 bits)
    OFF_FALLBACK = 13        # byte 13 (8 bits)
    OFF_WINDOW_ID = 14       # bytes 14-15 (16 bits)
    OFF_PHASE_REF = 16       # byte 16 (8 bits)
    OFF_CRC = 17             # byte 17 (8 bits)
    
    # Bit positions in 144-bit header (big-endian)
    # RPP Address (bytes 0-3) → bits [143:112]
    RPP_THETA = (143, 139)      # 5 bits
    RPP_PHI = (138, 136)        # 3 bits
    RPP_OMEGA = (135, 133)      # 3 bits
    RPP_RADIUS = (132, 125)     # 8 bits
    RPP_RESERVED = (124, 112)   # 13 bits
    
    # Packet ID (bytes 4-7) → bits [111:80]
    PACKET_ID = (111, 80)       # 32 bits
    
    # Origin Ref (bytes 8-9) → bits [79:64]
    ORIGIN_REF = (79, 64)       # 16 bits
    
    # Consent byte (byte 10) → bits [63:56]
    CONSENT_VERBAL = (63, 63)       # 1 bit
    CONSENT_SOMATIC = (62, 59)      # 4 bits
    CONSENT_ANCESTRAL = (58, 57)    # 2 bits
    TEMPORAL_LOCK = (56, 56)        # 1 bit
    
    # Entropy byte (byte 11) → bits [55:48]
    PHASE_ENTROPY_INDEX = (55, 51)  # 5 bits
    COMPLECOUNT_TRACE = (50, 48)    # 3 bits
    
    # Temporal/Payload byte (byte 12) → bits [47:40]
    PAYLOAD_TYPE = (43, 40)         # 4 bits (lower nibble)
    
    # Fallback (byte 13) → bits [39:32]
    FALLBACK_VECTOR = (39, 32)      # 8 bits
    
    # Window ID (bytes 14-15) → bits [31:16]
    COHERENCE_WINDOW_ID = (31, 16)  # 16 bits
    
    # Target Phase (byte 16) → bits [15:8]
    TARGET_PHASE_REF = (15, 8)      # 8 bits
    
    # CRC (byte 17) → bits [7:0]
    HEADER_CRC = (7, 0)             # 8 bits


# =============================================================================
# VCD Waveform Writer
# =============================================================================

class VCDWriter:
    """Generates Value Change Dump files for GTKWave."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.signals: Dict[str, Tuple[str, int]] = {}
        self.id_counter = 0
        self.current_time = 0
        self.file = None
        
    def _next_id(self) -> str:
        chars = "!\"#$%&'()*+,-./:;<=>?@[]^_`{|}~"
        chars += "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        idx = self.id_counter
        self.id_counter += 1
        if idx < len(chars):
            return chars[idx]
        return chars[idx // len(chars)] + chars[idx % len(chars)]
    
    def add_signal(self, name: str, width: int = 1, module: str = "tb") -> str:
        full_name = f"{module}.{name}"
        sig_id = self._next_id()
        self.signals[full_name] = (sig_id, width)
        return sig_id
    
    def begin(self):
        self.file = open(self.filename, 'w')
        self.file.write(f"$date\n   {time.strftime('%Y-%m-%d %H:%M:%S')}\n$end\n")
        self.file.write("$version\n   SPIRAL HDL Simulation v2.1-RaCanonical\n$end\n")
        self.file.write("$timescale 1ns $end\n")
        
        self.file.write("$scope module tb $end\n")
        for name, (sig_id, width) in self.signals.items():
            short_name = name.split('.')[-1]
            self.file.write(f"$var wire {width} {sig_id} {short_name} $end\n")
        self.file.write("$upscope $end\n")
        self.file.write("$enddefinitions $end\n")
        self.file.write("#0\n")
        self.file.write("$dumpvars\n")
        
    def change(self, name: str, value: int, module: str = "tb"):
        full_name = f"{module}.{name}"
        if full_name not in self.signals:
            return
        sig_id, width = self.signals[full_name]
        if width == 1:
            self.file.write(f"{value}{sig_id}\n")
        else:
            self.file.write(f"b{value:0{width}b} {sig_id}\n")
    
    def advance(self, time_ns: int):
        if time_ns > self.current_time:
            self.current_time = time_ns
            self.file.write(f"#{time_ns}\n")
    
    def end(self):
        if self.file:
            self.file.close()


# =============================================================================
# Consent State Enumeration
# =============================================================================

class ConsentState(IntEnum):
    FULL_CONSENT = 0
    DIMINISHED_CONSENT = 1
    SUSPENDED_CONSENT = 2
    EMERGENCY_OVERRIDE = 3


# =============================================================================
# HDL Module Behavioral Models (Production Layout)
# =============================================================================

@dataclass
class ConsentHeaderParser:
    """
    Behavioral model of ConsentHeaderParser (Production Layout).
    
    Matches spiral_consent.v and consent_header.py exactly.
    """
    # RPP Address fields (bytes 0-3)
    rpp_theta: int = 0              # 5 bits [143:139]
    rpp_phi: int = 0                # 3 bits [138:136]
    rpp_omega: int = 0              # 3 bits [135:133]
    rpp_radius: int = 0             # 8 bits [132:125]
    rpp_reserved: int = 0           # 13 bits [124:112]
    
    # Packet identification
    packet_id: int = 0              # 32 bits [111:80]
    origin_ref: int = 0             # 16 bits [79:64]
    
    # Consent fields (byte 10)
    consent_verbal: bool = True     # 1 bit [63]
    consent_somatic: int = 15       # 4 bits [62:59]
    consent_ancestral: int = 0      # 2 bits [58:57]
    temporal_lock: bool = False     # 1 bit [56]
    
    # Entropy fields (byte 11)
    phase_entropy_index: int = 0    # 5 bits [55:51]
    complecount_trace: int = 0      # 3 bits [50:48]
    
    # Temporal/Payload (byte 12)
    payload_type: int = 0           # 4 bits [43:40]
    
    # Routing
    fallback_vector: int = 0        # 8 bits [39:32]
    coherence_window_id: int = 0    # 16 bits [31:16]
    target_phase_ref: int = 0       # 8 bits [15:8]
    
    # CRC
    header_crc: int = 0             # 8 bits [7:0]
    
    # Derived
    consent_state: ConsentState = ConsentState.FULL_CONSENT
    needs_fallback: bool = False
    has_pma_link: bool = False
    
    def _extract_bits(self, header: int, msb: int, lsb: int) -> int:
        """Extract bit field from header."""
        width = msb - lsb + 1
        mask = (1 << width) - 1
        return (header >> lsb) & mask
    
    def parse(self, header: int) -> None:
        """Parse 144-bit header using production layout."""
        L = CanonicalLayout
        
        # RPP Address fields
        self.rpp_theta = self._extract_bits(header, *L.RPP_THETA)
        self.rpp_phi = self._extract_bits(header, *L.RPP_PHI)
        self.rpp_omega = self._extract_bits(header, *L.RPP_OMEGA)
        self.rpp_radius = self._extract_bits(header, *L.RPP_RADIUS)
        self.rpp_reserved = self._extract_bits(header, *L.RPP_RESERVED)
        
        # Packet ID and Origin
        self.packet_id = self._extract_bits(header, *L.PACKET_ID)
        self.origin_ref = self._extract_bits(header, *L.ORIGIN_REF)
        
        # Consent fields
        self.consent_verbal = bool(self._extract_bits(header, *L.CONSENT_VERBAL))
        self.consent_somatic = self._extract_bits(header, *L.CONSENT_SOMATIC)
        self.consent_ancestral = self._extract_bits(header, *L.CONSENT_ANCESTRAL)
        self.temporal_lock = bool(self._extract_bits(header, *L.TEMPORAL_LOCK))
        
        # Entropy fields
        self.phase_entropy_index = self._extract_bits(header, *L.PHASE_ENTROPY_INDEX)
        self.complecount_trace = self._extract_bits(header, *L.COMPLECOUNT_TRACE)
        
        # Payload
        self.payload_type = self._extract_bits(header, *L.PAYLOAD_TYPE)
        
        # Routing
        self.fallback_vector = self._extract_bits(header, *L.FALLBACK_VECTOR)
        self.coherence_window_id = self._extract_bits(header, *L.COHERENCE_WINDOW_ID)
        self.target_phase_ref = self._extract_bits(header, *L.TARGET_PHASE_REF)
        
        # CRC
        self.header_crc = self._extract_bits(header, *L.HEADER_CRC)
        
        # Derive consent state (matches HDL logic)
        self._derive_consent_state()
        
        # Derive flags
        self.needs_fallback = self.phase_entropy_index > 25
        self.has_pma_link = self.coherence_window_id != 0
    
    def _derive_consent_state(self) -> None:
        """Derive consent state from somatic and verbal consent."""
        if self.consent_somatic < 3:  # < 0.2 (3/15)
            self.consent_state = ConsentState.SUSPENDED_CONSENT
        elif self.consent_somatic < 8 and not self.consent_verbal:  # < 0.5
            self.consent_state = ConsentState.DIMINISHED_CONSENT
        else:
            self.consent_state = ConsentState.FULL_CONSENT


@dataclass
class CoherenceEvaluator:
    """
    Behavioral model of CoherenceEvaluator with Ra-derived formula.
    
    Formula (scaled integer math):
        E = phase_entropy_index (0-31)
        C = complecount_trace (0-7)
        
        coherence_score = (GREEN_PHI_SCALED × E / 31) + (ANKH_SCALED × C / 7)
        
    In fixed-point (×100 scale):
        score = (165 × E / 31) + (509 × C / 7)
        
    Maximum possible score:
        (165 × 31 / 31) + (509 × 7 / 7) = 165 + 509 = 674
    """
    coherence_score: int = 0        # Scaled ×100 (0-674)
    coherence_valid: bool = False
    
    # Intermediate values for debugging
    entropy_contribution: int = 0
    complecount_contribution: int = 0
    
    def evaluate(self, phase_entropy_index: int, complecount_trace: int,
                 threshold: int) -> None:
        """
        Evaluate coherence using Ra-derived formula.
        
        Args:
            phase_entropy_index: 5-bit value (0-31)
            complecount_trace: 3-bit value (0-7)
            threshold: Scaled threshold (×100), e.g., 420 for 4.2
        """
        # Clamp inputs
        E = min(31, max(0, phase_entropy_index))
        C = min(7, max(0, complecount_trace))
        
        # Ra-derived formula (integer division to avoid floats)
        # entropy_contribution = GREEN_PHI × (E / 31)
        # Using: (GREEN_PHI_SCALED × E) / 31
        self.entropy_contribution = (GREEN_PHI_SCALED * E) // ENTROPY_MAX if ENTROPY_MAX > 0 else 0
        
        # complecount_contribution = ANKH × (C / 7)
        # Using: (ANKH_SCALED × C) / 7
        self.complecount_contribution = (ANKH_SCALED * C) // COMPLECOUNT_MAX if COMPLECOUNT_MAX > 0 else 0
        
        # Total score
        self.coherence_score = self.entropy_contribution + self.complecount_contribution
        
        # Threshold comparison
        self.coherence_valid = self.coherence_score >= threshold
    
    @staticmethod
    def score_to_float(scaled_score: int) -> float:
        """Convert scaled score back to float for display."""
        return scaled_score / SCALE_FACTOR


@dataclass
class ScalarTrigger:
    """
    Behavioral model of ScalarTrigger.
    
    Triggers when coherence remains above threshold for N cycles.
    """
    scalar_triggered: bool = False
    cycle_counter: int = 0
    
    def reset(self) -> None:
        self.scalar_triggered = False
        self.cycle_counter = 0
    
    def clock(self, coherence_score: int, activation_threshold: int,
              coherence_duration: int) -> None:
        """
        Process one clock cycle.
        
        Args:
            coherence_score: Current Ra-derived coherence score (×100)
            activation_threshold: Threshold for activation (×100)
            coherence_duration: Required cycles to trigger
        """
        if coherence_score >= activation_threshold:
            self.cycle_counter += 1
            if self.cycle_counter >= coherence_duration:
                self.scalar_triggered = True
                self.cycle_counter = coherence_duration  # Clamp
        else:
            self.cycle_counter = 0
            self.scalar_triggered = False


@dataclass
class FallbackResolver:
    """
    Behavioral model of FallbackResolver.
    
    XOR-based fallback address generation.
    """
    rpp_fallback_address: int = 0
    
    def resolve(self, trigger_fallback: bool, base_address: int, 
                fallback_vector: int) -> None:
        """Generate fallback address using XOR logic."""
        if trigger_fallback:
            self.rpp_fallback_address = base_address ^ fallback_vector
        else:
            self.rpp_fallback_address = 0


@dataclass
class PhaseMemoryAnchorRAM:
    """
    Behavioral model of PMA RAM.
    
    64-entry dual-port RAM, 144 bits per entry.
    """
    memory: Dict[int, int] = field(default_factory=dict)
    read_data: int = 0
    
    def write(self, address: int, data: int) -> None:
        """Write to PMA RAM."""
        addr = address & 0x3F  # 6-bit address
        self.memory[addr] = data & ((1 << 144) - 1)
    
    def read(self, address: int) -> int:
        """Read from PMA RAM."""
        addr = address & 0x3F
        self.read_data = self.memory.get(addr, 0)
        return self.read_data


# =============================================================================
# Header Builder (Production Layout)
# =============================================================================

def build_consent_header(
    rpp_theta: int = 0,
    rpp_phi: int = 0,
    rpp_omega: int = 0,
    rpp_radius: int = 0,
    rpp_reserved: int = 0,
    packet_id: int = 0,
    origin_ref: int = 0,
    consent_verbal: bool = True,
    consent_somatic: int = 15,
    consent_ancestral: int = 0,
    temporal_lock: bool = False,
    phase_entropy_index: int = 0,
    complecount_trace: int = 0,
    payload_type: int = 0,
    fallback_vector: int = 0,
    coherence_window_id: int = 0,
    target_phase_ref: int = 0,
    header_crc: int = 0
) -> int:
    """
    Build 144-bit consent header from fields (Production Layout).
    """
    header = 0
    L = CanonicalLayout
    
    def set_bits(value: int, msb: int, lsb: int) -> int:
        width = msb - lsb + 1
        mask = (1 << width) - 1
        return (value & mask) << lsb
    
    # RPP Address
    header |= set_bits(rpp_theta, *L.RPP_THETA)
    header |= set_bits(rpp_phi, *L.RPP_PHI)
    header |= set_bits(rpp_omega, *L.RPP_OMEGA)
    header |= set_bits(rpp_radius, *L.RPP_RADIUS)
    header |= set_bits(rpp_reserved, *L.RPP_RESERVED)
    
    # Packet ID and Origin
    header |= set_bits(packet_id, *L.PACKET_ID)
    header |= set_bits(origin_ref, *L.ORIGIN_REF)
    
    # Consent fields
    header |= set_bits(1 if consent_verbal else 0, *L.CONSENT_VERBAL)
    header |= set_bits(consent_somatic, *L.CONSENT_SOMATIC)
    header |= set_bits(consent_ancestral, *L.CONSENT_ANCESTRAL)
    header |= set_bits(1 if temporal_lock else 0, *L.TEMPORAL_LOCK)
    
    # Entropy fields
    header |= set_bits(phase_entropy_index, *L.PHASE_ENTROPY_INDEX)
    header |= set_bits(complecount_trace, *L.COMPLECOUNT_TRACE)
    
    # Payload
    header |= set_bits(payload_type, *L.PAYLOAD_TYPE)
    
    # Routing
    header |= set_bits(fallback_vector, *L.FALLBACK_VECTOR)
    header |= set_bits(coherence_window_id, *L.COHERENCE_WINDOW_ID)
    header |= set_bits(target_phase_ref, *L.TARGET_PHASE_REF)
    
    # CRC
    header |= set_bits(header_crc, *L.HEADER_CRC)
    
    return header


# =============================================================================
# Test Framework
# =============================================================================

class SPIRALTestbench:
    """Complete test framework for SPIRAL HDL modules."""
    
    def __init__(self):
        self.parser = ConsentHeaderParser()
        self.coherence = CoherenceEvaluator()
        self.scalar = ScalarTrigger()
        self.fallback = FallbackResolver()
        self.pma = PhaseMemoryAnchorRAM()
        
        self.vcd = VCDWriter("spiral_sim_canonical.vcd")
        self.log_file = open("spiral_sim_canonical_trace.log", "w")
        
        self.clock_period = 10  # ns
        self.sim_time = 0
        
        self.tests_passed = 0
        self.tests_failed = 0
        self.coverage: Dict[str, int] = {}
        
        self._setup_vcd()
    
    def _setup_vcd(self):
        """Register all signals for VCD tracing."""
        # Clock and control
        self.vcd.add_signal("clk", 1)
        self.vcd.add_signal("reset", 1)
        self.vcd.add_signal("enable", 1)
        
        # Parser outputs
        self.vcd.add_signal("rpp_theta", 5)
        self.vcd.add_signal("rpp_phi", 3)
        self.vcd.add_signal("rpp_omega", 3)
        self.vcd.add_signal("rpp_radius", 8)
        self.vcd.add_signal("consent_verbal", 1)
        self.vcd.add_signal("consent_somatic", 4)
        self.vcd.add_signal("phase_entropy_index", 5)
        self.vcd.add_signal("complecount_trace", 3)
        self.vcd.add_signal("fallback_vector", 8)
        self.vcd.add_signal("coherence_window_id", 16)
        self.vcd.add_signal("consent_state", 2)
        
        # Coherence signals (Ra-derived)
        self.vcd.add_signal("coherence_score", 10)  # 0-674
        self.vcd.add_signal("coherence_threshold", 10)
        self.vcd.add_signal("coherence_valid", 1)
        self.vcd.add_signal("entropy_contribution", 8)
        self.vcd.add_signal("complecount_contribution", 9)
        
        # Scalar trigger
        self.vcd.add_signal("scalar_triggered", 1)
        self.vcd.add_signal("cycle_counter", 4)
        
        # Fallback
        self.vcd.add_signal("trigger_fallback", 1)
        self.vcd.add_signal("rpp_fallback_address", 32)
        
        self.vcd.begin()
    
    def _log(self, msg: str):
        """Log with timestamp."""
        line = f"[{self.sim_time:>6}ns] {msg}"
        print(line)
        # Use ASCII-safe replacement for arrow
        safe_line = line.replace('\u2192', '->')
        self.log_file.write(safe_line + "\n")
    
    def _clock_cycle(self):
        """Advance one clock cycle."""
        self.sim_time += self.clock_period
        self.vcd.advance(self.sim_time)
    
    def _check(self, name: str, actual, expected) -> bool:
        """Check and log test result."""
        passed = actual == expected
        status = "PASS" if passed else "FAIL"
        
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
        
        self._log(f"  [{status}] {name}: {actual} (expected {expected})")
        self.coverage[name] = self.coverage.get(name, 0) + 1
        
        return passed
    
    def _record_vcd(self, **signals):
        """Record signal values to VCD."""
        for name, value in signals.items():
            self.vcd.change(name, int(value))
    
    # =========================================================================
    # Test Cases
    # =========================================================================
    
    def test_consent_header_parsing(self):
        """Test 1: Consent Header Parser (Production Layout)."""
        self._log("=" * 70)
        self._log("TEST 1: ConsentHeaderParser (Production Canonical Layout)")
        self._log("=" * 70)
        
        test_cases = [
            # (description, field_dict)
            ("All zeros", {}),
            
            ("Full consent, low entropy", {
                "rpp_theta": 9, "rpp_phi": 3, "rpp_omega": 2, "rpp_radius": 128,
                "packet_id": 0x12345678, "origin_ref": 0xABCD,
                "consent_verbal": True, "consent_somatic": 15,
                "phase_entropy_index": 5, "complecount_trace": 2,
                "coherence_window_id": 0x1234,
            }),
            
            ("Diminished consent (somatic < 0.5, no verbal)", {
                "consent_verbal": False, "consent_somatic": 7,
                "phase_entropy_index": 15, "complecount_trace": 5,
            }),
            
            ("Suspended consent (somatic < 0.2)", {
                "consent_somatic": 2,
                "phase_entropy_index": 31, "complecount_trace": 7,
            }),
            
            ("Max theta (27)", {
                "rpp_theta": 27, "rpp_phi": 6, "rpp_omega": 4,
            }),
            
            ("High entropy triggers fallback", {
                "phase_entropy_index": 28,  # > 25
                "fallback_vector": 0xAA,
            }),
            
            ("PMA linked", {
                "coherence_window_id": 0xFFFF,
            }),
            
            ("All max values", {
                "rpp_theta": 31, "rpp_phi": 7, "rpp_omega": 7, "rpp_radius": 255,
                "rpp_reserved": 0x1FFF,
                "packet_id": 0xFFFFFFFF, "origin_ref": 0xFFFF,
                "consent_verbal": True, "consent_somatic": 15,
                "consent_ancestral": 3, "temporal_lock": True,
                "phase_entropy_index": 31, "complecount_trace": 7,
                "payload_type": 15,
                "fallback_vector": 255, "coherence_window_id": 0xFFFF,
                "target_phase_ref": 255, "header_crc": 255,
            }),
        ]
        
        for desc, fields in test_cases:
            self._log(f"\n  Testing: {desc}")
            
            # Build header
            header = build_consent_header(**fields)
            
            # Parse header
            self.parser.parse(header)
            
            # Verify each field
            expected = {
                "rpp_theta": fields.get("rpp_theta", 0),
                "rpp_phi": fields.get("rpp_phi", 0),
                "rpp_omega": fields.get("rpp_omega", 0),
                "rpp_radius": fields.get("rpp_radius", 0),
                "packet_id": fields.get("packet_id", 0),
                "origin_ref": fields.get("origin_ref", 0),
                "consent_verbal": fields.get("consent_verbal", True),
                "consent_somatic": fields.get("consent_somatic", 15),
                "phase_entropy_index": fields.get("phase_entropy_index", 0),
                "complecount_trace": fields.get("complecount_trace", 0),
                "fallback_vector": fields.get("fallback_vector", 0),
                "coherence_window_id": fields.get("coherence_window_id", 0),
            }
            
            self._check(f"rpp_theta ({desc})", self.parser.rpp_theta, expected["rpp_theta"])
            self._check(f"rpp_phi ({desc})", self.parser.rpp_phi, expected["rpp_phi"])
            self._check(f"rpp_omega ({desc})", self.parser.rpp_omega, expected["rpp_omega"])
            self._check(f"rpp_radius ({desc})", self.parser.rpp_radius, expected["rpp_radius"])
            self._check(f"phase_entropy ({desc})", self.parser.phase_entropy_index, expected["phase_entropy_index"])
            self._check(f"complecount ({desc})", self.parser.complecount_trace, expected["complecount_trace"])
            self._check(f"coherence_window_id ({desc})", self.parser.coherence_window_id, expected["coherence_window_id"])
            
            # Record VCD
            self._record_vcd(
                rpp_theta=self.parser.rpp_theta,
                rpp_phi=self.parser.rpp_phi,
                rpp_omega=self.parser.rpp_omega,
                phase_entropy_index=self.parser.phase_entropy_index,
                complecount_trace=self.parser.complecount_trace,
                coherence_window_id=self.parser.coherence_window_id,
                consent_state=self.parser.consent_state,
            )
            self._clock_cycle()
    
    def test_coherence_evaluator_ra(self):
        """Test 2: CoherenceEvaluator with Ra-derived formula."""
        self._log("\n" + "=" * 70)
        self._log("TEST 2: CoherenceEvaluator (Ra-Derived Formula)")
        self._log("=" * 70)
        self._log(f"  GREEN_PHI (scaled): {GREEN_PHI_SCALED} (= 1.65)")
        self._log(f"  ANKH (scaled):      {ANKH_SCALED} (= 5.09)")
        self._log(f"  Max score: {GREEN_PHI_SCALED} + {ANKH_SCALED} = {GREEN_PHI_SCALED + ANKH_SCALED}")
        
        # Thresholds in scaled units (×100)
        # 4.2 → 420, 5.1 → 510, 6.0 → 600
        thresholds = [420, 510, 600]
        
        for threshold in thresholds:
            self._log(f"\n  Threshold: {threshold/100:.2f} (scaled: {threshold})")
            
            # Full sweep: entropy (0-31) × complecount (0-7)
            for entropy in range(32):
                for complecount in range(8):
                    self.coherence.evaluate(entropy, complecount, threshold)
                    
                    # Manually compute expected
                    exp_entropy_contrib = (GREEN_PHI_SCALED * entropy) // 31 if entropy > 0 else 0
                    exp_comple_contrib = (ANKH_SCALED * complecount) // 7 if complecount > 0 else 0
                    exp_score = exp_entropy_contrib + exp_comple_contrib
                    exp_valid = exp_score >= threshold
                    
                    # Check score
                    self._check(
                        f"score(E={entropy},C={complecount},T={threshold})",
                        self.coherence.coherence_score,
                        exp_score
                    )
                    
                    # Check validity
                    self._check(
                        f"valid(E={entropy},C={complecount},T={threshold})",
                        self.coherence.coherence_valid,
                        exp_valid
                    )
                    
                    # Record VCD for interesting cases
                    if entropy % 8 == 0 and complecount in [0, 3, 7]:
                        self._record_vcd(
                            phase_entropy_index=entropy,
                            complecount_trace=complecount,
                            coherence_score=self.coherence.coherence_score,
                            coherence_threshold=threshold,
                            coherence_valid=int(self.coherence.coherence_valid),
                            entropy_contribution=self.coherence.entropy_contribution,
                            complecount_contribution=self.coherence.complecount_contribution,
                        )
                        self._clock_cycle()
        
        # Log some example scores
        self._log("\n  Example scores:")
        for e, c in [(0, 0), (15, 3), (31, 7), (20, 5)]:
            self.coherence.evaluate(e, c, 0)
            self._log(f"    E={e}, C={c} -> score={self.coherence.coherence_score} "
                     f"({self.coherence.coherence_score/100:.2f})")
    
    def test_scalar_trigger_timing(self):
        """Test 3: ScalarTrigger timing with Ra thresholds."""
        self._log("\n" + "=" * 70)
        self._log("TEST 3: ScalarTrigger Timing (Ra-Derived)")
        self._log("=" * 70)
        
        # Test with Ra-derived threshold (e.g., 4.2 = 420 scaled)
        activation_threshold = 420
        
        for duration in [1, 2, 3, 5, 8]:
            self._log(f"\n  Duration: {duration} cycles, Threshold: {activation_threshold/100:.2f}")
            self.scalar.reset()
            
            # Score that passes threshold (e.g., E=20, C=4 → ~106 + ~290 = ~396... need higher)
            # E=25, C=5 → (165×25/31) + (509×5/7) = 133 + 363 = 496 ✓
            high_score = 500  # Above threshold
            low_score = 300   # Below threshold
            
            self._record_vcd(reset=1, coherence_threshold=activation_threshold)
            self._clock_cycle()
            self._record_vcd(reset=0, enable=1)
            
            # Apply high score for duration + 2 cycles
            # Model triggers when cycle_counter >= coherence_duration
            # After clock(), counter is incremented THEN checked
            # So cycle 0 -> counter=1, triggers if duration=1
            # cycle N -> counter=N+1, triggers if duration <= N+1
            self._log(f"    Applying score={high_score} (above threshold)")
            for cycle in range(duration + 2):
                self.scalar.clock(high_score, activation_threshold, duration)
                
                # After clock: counter = cycle + 1 (since we started from reset)
                # Trigger fires when counter >= duration, i.e., cycle + 1 >= duration
                expected_triggered = (cycle + 1) >= duration
                self._check(
                    f"triggered@cycle{cycle}(d={duration})",
                    self.scalar.scalar_triggered,
                    expected_triggered
                )
                
                self._record_vcd(
                    coherence_score=high_score,
                    scalar_triggered=int(self.scalar.scalar_triggered),
                    cycle_counter=self.scalar.cycle_counter,
                )
                self._clock_cycle()
            
            # Apply low score - should reset
            self._log(f"    Applying score={low_score} (below threshold)")
            self.scalar.clock(low_score, activation_threshold, duration)
            self._check(f"reset_after_low(d={duration})", self.scalar.scalar_triggered, False)
            self._check(f"counter_reset(d={duration})", self.scalar.cycle_counter, 0)
    
    def test_fallback_resolver(self):
        """Test 4: FallbackResolver XOR logic."""
        self._log("\n" + "=" * 70)
        self._log("TEST 4: FallbackResolver XOR Logic")
        self._log("=" * 70)
        
        base_address = 0x12345678
        
        test_vectors = [
            (False, 0x00, 0, "No trigger"),
            (True, 0x00, base_address ^ 0x00, "Zero vector"),
            (True, 0xFF, base_address ^ 0xFF, "Full vector"),
            (True, 0x55, base_address ^ 0x55, "Alternating 01"),
            (True, 0xAA, base_address ^ 0xAA, "Alternating 10"),
            (True, 0x0F, base_address ^ 0x0F, "Low nibble"),
            (True, 0xF0, base_address ^ 0xF0, "High nibble"),
        ]
        
        for trigger, vector, expected, desc in test_vectors:
            self.fallback.resolve(trigger, base_address, vector)
            self._check(f"fallback({desc})", self.fallback.rpp_fallback_address, expected)
            
            self._record_vcd(
                trigger_fallback=int(trigger),
                fallback_vector=vector,
                rpp_fallback_address=self.fallback.rpp_fallback_address,
            )
            self._clock_cycle()
    
    def test_pma_ram(self):
        """Test 5: PhaseMemoryAnchorRAM."""
        self._log("\n" + "=" * 70)
        self._log("TEST 5: PhaseMemoryAnchorRAM")
        self._log("=" * 70)
        
        test_data = [
            (0, 0xCAFEBABE12345678DEADBEEF00112233),
            (1, 0xDEADBEEF),
            (63, 0x123456789ABCDEF0123456789ABCDEF),
            (32, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF),
        ]
        
        for addr, data in test_data:
            self.pma.write(addr, data)
            read_back = self.pma.read(addr)
            expected = data & ((1 << 144) - 1)
            self._check(f"pma_write_read@{addr}", read_back, expected)
            
            self._clock_cycle()
    
    def test_integration_scenarios(self):
        """Test 6: Integration Scenarios."""
        self._log("\n" + "=" * 70)
        self._log("TEST 6: Integration Scenarios")
        self._log("=" * 70)
        
        scenarios = [
            # (entropy, complecount, threshold, scalar_duration, consent_somatic, consent_verbal, desc)
            (20, 5, 420, 3, 15, True, "Normal: high coherence, full consent"),
            (5, 1, 420, 3, 15, True, "Low coherence triggers fallback"),
            (25, 6, 420, 3, 15, True, "Scalar trigger activates"),
            (20, 5, 420, 3, 7, False, "Diminished consent blocks"),
            (20, 5, 420, 3, 2, True, "Suspended consent blocks"),
            (28, 7, 420, 3, 15, True, "High entropy + max complecount"),
        ]
        
        for entropy, complecount, threshold, duration, somatic, verbal, desc in scenarios:
            self._log(f"\n  Scenario: {desc}")
            
            # Build header
            header = build_consent_header(
                phase_entropy_index=entropy,
                complecount_trace=complecount,
                consent_somatic=somatic,
                consent_verbal=verbal,
                fallback_vector=0xAB,
                coherence_window_id=0x1234,
            )
            
            # Parse
            self.parser.parse(header)
            
            # Evaluate coherence
            self.coherence.evaluate(entropy, complecount, threshold)
            
            # Run scalar trigger for duration cycles
            self.scalar.reset()
            for _ in range(duration + 1):
                self.scalar.clock(self.coherence.coherence_score, threshold, duration)
            
            # Resolve fallback
            should_fallback = not self.coherence.coherence_valid
            self.fallback.resolve(should_fallback, 0x12345678, self.parser.fallback_vector)
            
            # Determine routing decision
            consent_ok = self.parser.consent_state == ConsentState.FULL_CONSENT
            can_route = self.coherence.coherence_valid and consent_ok
            
            self._log(f"    coherence_score={self.coherence.coherence_score} "
                     f"({self.coherence.coherence_score/100:.2f})")
            self._log(f"    coherence_valid={self.coherence.coherence_valid}")
            self._log(f"    scalar_triggered={self.scalar.scalar_triggered}")
            self._log(f"    consent_state={self.parser.consent_state.name}")
            self._log(f"    should_fallback={should_fallback}")
            self._log(f"    can_route={can_route}")
            
            self._record_vcd(
                phase_entropy_index=entropy,
                complecount_trace=complecount,
                coherence_score=self.coherence.coherence_score,
                coherence_valid=int(self.coherence.coherence_valid),
                scalar_triggered=int(self.scalar.scalar_triggered),
                consent_state=self.parser.consent_state,
                trigger_fallback=int(should_fallback),
            )
            self._clock_cycle()
            
            self.coverage[f"integration_{desc.replace(' ', '_')[:20]}"] = 1
    
    def run_all_tests(self):
        """Run complete test suite."""
        self._log("=" * 70)
        self._log("SPIRAL Protocol HDL Simulation (Production Canonical)")
        self._log("=" * 70)
        self._log(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"Ra Constants: GREEN_PHI={GREEN_PHI_SCALED/100:.3f}, ANKH={ANKH_SCALED/100:.3f}")
        
        self._record_vcd(clk=0, reset=1, enable=0)
        self._clock_cycle()
        self._record_vcd(reset=0, enable=1)
        self._clock_cycle()
        
        # Run all tests
        self.test_consent_header_parsing()
        self.test_coherence_evaluator_ra()
        self.test_scalar_trigger_timing()
        self.test_fallback_resolver()
        self.test_pma_ram()
        self.test_integration_scenarios()
        
        # Summary
        self._log("\n" + "=" * 70)
        self._log("TEST SUMMARY")
        self._log("=" * 70)
        total = self.tests_passed + self.tests_failed
        rate = (self.tests_passed / total * 100) if total > 0 else 0
        self._log(f"Total tests:  {total}")
        self._log(f"Passed:       {self.tests_passed}")
        self._log(f"Failed:       {self.tests_failed}")
        self._log(f"Pass rate:    {rate:.1f}%")
        
        # Coverage
        self._log("\n" + "=" * 70)
        self._log("COVERAGE REPORT")
        self._log("=" * 70)
        for name, count in sorted(self.coverage.items()):
            self._log(f"  {name}: {count} paths")
        self._log(f"\nTotal unique paths tested: {len(self.coverage)}")
        
        # Cleanup
        self._log(f"\nTrace log saved to: spiral_sim_canonical_trace.log")
        self._log(f"Waveform saved to: spiral_sim_canonical.vcd")
        
        self.vcd.end()
        self.log_file.close()
        
        return self.tests_failed == 0


if __name__ == "__main__":
    tb = SPIRALTestbench()
    success = tb.run_all_tests()
    sys.exit(0 if success else 1)
