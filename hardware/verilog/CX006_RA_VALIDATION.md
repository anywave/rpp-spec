# CX-006: exact Python policy in all three RTL score bindings

Base `275a115`; branch `codex/rtl-scaling-repair`. The authorized repair replaces
the two faulty combinational arithmetic pipelines with one shared exact policy
calculation. Public module names and ports, published macros `165`, `509`, `62`,
and Python source, layouts, consent header and golden vectors are unchanged.

The shared calculation is
`floor(165 * entropy / 31) + floor(509 * complecount / 7)`. Each term is truncated
before addition, as in the actual Python reference over all 256 header inputs.
Products need 13 bits (maximum 5115) and 12 bits (maximum 3563); contributions
need 8 and 9 bits; the 10-bit sum has maximum 674. Both public combinational
bindings instantiate this calculation. The registered scorer is unchanged.

This is a full replacement of the broken arithmetic, rather than adoption of
the historical two-line shift proposal. The retired `1618/5089` reciprocal
calculation uses different approximations from the published `165/509` policy.
An actual disposable run correcting its shift to 16 and widening its completion
reciprocal product to 25 bits still disagrees at **214/256** score inputs
(**2568/3072** threshold-grid rows), and at **9/3072** threshold decisions. Its
maximum-input score is 669. Rounded normalized LUT arithmetic also cannot
reproduce every separately truncated term. Constant unsigned division provides
the bounded exact implementation without changing a published value.

## Actual simulation results

`tools/prove_out/rtl_repair.py` compiles and runs Icarus, validates every row of
the 32 × 8 × 12 grid, then compares actual HDL output with the imported Python
reference. The twelve thresholds are `0,136,137,138,299,300,499,500,673,674,675,1023`.
Saved CSVs are recorded native output, not Python-predicted RTL output.

| Binding | Before score differences / 3072 | Before decision differences / 3072 | After score / decision differences |
|---|---:|---:|---:|
| Registered `CoherenceEvaluatorRa` | 0 | 0 | **0 / 0** |
| Combinational `CoherenceEvaluator_Ra` | 3060 | 967 | **0 / 0** |
| Compatibility `CoherenceEvaluator_Ra_Precise` | 2940 | 345 | **0 / 0** |

Both input axes are nondecreasing after repair: **0 decreases** at each binding's
**248 entropy-adjacent pairs** and **224 completion-adjacent pairs**. Band outputs
have **0** disagreements against score cutoffs 300 and 500. The retained
normalization expression has **0** expression disagreements.

The RA bench remains **33 checks / 33 passed / 0 failed**, compile/runtime exit
**0**. Its score probes now assert exact values **0, 297, 369, 674** as well as
the appropriate bands. The former 450 smoke value is no longer accepted.
Mutable comments/display labels describe the current exact bindings.

The old `CX005_RA_SHIFT_ONLY.diff` remains historical, unapplied evidence for the
old source. `check_ra_testbench.py` recognizes the new exact pipeline and does
not attempt that obsolete diagnostic on a source that has no reciprocal stage.

## Executed hardware mutations

Each mutation compiles and runs successfully on a disposable source copy and
fails the actual score-agreement assertion. Each has a separately compiled and
rerun clean control. Compiler/runtime failures and malformed grids propagate;
they never count as killed mutants.

| Named failing mutation | Score differences per repaired binding / 3072 | Decision differences per repaired binding / 3072 |
|---|---:|---:|
| `incorrect-shift`: apply `<< 2` to the exact sum, reproducing the fourfold scaling error of shifting by 14 instead of 16 | 3060 | 968 |
| `completion-product-truncation`: narrow the required 12-bit product to 11 bits | 1152 | 312 |
| `combined-floor`: truncate after summing the rational terms instead of truncating each term separately | 1080 | 2 |

Observed **killed=3 survived=0 clean_controls=3 failed_controls=0**.
The existing RA bench runner additionally executes its four mutations:
wrong mid-band, wrong encoded phi, medium output always false, and failed-check
exit removed: **killed=4 survived=0**, with **1** shared clean control.

## Commands and repeatability

Executed from the branch checkout with Python **3.12.14**, Icarus **12.0** and
Ruff **0.14.10**. These selectors name the existing extracted toolchain:

