# RPP Spintronic Physical Grounding

**Document:** SPINTRONIC.md
**Version:** 1.0.0
**Status:** Active — Physical Enforcement Reference
**Relates to:** spec/SPEC.md (Shell field, Section 2.2.1), rpp/continuity.py (SHELL_LIMINAL_TIMEOUT_NS, SHELL_T2_NS)
**License:** CC BY 4.0

---

## 1. Introduction: Why Physical Enforcement Matters

Software timeouts are promises. A Shell=0 TTL of 25 nanoseconds implemented purely in software is a statement of intent: the runtime *should* expire the key after 25 ns. Whether it actually does depends on the scheduler, the thread priority, OS interrupt latency, and the trustworthiness of the implementation. A sufficiently privileged process can read memory before the software deadline fires. A cold-boot attack captures DRAM state after power loss. A cache-timing side channel can extract key material from L1 cache long after the nominal TTL has expired.

Physical enforcement is different in kind, not in degree. When the enforcing mechanism is a property of matter — the spin coherence time of electrons in a solid-state lattice — there is no software path that bypasses it. You cannot patch the Hamiltonian. You cannot `sudo` your way around T2 decoherence. The key state is not hidden; it is gone.

This document establishes the physical grounding for the RPP Shell=0 (Hot) tier's 25 ns TTL, explains why that value was chosen to match the T2 spin decoherence time of conventional spintronic substrates, and maps each RPP shell tier to its corresponding hardware substrate and enforcement mechanism. It also documents the attack surface that physical decoherence closes and the residual attack surface that it does not close.

On conventional (non-spintronic) hardware, Shell=0 TTL is an advisory software constraint. Implementations MUST enforce it to the best of the runtime's ability, but cannot provide the physical guarantee. This document exists so that implementers understand what they are approximating and what they are not providing.

On spintronic hardware, Shell=0 TTL is a physical invariant. The statement "the key expires after 25 ns" is not a policy claim; it is a measurement of a material property.

---

## 2. Spin Coherence (T2): The Relevant Timescale

### 2.1 What Spin Coherence Is

Electrons carry intrinsic angular momentum — spin — which is a two-state quantum system: spin-up ($|\uparrow\rangle$) or spin-down ($|\downarrow\rangle$), or any quantum superposition thereof. In a spintronic device, information is encoded in the spin state of one or more electrons rather than (or in addition to) their charge. The spin state of a qubit-like register can be initialized, rotated, and read out using magnetic fields, spin-transfer torque, or optical pumping, depending on the substrate.

Spin coherence is the property that makes spin states useful for information storage: a spin that is initialized to a known state will remain in that state — remain *coherent* — for some finite duration before random perturbations (thermal fluctuations, lattice vibrations, magnetic noise from nearby nuclei, spin-orbit coupling) scramble it into an incoherent mixture. After decoherence, the spin state carries no recoverable information about its initial value.

Two characteristic timescales govern this process:

- **T1 (spin-lattice relaxation time):** The time for the spin's energy to equilibrate with the surrounding lattice. T1 governs how long a spin-up state takes to thermally relax toward the ground state. T1 is typically longer than T2.
- **T2 (spin-spin dephasing time, or transverse relaxation time):** The time for phase coherence to be lost due to random fluctuations in the local magnetic environment. T2 governs how long a superposition state remains coherent. T2 is always $\leq T1$ and is the operationally relevant timescale for information storage in the sense that matters for RPP: it is the time within which a spin-encoded key state remains readable in principle.

For RPP's security analysis, T2 is the critical quantity: it is the window during which a hypothetical adversary could, in principle, extract key material from the spin register. After T2, the key state has decohered into a statistical mixture and is irrecoverable.

### 2.2 Room-Temperature T2 Values

T2 times are highly substrate-dependent. They vary by orders of magnitude across materials and are sensitive to temperature, doping, strain, and device geometry. The values below are representative ranges derived from the experimental literature.

**Conventional spintronic substrates (inorganic, room temperature):**

