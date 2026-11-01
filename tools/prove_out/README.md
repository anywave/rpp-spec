# CX-003 coherence and sector prove-out

CX-005 extension at master `95c67ef`: see [CX005_CONDITIONS.md](CX005_CONDITIONS.md)
for the complete proved-condition checklist and unchanged partly-proved verdicts,
[CX005_VALIDATION.md](CX005_VALIDATION.md) for new actual RTL/native-Rust counts,
[FOREIGN_BINDINGS.md](FOREIGN_BINDINGS.md) for foreign-domain limits, and
[CX005_PROPOSALS.md](CX005_PROPOSALS.md) for exact unapplied adoption patches.
The commands/counts below are the historical CX-003 record; use the CX-005
validation commands for the current checkout.

The source under study is the immutable rpp-spec master snapshot
`0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e`. This extension does not change core,
constants, formats, consent headers, original tests or specification text. Nothing
in it restores a website readout or adopts a proposed quantity into the protocol.

Verdicts: **coherence partly proved**, **sector partly proved**. There are useful,
reproducible finite-domain computations and actual protocol consumers. There is
no validated, profile-independent meaning for a lone “Coherence0.847” or “Sector4”.
Keep the generic page readouts absent. See [COHERENCE_TRACE.md](COHERENCE_TRACE.md),
[SECTOR_TRACE.md](SECTOR_TRACE.md) and [HARDWARE_RA.md](HARDWARE_RA.md).

Run from this existing checkout, explicitly selecting its source rather than a
shared editable install:

```bash
cd /workspace/cx004-prove-out
export PYTHONPATH=/workspace/cx004-prove-out
/workspace/venvs/rpp-spec/bin/python -c "from pathlib import Path; import rpp; assert Path(rpp.__file__).resolve().is_relative_to(Path('/workspace/cx004-prove-out')); print(rpp.__file__)"
/workspace/venvs/rpp-spec/bin/python -m tools.prove_out.experiments
/workspace/venvs/rpp-spec/bin/python -m pytest tools/prove_out/tests/ -q -o addopts=
/workspace/venvs/rpp-spec/bin/python -m tools.prove_out.mutation_check
/workspace/venvs/rpp-spec/bin/python -m pytest tests/ -q
/workspace/venvs/rpp-spec/bin/python tests/test_golden_vectors_mobius32.py
```

Observed: **150 synthetic one-input scalar/decision/simulation rows**, **512 sector
rows**, **28 new tests**, **7 killed /0 survived selected in-memory mutants**,
**1256 original tests**, **5/5 standalone golden checks**. Existing deprecation
notices remain visible. All text artifacts use UTF-8 and LF. Experiments use no
wall-clock input, random source, key generation, model/inference call or network.
The isolated SpinSite experiment advances *simulated* nanoseconds, and does not
invoke its VCD writer (which otherwise stamps a wall-clock date).

The finite checks exercise10,201(E,C) pairs, all675 integer raw scores,46,656
ordinary-address similarity pairs, all512 legacy theta classes,18,432 encoded
legacy combinations and all27 ordinary Repitans. These finite checks are not
experimental evidence of human/digital energetic coupling or real hardware.
The total/disjoint legacy partition argument factors the full2^28 address space
through its9-bit theta field; it is not a claim to enumerate268 million addresses.

## Reproducible artifacts

- `results/coherence-sweeps.csv`, `results/SWEEPS.md`: one variable at a time, with
  held inputs, output units and decisions. The score families are not conflated.
- `results/sector-map.csv`: every legacy theta plus the documented informational
  v2 theta projection. Names agree36/512 and differ476/512; the projection is
  explicitly lossy. No radius projection choice is made.
- `results/hdl-comparison.csv`, `results/hdl-summary.json`: actual Icarus output
  against Python on256 shared header-code pairs. See below for failed equality.
- `results/existing-ra-simulation.log`: the existing RA testbench's30 passes and
  2 failures. Its process exit0 does not erase those failures.
- `results/SOURCE_USES.md`: the complete source grep inventory, complementing
  the end-to-end definition/consumer maps.
- `proposed.py`: operational, count-defined progress and strictly validated v2
  address-affinity proposals with tests. They are separate from shipped code;
  policy weights are not presented as physical constants or calibrated confidence.

Repeat the CSV generation twice with `--output-dir /tmp/cx004-prove-repeat-one`
and `--output-dir /tmp/cx004-prove-repeat-two`; both `cmp` commands returned0.
Both scalar CSV SHA-256 values were
`4883b26632bf3c8b5258442e7bf15514a7ed3135e2739ea931b41dd5fbb37222`.
Both sector CSV values were
`42ed1f793de3ed1d0b34639425c90d841449812106abc9607913bcef86114895`.

## Actual HDL reproduction

Icarus12.0 was extracted locally from a checksum-verified package with signed
Debian metadata; no system install occurred. Full verification and original
compile-command correction are documented in HARDWARE_RA.md. With a normal
installed Icarus, omit the task-local `-B`/`-M` prefixes below:

