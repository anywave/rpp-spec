# CX-006 recorded native HDL evidence

`before-scores.csv`, `after-scores.csv` and
`width-and-shift-only-scores.csv` each contain 3072 actual Icarus output rows.
The third records why correcting the historical reciprocal width/shift alone
does not satisfy the existing Python policy. `summary.json` records finite-domain
comparisons, actual hardware mutations, clean controls, source/artifact hashes
and explicit both-axis monotonicity counts.

Regenerate these four primary files with `python -m tools.prove_out.rtl_repair`
using the commands in `hardware/verilog/CX006_RA_VALIDATION.md`. Intermediate
images and full process logs go only to the explicit `--work-dir`.

The two `*-policy-summary.json` files separately retain the broader existing
`CompletionEvidence` before/after runs, including unchanged consent-derivation,
fallback and trigger counts. Their raw-log hashes identify the observed runs;
the four primary files define the byte-repeatable comparison artifacts.
