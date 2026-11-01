# CX-005 E4: synthesis summary status

Either synthesis flow can fail after writing parseable nextpnr numbers. The
summary labels **both A and B** as completed, failed (partial diagnostics), or
incomplete/unknown. Completion requires an explicit `ok` marker and at least one
parsed resource/timing value: an empty or wholly unparseable log is insufficient.
Missing/unknown status stays incomplete. Log and status reads use explicit UTF-8
with replacement decoding. Published reference numbers are unchanged.

Round 2 closes the adversarial review gaps in `eb6a98c`: Flow A now has the same
status contract as Flow B, and merely existing empty/unparseable logs no longer
establish completion. The actual workflow resets both markers to `incomplete`
before either flow, writes Flow A's outcome after its real Yosys/nextpnr commands,
and still exits 1 on either Flow A failure. Flow B remains optional. Mocked tool
executables exercise the actual workflow fragment for Yosys failure, nextpnr
failure with a partial log, and success; they also verify stale `ok` markers are
reset before commands run. No hosted toolchain or actual synthesis was run.

Validation on Python 3.12.14, Icarus not needed:

| Command (from checkout, using the task venv) | Result |
|---|---|
| `python -m pytest tools/ci_summary/ -q -o addopts=` | 20 passed |
| `python -m tools.ci_summary.mutation_check` | killed=11 survived=0 controls=11/0 skipped=0 |
| `python -m pytest tests/ -q` | 1256 passed, 1 existing warning |
| `python tests/test_golden_vectors_mobius32.py` | SUMMARY pass=5 fail=0 |
| `ruff --version` | ruff 0.14.10 |
| `ruff check rpp/ tests/ tools/ci_synth_summary.py tools/ci_summary/ --ignore E501` | exit 0 |
| `git diff --cached --check` | exit 0 |

Every new test docstring names a failing mutation. Seven source mutants and four
workflow-fragment mutants execute both changed behavior and original clean
controls. They catch missing Flow A reporting, trusting missing/empty/unparseable
logs, ignoring failure, dropping success, suppressing the workflow failure exit,
and stale markers. Encoding tests audit both status readers as well as log
decoding; unknown status text never enters the Markdown. Source files are never
mutated. The workflow fixture and mutation runner use only the standard library.

TR PR title: **Label failed and incomplete synthesis flows**.
Branch `codex/synthesis-summary` → `master`; use this file as the body. Run the same
commands on Windows 11 / Python 3.13. Native Windows is expected to report
17 passed / 3 skipped (the GitHub Linux shell-fragment cases), and the mutation
runner killed=7 / survived=0 / controls=7/0 / skipped=4. Windows has not been run
here. Hosted synthesis itself was not rerun; this change is tested against log
fixtures and mocked workflow commands, including a failure with valid partial data.

Audit scope and skips: all five existing workflows use full action SHAs already;
no repinning needed. The advisory drift job remains advisory per TR's ruling.
Unpinned dependency/build-tool policy and hosted synthesis tool upgrades would
expand reproducibility/release scope and were skipped. The RA source-list/exit
status fixes belong to E2. Existing core-policy conflicts remain for the packet.