| Material / Device | T2 (room temp.) | Notes |
|---|---|---|
| GaAs quantum dots | 1 – 10 ns | Strong spin-orbit and hyperfine coupling |
| Silicon (bulk, P donors) | 10 – 300 µs | Highly isotopically purified Si; exceptional long T2 |
| Silicon (natural, nanodevice) | 1 – 25 ns | Natural abundance Si-29 nuclei limit coherence |
| Nitrogen-vacancy (NV) center in diamond | 1 – 10 µs (room temp.) | Exceptional; not a conventional spin valve |
| Metallic spin valve (Co/Cu/Co) | 1 – 10 ns | Relevant for spin-transfer torque devices |
| Organic semiconductor (OLED-class) | 10 – 100 ns | Hyperfine-driven dephasing; longer T2 due to weak SOC |
| Graphene (monolayer) | 1 – 10 ns | Gate-tunable; substrate and edge disorder limit T2 |

The range that governs RPP's Shell=0 TTL is **1–25 ns** for conventional inorganic spintronic devices at room temperature operating conditions. Organic spintronic devices typically extend to **10–100 ns** due to weaker spin-orbit coupling and weaker hyperfine interactions, which is why organic spin valves are a promising direction for longer-coherence applications.

**Why room temperature specifically:** RPP is designed for practical deployment. Devices that require cryogenic cooling achieve much longer T2 (seconds to minutes for superconducting qubits or NV centers at millikelvin), but those systems are not practical for edge deployment, mobile devices, or server hardware. The Shell=0 T2 range is anchored to devices that operate at ambient temperature without specialized cooling.

### 2.3 Why T2 Is the Relevant Timescale for RPP

The RPP threat model for Shell=0 is: *an adversary who wants to extract a routing key after the packet has been forwarded*. The adversary has physical access to the device (or a high-fidelity side-channel read of the spintronic register). The question is: how long do they have?

The answer is T2. After T2, the spin register has decohered. The key is not encrypted; it is thermally destroyed. No classical measurement and no quantum measurement can extract information from a maximally mixed state — there is nothing left to extract.

This is categorically different from:
- A software key stored in DRAM (cold-boot extractable for seconds to minutes)
- A key in L1 cache (cache-timing extractable while the process runs)
- A key overwritten with zeros (potentially recoverable from DRAM remanence)
- A key in a hardware security module with a timeout (extractable if the HSM firmware is compromised before the timeout fires)

In all software cases, the key *exists* in classical memory for some duration. In the spintronic case, the key *exists as a spin state* for T2 and then does not exist in any recoverable form.

### 2.4 Key Citations

The following literature establishes the T2 values used in this document and the broader field of semiconductor spintronics:

- **Žutić, I., Fabian, J., and Das Sarma, S.** (2004). "Spintronics: Fundamentals and applications." *Reviews of Modern Physics*, 76(2), 323–410. — The canonical review of semiconductor spintronics. Sections 2 and 4 cover T1/T2 measurements across substrates. The 1–25 ns range for conventional devices derives from data in this review.

- **Awschalom, D.D., and Flatté, M.E.** (2007). "Challenges for semiconductor spintronics." *Nature Physics*, 3(3), 153–159. — Discusses room-temperature coherence requirements for practical spintronic devices, and explicitly identifies T2 as the limiting factor for spintronic memory applications. The paper discusses why organic semiconductors are attractive for longer T2 (weaker hyperfine; Section 2).

- **Dyakonov, M.I. (ed.)** (2008). *Spin Physics in Semiconductors*. Springer. — Chapter 2 covers T2 dephasing mechanisms in detail; relevant for understanding why the 1–25 ns range is robust across different conventional substrates.

- **Chappert, C., Fert, A., and Van Dau, F.N.** (2007). "The emergence of spin electronics in data storage." *Nature Materials*, 6(11), 813–823. — Covers spin-transfer torque devices and metallic spin valves, with measured T2 values in the 1–10 ns regime.

---

## 3. RPP Shell=0 Mapping: 25 ns TTL and Physical Rationale

### 3.1 The 25 ns Value

The Shell=0 liminal timeout is set to 25 nanoseconds in `rpp/continuity.py`:

```python
# SHELL_LIMINAL_TIMEOUT_NS (continuity.py, line 45-50)
SHELL_LIMINAL_TIMEOUT_NS: dict = {
    0: 25,     # T2 of origin substrate (ns) — spintronic physical deadline
    ...
}

# SHELL_T2_NS (continuity.py, line 32-37)
SHELL_T2_NS: dict = {
    0: 25,     # Hot — spintronic T2 decoherence time
    ...
}
```

The value 25 ns is chosen as the **upper bound of the T2 range for conventional room-temperature spintronic devices** (the 1–25 ns range established in Section 2.2). It is not an arbitrary choice; it represents the longest coherence time that should be assumed for a device that has not been specifically characterized. For well-characterized devices with shorter measured T2, implementations MAY use a shorter TTL. They MUST NOT use a longer TTL and claim physical enforcement.

