"""
RPP Spintronics Substrate Simulation
======================================

Simulates the physical spin lattice that underlies the RPP Transport/Resonance Layer.

Architecture:
  - Spin sites arranged in the RPP spherical coordinate geometry (theta/phi/shell)
  - Each site has a Bloch vector (mx, my, mz) representing electron spin state
  - Larmor precession at frequency derived from Ra ANKH constant
  - T2 decoherence modulated by RAC consent level
  - Routing via spin-transfer torque along sector adjacency graph

RPP address → lattice position mapping:
  - Theta (Repitan 1-27) → azimuthal sector of spin lattice
  - Phi (RAC 1-6) → polar layer of spin lattice (consent gradient)
  - Shell → radial depth (T1/T2 profile: Hot=fast, Frozen=slow)
  - Harmonic/Omega → precession frequency mode

Physics model (simplified Bloch equations):
  dMx/dt = Ω × My - Mx / T2
  dMy/dt = -Ω × Mx - My / T2
  dMz/dt = -(Mz - M0) / T1

Where:
  Ω = ANKH × harmonic_scale   (Ra master harmonic × tier scaling)
  T1 = shell_T1[shell]          (longitudinal: energy to environment)
  T2 = rac_T2[rac_level]        (transverse: phase coherence, consent-gated)
  M0 = 1.0                      (thermal equilibrium = fully up)

Run:
  python spintronic_sim.py                    # ASCII visualization
  python spintronic_sim.py --vcd sim.vcd      # + VCD for GTKWave
  python spintronic_sim.py --address 0xD06180  # route a specific v2.0 address
  python spintronic_sim.py --semantic 0 12 40 1  # route a v1.0 semantic address
"""

from __future__ import annotations

import argparse
import io
import math
import sys
import time

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Ra Constants
# ─────────────────────────────────────────────────────────────────────────────

PHI   = 1.6180339887498948   # Golden ratio — coherence attractor
ANKH  = 5.08938              # Master harmonic (PHI^3 ≈ 4.236, Ra-adjusted)
RADEL = 2.71828182845904     # Euler's e — decay damping
ALPHA_INV = 137.035999084    # Fine-structure inverse — binding threshold

# Simulation clock
CLOCK_NS = 10                # 10 ns per tick = 100 MHz

# Spin lattice geometry
N_REPITAN = 27               # Theta sectors (Ra Repitans)
N_RAC     = 6                # Phi layers (RAC access levels)
N_SHELLS  = 4                # Radial shells (Hot→Warm→Cold→Frozen)

# Shell relaxation profiles (ns)
# Hot storage: fast write/read, short T1/T2
# Frozen: slow, high coherence, long T1/T2
SHELL_T1 = {0: 50,   1: 200,  2: 800,  3: 3200}   # longitudinal (energy)
SHELL_T2 = {0: 25,   1: 100,  2: 400,  3: 1600}   # transverse (phase)

# RAC level consent modulation of T2 (multiplier)
# RAC1 = highest sensitivity = longest T2 (most protected)
# RAC6 = public = shortest T2 (least coherent)
RAC_T2_MULT = {1: 4.0, 2: 2.5, 3: 1.5, 4: 1.0, 5: 0.7, 6: 0.5}

# Omega tier → precession frequency scale
OMEGA_FREQ = {0: 0.5, 1: 0.75, 2: 1.0, 3: 1.5, 4: 2.0}

# Sector adjacency (from RPP_Canonical.hs)
SECTOR_ADJACENCY: Dict[int, List[int]] = {
    0: [1, 2],          # Core ↔ Gene, Memory
    1: [0, 5, 6],       # Gene ↔ Core, Bridge, Guardian
    2: [0, 3, 5],       # Memory ↔ Core, Witness, Bridge
    3: [2, 5],          # Witness ↔ Memory, Bridge
    4: [5, 7],          # Dream ↔ Bridge, Shadow
    5: [1, 2, 3, 4, 6], # Bridge ↔ Gene, Memory, Witness, Dream, Guardian
    6: [1, 5],          # Guardian ↔ Gene, Bridge
    7: [4],             # Shadow ↔ Dream
}

SECTOR_NAMES = [
    "Core", "Gene", "Memory", "Witness",
    "Dream", "Bridge", "Guardian", "Shadow"
]

