"""
SPIRAL Protocol - HDL Behavioral Simulation & Verification
===========================================================

This module provides a cycle-accurate behavioral model of the SPIRAL HDL
modules, enabling verification without requiring external simulators.

The simulation generates:
1. Test coverage reports
2. Trace logs (console + file)
3. VCD waveform files compatible with GTKWave

Run: python hdl_simulation.py
View waveforms: gtkwave spiral_sim.vcd
"""

import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable
from enum import IntEnum
import struct
import time

# Add project root to path
sys.path.insert(0, r'C:\Users\schmi\Documents\GitHub\rpp-spec')


# =============================================================================
# VCD Waveform Writer
# =============================================================================

class VCDWriter:
    """Generates Value Change Dump files for GTKWave visualization."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.signals: Dict[str, Tuple[str, int]] = {}  # name -> (id, width)
        self.id_counter = 0
        self.current_time = 0
        self.file = None
        
    def _next_id(self) -> str:
        """Generate unique signal identifier."""
        chars = "!\"#$%&'()*+,-./:;<=>?@[]^_`{|}~"
        chars += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        chars += "abcdefghijklmnopqrstuvwxyz"
        chars += "0123456789"
        idx = self.id_counter
        self.id_counter += 1
        if idx < len(chars):
            return chars[idx]
        return chars[idx // len(chars)] + chars[idx % len(chars)]
    
    def add_signal(self, name: str, width: int = 1, module: str = "tb") -> str:
        """Register a signal for tracing."""
        full_name = f"{module}.{name}"
        sig_id = self._next_id()
        self.signals[full_name] = (sig_id, width)
        return sig_id
    
    def begin(self):
        """Write VCD header."""
        self.file = open(self.filename, 'w')
        self.file.write(f"$date\n   {time.strftime('%Y-%m-%d %H:%M:%S')}\n$end\n")
        self.file.write("$version\n   SPIRAL HDL Simulation v2.0\n$end\n")
        self.file.write("$timescale 1ns $end\n")
        
        # Write signal definitions
        self.file.write("$scope module tb $end\n")
        for name, (sig_id, width) in self.signals.items():
            short_name = name.split('.')[-1]
            self.file.write(f"$var wire {width} {sig_id} {short_name} $end\n")
        self.file.write("$upscope $end\n")
        self.file.write("$enddefinitions $end\n")
        self.file.write("#0\n")
        self.file.write("$dumpvars\n")
        
    def change(self, name: str, value: int, module: str = "tb"):
        """Record a value change."""
        full_name = f"{module}.{name}"
        if full_name not in self.signals:
            return
        sig_id, width = self.signals[full_name]
        if width == 1:
            self.file.write(f"{value}{sig_id}\n")
        else:
            self.file.write(f"b{value:0{width}b} {sig_id}\n")
    
    def advance(self, time_ns: int):
        """Advance simulation time."""
        if time_ns > self.current_time:
            self.current_time = time_ns
            self.file.write(f"#{time_ns}\n")
    
    def end(self):
        """Close VCD file."""
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
# HDL Module Behavioral Models
# =============================================================================

@dataclass
class ConsentHeaderParser:
    """
    Behavioral model of ConsentHeaderParser_Stub.
    
    Parses 144-bit consent header using stub's arbitrary bit positions.
    """
    # Outputs (directly from stub bit positions)
    coherence_window_id: int = 0    # [143:132] 12 bits
    phase_entropy_index: int = 0    # [131:126] 6 bits
    fallback_vector: int = 0        # [125:118] 8 bits
    complecount_trace: int = 0      # [117:113] 5 bits
    payload_type: int = 0           # [112:109] 4 bits
    consent_state: int = 0          # [108:107] 2 bits
    
    def parse(self, consent_header: int) -> None:
        """Parse header using stub bit positions."""
        self.coherence_window_id = (consent_header >> 132) & 0xFFF
        self.phase_entropy_index = (consent_header >> 126) & 0x3F
        self.fallback_vector = (consent_header >> 118) & 0xFF
        self.complecount_trace = (consent_header >> 113) & 0x1F
        self.payload_type = (consent_header >> 109) & 0xF
        self.consent_state = (consent_header >> 107) & 0x3


@dataclass
class CoherenceEvaluator:
    """
    Behavioral model of CoherenceEvaluator_Stub.
    
    Simple additive coherence model:
    score = (entropy << 1) + complecount
    valid = score >= threshold
    """
    coherence_score: int = 0
    coherence_valid: bool = False
    
    def evaluate(self, phase_entropy_index: int, complecount_trace: int, 
                 pmq_threshold: int) -> None:
        """Evaluate coherence using stub logic."""
        # Stub: {phase_entropy_index, 1'b0} + {2'b00, complecount_trace}
        self.coherence_score = (phase_entropy_index << 1) + complecount_trace
        self.coherence_score &= 0x7F  # 7-bit result
        self.coherence_valid = self.coherence_score >= pmq_threshold


@dataclass
class FallbackResolver:
    """
    Behavioral model of FallbackResolver_Stub.
    
    XOR-based fallback address generation.
    """
    rpp_fallback_address: int = 0
    base_address: int = 0x00000000
    
    def resolve(self, trigger_fallback: bool, fallback_vector: int) -> None:
        """Generate fallback address using stub logic."""
        if trigger_fallback:
            self.rpp_fallback_address = self.base_address ^ fallback_vector
        else:
            self.rpp_fallback_address = 0  # High-Z in real HDL


@dataclass
class ScalarTrigger:
    """
    Behavioral model of ScalarTrigger module.
    
    Sustained coherence detection with duration requirement.
    """
    coherence_counter: int = 0
    scalar_triggered: bool = False
    
    def reset(self) -> None:
        """Reset trigger state."""
        self.coherence_counter = 0
        self.scalar_triggered = False
    
    def clock(self, enable: bool, radius: int, activation_threshold: int,
              coherence_duration: int) -> None:
        """Process one clock cycle."""
        if not enable:
            self.scalar_triggered = False
            return
            
        if radius >= activation_threshold:
            if self.coherence_counter < coherence_duration:
                self.coherence_counter += 1
            else:
                self.scalar_triggered = True
        else:
            self.coherence_counter = 0
            self.scalar_triggered = False


@dataclass
class PhaseMemoryAnchorRAM:
    """
    Behavioral model of PhaseMemoryAnchorRAM module.
    
    Simple dual-port RAM for PMA records.
    """
    depth: int = 64
    memory: List[int] = field(default_factory=list)
    
    def __post_init__(self):
        self.memory = [0] * self.depth
    
    def write(self, addr: int, data: int) -> None:
        """Write to RAM."""
        if 0 <= addr < self.depth:
            self.memory[addr] = data & ((1 << 144) - 1)
    
    def read(self, addr: int) -> int:
        """Read from RAM."""
        if 0 <= addr < self.depth:
            return self.memory[addr]
        return 0


# =============================================================================
# Testbench
# =============================================================================

class SpiralTestbench:
    """
    Comprehensive testbench for SPIRAL HDL modules.
    """
    
    def __init__(self, vcd_filename: str = "spiral_sim.vcd"):
        # Instantiate modules
        self.parser = ConsentHeaderParser()
        self.coherence = CoherenceEvaluator()
        self.fallback = FallbackResolver()
        self.scalar = ScalarTrigger()
        self.pma_ram = PhaseMemoryAnchorRAM()
        
        # VCD writer
        self.vcd = VCDWriter(vcd_filename)
        self._setup_vcd_signals()
        
        # Test statistics
        self.test_count = 0
        self.pass_count = 0
        self.fail_count = 0
        self.coverage: Dict[str, int] = {}
        
        # Trace log
        self.trace_log: List[str] = []
        
        # Simulation time
        self.time_ns = 0
        self.clock_period = 10  # 100 MHz
        
    def _setup_vcd_signals(self):
        """Register signals for VCD tracing."""
        # Clock and control
        self.vcd.add_signal("clk", 1)
        self.vcd.add_signal("reset", 1)
        self.vcd.add_signal("enable", 1)
        
        # Parser outputs
        self.vcd.add_signal("coherence_window_id", 12)
        self.vcd.add_signal("phase_entropy_index", 6)
        self.vcd.add_signal("fallback_vector", 8)
        self.vcd.add_signal("complecount_trace", 5)
        self.vcd.add_signal("payload_type", 4)
        self.vcd.add_signal("consent_state", 2)
        
        # Coherence evaluator
        self.vcd.add_signal("coherence_score", 7)
        self.vcd.add_signal("coherence_valid", 1)
        self.vcd.add_signal("pmq_threshold", 7)
        
        # Scalar trigger
        self.vcd.add_signal("radius", 8)
        self.vcd.add_signal("activation_threshold", 7)
        self.vcd.add_signal("coherence_duration", 8)
        self.vcd.add_signal("coherence_counter", 8)
        self.vcd.add_signal("scalar_triggered", 1)
        
        # Fallback
        self.vcd.add_signal("trigger_fallback", 1)
        self.vcd.add_signal("rpp_fallback_address", 32)
        
    def _record_vcd(self, **signals):
        """Record signals to VCD."""
        for name, value in signals.items():
            self.vcd.change(name, value)
    
    def _clock_cycle(self):
        """Advance one clock cycle."""
        # Rising edge
        self.vcd.advance(self.time_ns)
        self._record_vcd(clk=1)
        self.time_ns += self.clock_period // 2
        
        # Falling edge
        self.vcd.advance(self.time_ns)
        self._record_vcd(clk=0)
        self.time_ns += self.clock_period // 2
    
    def _log(self, msg: str):
        """Add to trace log."""
        self.trace_log.append(f"[{self.time_ns:6d}ns] {msg}")
        print(f"[{self.time_ns:6d}ns] {msg}")
    
    def _check(self, name: str, actual, expected, tolerance=0) -> bool:
        """Check a test condition."""
        self.test_count += 1
        
        if tolerance > 0:
            passed = abs(actual - expected) <= tolerance
        else:
            passed = actual == expected
        
        if passed:
            self.pass_count += 1
            self._log(f"  [PASS] {name}: {actual}")
        else:
            self.fail_count += 1
            self._log(f"  [FAIL] {name}: got {actual}, expected {expected}")
        
        # Track coverage
        self.coverage[name] = self.coverage.get(name, 0) + 1
        
        return passed
    
    def _record_coverage(self, category: str):
        """Record test coverage."""
        self.coverage[category] = self.coverage.get(category, 0) + 1
    
    # =========================================================================
    # Test Cases
    # =========================================================================
    
    def _build_consent_header(self, window_id: int, entropy: int, fallback: int,
                                complecount: int, payload: int, consent: int,
                                reserved: int = 0) -> int:
        """
        Build a 144-bit consent header from canonical field values.
        
        Canonical Layout (CONSENT-HEADER-v1.md):
          [143:132] coherence_window_id  (12 bits)
          [131:126] phase_entropy_index  (6 bits)
          [125:118] fallback_vector      (8 bits)
          [117:113] complecount_trace    (5 bits)
          [112:109] payload_type         (4 bits)
          [108:107] consent_state        (2 bits)
          [106:0]   reserved             (107 bits)
        """
        header = 0
        header |= (window_id & 0xFFF) << 132
        header |= (entropy & 0x3F) << 126
        header |= (fallback & 0xFF) << 118
        header |= (complecount & 0x1F) << 113
        header |= (payload & 0xF) << 109
        header |= (consent & 0x3) << 107
        header |= (reserved & ((1 << 107) - 1))
        return header
    
    def test_consent_header_edge_cases(self):
        """Test 1: Consent Header Parser edge cases (Canonical Layout)."""
        self._log("=" * 60)
        self._log("TEST 1: ConsentHeaderParser Edge Cases (Canonical)")
        self._log("=" * 60)
        
        # Build test vectors using canonical field builder
        test_vectors = [
            # (header, expected_window_id, expected_entropy, expected_fallback, 
            #  expected_complecount, expected_payload, expected_consent, description)
            
            # Edge case: All zeros
            (self._build_consent_header(0, 0, 0, 0, 0, 0), 
             0, 0, 0, 0, 0, 0, "All zeros"),
            
            # Edge case: All ones in canonical fields
            (self._build_consent_header(0xFFF, 0x3F, 0xFF, 0x1F, 0xF, 0x3),
             0xFFF, 0x3F, 0xFF, 0x1F, 0xF, 0x3, "All ones"),
            
            # FULL_CONSENT packet (consent=0b00)
            (self._build_consent_header(0x001, 0x08, 0x2A, 0x05, 0x1, 0x0),
             0x001, 0x08, 0x2A, 0x05, 0x1, 0x0, "FULL_CONSENT packet"),
            
            # DIMINISHED_CONSENT packet (consent=0b01)
            (self._build_consent_header(0x100, 0x10, 0x55, 0x0A, 0x2, 0x1),
             0x100, 0x10, 0x55, 0x0A, 0x2, 0x1, "DIMINISHED_CONSENT packet"),
            
            # SUSPENDED_CONSENT packet (consent=0b10)
            (self._build_consent_header(0x800, 0x20, 0xAA, 0x0F, 0x4, 0x2),
             0x800, 0x20, 0xAA, 0x0F, 0x4, 0x2, "SUSPENDED_CONSENT packet"),
            
            # EMERGENCY_OVERRIDE packet (consent=0b11)
            (self._build_consent_header(0xCAF, 0x3F, 0xFF, 0x1F, 0x8, 0x3),
             0xCAF, 0x3F, 0xFF, 0x1F, 0x8, 0x3, "EMERGENCY_OVERRIDE packet"),
            
            # Window ID boundary: MSB only
            (self._build_consent_header(0x800, 0, 0, 0, 0, 0),
             0x800, 0, 0, 0, 0, 0, "Window ID MSB"),
            
            # Window ID boundary: LSB only
            (self._build_consent_header(0x001, 0, 0, 0, 0, 0),
             0x001, 0, 0, 0, 0, 0, "Window ID LSB"),
            
            # High entropy (fallback trigger candidate)
            (self._build_consent_header(0x123, 0x38, 0xBE, 0x10, 0x3, 0x0),
             0x123, 0x38, 0xBE, 0x10, 0x3, 0x0, "High entropy (56)"),
            
            # Avatar payload type (0x3)
            (self._build_consent_header(0x456, 0x0C, 0x42, 0x08, 0x3, 0x0),
             0x456, 0x0C, 0x42, 0x08, 0x3, 0x0, "Avatar payload"),
        ]
        
        for header, exp_wid, exp_ent, exp_fb, exp_cc, exp_pt, exp_cs, desc in test_vectors:
            self._log(f"\n  Testing: {desc}")
            self.parser.parse(header)
            
            self._check(f"window_id ({desc})", self.parser.coherence_window_id, exp_wid)
            self._check(f"entropy ({desc})", self.parser.phase_entropy_index, exp_ent)
            self._check(f"fallback ({desc})", self.parser.fallback_vector, exp_fb)
            self._check(f"complecount ({desc})", self.parser.complecount_trace, exp_cc)
            self._check(f"payload ({desc})", self.parser.payload_type, exp_pt)
            self._check(f"consent ({desc})", self.parser.consent_state, exp_cs)
            
            # Record VCD
            self._record_vcd(
                coherence_window_id=self.parser.coherence_window_id,
                phase_entropy_index=self.parser.phase_entropy_index,
                fallback_vector=self.parser.fallback_vector,
                complecount_trace=self.parser.complecount_trace,
                payload_type=self.parser.payload_type,
                consent_state=self.parser.consent_state
            )
            self._clock_cycle()
            
            self._record_coverage("consent_header_parse")
    
    def test_coherence_evaluator_sweep(self):
        """Test 2: CoherenceEvaluator full sweep."""
        self._log("\n" + "=" * 60)
        self._log("TEST 2: CoherenceEvaluator Sweep")
        self._log("=" * 60)
        
        thresholds = [30, 45, 63, 100, 127]
        
        for threshold in thresholds:
            self._log(f"\n  Threshold: {threshold}")
            
            # Sample sweep (full sweep would be 64Ã—32 = 2048 combinations)
            for entropy in [0, 10, 20, 31, 40, 50, 63]:
                for complecount in [0, 8, 16, 24, 31]:
                    self.coherence.evaluate(entropy, complecount, threshold)
                    
                    # Expected: score = (entropy << 1) + complecount
                    expected_score = ((entropy << 1) + complecount) & 0x7F
                    expected_valid = expected_score >= threshold
                    
                    self._check(
                        f"score(e={entropy},c={complecount},t={threshold})",
                        self.coherence.coherence_score,
                        expected_score
                    )
                    self._check(
                        f"valid(e={entropy},c={complecount},t={threshold})",
                        self.coherence.coherence_valid,
                        expected_valid
                    )
                    
                    # Record VCD
                    self._record_vcd(
                        phase_entropy_index=entropy,
                        complecount_trace=complecount,
                        pmq_threshold=threshold,
                        coherence_score=self.coherence.coherence_score,
                        coherence_valid=int(self.coherence.coherence_valid)
                    )
                    self._clock_cycle()
                    
                    self._record_coverage("coherence_sweep")
    
    def test_scalar_trigger_timing(self):
        """Test 3: ScalarTrigger timing and duration."""
        self._log("\n" + "=" * 60)
        self._log("TEST 3: ScalarTrigger Timing")
        self._log("=" * 60)
        
        # Test various durations
        for duration in [1, 2, 3, 5, 10]:
            self._log(f"\n  Duration: {duration}")
            self.scalar.reset()
            
            threshold = 40
            radius_high = 50  # Above threshold
            radius_low = 30   # Below threshold
            
            self._record_vcd(
                reset=1,
                activation_threshold=threshold,
                coherence_duration=duration
            )
            self._clock_cycle()
            self._record_vcd(reset=0, enable=1)
            
            # Apply high radius for (duration + 2) cycles
            self._log(f"    Applying radius={radius_high} (above threshold)")
            for cycle in range(duration + 2):
                self.scalar.clock(True, radius_high, threshold, duration)
                
                self._record_vcd(
                    radius=radius_high,
                    coherence_counter=self.scalar.coherence_counter,
                    scalar_triggered=int(self.scalar.scalar_triggered)
                )
                self._clock_cycle()
                
                expected_triggered = cycle >= duration
                self._check(
                    f"triggered@cycle{cycle}(d={duration})",
                    self.scalar.scalar_triggered,
                    expected_triggered
                )
            
            # Reset with low radius
            self._log(f"    Applying radius={radius_low} (below threshold)")
            self.scalar.clock(True, radius_low, threshold, duration)
            self._check(
                f"reset_after_low(d={duration})",
                self.scalar.scalar_triggered,
                False
            )
            self._check(
                f"counter_reset(d={duration})",
                self.scalar.coherence_counter,
                0
            )
            
            self._record_coverage("scalar_timing")
        
        # Test oscillating radius
        self._log("\n  Testing oscillating radius...")
        self.scalar.reset()
        oscillation = [50, 50, 30, 50, 50, 50, 50, 50]  # Dip in middle
        
        for i, r in enumerate(oscillation):
            self.scalar.clock(True, r, 40, 3)
            self._log(f"    Cycle {i}: radius={r}, counter={self.scalar.coherence_counter}, triggered={self.scalar.scalar_triggered}")
            self._record_vcd(
                radius=r,
                coherence_counter=self.scalar.coherence_counter,
                scalar_triggered=int(self.scalar.scalar_triggered)
            )
            self._clock_cycle()
            self._record_coverage("scalar_oscillation")
    
    def test_fallback_resolver(self):
        """Test 4: FallbackResolver XOR logic."""
        self._log("\n" + "=" * 60)
        self._log("TEST 4: FallbackResolver XOR Logic")
        self._log("=" * 60)
        
        test_vectors = [
            (True, 0x00, 0x00000000, "Zero vector"),
            (True, 0xFF, 0x000000FF, "Full vector"),
            (True, 0x2A, 0x0000002A, "0x2A vector"),
            (True, 0x55, 0x00000055, "0x55 vector"),
            (True, 0xAA, 0x000000AA, "0xAA vector"),
            (False, 0xFF, 0, "Trigger disabled"),
        ]
        
        for trigger, vector, expected_addr, desc in test_vectors:
            self.fallback.resolve(trigger, vector)
            
            self._check(
                f"fallback({desc})",
                self.fallback.rpp_fallback_address,
                expected_addr
            )
            
            self._record_vcd(
                trigger_fallback=int(trigger),
                fallback_vector=vector,
                rpp_fallback_address=self.fallback.rpp_fallback_address
            )
            self._clock_cycle()
            
            self._record_coverage("fallback_xor")
    
    def test_pma_ram(self):
        """Test 5: PhaseMemoryAnchorRAM read/write."""
        self._log("\n" + "=" * 60)
        self._log("TEST 5: PhaseMemoryAnchorRAM")
        self._log("=" * 60)
        
        # Write test patterns
        test_patterns = [
            (0, 0xCAFEBABE12345678),
            (1, 0xDEADBEEFDEADBEEF),
            (63, 0x123456789ABCDEF0),  # Last address
        ]
        
        for addr, data in test_patterns:
            self.pma_ram.write(addr, data)
            read_back = self.pma_ram.read(addr)
            
            self._check(
                f"pma_write_read@{addr}",
                read_back,
                data
            )
            self._clock_cycle()
            self._record_coverage("pma_ram")
    
    def test_integration_scenarios(self):
        """Test 6: Integration scenarios."""
        self._log("\n" + "=" * 60)
        self._log("TEST 6: Integration Scenarios")
        self._log("=" * 60)
        
        scenarios = [
            # (coherence_valid, scalar_triggered, consent_state, description)
            (True, False, ConsentState.FULL_CONSENT, "Normal operation"),
            (False, False, ConsentState.FULL_CONSENT, "Coherence fail â†’ fallback"),
            (True, True, ConsentState.FULL_CONSENT, "Scalar triggered"),
            (True, False, ConsentState.DIMINISHED_CONSENT, "Diminished consent"),
            (False, True, ConsentState.SUSPENDED_CONSENT, "Suspended + fallback"),
            (True, True, ConsentState.EMERGENCY_OVERRIDE, "Emergency override"),
        ]
        
        for coh_valid, scalar_trig, consent, desc in scenarios:
            self._log(f"\n  Scenario: {desc}")
            
            # Determine expected behavior
            should_fallback = not coh_valid
            should_route = coh_valid and consent == ConsentState.FULL_CONSENT
            
            self._log(f"    coherence_valid={coh_valid}, scalar_triggered={scalar_trig}")
            self._log(f"    consent_state={consent.name}")
            self._log(f"    -> should_fallback={should_fallback}, should_route={should_route}")
            
            # Record state
            self._record_vcd(
                coherence_valid=int(coh_valid),
                scalar_triggered=int(scalar_trig),
                consent_state=consent.value,
                trigger_fallback=int(should_fallback)
            )
            self._clock_cycle()
            
            self._record_coverage(f"integration_{desc.replace(' ', '_')}")
    
    # =========================================================================
    # Run All Tests
    # =========================================================================
    
    def run_all(self) -> Tuple[int, int, int]:
        """Run all tests and generate reports."""
        self._log("=" * 60)
        self._log("SPIRAL Protocol HDL Simulation")
        self._log("=" * 60)
        self._log(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Start VCD
        self.vcd.begin()
        self._record_vcd(clk=0, reset=1, enable=0)
        self._clock_cycle()
        self._record_vcd(reset=0, enable=1)
        self._clock_cycle()
        
        # Run tests
        self.test_consent_header_edge_cases()
        self.test_coherence_evaluator_sweep()
        self.test_scalar_trigger_timing()
        self.test_fallback_resolver()
        self.test_pma_ram()
        self.test_integration_scenarios()
        
        # End VCD
        self.vcd.end()
        
        # Print summary
        self._log("\n" + "=" * 60)
        self._log("TEST SUMMARY")
        self._log("=" * 60)
        self._log(f"Total tests:  {self.test_count}")
        self._log(f"Passed:       {self.pass_count}")
        self._log(f"Failed:       {self.fail_count}")
        self._log(f"Pass rate:    {100*self.pass_count/max(1,self.test_count):.1f}%")
        
        # Coverage report
        self._log("\n" + "=" * 60)
        self._log("COVERAGE REPORT")
        self._log("=" * 60)
        for category, count in sorted(self.coverage.items()):
            self._log(f"  {category}: {count} paths")
        
        total_paths = sum(self.coverage.values())
        self._log(f"\nTotal unique paths tested: {total_paths}")
        
        # Save trace log
        log_filename = "spiral_sim_trace.log"
        with open(log_filename, 'w') as f:
            f.write('\n'.join(self.trace_log))
        self._log(f"\nTrace log saved to: {log_filename}")
        self._log(f"Waveform saved to: {self.vcd.filename}")
        
        return self.test_count, self.pass_count, self.fail_count


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    # Change to output directory
    output_dir = r"C:\Users\schmi\Documents\GitHub\rpp-spec\hardware\verilog"
    os.chdir(output_dir)
    
    # Run simulation
    tb = SpiralTestbench("spiral_sim.vcd")
    total, passed, failed = tb.run_all()
    
    # Exit code
    sys.exit(0 if failed == 0 else 1)