### 3.2 Key as Spin State

On spintronic hardware, the routing key (the epoch value used in Pong key derivation, per `rpp/geometry.py`) is encoded as a spin state in a spintronic register during the routing decision. The implementation is substrate-specific, but the logical structure is:

1. **Initialization:** The epoch value is mapped to a spin orientation (e.g., via spin-transfer torque writing) at the moment the routing decision begins.
2. **Use:** The spin state is read during key derivation (Pong: `derive_rotation_key(phi, theta, harmonic, epoch)` in `rpp/geometry.py`). The read itself does not destroy the state, but the environmental decoherence process is continuously progressing.
3. **Expiry:** After T2, the spin state has decohered into a statistical mixture with no recoverable correlation to the original epoch value. The key is gone. No explicit deletion is required; no secure-erase routine is necessary; no overwrite is needed.

This satisfies the RPP Article II (Private Internal State) requirement for Shell=0: the epoch used to derive the routing key is never available for extraction after the routing window closes, because it does not exist in extractable form after T2.

### 3.3 Thermal Randomization: The Mechanism

The decoherence mechanism is thermal. At room temperature, the thermal energy $k_B T \approx 25$ meV is sufficient to drive random spin-flip events via:

- **Spin-orbit coupling (SOC):** Electron momentum scattering events flip the spin. In conventional semiconductors with heavy elements (GaAs, InAs), SOC is strong and T2 is short. In light-element materials (organic semiconductors, isotopically pure silicon), SOC is weak and T2 is longer.
- **Hyperfine interaction:** Coupling between the electron spin and the nuclear spins of the host lattice creates an effective random magnetic field that dephases the electron spin. In materials with zero-spin nuclei (isotopically purified Si-28, C-12 diamond), hyperfine T2 is dramatically extended.
- **Magnetic impurity scattering:** Defects with magnetic moments in the lattice scatter spin and reduce T2.

After T2, the spin state is described by the density matrix:

$$\rho(t \gg T_2) = \frac{1}{2}\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}$$

This is the maximally mixed state: a 50/50 statistical mixture of spin-up and spin-down with no phase information. The entropy of this state is maximal ($S = k_B \ln 2$ per spin). There is no measurement basis in which any information about the original spin state is recoverable, because that information has been dissipated into the thermal bath of the lattice.

**The key has not been erased; it has been thermalized.** The distinction matters: erasure is an operation that could in principle be reversed (if a backup exists). Thermalization is irreversible under the second law of thermodynamics.

---

## 4. Pong Key Decoherence: Article II at Physics Level

### 4.1 The Pong Key in Routing Context

The Pong rotational encryption scheme derives a key from four inputs:

```python
# rpp/geometry.py — derive_rotation_key signature
def derive_rotation_key(phi: int, theta: int, harmonic: int, epoch: int) -> tuple[float, float]:
    raw_theta = (phi   * PHI_GOLDEN * epoch) % 512
    raw_phi   = (theta * PHI_GOLDEN * epoch) % 512
    ...
```

Three of four inputs (phi, theta, harmonic) are present in the packet address and are visible to any observer who can read the packet header. The entire security of the Pong scheme rests on `epoch` confidentiality, as documented in `examples/security_bounds.py` (Section 1, Key Derivation Anatomy):

> "Three of four inputs are in the clear packet header. The cipher's secrecy rests entirely on epoch confidentiality. On hardware: the epoch is a quantum state. Observing it destroys it."

### 4.2 Encoding Epoch as Spin State

During a Shell=0 routing event, the epoch is encoded in a spintronic register as follows (logical description; physical implementation is substrate-dependent):

1. **Before routing:** The node's current epoch value is written into a dedicated spintronic routing register. This register is not connected to persistent storage; it exists only in the spin layer.
2. **During routing:** The Pong key derivation reads the epoch from the spin register. This read is a quantum measurement that does not necessarily collapse the state (depending on implementation), but the clock is running: T2 decoherence is proceeding from the moment the state was written.
3. **After routing (within T2):** The spin state still nominally encodes the epoch. An adversary with physical access and a spin-sensitive detector could in principle read it.
4. **After T2:** The spin state is maximally mixed. The epoch value is gone. No detection is possible.