SECTOR_MIN_COHERENCE = {
    0: 0.80,  # Core (highest protection)
    1: 0.60,  # Gene
    2: 0.75,  # Memory
    3: 0.40,  # Witness
    4: 0.50,  # Dream
    5: 0.70,  # Bridge
    6: 0.75,  # Guardian
    7: 0.30,  # Shadow (most accessible)
}


# ─────────────────────────────────────────────────────────────────────────────
# Address Translation
# ─────────────────────────────────────────────────────────────────────────────

def repitan_to_sector(theta_repitan: int) -> int:
    """Map Repitan index (1-27) to ThetaSector (0-7)."""
    if theta_repitan <= 3:  return 0  # Core
    if theta_repitan <= 6:  return 1  # Gene
    if theta_repitan <= 10: return 2  # Memory
    if theta_repitan <= 13: return 3  # Witness
    if theta_repitan <= 17: return 4  # Dream
    if theta_repitan <= 20: return 5  # Bridge
    if theta_repitan <= 24: return 6  # Guardian
    return 7                           # Shadow (25-27)


def decode_v2(address: int) -> Tuple[int, int, int, float]:
    """Decode 32-bit v2.0 transport address → (theta, phi, omega, radius)."""
    theta  = (address >> 27) & 0x1F
    phi    = ((address >> 24) & 0x07) + 1   # stored as 0-5, semantic 1-6
    omega  = (address >> 21) & 0x07
    radius = ((address >> 13) & 0xFF) / 255.0
    return theta, phi, omega, radius


def decode_v1(address: int) -> Tuple[int, int, int, int]:
    """Decode 28-bit v1.0 semantic address → (shell, theta, phi, harmonic)."""
    shell    = (address >> 26) & 0x3
    theta    = (address >> 17) & 0x1FF
    phi      = (address >> 8)  & 0x1FF
    harmonic = address & 0xFF
    return shell, theta, phi, harmonic


