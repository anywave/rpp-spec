# Pair drift findings by passage and keep review deterministic

PR #4 adds an independent deterministic drift coordinator. The final revision removes hunk-wide
physics borrowing: replacement now needs a unique same-kind/owner passage correspondence from
exact edit spans and unchanged lines. It also addresses adversarial Git color/attribute handling,
reviewed-file validation, invalid catalogs and whitespace-bearing paths. Ambiguous cases emit the
stricter findings; no RPP source, original tests, spec, layouts, constants, headers or vectors change.

**READY** at `1bc6efd9ffdc19ede929d11a2394d5c9357be1b7` after the complete local validation and adversarial self-review. Required hosted
checks must still be green on the merge candidate; TR merges only after the independent lint repair.

- `python -m pytest tools/drift/tests/ -q -o addopts=`: **269 passed**.
- `python -m tools.drift.mutation_check`: **40 killed, 0 survived**, all **40 clean controls passed**
  (22 rules +18 algorithm/Git/schema/path branches).
- `python -m tools.drift.snapshot`: **75 files, 243 open baselines, 4 steward items, 2 advisory groups**.
- Last 30 master commits: **13 HIGH, 209 MEDIUM, 3 LOW**, unchanged from CX-001-002; every HIGH/MEDIUM
  has commit and evidence in HISTORY.md/history.json. No finding was silently fixed.
- `python -m pytest tests/ -q`: **1256 passed**; standalone golden vectors: **pass=5 fail=0**.
- `git diff --check`: exit 0. Original two-case blocker reproduction: **2 passed, 0 failed**.
- Two runs on `0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e..1bc6efd9ffdc19ede929d11a2394d5c9357be1b7`: both exit 0, both cmp commands exit 0.
  JSON SHA-256 both `beee977a6c3589d05365fd0ed5475757b81900861d04d37616d24f094acea007`; Markdown SHA-256 both `e22ae9b29deb19a2545029166ee0c6399c662a770d85ee8ff3bbb104b02460be`.

See VALIDATION.md for exact commands and limits, RULES.md for predicates/IMPOSED choices and the
full baseline, and CX-004-001 for the A2 matrix and all three branch handoffs. No entry is accepted;
unchanged unresolved items are visible without dirtying the exit. Radius API/byte rules remain
SOURCED, half-to-even IMPOSED; the steward/lifecycle topics remain RADIX's.

Native Windows at this new head and hosted CI remain for TR; repeat the documented suite,
mutations and identical-input checks on Windows 11/Python 3.13. Two POSIX-only path tests have
explicit Windows skips, with cross-platform pure controls. The drift job stays advisory, pinned
and read-only. The separate codex/ci-lint-001 PR pins Ruff0.14.10, clears19 findings and restores
main lint as a gate; no lint source cleanup is bundled here. No physical claim or page readout is added.
