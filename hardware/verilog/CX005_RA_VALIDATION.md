# CX-005 E2: RA testbench expectations and failure status

Source base: `95c67ef`. Branch: `codex/ra-testbench`.

Both originally failing checks had incorrect testbench expectations:

| Check | Evidence | Correction |
|---|---|---|
| Mid-coherence | `E=15,C=3` gives Python weighted score **297**, below the existing medium threshold **300**. The unchanged approximate RTL gives **160**, also low. | Assert the low band and exclude medium/high. Retain an implementation-only `E=15,C=4` classification smoke probe, observed RTL **450**. That value depends on erroneous shifts and product truncation; it cannot validate the formula or agreement with Python. |
| Phi extraction | The unchanged header address `0x61500000` has raw `[26:24]=1`. `ConsentHeaderParser` returns this raw field. Canonical decoding adds one, so its RAC level is **2**. | Expect raw phi **1**, and correct the fixture comment. Keep the header bytes, parser and address layout unchanged. |

The exact Python values and approximate values are also retained in
`tools/prove_out/results/hdl-comparison.csv`, rows `(15,3)` and `(15,4)`.
The known approximate/LUT arithmetic disagreement remains an E1/core-adoption
blocker; correcting these two testbench expectations does not resolve it.
The testbench expectation corrections require no core/spec/constants/header edit. The HIGH reciprocal-scaling defect below remains unresolved for RADIX; its exact diagnostic RTL diff is proposed only, never applied.

The documented compile command previously included two sources defining
`ConsentHeaderParser`, `PMARecordParser` and `CRC8_Byte`; Icarus exits **6**.
The revised source list includes `spiral_consent.v` once and specifies the top.
The testbench now calls `$fatal(1, ...)` after any failed check, so CI can use
process status. The old testbench printed two failures and exited **0**.

## HIGH: reciprocal scaling and product overflow, unresolved — RADIX

`spiral_ra_coherence.v:136-140` multiplies by reciprocal coefficients documented
as `211/65536` and `936/65536`, but slices `[23:14]`, equivalent to shifting by
14 before ten-bit truncation. A denominator of 65536 calls for a shift of 16.
The 24-bit `ankh_div` product also overflows for part of the input domain.

For `E=15,C=4`, the full reciprocal products are **5,120,970** and
**19,053,216**. The second truncates to **2,276,000** in its 24-bit wire.
The shipped slices yield **312 + 138 = 450**; the apparent medium-band success
depends on faulty scaling/truncation. It is not independent evidence for the
formula, even though the separate Python score happens to lie in that band.

The exact two-line scaling proposal is retained in
`CX005_RA_SHIFT_ONLY.diff` and reproduced below. It is **NOT APPLIED** and is
**not a complete repair**: retaining 24-bit products changes this point to
**78 + 34 = 112**. Widening products and choosing whether this approximate
1618/5089-derived family should implement the published 165/509 Python policy
need separate review. No such policy choice is made here.

```diff
--- a/hardware/verilog/spiral_ra_coherence.v
+++ b/hardware/verilog/spiral_ra_coherence.v
@@ -136,7 +136,7 @@ module CoherenceEvaluator_Ra (
     wire [23:0] phi_div  = term_phi * 24'd211;   // ×211/65536 ≈ /310
     wire [23:0] ankh_div = term_ankh * 24'd936;  // ×936/65536 ≈ /70

-    wire [9:0] score_phi  = phi_div[23:14];   // Result after >>14
-    wire [9:0] score_ankh = ankh_div[23:14];
+    wire [9:0] score_phi  = phi_div[23:16];   // Result after >>16
+    wire [9:0] score_ankh = ankh_div[23:16];

     wire [9:0] final_score = score_phi + score_ankh;
```

Icarus was run on a disposable RTL copy with exactly this diff. Compile **0**;
**33 checks, 32 passed, 1 failed; runtime 1**. The only failed check is the
implementation-only `E15 C4` classification smoke probe, now score **112**.
The `E31 C7` diagnostic score changes **632 → 413**; `E15 C3` changes
**160 → 296**. These are observed/calculateable counterexamples, not approved
replacement values. The runner reproduces the shift-only experiment after its
four mutation checks and asserts that this partial proposal is not reported as
33/33. The shipped RTL file remains byte-identical to `95c67ef`.

RADIX options: retain the approximate scorer with this defect explicitly open;
commission a complete width/scaling repair against a selected numeric oracle;
or retire this scorer in favor of an already verified binding. Recommended
default: review a complete repair against the chosen oracle before adoption,
because a two-line shift correction still leaves a demonstrated overflow.

## Executed commands and counts

Linux, Python **3.12.14**, Icarus **12.0**, Ruff **0.14.10**. Set these command
selectors for the extracted toolchain used here:

