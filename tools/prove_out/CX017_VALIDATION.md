# CX-017 technical validation

The frozen criteria and named domains govern these finite experiments.

## Results by binding

| Named quantity/binding | Result within the declared experiment |
|---|---|
| Python ra-policy-674 | PROVED on 10,201 fraction points: formula, [0,674] range and both monotone drivers; coefficient is score/674 |
| Current registered, combinational and compatibility Ra RTL | PROVED: each matches Python on 3,072 code/threshold points, with zero score or decision disagreements and no axis decreases |
| Registered completion / normalized byte | Distinct expressions confirmed: input C==7 differs from Python's derived completion in 31/256 cases; normalization is (score*38)>>8, not score/674 |
| Python canonical-v2 coordinate affinity | PROVED on 107,520 distance classes: declared formula, ordinary bounds, symmetry and 382,556 adjacent driver comparisons; 8,192 reserved probes are irrelevant |
| Consolidated / canonical affinity RTL | Each matches its own arithmetic exactly on 107,520 points and 5,832 wrap/reverse probes; thresholds do not change scores. Exact Python==byte/255 fails in 107,253 / 107,236 cases |
| Python semantic-v1 / canonical-v2 sector | PROVED for all 512 / 27 theta inputs; 395,264 / 228,393 other-field probes preserve labels |
| Both RTL theta helpers / same-sector paths | PROVED for 27 ordinary codes, 729 pairs and 534 irrelevant-field probes each; five sentinel codes differ from Python in each helper |
| Canonical decoder | PROVED ordinary label/component/validity comparison: 216 ordinary words; all 40 sentinel labels differ from Python, with no component/validity differences |
| Adjacency graphs | Canonical matches Python on all 64 pairs. Consolidated differs on four directed edges: WITNESS/DREAM and GUARDIAN/SHADOW, in both directions |
| Legacy stub / Python legacy evaluator | Exact agreement on 2,048 inputs; finite-width wrapping produces 30 entropy-axis decreases. This is not the monotone 674-point policy |
| Python canonical / floating Ra evaluators | Canonical matches the 674-point policy on 256 inputs. Floating Ra matches its own formula, maximum 6.707013569425705; x100 differs from the 674-point score on 194/256 inputs |
| Other simulation profiles | 150 deterministic reference rows replayed; HRDA, complement geometry, consent inputs and SpinSite remain separate model quantities |

The affinity diagnostic maxima abs(Python-byte/255) are 0.017843137254901942 (consolidated) and 0.018169934640522967
(canonical). The ordinary Python minimum is mathematically 1/90, observed binary64 0.011111111111111183; both RTL minima
are zero. Constructor-accepted theta31 can produce affinity 1.0666666666666667, and null self-affinity is 0.7; these are
explicitly outside the ordinary-coordinate claim. The fixed radius grid and endpoint reversals do not enumerate every
pair of binary64 radii.

## D1 and the smallest changes, proposed only

D1 already requires a caller-named neutral-radius or shell-projection policy. Tools-only Python projections test all 512
theta and phi inputs and eight shell policy cases. The actual Rust migration test executes separately on Rust 1.85.1.
Its existing fixtures test named alternatives and lossy mapping; this is not a claim that Rust independently executed
the Python sweep. The simulation helper still hardcodes shell/3 and is not an explicit-policy migration API.

A desired common affinity output needs a named representation and rounding contract before changing either binding:
**MODEL CHANGE**, not an adopted byte/255 tolerance. A desired common adjacency graph needs the four extra consolidated
directed edges removed, or a separately named graph profile: **MODEL CHANGE**. Sentinel unification likewise requires an
explicit profile rule. No proposed change is applied. D5 retains named quantities as experiments.

## Reproduction and limits

Run python -m tools.prove_out.verdict with --iverilog, --vvp, optional --ivl-dir, optional --cargo, and separate
external --work-dir / --output-dir paths. Configure RUSTC/PATH and any loader path externally; the tool checks cargo and
rustc are 1.85.1, then invokes offline locked Cargo. New native/sector compile/run waits are bounded at 120 seconds; the
reused rtl_repair.run_grid helper retains unbounded waits on its fixed 3,072-point grid and fingerprinted sources.
Repeating the complete run produces identical summary and eleven CSV artifacts; committed results retain the compact
summary and 16 witnesses, not the 107,520-row CSV. Source digests use canonical LF.

Thirteen actual recompiled RTL mutations have passing fresh controls and fail asserted contracts; compiler/tool errors
do not count. Four test-only Python mutations exercise score removal, reserved influence, unknown-row acceptance and
removal of explicit UTF-8. The existing test_properties checks for isolated SpinSite exponential decay, complement drift
and caller consent remain model tests, not device calibration. All results concern deterministic functions and
simulations. They establish no physical measurement, payload semantics, cryptography, consent grant or model quality; no
core/specification/constants or historical artifacts were changed.

Validation: 33 new cases (16 main, 17 sector); existing 54 cases make 87. Run python -m pytest -q tools/prove_out/tests;
original suite remains 1,256, golden 5 passed / 0 failed. Ruff 0.14.10 and diff --check exited zero. For each of
python-score-zero, reserved-influence and unknown-affinity-row, set CX017_MUTATION and run its target in
test_verdict.py; the committed fixture contains the bounded mapping. Each target failed with AssertionError; each had an
unmodified passing baseline/clean target and an unaffected passing control. Two three-mutant receipts agree byte for
byte. Native results separately record 13 killed / 0 survived and 13 fresh clean controls. These are executed counts.

Independent guard review ran 49 source variants: 47 assertion kills, one equivalent bounds-guard deletion excluded, and
one missing-orientation-grid variant rejected with KeyError (fail-closed, not counted). Exact formulas imply byte bounds
on AFF_DOMAIN, so removing that redundant bound check is not an eligible failure. There are zero eligible non-equivalent
survivors. Thirty unique baselines plus one recheck, and 49 clean controls plus three rechecks, pass. Receipt SHA256
e49c16da9776aeb1819d68c67adf45b8a6a683b84b57a0234bede450f86fa363. These guard, Python and native counts describe
separate executions with overlapping defect patterns; they are not summed as unique defects.

Unexecuted docstring variants are limited to separate CSV row-order/injected-clock changes (CRLF was executed), decoder
omega/radius/reserved extraction changes (phi/word/sentinel variants were executed), and D1 phi/harmonic multipliers
(theta/default/unknown/input-domain/both-radius-policy variants were executed). Synthetic parser fixtures remain parser
controls, not independent native evidence. Compile/tool failures never count.

Self-review used
[anywave-pre-push-review](https://github.com/anywave/trellis-channel/blob/main/boot/codex-skills/anywave-pre-push-review/SKILL.md),
blob 8a9dbbd4f2f1be52acc48d4028f9536f560cd1dd. Full merge-base 94c372be review found the second affinity/helper/decoder
paths; add-only criteria amendments preceded their runs. Native wrap/reverse probes closed an anchor-only gap; the first
orientation stimulus now transitions before sampling. Windows review fixed ACP-dependent I/O and workspace-only tool
paths. Actual visited counters replaced hardcoded coverage receipts; the formula-unit fixture now isolates formula
failure from repeated-score failure. New wrappers have 120-second waits; the inherited fixed-grid Ra helper limitation
is explicit.
