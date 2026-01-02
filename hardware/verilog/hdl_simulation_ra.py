"""
SPIRAL Protocol - Ra-Canonical HDL Simulation & Verification
=============================================================

This module provides cycle-accurate behavioral models of the SPIRAL HDL
modules with Ra-derived coherence evaluation.

Implements the canonical coherence formula:
    E = phase_entropy_index / 31
    C = complecount_trace / 7
    coherence_score = (phi x E) + (ANKH_SYMBOL x C)

Where:
    PHI (GREEN_PHI) ~ 1.618
    ANKH_SYMBOL (ANKH)     ~ 5.089

Run: python hdl_simulation_ra.py
View waveforms: gtkwave spiral_ra_sim.vcd
"""

import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import IntEnum
import time
import json

# Ra System constants
GREEN_PHI = 1.618033988749895
ANKH = 5.08897958067581  # GREEN_PHI ** 3

# =============================================================================
# VCD Waveform Writer
# =============================================================================

class VCDWriter:
    """Generates Value Change Dump files for GTKWave visualization."""

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
        self.file.write("$version\n   SPIRAL Ra-Canonical Simulation v2.1\n$end\n")
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

    def comment(self, text: str):
        if self.file:
            self.file.write(f"$comment {text} $end\n")

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


class RoutingDecision(IntEnum):
    ROUTE_NORMAL = 0
    ROUTE_FALLBACK = 1
    ROUTE_PMA = 2
    ROUTE_BLOCKED = 3
    ROUTE_EMERGENCY = 4


# =============================================================================
# HDL Module Behavioral Models
# =============================================================================

@dataclass
class ConsentHeaderParser:
    """
    Behavioral model of ConsentHeaderParser (spec-compliant).

    Byte layout per CONSENT-HEADER-v1.md:
        Bytes 0-3:   RPP Address [theta:5|phi:3|omega:3|radius:8|reserved:13]
        Bytes 4-7:   Packet ID
        Bytes 8-9:   Origin Reference
        Byte 10:     [verbal:1|somatic:4|ancestral:2|temporal:1]
        Byte 11:     [entropy:5|complecount:3]
        Byte 12:     [reserved:4|payload_type:4]
        Byte 13:     Fallback Vector
        Bytes 14-15: Coherence Window ID (16 bits)
        Byte 16:     Target Phase Reference
        Byte 17:     Header CRC
    """
    # RPP Address components
    rpp_theta: int = 0
    rpp_phi: int = 0
    rpp_omega: int = 0
    rpp_radius: int = 0

    # Identification
    packet_id: int = 0
    origin_ref: int = 0

    # Consent fields
    consent_verbal: bool = False
    consent_somatic: int = 0
    consent_ancestral: int = 0
    temporal_lock: bool = False

    # Entropy fields
    phase_entropy_index: int = 0  # 5 bits (0-31)
    complecount_trace: int = 0   # 3 bits (0-7)

    # Payload
    payload_type: int = 0

    # Routing
    fallback_vector: int = 0
    coherence_window_id: int = 0  # 16 bits
    target_phase_ref: int = 0
    header_crc: int = 0

    # Derived
    consent_state: ConsentState = ConsentState.FULL_CONSENT
    needs_fallback: bool = False
    has_pma_link: bool = False

    def parse(self, header: int) -> None:
        """Parse 144-bit header (big-endian)."""
        # Extract bytes
        bytes_list = [(header >> (8 * (17 - i))) & 0xFF for i in range(18)]

        # RPP Address (bytes 0-3)
        rpp_addr = (bytes_list[0] << 24) | (bytes_list[1] << 16) | (bytes_list[2] << 8) | bytes_list[3]
        self.rpp_theta = (rpp_addr >> 27) & 0x1F
        self.rpp_phi = (rpp_addr >> 24) & 0x07
        self.rpp_omega = (rpp_addr >> 21) & 0x07
        self.rpp_radius = (rpp_addr >> 13) & 0xFF

        # Identification
        self.packet_id = (bytes_list[4] << 24) | (bytes_list[5] << 16) | (bytes_list[6] << 8) | bytes_list[7]
        self.origin_ref = (bytes_list[8] << 8) | bytes_list[9]

        # Consent (byte 10)
        self.consent_verbal = bool(bytes_list[10] >> 7)
        self.consent_somatic = (bytes_list[10] >> 3) & 0x0F
        self.consent_ancestral = (bytes_list[10] >> 1) & 0x03
        self.temporal_lock = bool(bytes_list[10] & 0x01)

        # Entropy (byte 11)
        self.phase_entropy_index = (bytes_list[11] >> 3) & 0x1F
        self.complecount_trace = bytes_list[11] & 0x07

        # Payload (byte 12)
        self.payload_type = bytes_list[12] & 0x0F

        # Routing
        self.fallback_vector = bytes_list[13]
        self.coherence_window_id = (bytes_list[14] << 8) | bytes_list[15]
        self.target_phase_ref = bytes_list[16]
        self.header_crc = bytes_list[17]

        # Derive consent state
        if self.consent_somatic < 3:  # < 0.2
            self.consent_state = ConsentState.SUSPENDED_CONSENT
        elif self.consent_somatic < 8 and not self.consent_verbal:  # < 0.5
            self.consent_state = ConsentState.DIMINISHED_CONSENT
        else:
            self.consent_state = ConsentState.FULL_CONSENT

        # Derived flags
        self.needs_fallback = self.phase_entropy_index > 25
        self.has_pma_link = self.coherence_window_id != 0