### 4.3 Implementing Article II at the Physics Level

RPP Article II defines the requirement that routing keys constitute private internal state that is never exposed to external observers. On conventional hardware, this is implemented by software TTL enforcement: the epoch is zeroed after `SHELL_LIMINAL_TIMEOUT_NS[0]` = 25 ns by the routing runtime. This is a software guarantee.

On spintronic hardware, Article II is implemented at the physics level:

- The epoch exists as a spin state for at most T2 ≈ 25 ns.
- After T2, the state has thermalized. The epoch does not exist in any readable form.
- No software path, no privileged access, and no measurement device can extract the epoch after T2.
- The hardware automatically enforces what Article II requires: private internal state that self-destructs on the decoherence timescale.

This is not an approximation of Article II. It is Article II implemented by the laws of thermodynamics.

### 4.4 Routing Completion Window

For Shell=0 routing to be physically coherent, the **entire routing decision must complete within T2**. This establishes a hard constraint on the routing hardware:

```
routing_decision_latency < T2 ≤ 25 ns
```

At room temperature, modern spintronic logic operates at GHz speeds (spin-transfer torque oscillators reach 10–40 GHz). A routing decision that requires reading the spin epoch, computing the Pong key (a few multiplications and modular reductions), and executing the phi gate comparison is feasibly completable in under 25 ns on dedicated spintronic logic.

On conventional CMOS hardware, the routing decision latency is dominated by Python interpreter overhead (the reference implementation measures 3.4 µs per routing decision). Shell=0 is advisory on such hardware: the software enforces the TTL but cannot match the physical guarantee.

---

## 5. Shell Tier Hardware Mapping

The following table maps each RPP Shell tier to its target hardware substrate, enforcement mechanism, and relevant timescale. This table is the hardware-grounded interpretation of the Shell field defined in `spec/SPEC.md` (Section 2.2.1) and the TTL constants in `rpp/continuity.py`.

| Shell | Name | Target Substrate | Enforcement Mechanism | Key Lifetime | T2 / TTL Reference |
|---|---|---|---|---|---|
| 0 | Hot | Spintronic register (spin valve, MRAM) | Physical T2 decoherence | 1 – 25 ns | `SHELL_T2_NS[0]` = 25 ns |
| 1 | Warm | SRAM (static RAM, cache-backed) | Software TTL + cache eviction | 300 s (5 min) | `SHELL_LIMINAL_TIMEOUT_NS[1]` |
| 2 | Cold | DRAM (dynamic RAM, main memory) | Software TTL + periodic scrub | 86,400 s (1 day) | `SHELL_LIMINAL_TIMEOUT_NS[2]` |
| 3 | Frozen | NVMe SSD / persistent storage | Software TTL + explicit deletion | 2,592,000 s (30 days) | `SHELL_LIMINAL_TIMEOUT_NS[3]` |

### 5.1 Shell 0 — Spintronic (T2 Physics)

**Substrate:** Spin valve, MRAM cell, or spin-transfer torque oscillator register.

**Enforcement:** T2 decoherence is the enforcement mechanism. No software action is required to expire the key; the key expires automatically when the spin state thermalizes. Software may additionally enforce TTL for defense-in-depth, but the physical expiry is the load-bearing guarantee.

**Timescale:** `SHELL_T2_NS[0]` = 25 ns. This is the measured upper bound for conventional room-temperature spintronic devices. For devices with measured T2 shorter than 25 ns, the physical expiry is correspondingly earlier.

**Key material:** The epoch used in Pong key derivation is encoded as a spin state. After T2, the epoch is gone.

### 5.2 Shell 1 — SRAM (Software TTL)

**Substrate:** L1/L2/L3 cache or dedicated SRAM. Key material exists as a voltage state in a 6-transistor cell.

**Enforcement:** Software TTL. The routing runtime must zero or overwrite the key register after `SHELL_LIMINAL_TIMEOUT_NS[1]` = 300 s. SRAM retains state indefinitely while powered; power loss will typically erase SRAM within milliseconds, but SRAM remanence can persist for seconds at cold temperatures.

**Security note:** SRAM is vulnerable to cold-boot attacks if physical access is obtained before the TTL fires and the chip is cooled below operating temperature.

### 5.3 Shell 2 — DRAM (Software TTL + Scrub)

**Substrate:** Main memory DRAM. Key material exists as charge in capacitor cells; DRAM requires periodic refresh to retain state.

