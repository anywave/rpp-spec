# CX-005 E1 validation

Branch: `codex/coherence-sector-completion`, from `95c67ef`. Both updated
verdicts are **partly proved**; see CX005_CONDITIONS.md for the exact remaining
steward/core predicates. No generic readout is authorized by these results.
Only tools/prove_out changes are included. Original source, published constants,
specification, vectors, headers and outboxes remain unchanged.

All commands run in this checkout with `PYTHONPATH=.` and
`/workspace/work/cx005/venv/bin/python` as Python3.12.14. The Python package import
resolves inside this worktree. The existing deprecation notices are retained.

| Command | Observed result |
|---|---|
| `python -m pytest tools/prove_out/tests/ -q -o addopts=` | **54 passed**: previous28 plus8 completion cases,15 foreign/native evidence cases and3 evidence-byte cases. |
| `python -m tools.prove_out.mutation_check` | **killed=22 survived=0**: previous7 plus4 completion,9 foreign-model/artifact and2 evidence-byte witnesses. |
| `python -m pytest tests/ -q` | **1256 passed,1 pre-existing warning**. |
| `python tests/test_golden_vectors_mobius32.py` | **SUMMARY pass=5 fail=0**. |
| `ruff --version` | **ruff0.14.10**. |
| `ruff check rpp/ tests/ --ignore E501` | **exit0**. |
| `ruff check tools/prove_out/completion.py tools/prove_out/foreign_reference.py tools/prove_out/native_rust/run.py tools/prove_out/tests/test_completion.py tools/prove_out/tests/test_foreign_reference.py tools/prove_out/mutation_check.py --ignore E501` | **exit0**. |
| `git diff --check` and staged equivalent | **exit0**. |
| `python -m tools.drift check --base95c67ef --head <full branch SHA> --output-dir <scratch>` (space after `--base` in executable command below) | **high=0 medium=0 low=0**, open baselines243/steward items4/advisories2 unchanged; **exit0**. |

Every new test has a concrete failing mutation in its docstring. The runner's
22 named mutations are actually executed in test memory; a survived mutant
fails the runner. Hypothetical alternatives in docstrings are not additional
executed mutants; the Round2 inventory below and FOREIGN_BINDINGS distinguish
them explicitly. The parser deliberately rejects incomplete, duplicate,
malformed and unknown-valued recognized RTL rows instead of counting them as
agreement. Test names are fixed strings, with no data-dumping interpolation.

## Actual additional RTL execution

Icarus12.0 was locally extracted from authenticated Debian package metadata by
the parent task. The root's task-local prefix is not a repository dependency.
With normal installed `iverilog`/`vvp`, omit `-B`/`-M` and their values:

```bash
mkdir -p /workspace/work/cx005/e1-run
/workspace/work/cx005/iverilog/usr/bin/iverilog -B /workspace/work/cx005/iverilog/usr/lib/x86_64-linux-gnu/ivl -g2012 -s CompletionEvidence -o /workspace/work/cx005/e1-run/completion.vvp tools/prove_out/completion_tb.v hardware/verilog/coherence_evaluator_ra.v hardware/verilog/spiral_ra_coherence.v
/workspace/work/cx005/iverilog/usr/bin/vvp -M /workspace/work/cx005/iverilog/usr/lib/x86_64-linux-gnu/ivl /workspace/work/cx005/e1-run/completion.vvp > /workspace/work/cx005/e1-run/completion.log
python -m tools.prove_out.completion --rtl-log /workspace/work/cx005/e1-run/completion.log
```

Compile and run exit0. The analyzer requires all expected domains exactly once:

| Probe | Count and observed result |
|---|---|
| Three score modules | **3072 points**, all256 header inputs at12 thresholds:0,136,137,138,299,300,499,500,673,674,675,1023. |
| Exact/approximate/LUT score differences versus Python | **0 /3060 /2940** across3072. |
| Exact/approximate/LUT decision differences at the configured threshold | **0 /967 /345** across3072. |
| Entropy-axis decreases on248 adjacent pairs | Exact0; approximate5; LUT0. |
| Completion-axis decreases on224 adjacent pairs | Exact0; approximate63; LUT32. |
| ConsentStateDeriver | **32 cases**, **13 named-state differences** with Python. Experimental wiring maps boolean override to supplied strength3 or0; this is not a protocol adapter. |
| FallbackResolver_Ra versus Python canonical fallback | **207360 cases**, **134400 theta differences**; phi/omega/radius differences **0/0/0**. Experimental phi0..5↔phi1..6 adapter is explicitly declared. |
| ScalarTriggerRa_Khat consecutive-cycle behavior | **34 points**, **0 differences** after inverting the high/low condition for comparison with FallbackGate. First true output indices12 and29 mean the13th true sample of each run. This verifies counter timing only, not equivalence of the two triggering policies. |

The full simulator log was retained only in the original execution's scratch;
it is not committed. The committed JSON is a saved summary snapshot, with the
log's SHA-256, complete-domain counts and16 fallback counterexamples. The
ordinary pytest summary check does not rerun RTL or regenerate the summary
from a committed log. A fresh independent check needs the native Icarus command
above. The original run's canonical-LF log digest
is `1b1976c0be736dd117ddaa3b2321bf79454865ed167e17f9675ba89c131a31f8`.
Re-running the same vvp file into completion-repeat.log and running `cmp` returned0.
The repeated analyzer wrote six artifacts; **identical_artifacts=6 different=0**.
Their SHA-256 values:

| Artifact | SHA-256 |
|---|---|
| consent-derivation.csv | `2bb94d866f88d11e419158617b6673ada91351b8aac920b76e80eec1635006e9` |
| fallback-counterexamples.csv | `ae052177cc650a8b76307f3abca8e88b58b9f8a47b3795f0d8f3845b64628b7f` |
| policy.csv | `82f95cee2ac0c03d19666ea2665aa6ce152b26af1b74457b31033fe40c4bbb52` |
| sector-access.csv | `1305727a7666950df026eb7bd6ce1946ea2c63c03a445d5dd374b2d1137ea136` |
| sector-projection.md | `50ba1a6fd1bd5a0627d8f0e34aa1de5967e0948b5251f6f82ee327e0ca3d6745` |
| summary.json | `1e9919da3496ebef956ecb65ed40810e629d65cd642c1a590c87b132c43c62a3` |

## Foreign bindings

See FOREIGN_BINDINGS.md for complete commands and source hashes. Python
transcription characterization exercises6006 Rust ordinary points,36 adjacent-float
boundaries and65536 Clash products/group-score slice cases. Those formula/model
properties are self-consistency evidence, not independent foreign-binding
execution. A separate actual Rust1.85.1 harness called
the unchanged public ra_core gate functions: **6042 rows, reference_mismatches=0**.
Its recorded second cached offline build/run yielded identical CSV and summary bytes.
Ordinary pytest checks that saved native artifact; it does not compile or run Rust.
The canonical native Rust CSV digest equals the reference digest:
`8ad8786406cc1f24625dda28fb2f6eb1432a94c196541389bd93d67304d8f9ff`.
No Rust property suite, proptest or random generator was run. GHC/Clash native
execution/synthesis remains unrun; all Clash results here are transcription
characterization only. The prior6042-row actual Rust comparison is the sole
independent native foreign-binding agreement claim in this extension.
No physical-device or biological measurement test is claimed.

## Repeated finite policy checks and conservative choices

The new policy table covers675 raw scores. The45 state/sector rows cover the
zero/nonzero branches of every runtime sector decision. The new512-row Markdown
projection table supplements the complete CSV:36 names agree and476 differ.
No radius derivation is selected. Existing bindings are preserved as separate
quantities; explicit experimental adapters never grant consent or become a
published wire-format rule. Unknown RTL values are an error. Legacy counter
and mismatch behavior is characterized rather than silently normalized.