@dataclass
class CoherenceEvaluator_Ra:
    """
    Behavioral model of CoherenceEvaluator_Ra.

    Ra-derived coherence formula:
        E = phase_entropy_index / 31
        C = complecount_trace / 7
        coherence_score = (phi x E) + (ANKH_SYMBOL x C)

    Max coherence ~ 6.707 (when E=1, C=1)
    """
    coherence_score: float = 0.0
    coherence_score_x100: int = 0  # Fixed-point x100
    coherence_valid: bool = False
    high_coherence: bool = False
    medium_coherence: bool = False
    low_coherence: bool = False

    def evaluate(self, phase_entropy_index: int, complecount_trace: int,
                 threshold: float = 3.0) -> None:
        """Evaluate coherence using Ra formula."""
        # Normalize inputs
        E = phase_entropy_index / 31.0 if phase_entropy_index <= 31 else 1.0
        C = complecount_trace / 7.0 if complecount_trace <= 7 else 1.0

        # Ra formula
        self.coherence_score = (GREEN_PHI * E) + (ANKH * C)
        self.coherence_score_x100 = int(self.coherence_score * 100)

        # Threshold comparison
        self.coherence_valid = self.coherence_score >= threshold

        # Classification
        self.high_coherence = self.coherence_score >= 5.0
        self.medium_coherence = 3.0 <= self.coherence_score < 5.0
        self.low_coherence = self.coherence_score < 3.0


@dataclass
class ScalarTrigger_Ra:
    """
    Behavioral model of ScalarTrigger_Ra.

    Enhanced scalar trigger with coherence gating.
    """
    coherence_counter: int = 0
    scalar_triggered: bool = False
    above_threshold: bool = False
    stable_resonance: bool = False

    def reset(self) -> None:
        self.coherence_counter = 0
        self.scalar_triggered = False
        self.above_threshold = False
        self.stable_resonance = False

    def clock(self, enable: bool, radius: int, activation_threshold: int,
              coherence_duration: int, coherence_valid: bool) -> None:
        """Process one clock cycle."""
        self.above_threshold = radius >= activation_threshold

        if not enable:
            self.scalar_triggered = False
            self.stable_resonance = False
            return

        if self.above_threshold:
            if self.coherence_counter < coherence_duration:
                self.coherence_counter += 1
                self.scalar_triggered = False
            else:
                self.scalar_triggered = True
        else:
            self.coherence_counter = 0
            self.scalar_triggered = False

        self.stable_resonance = self.scalar_triggered and coherence_valid


@dataclass
class ScalarTrigger_Ra_Khat:
    """
    Behavioral model of ScalarTrigger_Ra_Khat.

    KHAT-fixed 12-cycle duration scalar trigger.
    KHAT = sqrt(10) ~ 3.162 -> scaled 316 -> 316 mod 16 = 12 cycles
    """
    KHAT_DURATION: int = 12  # Fixed duration

    coherence_counter: int = 0
    scalar_triggered: bool = False
    above_threshold: bool = False

    def reset(self) -> None:
        self.coherence_counter = 0
        self.scalar_triggered = False
        self.above_threshold = False

    def clock(self, enable: bool, coherence_score: int,
              activation_threshold: int) -> None:
        """Process one clock cycle."""
        self.above_threshold = coherence_score >= activation_threshold

        if not enable:
            self.scalar_triggered = False
            return

        if self.above_threshold:
            if self.coherence_counter < 15:
                self.coherence_counter += 1
            if self.coherence_counter >= self.KHAT_DURATION:
                self.scalar_triggered = True
        else:
            self.coherence_counter = 0
            self.scalar_triggered = False