```bash
PY=/workspace/work/cx005/venv/bin/python
IV=/workspace/work/cx005/iverilog/usr/bin/iverilog
VVP=/workspace/work/cx005/iverilog/usr/bin/vvp
IVL=/workspace/work/cx005/iverilog/usr/lib/x86_64-linux-gnu/ivl
PYTHONPATH=. "$PY" -m tools.prove_out.rtl_repair --base 275a115 --iverilog "$IV" --vvp "$VVP" --ivl-dir "$IVL" --work-dir /workspace/work/cx006/repair-sweep-one --output-dir tools/prove_out/results/cx006
PYTHONPATH=. "$PY" -m tools.prove_out.rtl_repair --base 275a115 --iverilog "$IV" --vvp "$VVP" --ivl-dir "$IVL" --work-dir /workspace/work/cx006/repair-sweep-two --output-dir /workspace/work/cx006/repair-repeat
cmp tools/prove_out/results/cx006/before-scores.csv /workspace/work/cx006/repair-repeat/before-scores.csv
cmp tools/prove_out/results/cx006/after-scores.csv /workspace/work/cx006/repair-repeat/after-scores.csv
cmp tools/prove_out/results/cx006/width-and-shift-only-scores.csv /workspace/work/cx006/repair-repeat/width-and-shift-only-scores.csv
cmp tools/prove_out/results/cx006/summary.json /workspace/work/cx006/repair-repeat/summary.json
"$PY" hardware/verilog/check_ra_testbench.py --iverilog "$IV" --vvp "$VVP" --ivl-dir "$IVL" --output-dir /workspace/work/cx006/ra-check
PYTHONPATH=. "$PY" -m pytest tools/prove_out/tests/ -q -o addopts=
PYTHONPATH=. "$PY" -m pytest tests/ -q
PYTHONPATH=. "$PY" tests/test_golden_vectors_mobius32.py
/workspace/work/cx005/venv/bin/ruff --version
/workspace/work/cx005/venv/bin/ruff check rpp/ tests/ tools/prove_out/rtl_repair.py hardware/verilog/check_ra_testbench.py --ignore E501
git diff --cached --check
```

Observed: both hardware sweeps **exit 0**; all four `cmp` commands **exit 0**;
RA **33/33**, mutations **4/0**; existing prove-out pytest checks **54 passed**;
package pytest **1256 passed**, one existing warning; golden **pass=5 fail=0**;
Ruff **0.14.10 / exit 0**. Pytest's saved CX-005 snapshots remain historical
checks; the separate `rtl_repair` command above performs the current native HDL
execution. New results go under `tools/prove_out/results/cx006/` without replacing
any historical evidence.

Primary byte-identical artifact SHA-256 values:

| Artifact | SHA-256 |
|---|---|
| `before-scores.csv` | `c5f3b8894ca2ebe8bc079c14ad8237aa05a6b399701f4ac4671e773910457945` |
| `after-scores.csv` | `e4f2129f3901877e984bcbd380920836eb3722d905faf226937305c4b2d7fbc0` |
| `width-and-shift-only-scores.csv` | `da5a29848a24a02988745c36ebc97062faccb24cb484f0b565097055ef74edd7` |
| `summary.json` | `80cbee8205f66333e5da705f6c41bcc3ba1200643cbee687c78e6790f5e83254` |

An independent reviewer separately compiled this TB, ran Icarus, and checked all
3072 actual rows using a separate `Fraction` oracle plus the actual Python scorer:
all three bindings **0 score / 0 decision differences**, **0 band differences**,
**0 normalization-expression differences**, and **0 decreases on both axes**.

## Preserved behavior and limits

The driver enforces byte-identical registered-scorer source and the entire
trigger/fallback/consent module tail against `275a115`. The broader
`CompletionEvidence` simulation was run before and after: named consent
derivation differences remain **13/32**; fallback differences remain
**134400/207360**; condition-inverted trigger differences remain **0/34**, with
first-active indices **12,29**. These unresolved semantics were not repaired.
The corresponding before/after policy summary files retain their observed raw
log hashes; those hashes describe the original run, not a cross-platform log
format contract.

The old normalization expression `((score * 38) >> 8) & 255` is preserved. Its
maximum at repaired score 674 is **100**, not a newly calibrated 0–255 scale.
No normalized-output definition is adopted here. Public band/valid comparisons
are preserved; their results change only because their score is repaired.
No synthesis resource count, clock closure or real-device performance is claimed.
This proves the declared finite raw-score/decision binding, without promoting
the generic coherence or sector verdict or deciding another steward item.

For Windows 11 / Python 3.13, TR should repeat the package, prove-out, golden,
Ruff and both hardware commands, using native Icarus executable paths and
normally omitting `--ivl-dir`. Use the same literal `--base 275a115` and separate
scratch/output directories. Compare the three CSVs and primary summary bytes
with the hashes above; expect **33/33**, hardware mutants **3/0 + 4/0**, and
all three bindings **0/0** across the 3072-point grid.