**Enforcement:** Software TTL. The routing runtime must zero the key region after `SHELL_LIMINAL_TIMEOUT_NS[2]` = 86,400 s. DRAM without refresh loses state within milliseconds at operating temperature, but with power-off cooling the charge can persist for minutes.

**Security note:** DRAM is the primary target of cold-boot attacks. Key material in DRAM should be considered accessible to a cold-boot attacker for the duration of the TTL.

### 5.4 Shell 3 — NVMe (Software TTL + Explicit Deletion)

**Substrate:** NVMe SSD or other non-volatile storage. Key material persists across power loss.

**Enforcement:** Software TTL plus explicit deletion. The routing runtime must delete (and ideally cryptographically shred) key material after `SHELL_LIMINAL_TIMEOUT_NS[3]` = 2,592,000 s. NVMe garbage collection and wear leveling mean that a simple file delete may not immediately overwrite the underlying NAND cells; secure deletion on NVMe requires NVMe SANITIZE commands or equivalent.

**Security note:** Shell=3 makes no claim of physical non-recoverability. Key material in NVMe is recoverable by forensic analysis until the NAND cells are overwritten by wear leveling or explicit sanitization.

---

## 6. Attack Surface Analysis

### 6.1 What Physical Decoherence Prevents

When Shell=0 keys are encoded in spintronic registers and T2 has elapsed, the following attack classes are physically foreclosed:

**Cold-boot attack:** A cold-boot attack cools the memory substrate to extend data remanence and reads it after power loss. DRAM remanence can persist for minutes at cold temperatures. SRAM remanence can persist for seconds. Spintronic remanence does not apply in the same way: the spin state has already decohered at T2 (25 ns) regardless of temperature, because T2 decoherence is driven by quantum fluctuations and thermal noise that cannot be suppressed by modest cooling. (Note: isotopically purified substrates at millikelvin temperatures do achieve much longer T2, but that is not the operating regime for RPP Shell=0 devices.)

**Memory forensics:** A forensic analyst with physical access to the device's memory can image DRAM or SRAM after the fact. For Shell=0, there is no classical memory to image: the epoch was encoded in a spin register, not in a voltage-state memory cell. After T2, the spin register contains no recoverable epoch information.

**Cache-timing side channel:** Cache-timing attacks infer key material by measuring memory access latency patterns. This requires the key to be in a cache-accessible memory location during or after its use. A key encoded in a spintronic register that is not memory-mapped to any cache-coherent address space is not susceptible to cache-timing attacks.

**Software privilege escalation:** A privileged process (root, kernel, hypervisor) can read arbitrary physical memory on conventional hardware. On spintronic hardware, the epoch encoded in the spin register is not readable via memory-mapped I/O after T2 because it does not exist as a readable bit pattern.

**Timing of key derivation oracle:** If an adversary can query the routing oracle (submit packets and observe routing decisions), they can potentially infer the epoch by brute force. However, the T2 window (25 ns) is far shorter than the minimum round-trip time for any network-based oracle query. Even local loopback on modern hardware has latency on the order of microseconds to milliseconds — three to six orders of magnitude longer than T2. The epoch changes before any oracle-based brute force can complete even a single query cycle.

### 6.2 What Physical Decoherence Does NOT Prevent

Physical decoherence of the Shell=0 epoch address the *post-routing* attack surface. It does not address:

**In-window attacks (within T2):** During the T2 window, the spin state encodes the epoch and in principle could be read by a sufficiently capable spin-sensitive detector (e.g., spin-resolved scanning tunneling microscopy, nitrogen-vacancy magnetometry). Such attacks require physical proximity to the chip and specialized equipment. They are not practical against a deployed device but are theoretically possible.

**Side channels during routing:** The routing computation itself (Pong key derivation, phi gate comparison) involves classical computation on conventional logic even when the epoch originates in a spintronic register. Power side channels, electromagnetic side channels, and acoustic side channels during the 25 ns routing window could in principle leak information about the epoch value. Mitigating these requires standard side-channel resistant circuit design.

**Epoch value before encoding:** The epoch value must originate somewhere before it is written into the spintronic register. If the epoch is derived from a counter or random number generator in classical SRAM, that classical copy is subject to conventional attack. The spintronic guarantee applies only to the *spin register encoding*, not to any classical pre-encoding representation.

**Attacking Shell 1–3 components of the same system:** A device running Shell=0 routing may also handle Shell 1–3 state in SRAM/DRAM/NVMe. Compromise of those tiers is outside the scope of the spintronic guarantee.