def v1_to_v2(shell: int, theta: int, phi: int, harmonic: int) -> Tuple[int, int, int, float]:
    """Translate v1.0 semantic → v2.0 transport (lossy projection)."""
    theta_v2  = max(1, min(27, (theta * 27) // 512 + 1))
    phi_v2    = max(1, min(6,  (phi * 6) // 512 + 1))
    omega_v2  = min(4, (harmonic * 5) // 256)
    radius_v2 = shell / 3.0
    return theta_v2, phi_v2, omega_v2, radius_v2


# ─────────────────────────────────────────────────────────────────────────────
# Spin Site
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SpinSite:
    """
    Single spin site on the RPP lattice.

    Position in lattice:
      repitan  (1-27): azimuthal sector
      rac      (1-6):  polar consent layer
      shell    (0-3):  radial depth

    State (Bloch vector):
      mx, my: transverse components (coherence)
      mz:     longitudinal component (population)
    """
    repitan: int
    rac: int
    shell: int

    mx: float = 0.0   # transverse x (coherence)
    my: float = 0.0   # transverse y (coherence)
    mz: float = 1.0   # longitudinal (ground state = up)

    phase: float = 0.0   # cumulative precession phase (radians)
    active: bool = False  # currently routing a packet

    @property
    def sector(self) -> int:
        return repitan_to_sector(self.repitan)

    @property
    def coherence(self) -> float:
        """Transverse coherence magnitude = |Mxy| / M0."""
        return math.sqrt(self.mx**2 + self.my**2)

    @property
    def population(self) -> float:
        """Longitudinal spin population (0=down, 1=up)."""
        return (self.mz + 1.0) / 2.0

    @property
    def bloch_angles(self) -> Tuple[float, float]:
        """Return (polar_angle_deg, azimuthal_angle_deg) on Bloch sphere."""
        r = math.sqrt(self.mx**2 + self.my**2 + self.mz**2)
        if r < 1e-10:
            return 90.0, 0.0
        polar = math.degrees(math.acos(self.mz / r))
        azimuthal = math.degrees(math.atan2(self.my, self.mx))
        return polar, azimuthal

    def excite(self, amplitude: float = 0.8):
        """Write a spin state (tipping pulse from z toward xy plane)."""
        angle = amplitude * math.pi / 2
        self.mz = math.cos(angle)
        self.my = math.sin(angle)
        self.mx = 0.0
        self.active = True

    def step(self, dt_ns: float, omega: float):
        """
        Evolve spin state by dt_ns using Bloch equations.

        Args:
            dt_ns: time step in nanoseconds
            omega: precession angular frequency (rad/ns)
        """
        t1 = SHELL_T1[self.shell]
        t2_base = SHELL_T2[self.shell]
        t2 = t2_base * RAC_T2_MULT.get(self.rac, 1.0)

        # Larmor precession (rotation in xy plane)
        cos_p = math.cos(omega * dt_ns)
        sin_p = math.sin(omega * dt_ns)
        mx_new = self.mx * cos_p - self.my * sin_p
        my_new = self.mx * sin_p + self.my * cos_p

        # T2 transverse relaxation (decoherence)
        decay_t2 = math.exp(-dt_ns / t2)
        mx_new *= decay_t2
        my_new *= decay_t2

        # T1 longitudinal relaxation (return to equilibrium)
        decay_t1 = math.exp(-dt_ns / t1)
        mz_new = self.mz * decay_t1 + 1.0 * (1 - decay_t1)

        self.mx = mx_new
        self.my = my_new
        self.mz = mz_new
        self.phase += omega * dt_ns

        # Deactivate if coherence drops below threshold
        if self.coherence < 0.05:
            self.active = False


# ─────────────────────────────────────────────────────────────────────────────
# Spin Lattice
# ─────────────────────────────────────────────────────────────────────────────

class SpinLattice:
    """
    Full RPP spin lattice: 27 Repitans × 6 RAC layers × 4 shells.

    Total sites: 27 × 6 × 4 = 648 spin sites.
    """

    def __init__(self):
        self.sites: Dict[Tuple[int,int,int], SpinSite] = {}
        for repitan in range(1, N_REPITAN + 1):
            for rac in range(1, N_RAC + 1):
                for shell in range(N_SHELLS):
                    key = (repitan, rac, shell)
                    self.sites[key] = SpinSite(repitan=repitan, rac=rac, shell=shell)

    def get(self, repitan: int, rac: int, shell: int) -> Optional[SpinSite]:
        return self.sites.get((repitan, rac, shell))

    def sector_sites(self, sector: int, rac: int, shell: int) -> List[SpinSite]:
        """All sites in a given sector/rac/shell (may span multiple Repitans)."""
        sites = []
        for repitan in range(1, N_REPITAN + 1):
            if repitan_to_sector(repitan) == sector:
                s = self.get(repitan, rac, shell)
                if s:
                    sites.append(s)
        return sites

    def step_all(self, dt_ns: float, omega: float):
        for site in self.sites.values():
            site.step(dt_ns, omega)

    def coherence_map(self, shell: int = 0) -> List[List[float]]:
        """Return coherence[sector][rac] for a given shell."""
        result = []
        for sector in range(8):
            row = []
            for rac in range(1, N_RAC + 1):
                sites = self.sector_sites(sector, rac, shell)
                if sites:
                    row.append(sum(s.coherence for s in sites) / len(sites))
                else:
                    row.append(0.0)
            result.append(row)
        return result

    def average_coherence(self) -> float:
        vals = [s.coherence for s in self.sites.values()]
        return sum(vals) / len(vals) if vals else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Routing Engine
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RoutingResult:
    allowed: bool
    route: Optional[str]
    reason: str
    path: List[int]          # sector traversal path
    coherence_at_dest: float
    cycles: int


class SpintronicRouter:
    """
    Routes RPP packets through the spin lattice via spin-transfer torque.

    Protocol:
    1. Source site excited with tipping pulse
    2. Spin current propagates through sector adjacency graph
    3. Consent gate checks coherence at each hop
    4. Destination site coherence determines allow/deny
    """

    def __init__(self, lattice: SpinLattice):
        self.lattice = lattice

    def route(
        self,
        theta: int,   # Repitan 1-27
        phi: int,     # RAC level 1-6
        omega: int,   # Omega tier 0-4
        radius: float,  # intensity 0.0-1.0
        sim_cycles: int = 20,
        verbose: bool = True,
    ) -> RoutingResult:
        """
        Route a v2.0 transport address through the spin lattice.
        Returns routing decision after simulating spin propagation.
        """
        sector = repitan_to_sector(theta)
        shell = round(radius * (N_SHELLS - 1))
        omega_freq = OMEGA_FREQ.get(omega, 1.0) * ANKH * 0.01  # rad/ns

        if verbose:
            print(f"\n{'─'*60}")
            print(f"  SPINTRONIC ROUTING")
            print(f"{'─'*60}")
            print(f"  Address:  θ={theta} ({SECTOR_NAMES[sector]})  "
                  f"φ=RAC{phi}  h=Ω{omega}  r={radius:.2f}")
            print(f"  Shell:    {shell} ({'Hot' if shell==0 else 'Warm' if shell==1 else 'Cold' if shell==2 else 'Frozen'})")
            print(f"  Freq:     {omega_freq*1000:.3f} mrad/ns "
                  f"(ANKH={ANKH:.4f} × Ω{omega} scale {OMEGA_FREQ[omega]})")

        # Find path via BFS through sector adjacency
        path = self._find_path(0, sector)  # route from Core (sector 0)
        if verbose:
            path_names = " → ".join(SECTOR_NAMES[s] for s in path)
            print(f"  Path:     {path_names}")

        # Excite sites along the path
        for hop_sector in path:
            sites = self.lattice.sector_sites(hop_sector, phi, shell)
            for site in sites:
                site.excite(amplitude=min(0.9, radius + 0.2))

        # Simulate spin propagation
        coherence_trace = []
        for cycle in range(sim_cycles):
            self.lattice.step_all(CLOCK_NS, omega_freq)

            # Apply spin-transfer torque at each hop boundary
            for i in range(len(path) - 1):
                src_sites = self.lattice.sector_sites(path[i], phi, shell)
                dst_sites = self.lattice.sector_sites(path[i+1], phi, shell)
                if src_sites and dst_sites:
                    src_coh = sum(s.coherence for s in src_sites) / len(src_sites)
                    if src_coh > 0.2:
                        # Spin-transfer torque: partially align dst toward src
                        src_avg_my = sum(s.my for s in src_sites) / len(src_sites)
                        for dst in dst_sites:
                            dst.mx += src_avg_my * 0.05
                            dst.my += src_avg_my * 0.05

            # Track coherence at destination
            dest_sites = self.lattice.sector_sites(sector, phi, shell)
            if dest_sites:
                coh = sum(s.coherence for s in dest_sites) / len(dest_sites)
                coherence_trace.append(coh)

        final_coherence = coherence_trace[-1] if coherence_trace else 0.0
        min_required = SECTOR_MIN_COHERENCE[sector]

        # Consent gate decision
        if final_coherence >= min_required:
            route_str = f"spintronic://{SECTOR_NAMES[sector].lower()}/rac{phi}/shell{shell}/r{theta}"
            allowed = True
            reason = (f"Coherence {final_coherence:.3f} ≥ required {min_required:.2f} "
                      f"for {SECTOR_NAMES[sector]}")
        else:
            route_str = None
            allowed = False
            reason = (f"Coherence {final_coherence:.3f} < required {min_required:.2f} "
                      f"for {SECTOR_NAMES[sector]} (decoherence at RAC{phi})")

        if verbose:
            self._print_result(allowed, route_str, reason, final_coherence,
                               coherence_trace, sim_cycles)

        return RoutingResult(
            allowed=allowed,
            route=route_str,
            reason=reason,
            path=path,
            coherence_at_dest=final_coherence,
            cycles=sim_cycles,
        )

    def _find_path(self, src_sector: int, dst_sector: int) -> List[int]:
        """BFS shortest path through sector adjacency graph."""
        if src_sector == dst_sector:
            return [dst_sector]
        visited = {src_sector}
        queue = [[src_sector]]
        while queue:
            path = queue.pop(0)
            curr = path[-1]
            for neighbor in SECTOR_ADJACENCY.get(curr, []):
                if neighbor == dst_sector:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return [src_sector, dst_sector]  # fallback: direct

    def _print_result(self, allowed, route, reason, final_coh,
                      trace, cycles):
        print(f"\n  COHERENCE TRACE (destination sector):")
        width = 50
        for i, c in enumerate(trace):
            bar = int(c * width)
            tag = " ← peak" if c == max(trace) else ""
            print(f"    t={i*CLOCK_NS:3d}ns  {'█'*bar}{'░'*(width-bar)}  {c:.3f}{tag}")

        print(f"\n  CONSENT GATE:")
        if allowed:
            print(f"    ✓  ALLOW  — {reason}")
            print(f"    route → {route}")
        else:
            print(f"    ✗  DENY   — {reason}")


# ─────────────────────────────────────────────────────────────────────────────
# ASCII Lattice Visualization
# ─────────────────────────────────────────────────────────────────────────────

def print_lattice(lattice: SpinLattice, shell: int = 0, title: str = ""):
    """Print ASCII coherence map of the spin lattice for a given shell."""
    cmap = lattice.coherence_map(shell)

    shell_name = ['Hot', 'Warm', 'Cold', 'Frozen'][shell]
    print(f"\n{'═'*70}")
    if title:
        print(f"  {title}")
    print(f"  SPIN LATTICE  —  Shell {shell} ({shell_name})")
    print(f"  Coherence map: sectors × RAC levels")
    print(f"{'─'*70}")
    print(f"  {'Sector':<12}  RAC1    RAC2    RAC3    RAC4    RAC5    RAC6")
    print(f"{'─'*70}")

    BARS = " ▁▂▃▄▅▆▇█"

    for sector_idx, (name, row) in enumerate(zip(SECTOR_NAMES, cmap)):
        cells = []
        for coh in row:
            bar_idx = min(8, int(coh * 9))
            bar = BARS[bar_idx]
            cells.append(f"  {bar} {coh:.2f}")
        print(f"  {name:<12}{''.join(cells)}")

    print(f"{'─'*70}")
    print(f"  Average coherence: {lattice.average_coherence():.4f}")
    print(f"{'═'*70}")


# ─────────────────────────────────────────────────────────────────────────────
# VCD Writer
# ─────────────────────────────────────────────────────────────────────────────

class VCDWriter:
    """Generates Value Change Dump files for GTKWave."""

    def __init__(self, filename: str):
        self.filename = filename
        self._sigs: Dict[str, Tuple[str, int]] = {}
        self._counter = 0
        self._t = 0
        self._f = None

    def _id(self) -> str:
        chars = "!#$%&'()*+-./0123456789:<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        n = self._counter
        self._counter += 1
        if n < len(chars):
            return chars[n]
        return chars[n // len(chars)] + chars[n % len(chars)]

    def add(self, name: str, width: int = 8) -> str:
        sig_id = self._id()
        self._sigs[name] = (sig_id, width)
        return sig_id

    def begin(self):
        self._f = open(self.filename, 'w')
        self._f.write(f"$date {time.strftime('%Y-%m-%d %H:%M:%S')} $end\n")
        self._f.write("$version RPP-Spintronic-Sim v1.0 $end\n")
        self._f.write("$timescale 1ns $end\n")
        self._f.write("$scope module spintronic_tb $end\n")
        for name, (sid, w) in self._sigs.items():
            self._f.write(f"$var wire {w} {sid} {name} $end\n")
        self._f.write("$upscope $end\n$enddefinitions $end\n#0\n$dumpvars\n")
        for name, (sid, w) in self._sigs.items():
            self._f.write(f"b{'0'*w} {sid}\n")
        self._f.write("$end\n")

    def tick(self, t: int):
        self._t = t
        self._f.write(f"#{t}\n")

    def set(self, name: str, value: int):
        if name in self._sigs:
            sid, w = self._sigs[name]
            self._f.write(f"b{value:0{w}b} {sid}\n")

    def set_float(self, name: str, value: float, scale: int = 255):
        self.set(name, int(value * scale) & ((1 << self._sigs[name][1]) - 1))

    def end(self):
        if self._f:
            self._f.close()
            print(f"\n  VCD written → {self.filename}")
            print(f"  View with: gtkwave {self.filename}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Simulation
# ─────────────────────────────────────────────────────────────────────────────

def run_simulation(
    theta: int,
    phi: int,
    omega: int,
    radius: float,
    cycles: int = 30,
    vcd_path: Optional[str] = None,
    shell_display: int = 0,
):
    lattice = SpinLattice()
    router  = SpintronicRouter(lattice)

    print(f"\n  RPP SPINTRONICS SUBSTRATE SIMULATION")
    print(f"  {'─'*50}")
    print(f"  Ra Constants: φ={PHI:.4f}  𝔄={ANKH:.4f}  α⁻¹={ALPHA_INV:.1f}")
    print(f"  Lattice: {N_REPITAN} Repitans × {N_RAC} RAC × {N_SHELLS} shells "
          f"= {N_REPITAN*N_RAC*N_SHELLS} spin sites")
    print(f"  Clock: {CLOCK_NS}ns ({1000//CLOCK_NS} MHz)")

    # Show equilibrium state
    print_lattice(lattice, shell=shell_display, title="EQUILIBRIUM STATE (ground state)")

    # Set up VCD
    vcd = None
    if vcd_path:
        vcd = VCDWriter(vcd_path)
        vcd.add("clk", 1)
        vcd.add("theta", 5)
        vcd.add("phi_rac", 3)
        vcd.add("omega_tier", 3)
        vcd.add("radius_8bit", 8)
        vcd.add("dest_coherence", 8)
        vcd.add("lattice_avg_coherence", 8)
        vcd.add("access_granted", 1)
        vcd.add("gate_threshold", 8)
        sector = repitan_to_sector(theta)
        vcd.add("sector", 3)
        vcd.begin()

    # Route
    result = router.route(theta, phi, omega, radius,
                          sim_cycles=cycles, verbose=True)

    # Show post-routing state
    shell_target = round(radius * (N_SHELLS - 1))
    print_lattice(lattice, shell=shell_target,
                  title=f"POST-ROUTING STATE (shell {shell_target})")

    # VCD output
    if vcd:
        sector = repitan_to_sector(theta)
        threshold = SECTOR_MIN_COHERENCE[sector]
        for cycle in range(cycles):
            t = cycle * CLOCK_NS
            vcd.tick(t)
            vcd.set("clk", cycle % 2)
            vcd.set("theta", theta)
            vcd.set("phi_rac", phi - 1)
            vcd.set("omega_tier", omega)
            vcd.set("radius_8bit", round(radius * 255))
            vcd.set("sector", sector)
            vcd.set("gate_threshold", round(threshold * 255))
            # Approximate coherence trace
            decay = math.exp(-cycle * CLOCK_NS / (SHELL_T2[shell_target] *
                             RAC_T2_MULT.get(phi, 1.0)))
            ramp  = 1 - math.exp(-cycle * CLOCK_NS / (SHELL_T1[shell_target] * 0.5))
            coh   = min(1.0, ramp * radius * decay + 0.1)
            vcd.set_float("dest_coherence", coh)
            vcd.set_float("lattice_avg_coherence", lattice.average_coherence())
            vcd.set("access_granted", 1 if result.allowed else 0)
        vcd.end()

    # Summary
    print(f"\n{'═'*60}")
    print(f"  ROUTING DECISION")
    print(f"{'─'*60}")
    print(f"  {'ALLOW' if result.allowed else 'DENY '}")
    print(f"  Route:     {result.route or 'null'}")
    print(f"  Reason:    {result.reason}")
    print(f"  Coherence: {result.coherence_at_dest:.4f}")
    print(f"  Cycles:    {result.cycles} × {CLOCK_NS}ns = {result.cycles*CLOCK_NS}ns")
    print(f"{'═'*60}\n")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RPP Spintronics Substrate Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--address", type=lambda x: int(x, 0),
                        help="v2.0 32-bit transport address (hex, e.g. 0xD06180)")
    parser.add_argument("--semantic", nargs=4, type=int,
                        metavar=("SHELL", "THETA", "PHI", "HARMONIC"),
                        help="v1.0 28-bit semantic fields (e.g. 0 12 40 1)")
    parser.add_argument("--theta",  type=int, default=10,   help="Repitan 1-27")
    parser.add_argument("--phi",    type=int, default=3,    help="RAC level 1-6")
    parser.add_argument("--omega",  type=int, default=2,    help="Omega tier 0-4")
    parser.add_argument("--radius", type=float, default=0.5, help="Intensity 0.0-1.0")
    parser.add_argument("--cycles", type=int, default=30,   help="Simulation cycles")
    parser.add_argument("--vcd",    type=str, default=None, help="VCD output path")
    parser.add_argument("--shell",  type=int, default=0,
                        help="Shell to display in lattice map (0=Hot)")

    args = parser.parse_args()

    if args.address is not None:
        theta, phi, omega, radius = decode_v2(args.address)
        print(f"  v2.0 address {hex(args.address)} → θ={theta} φ=RAC{phi} Ω={omega} r={radius:.3f}")
    elif args.semantic is not None:
        shell_s, theta_s, phi_s, harm_s = args.semantic
        theta, phi, omega, radius = v1_to_v2(shell_s, theta_s, phi_s, harm_s)
        print(f"  v1.0 semantic shell={shell_s} θ={theta_s} φ={phi_s} h={harm_s}")
        print(f"    → v2.0 transport θ={theta} φ=RAC{phi} Ω={omega} r={radius:.3f}")
    else:
        theta  = args.theta
        phi    = args.phi
        omega  = args.omega
        radius = args.radius

    run_simulation(
        theta=theta,
        phi=phi,
        omega=omega,
        radius=radius,
        cycles=args.cycles,
        vcd_path=args.vcd,
        shell_display=args.shell,
    )


if __name__ == "__main__":
    main()
