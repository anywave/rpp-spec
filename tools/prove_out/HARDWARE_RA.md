# CX-004 Part C: hardware and ra-system source trace / executed HDL evidence

RPP source revision: `0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e` in `/workspace/cx004-prove-out`.
Latest authoritative inbox read before acting: `d9214588220854667692ad5614d355763360133d`,
`codex/inbox/rpp-spec.md`, including CX-003 and CX-004. No RPP or ra-system source was edited.
The experiments call no LLM or embedding model and use fixed inputs; the numerical
simulation models are identified below. No secret, transaction or remote write beyond
the authorized branch push is used.

## Executed hardware findings

Native hardware tools were initially absent: `shutil.which` returned None for iverilog, vvp,
Clash, GHC, rustc and cargo. A local Icarus extraction was then obtained with the parent's
explicit authorization, without a system install:

1. Private apt state/configuration under `/tmp/cx004-apt`, using the existing Debian archive
   keyring `/usr/share/keyrings/debian-archive-keyring.gpg` and official signed Debian trixie
   `https://deb.debian.org/debian` metadata. Default signature, checksum and TLS checks retained.
2. `APT_CONFIG=/tmp/cx004-apt/apt.conf /usr/bin/apt-get update` fetched authenticated InRelease
   and Packages metadata (9,819 kB); no insecure/trusted=yes flags and no system apt state writes.
3. `APT_CONFIG=/tmp/cx004-apt/apt.conf /usr/bin/apt-get download iverilog` downloaded version
   `12.0-2+b1` (2,046,080 bytes). Signed Packages metadata SHA-256:
   `febe027d2d3f5a7e570844d55758339ab5490acc09f404f214a8719d89d07056`.
4. `sha256sum -c` against that digest returned `OK` for the downloaded package.
5. `dpkg-deb -x /tmp/cx004-apt/iverilog_12.0-2+b1_amd64.deb /tmp/cx004-iverilog`.
   `/tmp/cx004-iverilog/usr/bin/iverilog -B /tmp/cx004-iverilog/usr/lib/x86_64-linux-gnu/ivl -V`
   reports Icarus Verilog 12.0 (stable). No system install or source change was made.

Compiler: `/tmp/cx004-iverilog/usr/bin/iverilog`.
Compiler data prefix: `-B /tmp/cx004-iverilog/usr/lib/x86_64-linux-gnu/ivl`.
Runtime: `/tmp/cx004-iverilog/usr/bin/vvp`.
Runtime module prefix: `-M /tmp/cx004-iverilog/usr/lib/x86_64-linux-gnu/ivl`.

### Existing comprehensive testbench

The command documented in `hardware/verilog/spiral_testbench_ra.v:13` lists both
`spiral_consent.v` and `spiral_consolidated.v`. It fails compilation (exit 6) with duplicate
`ConsentHeaderParser`, `PMARecordParser` and `CRC8_Byte` declarations. This is a source-list
problem, not evidence that any hardware test passed.

The unchanged testbench's parser ports (lines 186–211) match `spiral_consent.v`, so the supported
compile correction is to omit the redundant consolidated file, without changing source:

```bash
/tmp/cx004-iverilog/usr/bin/iverilog -B /tmp/cx004-iverilog/usr/lib/x86_64-linux-gnu/ivl \
  -g2012 -s spiral_testbench_ra -o /tmp/cx004-hw-output/existing_ra.vvp \
  hardware/verilog/spiral_testbench_ra.v hardware/verilog/spiral_ra_coherence.v \
  hardware/verilog/spiral_consent.v
cd /tmp/cx004-hw-output
/tmp/cx004-iverilog/usr/bin/vvp -M /tmp/cx004-iverilog/usr/lib/x86_64-linux-gnu/ivl existing_ra.vvp
```

Observed: compile exit 0; **32 checks executed, 30 passed, 2 failed**. Importantly, vvp exited 0
because the testbench only prints its failure count and calls `$finish` (lines 607–625).
The two failed checks were `Mid coherence should be medium` and `Phi extraction`.
The run printed max approximate coherence **632**, while the testbench expected approximately 670.
The mid vector is entropy=15, complecount=3 (lines 318–320); even the Python reference is 297,
which is below the HDL's medium threshold of 300. Thus that expectation is itself not a sound
cross-binding equality check. The phi check expects 3 at line 515; leave it as a reported
existing failure, not a core/header fix. Logs and VCD were generated only under `/tmp/cx004-hw-output`.