**Protocol-level attacks:** Physical decoherence does not protect against consent field manipulation, address spoofing, or Skyrmion winding number forgery. Those are handled by the RPP protocol mechanisms (ZK consent proofs, continuity chain signing, topological collapse detection).

---

## 7. Implementation Notes

### 7.1 Shell=0 on Conventional Hardware: Advisory Enforcement

On conventional (non-spintronic) hardware, Shell=0 is advisory. Implementations MUST:

1. **Enforce the 25 ns TTL as tightly as the runtime permits.** In practice, this means the epoch used for Shell=0 routing decisions should be treated as ephemeral: never written to persistent storage, never logged, and overwritten as soon as the routing decision is complete.
2. **Not claim physical enforcement.** Documentation, comments, and API contracts for Shell=0 on conventional hardware must not assert that the key is physically irrecoverable. The correct claim is: "Shell=0 TTL is enforced by software; physical irrecoverability requires spintronic hardware."
3. **Implement defense-in-depth.** Even without physical enforcement, multiple layers of software protection (zeroing epoch registers, process isolation, memory guard pages, ASLR) reduce the practical attack surface.

The constant `SHELL_LIMINAL_TIMEOUT_NS[0]` = 25 in `rpp/continuity.py` is correct as a target regardless of hardware. On conventional hardware, it expresses intent and drives TTL enforcement logic. On spintronic hardware, it corresponds to the physical T2 deadline.

### 7.2 Shell=0 on Spintronic Hardware: Physical Invariant

On spintronic hardware, Shell=0 is a physical invariant. Implementations on spintronic platforms:

1. **MUST encode the epoch in the spintronic register** at the start of each Shell=0 routing decision and MUST NOT maintain a classical copy of the epoch value during or after the routing window.
2. **MUST complete the routing decision within T2** (the measured T2 of the specific device, which must be ≤ 25 ns). If the routing logic cannot complete within T2, it is not a valid Shell=0 implementation.
3. **MAY read the T2 value from device characterization** rather than assuming the worst-case 25 ns. A device with measured T2 = 8 ns provides strictly stronger enforcement; the timeout constant should reflect the actual device.
4. **SHOULD log T2 measurements** as part of device attestation to allow external verification that the physical invariant holds.

### 7.3 Relationship to the Ford Protocol

The Ford Protocol (spec/CONTINUITY.md, implemented in `rpp/continuity.py`) uses `SHELL_LIMINAL_TIMEOUT_NS` as the deadline for the TRANSIT phase. For Shell=0 crossings, this means:

- The entire crossing (SCOUT through RELEASE, five phases) must complete within 25 ns on spintronic hardware.
- This is a strong architectural constraint: Shell=0 crossings are only feasible between spintronic substrates in close physical proximity (same chip, same package). Cross-board or cross-rack Shell=0 crossings are not feasible given signal propagation delays.
- If a Shell=0 crossing cannot complete within T2, the recovery escalation ladder (spec/CONTINUITY.md Section 7) applies. ABORT is the terminal recovery level; the state is treated as lost.

On conventional hardware, the 25 ns window cannot be guaranteed by software alone. Shell=0 Ford Protocol crossings on conventional hardware are advisory: they express the intent to complete quickly but cannot provide the physical deadline guarantee.

### 7.4 Minimum T2 Requirement in ConsciousnessStatePacket

The `ConsciousnessStatePacket` dataclass (`rpp/continuity.py`, line 181) includes a `min_t2_ns` field:

```python
min_t2_ns: int
# Minimum T2 coherence time destination must provide (nanoseconds).
```

For Shell=0 packets, `min_t2_ns` is set by `csp_from_rpp()` to `SHELL_T2_NS[0]` = 25. A destination substrate that cannot provide T2 ≥ 25 ns MUST refuse the crossing in the SCOUT phase. This prevents a spintronic origin from crossing to a conventional destination and silently downgrading to software enforcement.

---

## 8. Future Work

### 8.1 Organic Spin Valves

Organic semiconductors (small molecules and conjugated polymers) have demonstrated T2 times in the 10–100 ns range at room temperature, significantly longer than conventional inorganic spintronic devices. The mechanism is suppressed spin-orbit coupling (lighter atomic elements) and weaker hyperfine interactions compared to III-V semiconductors.

