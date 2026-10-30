# Validation record

Commands ran from `/workspace/rpp-spec` using the retained Python 3.12 virtual environment.
The application source, original tests, address layouts, consent header and golden vectors are
unchanged relative to `0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e`.

| Command | Observed result |
|---|---|
| `python -m pytest tools/drift/tests/ -q -o addopts=` | 66 passed |
| `python -m tools.drift.mutation_check` | SUMMARY killed=15 survived=0 (each detector deletion causes its positive assertion to fail) |
| `python -m pytest tests/ -q` | 1256 passed, 1 pre-existing legacy-format deprecation warning |
| `python tests/test_golden_vectors_mobius32.py` | SUMMARY pass=5 fail=0 |
| `python -m tools.drift.history --master 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --output-dir tools/drift` | SUMMARY commits=30 high=8 medium=84 low=3 |
| `git diff --cached --check` | exit 0 |

Pytest also emits the existing pytest-asyncio default fixture-loop-scope deprecation notice.
These notices were not suppressed and repository configuration was not changed to hide them.

## Byte-for-byte check

Both invocations reviewed the exact same range with the exact same coordinator catalog:

```bash
python -m tools.drift check --base 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --head b50609e6d69957e24dfd3d2df2325e4127cd05f5 --output-dir /tmp/drift-run-one
python -m tools.drift check --base 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --head b50609e6d69957e24dfd3d2df2325e4127cd05f5 --output-dir /tmp/drift-run-two
sha256sum /tmp/drift-run-one/drift-report.json /tmp/drift-run-two/drift-report.json /tmp/drift-run-one/drift-report.md /tmp/drift-run-two/drift-report.md
cmp /tmp/drift-run-one/drift-report.json /tmp/drift-run-two/drift-report.json
cmp /tmp/drift-run-one/drift-report.md /tmp/drift-run-two/drift-report.md
```

Both runs: exit 0, high=0 medium=0 low=0; rules_run=15, rules_not_checkable=2280.
The latter count inventories full-meaning source statements, including explanatory prose and table
rows; it is not a count of independently detected defects or executable checks.

| File | First SHA-256 | Second SHA-256 |
|---|---|---|
| drift-report.json | 56ab51719da2643b6e53172e338dcd111077faa503bb3f8c80b8588893942fc7 | 56ab51719da2643b6e53172e338dcd111077faa503bb3f8c80b8588893942fc7 |
| drift-report.md | 2d791e039fbe0592667945c998bc70dc515bd4bd33aabeef05f893a42c7badbc | 2d791e039fbe0592667945c998bc70dc515bd4bd33aabeef05f893a42c7badbc |

Both `cmp` commands returned 0. Catalog SHA-256:
`7ed58588e9abd21ff406ae075c29cc7c04b8cecb17682e1dfbb25349bd444552`.
The pinned range ends at the implementation commit, before this validation record is added;
changing the range changes the commit metadata and therefore the report hashes.

## Not run / limits

- Hosted GitHub Actions has not been observed; the new workflow was checked locally for pinned
  actions, read-only permissions, advisory behavior and command compatibility.
- No FPGA synthesis/simulation, Haskell/Clash, LaTeX or live network/substrate integrations:
  the coordinator is standalone tooling and those sources were not changed.
- Target historical code was never imported or executed. Historical results come from static
  predicates; negations and equivalently rewritten code can be conservative review candidates.
- Lifecycle/deprecation precedence remains unresolved, as TR directed. Physical baseline claims
  remain unresolved for RADIX. No source passage was rewritten to settle either issue.
