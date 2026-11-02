# CX-017 technical validation

The frozen criteria and named domains govern these finite experiments.

## Results by binding

| Named quantity/binding | Result within the declared experiment |
|---|---|
| Python ra-policy-674 | PROVED on 10,201 fraction points: formula, [0,674] range and both monotone drivers; coefficient is score/674 |
| Current registered, combinational and compatibility Ra RTL | PROVED: each matches Python on 3,072 code/threshold points, with zero score or decision disagreements and no axis decreases |
| Registered completion / normalized byte | Distinct expressions confirmed: input C==7 differs from Python's derived completion in 31/256 cases; normalization is (score*38)>>8, not score/674 |
| Python canonical-v2 coordinate affinity | PROVED on 107,520 distance classes: declared formula, ordinary bounds, symmetry and 382,556 adjacent driver comparisons; 8,192 reserved probes are irrelevant |
| Python ordinary theta wrap | All 729 ordered address pairs, including 182 wrap pairs, satisfy the declared circular formula exactly; all 729 reverse comparisons agree |
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

Run the complete committed generator, with fresh work and output directories outside the checkout:

```text
python -m tools.prove_out.reproduce --iverilog <iverilog> --vvp <vvp> --cargo <cargo> --work-dir <fresh-work> --output-dir <fresh-output> --check-committed
```

Use Python with pytest installed, Icarus 12 and Rust 1.85.1. An extracted Icarus installation also needs
`--ivl-dir <ivl-directory>`. Configure RUSTC/PATH and any loader path externally; the tool checks cargo and rustc are
1.85.1, then invokes offline locked Cargo. This command also works in PowerShell with fresh external Windows paths.
Each invocation executes two complete native builds and two fresh mutation batches. The committed generator produces
the WHOLE summary, including verification, and writes the receipts; no verification block is added by hand.
`--check-committed` compares all five files named by `reproduce.COMMITTED` byte for byte against the checkout.

Before constructing the final summary twice, the generator compares every primary CSV byte, the complete primary
payload and the complete mutation receipt. The determinism receipt hashes those primary files; the final summary
hashes that receipt. Neither file hashes itself. Canonical LF source fingerprints and strict JSON contain no temporary
paths, timings or nonfinite JSON values. Existing `.gitattributes` marks all committed evidence paths `-text`.
Large sweep CSVs remain reproducible external artifacts; the committed subset includes both counterexample CSVs.
New native/sector and mutation subprocess waits are bounded at 120 seconds; the reused rtl_repair.run_grid helper
retains unbounded waits on its fixed 3,072-point grid and fingerprinted sources.

On 2026-11-02 two independent CLI invocations used fresh external `cx018-first-*` and `cx018-second-*` directories.
The first generated the committed subset; the second used `--check-committed`. Each ran two complete builds, for four
actual builds total. All 17 generated files matched between invocations; all five committed files matched as raw bytes.
The determinism receipt covers 15 primary files. Repeated execution does not multiply the distinct mutation count.

| Committed file | Bytes | SHA256 |
|---|---:|---|
| summary.json | 77423 | 03652557233756154558b9f3bdd3de464bbc000e0e6a9073f0ddfb35369bba44 |
| mutation-receipts.json | 64874 | 8cab4887cd5e7dab4a7cb8d7cd9a5c189785f9d90f56ce027042f43c2b5303e3 |
| determinism.json | 1917 | 206aa25361ffdca4d6ec39f66e5467c884566ffd5bdbe141b48b7e2676470a47 |
| counterexamples.csv | 1051 | 9dda3d7059cb5a9064b00d7ebe4da13653fa43f6fe4fd263127b7356d131e5de |
| fractional-input-counterexamples.csv | 1204 | 026a164c836dadc9e4b40be052f91361def603024add784e9c7fa1f7aa57820c |

The added fractional-input CSV records negative, above-one, NaN and both infinities separately for engagement and
completion, with the other driver zero. Both actual score APIs agree on all ten observations. NaN engagement yields
165 points; NaN completion yields 509. Nonfinite inputs are tagged strings. These are counterexamples outside the
declared finite [0,1] contract, not an extension of the domain or an approved core repair.

Fresh receipt groups execute four gated Python mutations (score removal, reserved influence, unknown-row acceptance,
and actual abs-difference without theta wrap), one explicit-UTF-8 removal, 49 historical source-guard variants and four
new generator variants. The historical variants yield 47 assertion kills, one mathematically equivalent bounds omission
excluded, and one missing-orientation-grid KeyError excluded as fail-closed. Thirty unique baselines, 49 restored clean
controls and 49 unaffected controls pass; 51 selected positive assertions fail. Every eligible group has zero survivors.
The four new generator kills omit verification, omit byte comparison, permit nonfinite JSON or permit case aliases.
Every fixture/source mutation has passing baseline, restored clean and unaffected controls. Tool/compiler errors and
terminal non-assertion exception chains never count as assertion kills. These groups and the 13 independently recompiled
RTL kills overlap defect patterns and are not summed as unique defects.

Fixtures ignore ambient `CX017_MUTATION`. Only the dedicated runner sets both its allowlisted selector and
`CX017_MUTATION_RUNNER=1`, and clears inherited selectors before each subprocess. This prevents ambient test leakage;
it is not authentication against malicious callers. Runtime experiment modules do not read these variables.

Validation: `python -m pytest -q tools/prove_out/tests` passes 146 cases: the prior 87 plus four theta/fractional,
51 generator and four runner cases. `python -m pytest -q tests` remains 1,256 passed; the standalone
`python tests/test_golden_vectors_mobius32.py` remains 5 passed / 0 failed. Ruff 0.14.10 checks rpp/, tests/ and
tools/prove_out/ with `--ignore E501`; diff --check exits zero. Every new test names its failing mutation.
The existing test_properties checks for isolated SpinSite exponential decay, complement drift and caller consent remain
model tests, not device calibration. No core/specification/constants or published outbox changed.

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

CX-018 review maps the whole-file finding to reproduce.py and test_reproduce.py; wrap and out-of-domain findings to
coherence_cases.py and test_coherence_cases.py; fixture isolation to verdict_mutations.py and test_verdict_mutations.py;
plain-language restrictions to both headline lines in VERDICT.md. Independent review checked Windows filenames,
explicit UTF-8, deterministic source snapshots and the terminal-exception classifier. Findings remain unresolved where
they require RADIX adoption: coherence is NOT PROVABLE, sector is PROVED as an address label, and both stay off the website.

PR packaging is NOT READY: the full merge-base 94c372be diff is 21 files / 2,382 changed lines against the 30/1,500 cap.
All individual commits fit 10 files / 400 lines. The same-branch CX-018 fixes retain the requested evidence; no cap rule,
allowlist or baseline was weakened. TR must resolve the PR packaging before merge; this is not an all-green gate claim.
