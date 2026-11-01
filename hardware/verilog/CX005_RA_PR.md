# Correct RA testbench bands, encoded phi and failed-check exit status

The existing RA testbench expects medium coherence at an input whose Python
reference and RTL outputs are both low, and expects raw phi 3 from a fixture
whose encoded phi is 1. Correct those expectations while preserving the fixture
bytes and protocol implementation. Retain an explicitly implementation-only classification smoke probe, fix the
duplicate compile source list, and make any failed check exit nonzero.

Icarus 12.0: before 30/32 with runtime exit 0; after 33/33. Four executable
mutations killed, none survived. Package tests 1256 passed; golden 5/0;
Ruff 0.14.10 exit 0; whitespace exit 0. See `CX005_RA_VALIDATION.md` for exact
commands, classification limits and Windows repeats.

The HIGH RTL reciprocal-scaling and overflow defect remains unresolved. The
exact shift-only proposal is withheld and exercised on disposable copies: it
changes the bench to 32/33 with runtime exit 1, and is not a complete repair.
These testbench changes do not authorize a formula-agreement claim or adoption.