### Exhaustive actual Python vs three RTL bindings

A generated, deterministic comparison testbench drives every `entropy=0..31` and
`complecount=0..7` pair. It instantiates the three shipped modules unchanged, clocks the registered
one and waits for its result; threshold is explicitly configured to 137 for the comparison.
The Python comparison uses the actual `rpp.coherence.compute_coherence(entropy/31, complecount/7)`.
Mapping header entropy to Python engagement here is an explicit test wiring choice, not a claim
that the inputs measure the same real-world quantity.

```bash
/tmp/cx004-iverilog/usr/bin/iverilog -B /tmp/cx004-iverilog/usr/lib/x86_64-linux-gnu/ivl \
  -g2012 -s CompareCoherence -o /tmp/cx004-hw-output/compare_coherence.vvp \
  /tmp/cx004-hw-output/compare_coherence_tb.v \
  /workspace/cx004-prove-out/hardware/verilog/coherence_evaluator_ra.v \
  /workspace/cx004-prove-out/hardware/verilog/spiral_ra_coherence.v
/tmp/cx004-iverilog/usr/bin/vvp -M /tmp/cx004-iverilog/usr/lib/x86_64-linux-gnu/ivl \
  /tmp/cx004-hw-output/compare_coherence.vvp > /tmp/cx004-hw-output/compare.log
/workspace/venvs/rpp-spec/bin/python /tmp/cx004-hw-output/analyze_comparison.py \
  --repo /workspace/cx004-prove-out --log /tmp/cx004-hw-output/compare.log \
  --output-dir /tmp/cx004-hw-output/reproduced
```

Both compile/run commands exited 0. Exactly **256 distinct input points** were parsed, and the
analyzer rejects missing/duplicate grid points. Results:

| Binding | Score mismatches versus Python / 256 | Binding decision mismatches at configured 137 / 256 | Score decreases when only complecount increases / 224 adjacent pairs |
|---|---:|---:|---:|
| Python reference | — | — | 0 |
| `CoherenceEvaluatorRa` (coherence_evaluator_ra.v) | 0 | 0 | 0 |
| `CoherenceEvaluator_Ra` (spiral_ra_coherence.v main) | 255 | 61 | 63 |
| `CoherenceEvaluator_Ra_Precise` (same file LUT) | 245 | 35 | 32 |

Registered-module completion flag versus Python completion flag differs at **31/256 points**:
the RTL tests input complecount==7, whereas Python requires derived weighted-score complecount==7,
which only occurs at raw score 674. This is a definition difference, not clock settling error.

| Entropy | Complecount | Python | Registered exact RTL | Approximate RTL | LUT “Precise” RTL |
|---:|---:|---:|---:|---:|---:|
| 31 | 7 | 674 | 674 | 632 | 249 |
| 0 | 3 | 218 | 218 | 872 | 216 |
| 0 | 4 | 290 | 290 | 138 | 288 |
| 0 | 5 | 363 | 363 | 429 | 360 |
| 0 | 6 | 436 | 436 | 720 | 16 |
| 0 | 7 | 509 | 509 | 1011 | 88 |
| 15 | 3 | 297 | 297 | 160 | 294 |

Artifacts to copy into the permitted tools/prove_out tree if desired:
`compare_coherence_tb.v`, `analyze_comparison.py`, `compare.log`, `reproduced/comparison.csv`,
`reproduced/summary.json`, `existing_ra.log`, all under `/tmp/cx004-hw-output`.
The comparison is exhaustive for the 32×8 discrete header grid, **not** all float inputs, clock
histories, HDL toolchains or physical hardware. No Clash or Rust executable run is claimed.

## End-to-end hardware definition map

