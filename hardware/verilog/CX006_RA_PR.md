# Make all RTL coherence score bindings match the existing Python policy

Two combinational scorers use faulty reciprocal/rounded-LUT arithmetic, producing
different scores and threshold decisions from the published 165/509 Python
policy. Replace those pipelines with a shared bounded integer calculation that
truncates each contribution separately. Keep public ports/constants and the
registered scorer, normalization formula and unrelated policy modules unchanged.

Actual Icarus evidence over 256 inputs × 12 thresholds: score differences
`0/3060/2940 → 0/0/0`; decision differences `0/967/345 → 0/0/0`.
Both axes have zero decreases. RA bench 33/33; three new hardware mutants killed
with three clean controls; four existing RA mutations killed. Two artifact
generation runs are byte-identical. Package tests 1256 passed; prove-out tests
54 passed; golden 5/0; Ruff 0.14.10 and whitespace exit 0.

See `CX006_RA_VALIDATION.md` for commands, hashes and the preserved normalized
maximum of 100. Historical CX-005 evidence is retained; consent derivation,
fallback and completion-flag steward topics remain unresolved.