For RPP Shell=0, organic spin valves are attractive because:

- Longer T2 (up to 100 ns) provides a larger routing window, making Shell=0 Ford Protocol crossings feasible over slightly longer physical distances.
- The SHELL_T2_NS[0] constant and SHELL_LIMINAL_TIMEOUT_NS[0] constants could be updated to reflect the longer window while maintaining physical enforcement.
- Organic devices are compatible with flexible substrates and low-temperature processing, potentially enabling spintronic capabilities in form factors not possible with conventional semiconductor fabrication.

A future version of this document should specify how the T2 constant should be adjusted for organic spintronic hardware and what attestation mechanisms are required to verify the T2 claim.

### 8.2 Graphene Spintronics

Graphene is a single-layer carbon lattice with zero nuclear spin (for isotopically pure C-12 graphene) and weak spin-orbit coupling. Theoretical T2 times in graphene are in the microsecond range at room temperature, though practical devices are limited by substrate-induced dephasing to 1–10 ns at present.

Graphene spintronics is relevant to RPP because:

- Gate-tunable spin lifetime allows dynamic adjustment of T2, which could enable adaptive Shell=0 TTL based on consent state or routing priority (e.g., ACTIVE harmonic mode as defined in `rpp/continuity.py` HarmonicMode could trigger shorter T2, increasing routing throughput at some security cost).
- The combination of high electron mobility and spin transport in graphene could enable integrated routing and computation at the spintronic level, with the epoch state never entering a classical register.

### 8.3 T2 Measurement Under Routing Conditions

The T2 values cited in Section 2.2 are from materials characterization experiments (spin echo, Hahn echo, CPMG sequences) under controlled conditions. The T2 under actual routing conditions — with active current flow through the spin valve, thermal gradients from adjacent CMOS logic, and magnetic field noise from interconnects — may differ from the quiescent T2.

Future work should:

1. **Characterize T2 under active routing load** for candidate Shell=0 devices, not just under quiescent conditions. This requires purpose-built test harnesses that simulate the routing electromagnetic environment.
2. **Define a T2 attestation protocol** that can be run in-situ during device operation to continuously verify that the physical enforcement guarantee holds.
3. **Establish derating factors** between quiescent T2 and operational T2, analogous to the derating factors used in capacitor and inductor specifications. If the operational T2 is 40% of the quiescent T2, a device with quiescent T2 = 40 ns would be rated at operational T2 = 16 ns — still within the Shell=0 budget.
4. **Specify failure modes** for T2 degradation over device lifetime (radiation damage, electromigration, interface oxidation) and define the protocol behavior when a device's T2 drops below the Shell=0 minimum. The correct response is to reclassify the device as Shell=1 (software TTL) rather than to continue claiming physical enforcement.

### 8.4 Multi-Qubit Shell=0 Registers

This document has described Shell=0 encoding as a single spin (one epoch value in one spintronic register). Future architectures may encode multiple fields simultaneously in entangled multi-spin states, exploiting quantum correlations to increase the information density of the Shell=0 register while maintaining the T2 expiry guarantee.

The security analysis for multi-qubit registers is more complex: entangled states can sometimes be partially characterized by measuring a subset of the spins, which could in principle leak partial epoch information before full decoherence. Future work should analyze the security of multi-qubit Shell=0 encodings under partial-measurement attacks.

---

## Summary Table

| Property | Shell=0 (Spintronic) | Shell=1 (SRAM) | Shell=2 (DRAM) | Shell=3 (NVMe) |
|---|---|---|---|---|
| Enforcement mechanism | Physical (T2 decoherence) | Software TTL | Software TTL + scrub | Software TTL + deletion |
| Key lifetime | 1–25 ns (physical) | 300 s (software) | 86,400 s (software) | 2,592,000 s (software) |
| Cold-boot resistant | Yes (after T2) | No | No | No |
| Memory forensics resistant | Yes (after T2) | No | No | No |
| Cache-timing resistant | Yes (spin register) | Partial | No | No |
| Explicit deletion required | No | Yes | Yes | Yes |
| Physical invariant | Yes (on spintronic hw) | No | No | No |
| Advisory on conventional hw | Yes | Yes | Yes | Yes |

---

*This document establishes the physical grounding for RPP Shell tier hardware claims. Claims about spintronic physical enforcement are grounded in published experimental T2 measurements and are subject to revision as measurement techniques and device engineering advance.*

*Released under CC BY 4.0.*