```bash
PY=/workspace/work/cx005/venv/bin/python
IV=/workspace/work/cx005/iverilog/usr/bin/iverilog
VVP=/workspace/work/cx005/iverilog/usr/bin/vvp
IVL=/workspace/work/cx005/iverilog/usr/lib/x86_64-linux-gnu/ivl
```

The parent provisioned the same Debian Icarus package documented by CX-003,
SHA-256 `febe027d2d3f5a7e570844d55758339ab5490acc09f404f214a8719d89d07056`.

Before, with the duplicated source omitted so the original bench could run:

```bash
git show 95c67ef:hardware/verilog/spiral_testbench_ra.v > /workspace/work/cx005/e2-before/spiral_testbench_ra.v
"$IV" -B "$IVL" -g2012 -s spiral_testbench_ra -o /workspace/work/cx005/e2-before/ra.vvp /workspace/work/cx005/e2-before/spiral_testbench_ra.v hardware/verilog/spiral_ra_coherence.v hardware/verilog/spiral_consent.v
cd /workspace/work/cx005/e2-before
"$VVP" -M "$IVL" ra.vvp
```

Compile **exit 0**; **32 checks, 30 passed, 2 failed; runtime exit 0**.
Adding `hardware/verilog/spiral_consolidated.v` to that compile reproduces
**exit 6**, with all three duplicate module declarations.

From the E2 checkout, after:

```bash
"$PY" hardware/verilog/check_ra_testbench.py --iverilog "$IV" --vvp "$VVP" --ivl-dir "$IVL" --output-dir /workspace/work/cx005/e2-check
```

Clean compile/runtime **exit 0**; **33 checks, 33 passed, 0 failed**. The one
additional check is the implementation-only classification smoke probe, not a formula-validation check. The runner also rejects
missing/duplicate/inconsistent summaries and disagreements with individual rows.
The command executes four mutations in disposable copies, with the compiled
clean run as their shared control:

| Named failing mutation | Observable failure |
|---|---|
| `restored-wrong-mid-band` | 1 failed check; runtime exit **1** |
| `restored-wrong-encoded-phi` | 1 failed check; runtime exit **1** |
| `medium-output-always-false` | 1 failed check; runtime exit **1** |
| `failure-exit-removed` | The otherwise failing phi check exits **0**; the failure-status assertion rejects it. |

Observed **killed=4, survived=0, clean_controls=1, failed_controls=0**. Each
mutation compiles successfully; compilation errors never count as killed.
All mutated files, logs, images and VCDs stay under the supplied output directory.

```bash
PYTHONPATH=. "$PY" -m pytest tests/ -q
PYTHONPATH=. "$PY" tests/test_golden_vectors_mobius32.py
/workspace/work/cx005/venv/bin/ruff --version
/workspace/work/cx005/venv/bin/ruff check rpp/ tests/ hardware/verilog/check_ra_testbench.py --ignore E501
git diff --check
```

Observed **1256 passed, 1 pre-existing warning**; golden **pass=5 fail=0**;
Ruff **0.14.10**, lint **exit 0**; whitespace **exit 0**.
The package test count stays 1256 because the added assertion is an HDL check.

```bash
PYTHONPATH=. "$PY" -m tools.drift check --base 95c67ef --head "$(git rev-parse HEAD)" --output-dir /workspace/work/cx005/e2-drift
```

Observed **exit 0**, findings **high=0 medium=0 low=0**; unresolved inventory
**baselines=243, steward_items=4, advisories=2**. The tool requires the resolved
hexadecimal head passed above; literal `--head HEAD` exits 2 without a review.

## Conservative choices and Windows repeat

Keep the existing input bytes and report the parser's encoded field explicitly.
Retain the separate classification smoke probe without treating its medium result as formula agreement.
Do not repair alternate RTL arithmetic or claim it equals the Python reference.
No published outbox, source under `rpp/`, original package tests, spec text,
protocol header, golden vector or constant changes.

Round 2 repeats the commands above: package **1256 passed**, golden **5/0**,
Ruff **0.14.10 / exit 0**, and whitespace **exit 0**. The runner now has one
`EXPECTED_CHECKS` value for its control/mutation/proposal counts; it retains
the four executable mutations and separately reproduces the unapplied numeric
counterexample. `git apply --check hardware/verilog/CX005_RA_SHIFT_ONLY.diff`
exits **0** without modifying RTL; `git diff --exit-code 95c67ef --
hardware/verilog/spiral_ra_coherence.v` exits **0**. The runner itself exits
**0** after verifying that the proposal's disposable HDL process exits **1**;
that observed failure is evidence against calling the proposal a complete fix.

TR should repeat the package/golden/Ruff commands on Windows 11 / Python 3.13,
then run `python hardware/verilog/check_ra_testbench.py --iverilog <iverilog.exe>
--vvp <vvp.exe> --output-dir <scratch-directory>` with Icarus installed. Native
installs normally omit `--ivl-dir`. Expect **33/33**, **4 killed/0 survived**, followed by the unapplied shift-only experiment **32/33**, runtime exit **1**.