@dataclass
class ConsentStateDeriver:
    """
    Behavioral model of ConsentStateDeriver.

    Derives consent_state from somatic_coherence using Golden Ratio thresholds:
    - somatic >= 10 -> FULL_CONSENT (phi ~ 0.618)
    - somatic 6-9 -> DIMINISHED_CONSENT (1-phi ~ 0.382)
    - somatic 0-5 -> SUSPENDED_CONSENT (phi^2 boundary)
    """
    SOMATIC_FULL_THRESHOLD: int = 10  # phi ~ 0.618 -> ceil(0.618*16)
    SOMATIC_DIM_MIN: int = 6          # 1-phi ~ 0.382 -> floor(0.382*16)

    def derive(self, somatic_coherence: int, verbal_override: bool) -> ConsentState:
        """Derive consent state from somatic coherence."""
        if verbal_override:
            return ConsentState.FULL_CONSENT
        elif somatic_coherence >= self.SOMATIC_FULL_THRESHOLD:
            return ConsentState.FULL_CONSENT
        elif somatic_coherence >= self.SOMATIC_DIM_MIN:
            return ConsentState.DIMINISHED_CONSENT
        else:
            return ConsentState.SUSPENDED_CONSENT


@dataclass
class ETFController:
    """
    Behavioral model of ETFController (Emergency Token Freeze).

    ALPHA_INVERSE-derived constants (fine-structure constant inverse):
    - ETF_DURATION = 137 mod 16 = 9 cycles
    - ETF_RELEASE_THRESHOLD = 674 * (137/165) ~ 559
    """
    ETF_DURATION: int = 9             # 137 mod 16
    ETF_RELEASE_THRESHOLD: int = 559  # 674 * (137/165)

    etf_active: bool = False
    etf_counter: int = 0

    def reset(self) -> None:
        self.etf_active = False
        self.etf_counter = 0

    def clock(self, etf_trigger: bool, coherence_score: int) -> None:
        """Process one clock cycle."""
        if etf_trigger and not self.etf_active:
            # Enter ETF state
            self.etf_active = True
            self.etf_counter = self.ETF_DURATION
        elif self.etf_active:
            # ETF release conditions
            if self.etf_counter > 0:
                self.etf_counter -= 1
            elif coherence_score >= self.ETF_RELEASE_THRESHOLD:
                self.etf_active = False  # Mirror check passed


@dataclass
class FallbackResolver_Ra:
    """
    Behavioral model of FallbackResolver_Ra.

    XOR-based fallback with Ra-aligned modular arithmetic.
    """
    fallback_theta: int = 0
    fallback_phi: int = 0
    fallback_omega: int = 0
    fallback_radius: int = 0
    fallback_address: int = 0
    fallback_active: bool = False

    def resolve(self, trigger: bool, primary_theta: int, primary_phi: int,
                primary_omega: int, primary_radius: int, fallback_vector: int) -> None:
        """Resolve fallback address using XOR and modular wrapping."""
        self.fallback_active = trigger

        if not trigger:
            self.fallback_theta = primary_theta
            self.fallback_phi = primary_phi
            self.fallback_omega = primary_omega
            self.fallback_radius = primary_radius
        else:
            # Extract offsets
            theta_off = (fallback_vector >> 5) & 0x07
            phi_off = (fallback_vector >> 2) & 0x07
            omega_off = fallback_vector & 0x03

            # XOR and wrap
            theta_xor = primary_theta ^ theta_off
            if theta_xor > 27:
                theta_xor -= 27
            elif theta_xor == 0:
                theta_xor = 27
            self.fallback_theta = theta_xor

            phi_xor = primary_phi ^ phi_off
            if phi_xor > 5:
                phi_xor -= 6
            self.fallback_phi = phi_xor & 0x07

            omega_xor = primary_omega ^ omega_off
            if omega_xor > 4:
                omega_xor -= 5
            self.fallback_omega = omega_xor & 0x07

            self.fallback_radius = primary_radius

        # Assemble address
        self.fallback_address = (
            (self.fallback_theta << 27) |
            (self.fallback_phi << 24) |
            (self.fallback_omega << 21) |
            (self.fallback_radius << 13)
        )