```bash
mkdir -p /tmp/cx004-hdl-replay
/tmp/cx004-iverilog/usr/bin/iverilog -B /tmp/cx004-iverilog/usr/lib/x86_64-linux-gnu/ivl -g2012 -s CompareCoherence -o /tmp/cx004-hdl-replay/compare.vvp tools/prove_out/compare_coherence_tb.v hardware/verilog/coherence_evaluator_ra.v hardware/verilog/spiral_ra_coherence.v
/tmp/cx004-iverilog/usr/bin/vvp -M /tmp/cx004-iverilog/usr/lib/x86_64-linux-gnu/ivl /tmp/cx004-hdl-replay/compare.vvp > /tmp/cx004-hdl-replay/compare.log
/workspace/venvs/rpp-spec/bin/python -m tools.prove_out.analyze_hdl --repo . --log /tmp/cx004-hdl-replay/compare.log --output-dir /tmp/cx004-hdl-replay/analyzed
cmp /tmp/cx004-hdl-replay/analyzed/comparison.csv tools/prove_out/results/hdl-comparison.csv
cmp /tmp/cx004-hdl-replay/analyzed/summary.json tools/prove_out/results/hdl-summary.json
```

Python versus the registered exact scorer: **0/256 score mismatches**. Versus the
other two shipped scorers: **255/256 and245/256 mismatches**, with **63/224 and32/224
completion-axis decreases**. Configured-threshold137 binding decisions differ
0/256,61/256 and35/256 respectively. The registered module's completion flag differs
from Python at31/256 points because it tests the input completion field rather
than the derived score. These are actual simulated behaviors, not static estimates.
No HDL source was fixed. Icarus is a functional simulator, not a physical device.

The existing RA testbench executes32 checks after a supported source-list correction;
**30 pass,2 fail** (“Mid coherence should be medium” and “Phi extraction”).
No Rust, GHC/Clash native run, physical device test or biological study is claimed.
ra-system was inspected read-only at `e685d3abacca3105a7c377e9db80df33ce7c2985`;
its Rust/Clash definitions use different inputs/formulas and are not asserted equal.

## Every test can detect a concrete change

Tests characterize the frozen shipped behavior or the explicitly labelled proposal.
Some deliberately pin counterexamples; a future intentional fix needs a new card
and updated expectations. All mutations below are local hypothetical changes;
`mutation_check` executes seven selected witnesses in test memory only.

| Test (test_properties.py) | A change that makes its assertion fail |
|---|---|
|test_weighted_score_formula_and_monotonicity|Change165 to166 or replace scorer with0 (executed mutant score_max).|
|test_binding_and_stage_all_raw_scores|Move cutoff137 to138, or always admit (binding_threshold mutant).|
|test_nonfinite_input_is_not_rejected_by_shipped_score|Reject NaN rather than the snapshot's current clamp behavior.|
|test_valid_address_similarity_is_symmetric_bounded_and_identity|Change a weight/sign, or make distance directional.|
|test_reserved_constructor_states_break_unqualified_similarity_claim|Clamp the snapshot's reserved-state similarity to1 or reject sentinels.|
|test_complement_consistency_declines_with_one_input_drift|Return constant consistency1 (complement mutant).|
|test_consent_threshold_is_caller_input_not_binding_threshold|Move the ethereal cutoff.4 to.5 or137/674.|
|test_fallback_requires_thirteen_not_twelve_below_threshold_updates|Change counter>12 to counter>=12.|
|test_v1_partition_is_total_disjoint_and_matches_consent_for_all_theta|Change boundary64 or return GENE for all inputs (legacy_boundary mutant).|
|test_v1_sector_is_independent_of_other_fields|Include shell/phi/harmonic in the sector index.|
|test_v2_ordinary_sector_ranges_are_total_and_disjoint|Move MEMORY upper boundary10 to9.|
|test_cross_layer_projection_is_lossy_not_name_stable|Change the informational27/512 theta projection.|
|test_authorization_uses_runtime_matrix_not_universal_label|Grant BRIDGE in emergency or remove VOID's zero-only exception.|
|test_proposed_progress_has_explicit_counts_and_exact_endpoints|Return0 for full completion (proposal_progress mutant).|
|test_proposed_progress_rejects_undefined_inputs|Remove the corresponding bool/empty/negative/overflow-count guard.|
|test_proposed_affinity_reaches_both_endpoints|Return1 for every pair (proposal_theta mutant).|
|test_proposed_affinity_refuses_reserved_and_nonfinite_states|Remove the corresponding sentinel/range/finite/bool guard.|
|test_sweep_bytes_are_repeatable_and_have_one_changed_input|Add a random/time-dependent output or drop a row.|
|test_isolated_spin_site_implements_its_exponential_simulation|Remove relaxation (spin_decay mutant).|

## Conservative choices and limits

Use explicit profile tags and actual runtime admission checks, not “universal”
helper labels. Do not equate aliases across v1/v2, supply raw0..674 into a0..1
consent field, or infer content meaning from integer labels. Reserved states
are excluded from proposed affinity instead of silently saturating them.
All physical/biological meanings require external evidence not supplied here.
CX-001's four steward items, radius alternatives, lifecycle issue and243 open
baselines remain unresolved; no entry is marked accepted. No source change is
needed to report these limits, and core adoption remains a stop-and-ask.