| Source | Inputs / computation / units | Decision depending on it |
|---|---|---|
| coherence_evaluator_ra.v:34–47,51–81 | 5-bit entropy e, 3-bit complecount c; floor(165e/31)+floor(509c/7), range 0–674, dimensionless weighted counts (source calls ×100) | Registered score/valid output on enabled clock (84–96); valid iff score≥configurable threshold; completion iff c==7 |
| coherence_evaluator_ra.v:108–147 | Consecutive enabled above-threshold samples, saturating 4-bit counter | Scalar trigger uses old counter≥duration, so duration N triggers on the N+1-th enabled high sample from zero |
| coherence_evaluator_ra.v:159–201 | Same persistence logic, fixed KHAT duration 12=316 mod16 | KHAT scalar trigger; 13 high enabled samples from reset due nonblocking comparison |
| coherence_evaluator_ra.v:229–332 | Header score, configurable thresholds, consent, emergency freeze | Routing allowed only valid coherence + full consent + no ETF; decisions ETF/block > fallback on invalid coherence > delay > route |
| coherence_evaluator_ra.v:343–367 | 4-bit somatic score; thresholds full10, diminished6, verbal override | 3 named consent classes, omitting Python's distinct ATTENTIVE threshold7; do not assume full Python state-machine equivalence |
| coherence_evaluator_ra.v:378–405 | ETF duration9=137 mod16; release threshold559 labeled 674×137/165 | Freeze release after duration expires AND score≥559 |
| spiral_ra_coherence.v:129–148 | Active main datapath uses 1618e and5089c, 24-bit products×211/936, extracts bits[23:14], sums in10bits | Score/valid/classification; width truncation and reciprocal-shift mismatch cause nonmonotonicity, unlike the Python score |
| spiral_ra_coherence.v:150–161 | Normalization `(final_score*38)[15:8]`; high≥500, medium300..499, low<300 | Public 8-bit score and high/medium/low flags; scaling is not the Python score/674 normalization |
| spiral_ra_coherence.v:171–229 | Rounded e/31,c/7 LUTs×1000; 1618/5089 weights; 21-/22-bit multiplication; sum×13 then bits[26:17] | “Precise” score and configurable valid threshold; 22-bit Ankh term cannot hold 5,089,000 and overflows |
| spiral_ra_coherence.v:371–417 | Full consent or diminished+coherence permits route; PMA/fallback gates | Different admission logic than SpiralCoherenceIntegration; not evidence of an interchangeable implementation |

The main datapath's unused preliminary nets (76–116) do not drive final_score; the observed main
counterexamples above come from the active 129–148 path. Its Ankh product overflows 24 bits by
complecount=4; reciprocal comments describe /65536 but extraction shifts14. The LUT Ankh term's
maximum needs23 bits but is declared22 (line216), causing the C5→C6 drop. These are engineering
counterexamples. No published constant or core file was changed to repair them.

## spintronic_sim.py is a different simulated quantity

| Source | Definition / range / units | Use |
|---|---|---|
| spintronic_sim.py:56–81 | Hard-coded PHI, ANKH, alpha labels; 10ns simulation tick; chosen T1/T2 ns tables and RAC multipliers | Assumptions driving the software model, not measured device characterization |
| :159–191 | SpinSite has mx,my,mz; coherence=sqrt(mx²+my²), dimensionless with assumed M0=1 | Simulated transverse-vector magnitude; unrelated to the 165/509 weighted score |
| :208–246 | Excitation angle=amplitude*pi/2; xy rotation then exp(-dt/T2) damping; mz exponential approach to1 | Reproducible deterministic state update; isolated-site coherence decays monotonically for positive dt/T2 |
| :248–250 | Coherence<0.05 | Deactivates model site |
| :289–306 | Mean site coherence per sector/RAC/shell and whole lattice | Diagnostic averages, no supplied sensor observations |
| :344–403 | Shell=round(radius*3), frequency=OMEGA_FREQ*ANKH*.01; BFS; excite sites; torque increments | Final destination mean compared to hand-chosen sector thresholds0.30..0.80 (:100–109) for allow/deny |
| :383–390 | Neighbor torque adds source-average-my*.05 to both dst.mx and dst.my | No clipping enforces a universal coherence≤1 bound after arbitrary state/torque input |
| :619–625 | VCD destination trace reconstructed from an approximate ramp/decay formula | That displayed VCD curve is not a dump of the actual recorded SpinSite trajectory |

