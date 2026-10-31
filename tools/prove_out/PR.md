# Prove out coherence and sector without changing core

This read-only experiment card separates the overloaded coherence quantities and
sector profiles, then checks their arithmetic and actual protocol use. Both
verdicts are **partly proved**: v1/v2 partitions and selected score policies have
reproducible engineering behavior, while a generic user-facing Coherence0.847 or
profileless Sector readout remains unsupported and should stay absent. No rpp,
original test, spec, layout, consent header, constant or golden vector changes.

Validation from the repository root with this checkout explicitly on PYTHONPATH:

- `python -m pytest tools/prove_out/tests/ -q -o addopts=`: **28 passed**.
- `python -m tools.prove_out.mutation_check`: **killed=7 survived=0**.
- `python -m pytest tests/ -q`: **1256 passed**, one pre-existing warning.
- `python tests/test_golden_vectors_mobius32.py`: **pass=5 fail=0**.
- `python -m tools.prove_out.experiments`: **150 scalar/simulation rows,512 sector rows**;
  repeated CSV hashes identical and both cmp commands exit0.
- Actual Icarus comparison: **256 points**. Registered exact score agrees256/256;
  alternate implementations disagree255/256 and245/256. Their score monotonicity
  fails63/224 and32/224 adjacent completion steps. Completion-flag meaning differs31/256.
- Existing unchanged RA testbench: **32 checks,30 pass,2 fail**, despite vvp exit0.
  This PR reports those failures; it does not silently repair core/header code.
- `git diff --check`: exit0.

See tools/prove_out/README.md for exact commands and named failing mutations,
COHERENCE_TRACE.md and SECTOR_TRACE.md for every definition and consumer,
HARDWARE_RA.md for signed-package verification, simulation commands, physical
limitations and read-only ra-system e685d3ab source trace. Reference proposals live
only in tools/prove_out/proposed.py and have tests; adoption into core is deferred.

Native Rust/Clash, Windows and real hardware/biological validation were not run.
The current cloud had no Rust/GHC/Clash toolchains; Icarus was locally extracted
from a signature/checksum-verified package without system installation. Bateman
labels/weights are not presented as physical constants or calibrated confidence.
CX-001 steward topics and243 baselines remain unresolved for RADIX. TR opens the
single draft PR from codex/coherence-sector-prove-out into master; no merge.
