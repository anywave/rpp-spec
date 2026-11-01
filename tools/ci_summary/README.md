# CX-005 E4: synthesis summary status

The optional flow B can fail after writing a parseable nextpnr log. Previously its
resource/timing values appeared without the failure status. The summary now labels
failed values as partial diagnostics and requires both an `ok` marker and a log
before reporting completion. Missing/unknown status stays incomplete. Log and
status reads use explicit UTF-8. Published reference numbers are unchanged.

Validation on Python 3.12.14, Icarus not needed:

| Command (from checkout, using the task venv) | Result |
|---|---|
| `python -m pytest tools/ci_summary/ -q -o addopts=` | 6 passed |
| `python -m tools.ci_summary.mutation_check` | killed=4 survived=0 controls=4/0 |
| `python -m pytest tests/ -q -o addopts=` | 1256 passed, 1 existing warning |
| `python tests/test_golden_vectors_mobius32.py` | SUMMARY pass=5 fail=0 |
| `ruff --version` | ruff 0.14.10 |
| `ruff check rpp/ tests/ tools/ci_synth_summary.py tools/ci_summary/ --ignore E501` | exit 0 |
| `git diff --check` | exit 0 |

Every new test docstring names a failing mutation. The four in-memory mutants
execute both the changed behavior and original clean controls. Source files are
never mutated. The two remaining tests exercise UTF-8 transport and untrusted
status text without adding a report injection surface.

TR PR title: **Label failed and incomplete optional synthesis flows**.
Branch `codex/synthesis-summary` → `master`; use this file as the body. Run the same
commands on Windows 11 / Python 3.13. Hosted synthesis itself was not rerun; this
change is tested against log fixtures, including a failure with valid partial data.

Audit scope and skips: all five existing workflows use full action SHAs already;
no repinning needed. The advisory drift job remains advisory per TR's ruling.
Unpinned dependency/build-tool policy and hosted synthesis tool upgrades would
expand reproducibility/release scope and were skipped. The RA source-list/exit
status fixes belong to E2. Existing core-policy conflicts remain for the packet.