A “Coherence 0.847” from this model is not a calibrated confidence/probability, and it is not
mathematically the same quantity as score/674. The source labels its simulated Bloch parameters in
ns and mentions biological/physical ideas; this task adds no physical claim. Showing equations in
Python, choosing material-like timing constants or emitting VCD is not evidence of a fabricated
spintronic device, measured T2 expiry, biological binding or information destruction.
A real-hardware study would need a specified device/material, calibrated state preparation/readout,
measured T1/T2 under declared temperatures/noise/load, clocked routing/consent tests, measured error
rates and repeatability. No such experimental dataset was identified in these source files. The
existing CX-001 Shell-0 TTL and T2 steward items remain unresolved, not decided by this analysis.

## ra-system checked read-only

`git clone --depth 1 --single-branch https://github.com/anywave/ra-system.git /tmp/cx004-ra-system`
completed using existing platform Git authentication. Observed revision:
`e685d3abacca3105a7c377e9db80df33ce7c2985`. This is the currently reachable ra-system tree, not a
claim that the older RPP checkout pins that version. No ra-system file was modified.

| ra-system source | Definition and engineering use |
|---|---|
| rust/src/lib.rs:8–12,16–26,29–50 | Describes27 Repitans,6 RACs,5 Omega formats; reexports coordinate/gating types. Example calls access_level(.8,RAC6); no E/C-to-coherence measurement function here |
| rust/src/gates.rs:29–33,73–89 | Caller supplies normalized coherence; floor=1.62/Ankh≈.3183, ceiling1; full iff C≥RAC(level)/RAC1; partial alpha=(C-floor)/(threshold-floor) clamped0..1; else blocked |
| rust/src/gates.rs:92–100 | can_access is true for both full and partial; effective_coherence maps result to alpha. This scalar is access interpolation, not the RPP weighted score |
| rust/src/gates.rs:111–149 | Separate weighted resonance score .3*theta_match+.4*phi_access+.2*harmonic_match+.1*intensity; arbitrary caller-supplied components; defaults sum1 |
| rust/src/rac.rs:76–103 | RAC values [.6361725,.628318519,.57255525,.523598765,.4580442,.3998594565], normalized by first for thresholds |
| spec/ra_integration_spec.md:180–219 | States same normalized caller-coherence gating algorithm; RAC thresholds approximately1,.9874,.9,.823,.72,.6285. Input coherence meaning is assumed, not measured/derived |
| rust/src/constants.rs:3–7,34–56 | Explicitly says Bateman's own units/ratios, not physics claims. Current Green Phi1.629174025, Omega Major Phi1.62, Ankh5.08938. Do not silently replace RPP's older symbolic165 coefficient |
| haskell/clash/RaGroupCoherence.hs:67–75,88–93 | Avatar coherence/depth are caller-supplied8-bit inputs; cluster coherence is their average, not an E/C score |
| RaGroupCoherence.hs:200–218,346–405 | Avatar weight=(coherence*depth)>>8; sum non-inverted active weights divided by active count; saturating +38 if dominant cluster≥3, field strength adds77; stable iff no inversion and groupCoh>179 |
| RaGroupCoherence.hs:313–340 | “Emergence window” code chooses highest-coherence avatar's window; despite intersection comment, it does not compute intersection of all windows. Valid means≥3 active |
| RaGroupCoherence.hs:411–467,483–512 | Coherence delta±10 and threshold179 choose UI/breath/audio feedback, plus model safety flags; no sensor-driven evidence of biological entrainment |
| RaGroupCoherence.hs:573–579 | Source testBench stops based on not-safetyAlert; it is not an exhaustive cross-binding numerical equality test |

No rustc/cargo/GHC/Clash was available, so their native tests/synthesis were not executed.
Rust gates and Clash group fields consume fundamentally different inputs/functions from RPP's
weighted formula. Numerical equivalence across all bindings is therefore neither expected nor
established by their shared word “coherence”. Where actual HDL execution is available, the two
alternate RTL implementations explicitly fail equality and monotonicity as recorded above.

## Proposed report interpretation (no core adoption)

Coherence verdict: at most **partly proved** internally; **not yet meaningful as a single end-user
measurement across these implementations**. One Python/registered-RTL score is internally consistent
on its discrete test grid and controls admission thresholds, while other shipped HDL bindings differ
and physical/biological meanings are not established. A safe engineer sentence is “a configured
weighted readiness score used by this routing policy”; a user-facing unexplained0.847 readout should
stay absent. Any new normalized readiness definition belongs only to tools/prove_out until steward
adoption; no existing constants, TTL or radius decisions are resolved here.
