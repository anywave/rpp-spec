# CX-004 Part A — final validation and READY record

**READY** at validated implementation `1bc6efd9ffdc19ede929d11a2394d5c9357be1b7`. The following documentation commit adds this
record, PR handoff and CX-004-001; code/catalog are unchanged by that commit. Source/baseline
revision remains `0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e`. Authority is the CX-004 inbox at `d9214588220854667692ad5614d355763360133d`.
READY describes the reviewed coordinator implementation; TR still needs green required hosted
checks at the merge candidate and owns every merge. No hosted result for this new head is invented.

## Exact commands and observed results

All commands ran from /workspace/rpp-spec with the retained Python 3.12 environment.

| Command | Result |
|---|---|
| `python -m pytest tools/drift/tests/ -q -o addopts=` | **269 passed** |
| `python -m tools.drift.mutation_check` | **SUMMARY killed=40 survived=0 rule_mutants=22 branch_mutants=18**; **CONTROLS passed=40 failed=0** |
| `python -m tools.drift.snapshot` | **scanned_paths=75 open_baselines=243 open_steward_items=4 open_advisories=2** |
| `python -m tools.drift.history --master 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --output-dir tools/drift` | **commits=30 high=13 medium=209 low=3** |
| `PYTHONPATH=/workspace/rpp-spec python -m pytest tests/ -q` | **1256 passed**, 1 pre-existing warning |
| `PYTHONPATH=/workspace/rpp-spec python tests/test_golden_vectors_mobius32.py` | **SUMMARY pass=5 fail=0** |
| `python /tmp/cx001-readiness-repro/repro.py` | **cases=2 passed=2 failed=0**, exit 0 |
| `git diff --check` and staged/diff checks | exit 0 |

The 30-commit counts are **unchanged** from CX-001-002 (13/209/3, delta 0/0/0). The historical
ranges do not contain the new adversarial interaction; the new tests do. Canonical evidence and
catalog identity changed as documented, not the historical count. Merges use first parent and
can repeat changes. Complete evidence is in HISTORY.md/history.json; no historical source was fixed.

Every existing rule now has a positive **and** clean mutation target; 18 algorithm/Git/schema/path
branches have the same paired evidence. A kill requires exactly the targeted AssertionError failure
and a passing clean control; stale mutation anchors, collection errors and setup errors are rejected.
Trusted coordinator code is mutated only in memory, never target or production files on disk.
All new tests name mutations that would make their assertions fail.

## A1/A2 passage correction and imposed choices

Exact normalized hashes pair first (same path before cross-file moves). Otherwise replacement is a
unique one-old/one-new connected component from atomic Git edit spans and unchanged LF-line maps,
with matching path, passage kind and structural owner. All units, including nonphysics ones,
participate; another passage in a hunk cannot lend physics/normative/qualifier scope. Heading
hierarchies and Python class/function names define structural owners, not semantic similarity.

IMPOSED stricter choices: split/merge or multi-unit components, kind/owner changes and changed-text
renames retain removal findings and classify new physics wording separately. Equal-hash rewrapping
and owner/end-line changes are moved events, even with unchanged start line. No baseline is accepted.
The graph uses indexed exact coordinates and star unions for the same components without quadratic
all-pairs joins. These implementation details do not add a new semantic matching heuristic.

The committed matrix is in tests/test_boundary_interactions.py: **30 A2 parameter cases plus four
in-process I/O controls, 34 passed**. Additional path/Git tests and 39 catalog-error cases bring the
full suite to 269. All seven software-MUST anchors remain independently HIGH when lost.

## A4 adversarial self-review

Reviewed the complete 0a12c8d..1bc6efd9ffdc19ede929d11a2394d5c9357be1b7 diff and final source. No remaining concrete material defect was
found in the scoped review after addressing:

- same-hunk replacement borrowing; split/merge/type/owner ambiguity; normalized cross-file identity;
- Git color and binary diff attributes that could suppress findings; LF-only line parsing,
  canonical prefixes/algorithm/captions and atomic edit coordinates;
- WORD-only Markdown paths bypassing regular-file/NUL/UTF-8/size checks;
- malformed/zero-rule catalogs returning false clean or wrong status, unresolved-status and
  SOURCED/IMPOSED invariants, stable canonical catalog identity;
- valid repository paths with trailing whitespace; literal, spaced and Unicode paths; symlinks;
- statuses 0/1/2, stale-report cleanup, severity/id/path/line ordering, escaped evidence;
- drift.yml's read-only permissions, pinned actions, full fetch and nonpersistent credentials.

The drift workflow remains intentionally advisory and exposes tool errors in its summary. Part B
restores the separate main CI lint gate. Application source, original tests, spec, layouts, header,
vectors, constants and published CX-001 outboxes remain unchanged on this branch.

## Identical-input runs

```bash
python -m tools.drift check --base 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --head 1bc6efd9ffdc19ede929d11a2394d5c9357be1b7 --output-dir /tmp/cx004-a3-run-one
python -m tools.drift check --base 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --head 1bc6efd9ffdc19ede929d11a2394d5c9357be1b7 --output-dir /tmp/cx004-a3-run-two
sha256sum /tmp/cx004-a3-run-one/drift-report.json /tmp/cx004-a3-run-two/drift-report.json /tmp/cx004-a3-run-one/drift-report.md /tmp/cx004-a3-run-two/drift-report.md
cmp /tmp/cx004-a3-run-one/drift-report.json /tmp/cx004-a3-run-two/drift-report.json
cmp /tmp/cx004-a3-run-one/drift-report.md /tmp/cx004-a3-run-two/drift-report.md
```

Both checks exit 0, diff high=0 medium=0 low=0, 22 rules, 2281 full-meaning survey units;
243 baseline entries, 4 steward items and 2 advisory groups remain unresolved. Both cmp commands exit 0.

| File | Run 1 SHA-256 | Run 2 SHA-256 |
|---|---|---|
| JSON | beee977a6c3589d05365fd0ed5475757b81900861d04d37616d24f094acea007 | beee977a6c3589d05365fd0ed5475757b81900861d04d37616d24f094acea007 |
| Markdown | e22ae9b29deb19a2545029166ee0c6399c662a770d85ee8ff3bbb104b02460be | e22ae9b29deb19a2545029166ee0c6399c662a770d85ee8ff3bbb104b02460be |

Canonical catalog identity: `b69bc6f3d30eff3add7ba530942d4082cc3ac1d79727fee665ab16dd735df6ce`. The pinned input head precedes the
report/documentation commit; reviewing another head changes its metadata/hashes as expected.

## Not run / TR repeat

Native Windows 11/Python 3.13 and hosted CI at the new head were not run here. TR should repeat
all commands in the results table on Windows, plus the two pinned-range check/cmp runs. Two actual
POSIX trailing-space/CR-directory integration cases skip on Windows with explicit filesystem
reasons; their pure root-parser controls remain cross-platform, including the 40-mutation check.
No new Windows count is asserted. Existing legacy-format and pytest-asyncio notices stay visible.

The radius derivation, four steward items, lifecycle issue and 243 baseline claims stay with RADIX.
Part C's physical/biological claims are not endorsed by simulations. No merge, new PR, API call,
environment change or lattice post is performed; TR opens the two new draft PRs and updates PR #4.