The exact unapplied patches in CX005_PROPOSALS.md propose additive named APIs,
Python-aligned fallback theta and derived completion. Adoption, consent-profile
reconciliation, alternate scorer authority and the existing four steward items
remain RADIX decisions. The grouped243 baseline entries remain unresolved.

Final drift command, using an actual hexadecimal SHA (the CLI rejects HEAD):

```bash
python -m tools.drift check --base 95c67ef --head "$(git rev-parse HEAD)" --output-dir /workspace/work/cx005/e1-run/drift
```

## Round2: portable evidence bytes and precise test claims

The root `.gitattributes` is owned by this branch and contains both
`tools/prove_out/results/** -text` and `tools/overlay_sim/results/** -text`.
These rules cover CSV, Markdown and summary JSON evidence. No second attributes
file is required on the overlay branch. The byte/hash readers also canonicalize
CRLF to LF for pre-existing converted checkouts. This normalization preserves
lone CR, whitespace, UTF-8 bytes, final-newline presence and all content edits.
Source verification uses the same canonical-LF contract as reviewed Git blobs.

The new real Git regression creates a disposable repository with
`core.autocrlf=true`, commits all11 completion/foreign snapshots and representative
overlay CSV/JSON files, removes them and restores them using checkout-index.
The ordinary text control becomes CRLF, proving conversion is active; all13
protected files remain byte-identical to their Git blobs. The hash test covers
all11 saved files, including both foreign summaries and the completion summary,
and accepts only CRLF/LF equivalence. A changed-byte control still differs.
Executed mutations remove the attributes or remove normalization; both must fail.

The former `test_real_rtl_comparisons_keep_disagreements_visible` is now
`test_committed_rtl_summary_snapshot_keeps_disagreements_visible`, explicitly a
snapshot check. No raw log is added. This is an IMPOSED conservative choice;
recorded simulator counts remain historical execution evidence. The65536-row
Clash CSV is retained to avoid output churn and preserve inspectable model data;
this is an IMPOSED choice and adds no independent native Clash evidence.

Nine additional foreign mutations execute against the Python transcription,
source-hash guard or saved native artifact, not against compiled foreign code.
FOREIGN_BINDINGS lists their exact witnesses and every remaining unexecuted
foreign-test docstring mutation. The following completion/evidence docstring
alternatives are also unexecuted examples, not extra killed-mutant claims:

| Test | Unexecuted docstring alternatives |
|---|---|
| all_raw_score_thresholds_and_stages | Move137→138; skip a score; constant stage0. The executed witness always admits. |
| all_sector_access_states_and_void_exception | Individually allow emergency BRIDGE/nonzero VOID or omit a state. The executed witness always allows every sector. |
| sector_projection_table_has_every_theta_once | Remove/reorder a theta row. The executed witness changes theta0's projection to2. |
| committed_rtl_summary_snapshot_keeps_disagreements_visible | Rewrite a saved mismatch count as equality. |
| rtl_grid_rejects_duplicate_rows | Overwrite duplicate keys. |
| rtl_grid_refuses_unknown_and_malformed_values | Convert x to0; ignore malformed recognized rows. |
| generated_policy_tables_are_byte_repeatable | Add timestamp/random output, unstable ordering or drop a row. |
| crlf_normalization_preserves_other_bytes_and_content_changes | Strip lone CR/whitespace or normalize a content edit away. |
| all_completion_and_foreign_snapshot_hashes_accept_crlf_only | Alter one saved artifact byte. The executed witness hashes CRLF raw. |

The missing-grid guard and autocrlf attributes witnesses execute exactly the
mutations described by their tests. The original CX-003 tests remain covered by
their existing README table of seven selected executed mutations and other
hypothetical examples; none is reclassified as new execution in this round.
