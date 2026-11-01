# CX-005 E2: RA testbench expectations and failure status

Source base: `95c67ef`. Branch: `codex/ra-testbench`.

Both originally failing checks had incorrect testbench expectations:

| Check | Evidence | Correction |
|---|---|---|
| Mid-coherence | `E=15,C=3` gives Python weighted score **297**, below the existing medium threshold **300**. The unchanged approximate RTL gives **160**, also low. | Assert the low band and exclude medium/high. Add a separate `E=15,C=4` medium probe: Python **369**, approximate RTL **450**. These check classification, without asserting cross-binding score equality. |
| Phi extraction | The unchanged header address `0x61500000` has raw `[26:24]=1`. `ConsentHeaderParser` returns this raw field. Canonical decoding adds one, so its RAC level is **2**. | Expect raw phi **1**, and correct the fixture comment. Keep the header bytes, parser and address layout unchanged. |

The exact Python values and approximate values are also retained in
`tools/prove_out/results/hdl-comparison.csv`, rows `(15,3)` and `(15,4)`.
The known approximate/LUT arithmetic disagreement remains an E1/core-adoption
blocker; correcting these two testbench expectations does not resolve it.
No E2 core/spec/constants/header edit is proposed or required.

The documented compile command previously included two sources defining
`ConsentHeaderParser`, `PMARecordParser` and `CRC8_Byte`; Icarus exits **6**.
The revised source list includes `spiral_consent.v` once and specifies the top.
The testbench now calls `$fatal(1, ...)` after any failed check, so CI can use
process status. The old testbench printed two failures and exited **0**.

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
additional check is the genuine medium-band probe. The runner also rejects
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

## Conservative choices and Windows repeat

Keep the existing input bytes and report the parser's encoded field explicitly.
Use a separate medium input instead of accepting the old vector as medium.
Do not repair alternate RTL arithmetic or claim it equals the Python reference.
No published outbox, source under `rpp/`, original package tests, spec text,
protocol header, golden vector or constant changes.

TR should repeat the package/golden/Ruff commands on Windows 11 / Python 3.13,
then run `python hardware/verilog/check_ra_testbench.py --iverilog <iverilog.exe>
--vvp <vvp.exe> --output-dir <scratch-directory>` with Icarus installed. Native
installs normally omit `--ivl-dir`. Expect **33/33**, **4 killed/0 survived**.