@dataclass
class ConsentArbitrator_Ra:
    """
    Behavioral model of ConsentArbitrator_Ra.

    Arbitration logic for routing decisions.
    """
    route_allowed: bool = False
    use_fallback: bool = False
    use_pma_route: bool = False
    routing_decision: RoutingDecision = RoutingDecision.ROUTE_BLOCKED

    def arbitrate(self, coherence_valid: bool, scalar_triggered: bool,
                  consent_state: ConsentState, needs_fallback: bool,
                  pma_hit: bool) -> None:
        """Determine routing decision."""
        is_suspended = consent_state == ConsentState.SUSPENDED_CONSENT
        is_emergency = consent_state == ConsentState.EMERGENCY_OVERRIDE

        consent_allows = (
            consent_state == ConsentState.FULL_CONSENT or
            (consent_state == ConsentState.DIMINISHED_CONSENT and coherence_valid)
        )

        self.route_allowed = consent_allows and not is_suspended and not is_emergency
        self.use_fallback = needs_fallback and not coherence_valid and self.route_allowed
        self.use_pma_route = pma_hit and coherence_valid and self.route_allowed

        if is_emergency:
            self.routing_decision = RoutingDecision.ROUTE_EMERGENCY
        elif is_suspended:
            self.routing_decision = RoutingDecision.ROUTE_BLOCKED
        elif self.use_pma_route:
            self.routing_decision = RoutingDecision.ROUTE_PMA
        elif self.use_fallback:
            self.routing_decision = RoutingDecision.ROUTE_FALLBACK
        elif self.route_allowed:
            self.routing_decision = RoutingDecision.ROUTE_NORMAL
        else:
            self.routing_decision = RoutingDecision.ROUTE_BLOCKED


@dataclass
class PhaseMemoryAnchorRAM:
    """Behavioral model of PMA RAM."""
    depth: int = 256
    memory: List[int] = field(default_factory=list)

    def __post_init__(self):
        self.memory = [0] * self.depth

    def write(self, addr: int, data: int) -> None:
        if 0 <= addr < self.depth:
            self.memory[addr] = data & ((1 << 144) - 1)

    def read(self, addr: int) -> int:
        if 0 <= addr < self.depth:
            return self.memory[addr]
        return 0


# =============================================================================
# Testbench
# =============================================================================

class SpiralRaTestbench:
    """Comprehensive testbench for SPIRAL Ra-Canonical HDL modules."""

    def __init__(self, vcd_filename: str = "spiral_ra_sim.vcd"):
        # Instantiate modules
        self.parser = ConsentHeaderParser()
        self.coherence = CoherenceEvaluator_Ra()
        self.scalar = ScalarTrigger_Ra()
        self.fallback = FallbackResolver_Ra()
        self.arbitrator = ConsentArbitrator_Ra()
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
        self.time_ns = 0
        self.clock_period = 10

    def _setup_vcd_signals(self):
        """Register signals for VCD tracing."""
        # Control
        self.vcd.add_signal("clk", 1)
        self.vcd.add_signal("reset", 1)
        self.vcd.add_signal("enable", 1)

        # Parser outputs
        self.vcd.add_signal("rpp_theta", 5)
        self.vcd.add_signal("rpp_phi", 3)
        self.vcd.add_signal("rpp_omega", 3)
        self.vcd.add_signal("rpp_radius", 8)
        self.vcd.add_signal("phase_entropy_index", 5)
        self.vcd.add_signal("complecount_trace", 3)
        self.vcd.add_signal("coherence_window_id", 16)
        self.vcd.add_signal("consent_state", 2)
        self.vcd.add_signal("needs_fallback", 1)
        self.vcd.add_signal("has_pma_link", 1)

        # Coherence evaluator
        self.vcd.add_signal("coherence_score", 10)
        self.vcd.add_signal("coherence_valid", 1)
        self.vcd.add_signal("high_coherence", 1)
        self.vcd.add_signal("medium_coherence", 1)
        self.vcd.add_signal("low_coherence", 1)

        # Scalar trigger
        self.vcd.add_signal("radius", 8)
        self.vcd.add_signal("scalar_threshold", 8)
        self.vcd.add_signal("coherence_counter", 8)
        self.vcd.add_signal("scalar_triggered", 1)
        self.vcd.add_signal("above_threshold", 1)
        self.vcd.add_signal("stable_resonance", 1)

        # Fallback
        self.vcd.add_signal("fallback_trigger", 1)
        self.vcd.add_signal("fallback_theta", 5)
        self.vcd.add_signal("fallback_phi", 3)
        self.vcd.add_signal("fallback_omega", 3)
        self.vcd.add_signal("fallback_active", 1)

        # Arbitrator
        self.vcd.add_signal("route_allowed", 1)
        self.vcd.add_signal("use_fallback", 1)
        self.vcd.add_signal("use_pma_route", 1)
        self.vcd.add_signal("routing_decision", 3)

    def _trace(self, msg: str):
        """Add timestamped trace entry."""
        entry = f"[{self.time_ns:6d}ns] {msg}"
        self.trace_log.append(entry)
        print(entry)

    def _check(self, name: str, condition: bool) -> bool:
        """Record test result."""
        self.test_count += 1
        if condition:
            self.pass_count += 1
            self._trace(f"[PASS] {name}")
        else:
            self.fail_count += 1
            self._trace(f"[FAIL] {name}")
        return condition

    def _clock(self):
        """Advance one clock cycle."""
        self.vcd.change("clk", 0)
        self.time_ns += self.clock_period // 2
        self.vcd.advance(self.time_ns)
        self.vcd.change("clk", 1)
        self.time_ns += self.clock_period // 2
        self.vcd.advance(self.time_ns)

    def _update_vcd_coherence(self):
        """Update VCD signals for coherence module."""
        self.vcd.change("coherence_score", self.coherence.coherence_score_x100)
        self.vcd.change("coherence_valid", int(self.coherence.coherence_valid))
        self.vcd.change("high_coherence", int(self.coherence.high_coherence))
        self.vcd.change("medium_coherence", int(self.coherence.medium_coherence))
        self.vcd.change("low_coherence", int(self.coherence.low_coherence))

    def run_coherence_sweep(self):
        """Sweep all entropy x complecount combinations."""
        self._trace("="*60)
        self._trace("CoherenceEvaluator_Ra - Full Sweep")
        self._trace("="*60)

        print("\nEntropy | Comple | Score  | Scorex100 | H/M/L | Valid")
        print("--------|--------|--------|-----------|-------|------")

        results = []
        for entropy in range(32):
            for comple in range(8):
                self.coherence.evaluate(entropy, comple, threshold=3.0)

                self.vcd.change("phase_entropy_index", entropy)
                self.vcd.change("complecount_trace", comple)
                self._update_vcd_coherence()
                self._clock()

                hml = "H" if self.coherence.high_coherence else (
                      "M" if self.coherence.medium_coherence else "L")

                if entropy % 4 == 0:  # Print subset
                    print(f"   {entropy:2d}   |   {comple}    | {self.coherence.coherence_score:6.3f} |"
                          f"    {self.coherence.coherence_score_x100:3d}    |   {hml}   |   {'Y' if self.coherence.coherence_valid else 'N'}")

                results.append({
                    'entropy': entropy,
                    'complecount': comple,
                    'score': self.coherence.coherence_score,
                    'valid': self.coherence.coherence_valid
                })

                # Track coverage
                key = f"coh_{hml}"
                self.coverage[key] = self.coverage.get(key, 0) + 1

        # Verify key points
        self.coherence.evaluate(31, 7, 4.0)
        self._check("Max coherence (E=31, C=7) >= 4.0", self.coherence.coherence_valid)
        self._trace(f"  Max score: {self.coherence.coherence_score:.3f} (expected ~6.707)")

        self.coherence.evaluate(0, 0, 1.0)
        self._check("Min coherence (E=0, C=0) < 1.0", not self.coherence.coherence_valid)

        self.coherence.evaluate(15, 3, 3.0)
        self._check("Mid coherence should be medium", self.coherence.medium_coherence)

        return results

    def run_scalar_trigger_tests(self):
        """Test scalar trigger with various durations."""
        self._trace("="*60)
        self._trace("ScalarTrigger_Ra - Duration Tests")
        self._trace("="*60)

        # Test 1: Basic trigger with duration=4
        self.scalar.reset()
        self.vcd.change("reset", 1)
        self._clock()
        self.vcd.change("reset", 0)

        self._trace("Testing radius=150, threshold=100, duration=4")
        print("\nCycle | Counter | Above | Triggered | Stable")
        print("------|---------|-------|-----------|-------")

        for cycle in range(10):
            self.coherence.evaluate(15, 3, 3.0)  # Medium coherence
            self.scalar.clock(
                enable=True,
                radius=150,
                activation_threshold=100,
                coherence_duration=4,
                coherence_valid=self.coherence.coherence_valid
            )

            self.vcd.change("radius", 150)
            self.vcd.change("scalar_threshold", 100)
            self.vcd.change("coherence_counter", self.scalar.coherence_counter)
            self.vcd.change("scalar_triggered", int(self.scalar.scalar_triggered))
            self.vcd.change("above_threshold", int(self.scalar.above_threshold))
            self.vcd.change("stable_resonance", int(self.scalar.stable_resonance))
            self._clock()

            print(f"  {cycle:2d}  |    {self.scalar.coherence_counter}    |   {'Y' if self.scalar.above_threshold else 'N'}   |"
                  f"     {'Y' if self.scalar.scalar_triggered else 'N'}     |   {'Y' if self.scalar.stable_resonance else 'N'}")

        self._check("Scalar triggered after duration", self.scalar.scalar_triggered)

        # Test 2: Reset on threshold drop
        self._trace("\nDropping radius below threshold...")
        self.scalar.clock(True, 50, 100, 4, True)
        self.vcd.change("radius", 50)
        self._clock()

        self._check("Scalar reset when radius drops", not self.scalar.scalar_triggered)
        self._check("Counter reset when radius drops", self.scalar.coherence_counter == 0)

        # Test 3: Fluctuation recovery
        self._trace("\nFluctuation test...")
        self.scalar.reset()
        for _ in range(2):
            self.scalar.clock(True, 150, 100, 4, True)
            self._clock()
        self.scalar.clock(True, 50, 100, 4, True)  # Drop
        self._clock()
        for _ in range(6):
            self.scalar.clock(True, 150, 100, 4, True)  # Recover
            self._clock()

        self._check("Trigger after fluctuation recovery", self.scalar.scalar_triggered)

    def run_fallback_tests(self):
        """Test fallback resolver XOR logic."""
        self._trace("="*60)
        self._trace("FallbackResolver_Ra - XOR Logic")
        self._trace("="*60)

        # Test basic XOR
        self.fallback.resolve(
            trigger=False,
            primary_theta=12,
            primary_phi=3,
            primary_omega=2,
            primary_radius=128,
            fallback_vector=0b10101101  # theta_off=5, phi_off=3, omega_off=1
        )

        self._trace(f"Primary: theta={self.fallback.fallback_theta} phi={self.fallback.fallback_phi} "
                   f"omega={self.fallback.fallback_omega}")
        self._check("No trigger passes primary", self.fallback.fallback_theta == 12)

        # Trigger fallback
        self.fallback.resolve(True, 12, 3, 2, 128, 0b10101101)
        self.vcd.change("fallback_trigger", 1)
        self.vcd.change("fallback_theta", self.fallback.fallback_theta)
        self.vcd.change("fallback_phi", self.fallback.fallback_phi)
        self.vcd.change("fallback_omega", self.fallback.fallback_omega)
        self.vcd.change("fallback_active", int(self.fallback.fallback_active))
        self._clock()

        self._trace(f"Fallback: theta={self.fallback.fallback_theta} phi={self.fallback.fallback_phi} "
                   f"omega={self.fallback.fallback_omega}")
        self._check("Fallback active flag", self.fallback.fallback_active)

        # Test wrap-around
        self._trace("\nWrap-around tests:")
        self.fallback.resolve(True, 26, 5, 4, 128, 0b11111111)
        self._trace(f"Theta wrap: 26 XOR 7 = {self.fallback.fallback_theta}")
        self._check("Theta in valid range", 1 <= self.fallback.fallback_theta <= 27)
        self._check("Phi in valid range", self.fallback.fallback_phi <= 5)
        self._check("Omega in valid range", self.fallback.fallback_omega <= 4)

    def run_arbitrator_tests(self):
        """Test consent arbitrator decision matrix."""
        self._trace("="*60)
        self._trace("ConsentArbitrator_Ra - Decision Matrix")
        self._trace("="*60)

        print("\ncoh_v | sca_t | state | fb | pma | allowed | use_fb | use_pma | decision")
        print("------|-------|-------|----|----|---------|--------|---------|----------")

        # Sweep key combinations
        for coherence_valid in [False, True]:
            for consent_state in [ConsentState.FULL_CONSENT, ConsentState.DIMINISHED_CONSENT,
                                  ConsentState.SUSPENDED_CONSENT, ConsentState.EMERGENCY_OVERRIDE]:
                for needs_fallback in [False, True]:
                    for pma_hit in [False, True]:
                        self.arbitrator.arbitrate(
                            coherence_valid=coherence_valid,
                            scalar_triggered=False,
                            consent_state=consent_state,
                            needs_fallback=needs_fallback,
                            pma_hit=pma_hit
                        )

                        self.vcd.change("route_allowed", int(self.arbitrator.route_allowed))
                        self.vcd.change("use_fallback", int(self.arbitrator.use_fallback))
                        self.vcd.change("use_pma_route", int(self.arbitrator.use_pma_route))
                        self.vcd.change("routing_decision", int(self.arbitrator.routing_decision))
                        self._clock()

                        print(f"  {'Y' if coherence_valid else 'N'}   |   N   |  {consent_state:2d}   |"
                              f"  {'Y' if needs_fallback else 'N'} |  {'Y' if pma_hit else 'N'}  |"
                              f"    {'Y' if self.arbitrator.route_allowed else 'N'}    |"
                              f"   {'Y' if self.arbitrator.use_fallback else 'N'}    |"
                              f"    {'Y' if self.arbitrator.use_pma_route else 'N'}    |"
                              f"    {self.arbitrator.routing_decision.name}")

        # Key assertions
        self.arbitrator.arbitrate(True, False, ConsentState.FULL_CONSENT, False, False)
        self._check("FULL_CONSENT + coherent = allowed", self.arbitrator.route_allowed)

        self.arbitrator.arbitrate(True, False, ConsentState.SUSPENDED_CONSENT, False, False)
        self._check("SUSPENDED = blocked", not self.arbitrator.route_allowed)

        self.arbitrator.arbitrate(True, False, ConsentState.EMERGENCY_OVERRIDE, False, False)
        self._check("EMERGENCY = blocked", not self.arbitrator.route_allowed)

        self.arbitrator.arbitrate(False, False, ConsentState.DIMINISHED_CONSENT, False, False)
        self._check("DIMINISHED + incoherent = blocked", not self.arbitrator.route_allowed)

        self.arbitrator.arbitrate(True, False, ConsentState.DIMINISHED_CONSENT, False, False)
        self._check("DIMINISHED + coherent = allowed", self.arbitrator.route_allowed)

    def run_header_parser_tests(self):
        """Test consent header parser field extraction."""
        self._trace("="*60)
        self._trace("ConsentHeaderParser - Field Extraction")
        self._trace("="*60)

        # Build test header
        # theta=12, phi=3, omega=2, radius=128 → RPP addr
        rpp_addr = (12 << 27) | (3 << 24) | (2 << 21) | (128 << 13)

        # Build full 144-bit header
        header = (
            (rpp_addr << 112) |          # Bytes 0-3
            (0xDEADBEEF << 80) |          # Packet ID
            (0x1234 << 64) |              # Origin ref
            (0xE5 << 56) |                # Consent: verbal=1, somatic=12, ancestral=2, temporal=1
            (0xA5 << 48) |                # entropy=20, complecount=5
            (0x03 << 40) |                # payload=3
            (0xAA << 32) |                # fallback=0xAA
            (0x1A2B << 16) |              # window_id=0x1A2B
            (0x55 << 8) |                 # target_phase=0x55
            0xFF                           # CRC
        )

        self.parser.parse(header)

        self._trace(f"Header: 0x{header:036X}")
        self._trace(f"  theta={self.parser.rpp_theta} phi={self.parser.rpp_phi} "
                   f"omega={self.parser.rpp_omega} r={self.parser.rpp_radius}")
        self._trace(f"  entropy={self.parser.phase_entropy_index} "
                   f"complecount={self.parser.complecount_trace}")
        self._trace(f"  window_id=0x{self.parser.coherence_window_id:04X}")
        self._trace(f"  consent_state={self.parser.consent_state.name}")

        # Update VCD
        self.vcd.change("rpp_theta", self.parser.rpp_theta)
        self.vcd.change("rpp_phi", self.parser.rpp_phi)
        self.vcd.change("rpp_omega", self.parser.rpp_omega)
        self.vcd.change("rpp_radius", self.parser.rpp_radius)
        self.vcd.change("phase_entropy_index", self.parser.phase_entropy_index)
        self.vcd.change("complecount_trace", self.parser.complecount_trace)
        self.vcd.change("coherence_window_id", self.parser.coherence_window_id)
        self.vcd.change("consent_state", int(self.parser.consent_state))
        self.vcd.change("needs_fallback", int(self.parser.needs_fallback))
        self.vcd.change("has_pma_link", int(self.parser.has_pma_link))
        self._clock()

        self._check("Theta extraction", self.parser.rpp_theta == 12)
        self._check("Phi extraction", self.parser.rpp_phi == 3)
        self._check("Omega extraction", self.parser.rpp_omega == 2)
        self._check("Radius extraction", self.parser.rpp_radius == 128)
        self._check("Entropy extraction", self.parser.phase_entropy_index == 20)
        self._check("Complecount extraction", self.parser.complecount_trace == 5)
        self._check("Window ID extraction", self.parser.coherence_window_id == 0x1A2B)
        self._check("Has PMA link", self.parser.has_pma_link)
        self._check("Full consent (high somatic)", self.parser.consent_state == ConsentState.FULL_CONSENT)

    def run_integration_tests(self):
        """Full pipeline integration scenarios."""
        self._trace("="*60)
        self._trace("Integration - Full Pipeline")
        self._trace("="*60)

        # Scenario 1: Normal routing
        self._trace("\nScenario 1: Normal routing with full consent")
        rpp_addr = (12 << 27) | (3 << 24) | (2 << 21) | (128 << 13)
        header = (rpp_addr << 112) | (0xDEADBEEF << 80) | (0x1234 << 64) | \
                 (0xE5 << 56) | (0x50 << 48) | (0x03 << 40) | (0x00 << 32) | \
                 (0x0000 << 16) | (0x55 << 8) | 0xFF

        self.parser.parse(header)
        self.coherence.evaluate(self.parser.phase_entropy_index,
                               self.parser.complecount_trace, 2.0)
        self.arbitrator.arbitrate(
            self.coherence.coherence_valid,
            False,
            self.parser.consent_state,
            self.parser.needs_fallback,
            False
        )

        self._trace(f"  Coherence: {self.coherence.coherence_score:.3f}")
        self._trace(f"  Route decision: {self.arbitrator.routing_decision.name}")
        self._check("Scenario 1: Route allowed", self.arbitrator.route_allowed)

        # Scenario 2: Fallback triggered
        self._trace("\nScenario 2: Fallback triggered by high entropy")
        header = (rpp_addr << 112) | (0xDEADBEEF << 80) | (0x1234 << 64) | \
                 (0xE5 << 56) | (0xD8 << 48) | (0x03 << 40) | (0xAA << 32) | \
                 (0x0000 << 16) | (0x55 << 8) | 0xFF  # entropy=27

        self.parser.parse(header)
        self.coherence.evaluate(self.parser.phase_entropy_index,
                               self.parser.complecount_trace, 6.0)  # High threshold
        self.arbitrator.arbitrate(
            self.coherence.coherence_valid,
            False,
            self.parser.consent_state,
            self.parser.needs_fallback,
            False
        )

        self._trace(f"  Needs fallback: {self.parser.needs_fallback}")
        self._trace(f"  Use fallback: {self.arbitrator.use_fallback}")
        self._check("Scenario 2: Needs fallback", self.parser.needs_fallback)

        # Scenario 3: PMA-linked routing
        self._trace("\nScenario 3: PMA-linked routing with max coherence")
        header = (rpp_addr << 112) | (0xDEADBEEF << 80) | (0x1234 << 64) | \
                 (0xE5 << 56) | (0xFF << 48) | (0x03 << 40) | (0x00 << 32) | \
                 (0x1A2B << 16) | (0x55 << 8) | 0xFF  # entropy=31, comple=7, window=0x1A2B

        self.parser.parse(header)
        self.coherence.evaluate(self.parser.phase_entropy_index,
                               self.parser.complecount_trace, 4.0)
        self.arbitrator.arbitrate(
            self.coherence.coherence_valid,
            False,
            self.parser.consent_state,
            self.parser.needs_fallback,
            True  # PMA hit
        )

        self._trace(f"  Has PMA: {self.parser.has_pma_link}")
        self._trace(f"  Use PMA route: {self.arbitrator.use_pma_route}")
        self._check("Scenario 3: PMA route used", self.arbitrator.use_pma_route)

    def run_all_tests(self):
        """Execute complete test suite."""
        self.vcd.begin()
        self.vcd.change("clk", 0)
        self.vcd.change("reset", 0)
        self.vcd.change("enable", 1)

        try:
            self.run_coherence_sweep()
            self.run_scalar_trigger_tests()
            self.run_fallback_tests()
            self.run_arbitrator_tests()
            self.run_header_parser_tests()
            self.run_integration_tests()
        finally:
            self.vcd.end()

        # Summary
        self._trace("="*60)
        self._trace("TEST SUMMARY")
        self._trace("="*60)
        self._trace(f"Total tests: {self.test_count}")
        self._trace(f"Passed:      {self.pass_count}")
        self._trace(f"Failed:      {self.fail_count}")
        self._trace("")

        if self.fail_count == 0:
            self._trace("*** ALL TESTS PASSED ***")
        else:
            self._trace(f"*** {self.fail_count} TESTS FAILED ***")

        # Coverage report
        self._trace("\nCoverage:")
        for key, count in sorted(self.coverage.items()):
            self._trace(f"  {key}: {count}")

        # Save trace log
        trace_file = "spiral_ra_trace.log"
        with open(trace_file, 'w') as f:
            f.write('\n'.join(self.trace_log))
        print(f"\nTrace log: {trace_file}")
        print(f"Waveform:  {self.vcd.filename}")
        print("View with: gtkwave spiral_ra_sim.vcd")

        return self.fail_count == 0


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("="*60)
    print("SPIRAL Protocol - Ra-Canonical HDL Simulation")
    print("="*60)
    print(f"PHI (GREEN_PHI) = {GREEN_PHI:.15f}")
    print(f"ANKH_SYMBOL (ANKH)      = {ANKH:.15f}")
    print("="*60)
    print()

    tb = SpiralRaTestbench("spiral_ra_sim.vcd")
    success = tb.run_all_tests()

    sys.exit(0 if success else 1)
