# Deterministic advisory RPP drift coordinator — revision round 1

Changes to RPP scope/addressing claims now have independent static review tooling under
`tools/drift/`. This revision applies TR's verified passage-based Boundary F ruling, a complete
normalized Git-blob baseline, separate unchanged steward reporting, SOURCED radius contracts with
an IMPOSED half-to-even clause, and Windows UTF-8/index-mode fixes. The checker proposes findings;
application source, original tests, spec, address layouts, consent header and vectors are unchanged.
The existing SHA-pinned read-only PR CI remains advisory. TR maintains this PR body.

## Commands and counts

From the repository root with Python 3.12; full commands, scope and limitations are in
[VALIDATION.md](https://github.com/anywave/rpp-spec/blob/codex/drift-coordinator/tools/drift/VALIDATION.md).

- `python -m pytest tools/drift/tests/ -q -o addopts=` — **168 passed**.
- `python -m tools.drift.mutation_check` — **SUMMARY killed=22 survived=0**.
- `python -m pytest tests/ -q` — **1256 passed**, 1 pre-existing warning.
- `python tests/test_golden_vectors_mobius32.py` — **SUMMARY pass=5 fail=0**.
- `python -m tools.drift.snapshot` — **75 scanned paths, 243 open baseline passages,
  4 open MEDIUM steward items, 2 LOW advisory groups**.
- `python -m tools.drift.history --master 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --output-dir tools/drift`
  — **SUMMARY commits=30 high=13 medium=209 low=3**.
- Two `python -m tools.drift check` runs on `0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e..5424e95d4db56d3ca0c6cb892f243d1c4755d548` returned exit 0,
  diff high=0 medium=0 low=0, with unresolved counts displayed separately. Both cmp commands
  returned 0. Both JSON hashes: `9599653757c54ed3a727ebc2273291795501908b5c133e9f2020c2a992f152a9`. Both Markdown hashes: `ed17025111a6669b4f9d820f39bbc40dcd0fe7af565798a35ec291834b29791d`.
- `git diff --cached --check` — exit 0.

The UTF-8-disabled subprocess and `core.filemode=false` regressions ran locally on Linux.
Native Windows 11/Python 3.13 and hosted Actions were not run in this environment. Hardware,
Haskell, LaTeX and live substrate/network integrations were not run because no such source changed.
Historical code was never executed. Existing deprecation notices remain visible.

## Verified choices and unresolved decisions

The latest TR inbox at `7735c29f33e25188c8adc9a76561dc1ebf4a3522` supersedes earlier file-based F guidance.
All 243 baseline entries remain IMPOSED, unresolved for RADIX and routed [RFC] via TR.
Moves are separate events; removed/nonphysics-rewritten known passages produce MEDIUM
BND-F-BASELINE-REMOVED. Losing a software-MUST anchor remains HIGH. Unchanged MEDIUM steward
items do not affect exit status; changed passages are normal diff findings.

The four steward topics are Shell-0 software TTL, conflicting T2 bounds, conventional-hardware
physical claims, and fixed-0.5 versus shell/3.0 radius derivation. The radius API/byte contracts
are SOURCED; half-to-even is a separate IMPOSED clause with 1/510→0, 5/510→2, 0.5→128 vectors.
The six wording sites and True/-0.0/negative-zero URI case are LOW advisories. No source was fixed.
GEOMETRY minor radius, Mobius32 and unbundled parl are outside the v2 radius rule scope.
Lifecycle/deprecation precedence remains unresolved / checkable: no. No stop-and-ask is pending.

## Step 3 table

The last 30 reachable commits include merges, each against its first parent, so merged changes
can be counted twice. These are static candidates, not adjudicated unique defects. Every HIGH/
MEDIUM and its commit is listed in [HISTORY.md](https://github.com/anywave/rpp-spec/blob/codex/drift-coordinator/tools/drift/HISTORY.md);
[history.json](https://github.com/anywave/rpp-spec/blob/codex/drift-coordinator/tools/drift/history.json) retains all evidence.

| Commit | Parent | HIGH | MEDIUM | LOW |
|---|---|---:|---:|---:|
| 0a12c8dc311e | e4e50a4893e3 | 1 | 0 | 0 |
| 08721b89d546 | e4e50a4893e3 | 1 | 0 | 0 |
| e4e50a4893e3 | 214ad1df4d91 | 0 | 0 | 0 |
| 4e717c7d74ba | 214ad1df4d91 | 0 | 0 | 0 |
| 214ad1df4d91 | a1b5ee6fd23b | 0 | 0 | 0 |
| 15b6517d7e46 | 5728570d9475 | 0 | 0 | 0 |
| 5728570d9475 | 12285fd2a8a8 | 0 | 0 | 0 |
| 12285fd2a8a8 | c897a7a61e95 | 0 | 0 | 0 |
| c897a7a61e95 | a1b5ee6fd23b | 0 | 0 | 0 |
| 6d45a7113089 | 1a3434eb5c36 | 0 | 0 | 0 |
| 1a3434eb5c36 | 1c54b8256f1d | 0 | 0 | 0 |
| 1c54b8256f1d | a1b5ee6fd23b | 0 | 0 | 0 |
| a1b5ee6fd23b | 725347ed702a | 11 | 200 | 1 |
| 725347ed702a | f87314c0fd1f | 0 | 4 | 1 |
| f87314c0fd1f | 4eff1f96e2b2 | 0 | 0 | 0 |
| 4eff1f96e2b2 | 39d5fe351a80 | 0 | 0 | 0 |
| 39d5fe351a80 | 2082675e1a3a | 0 | 0 | 0 |
| 2082675e1a3a | c5d83b647a8a | 0 | 1 | 0 |
| c5d83b647a8a | c62d94183052 | 0 | 0 | 0 |
| c62d94183052 | a56fdf5b5ee6 | 0 | 0 | 0 |
| a56fdf5b5ee6 | 920aff68733a | 0 | 0 | 0 |
| 920aff68733a | 438f049178f4 | 0 | 0 | 0 |
| 438f049178f4 | ca1006d60934 | 0 | 2 | 0 |
| ca1006d60934 | ebf1f9a46ea9 | 0 | 0 | 0 |
| ebf1f9a46ea9 | ec58568980fd | 0 | 0 | 1 |
| ec58568980fd | 1dd4cc2fc14f | 0 | 0 | 0 |
| 1dd4cc2fc14f | 0486750a458a | 0 | 2 | 0 |
| 0486750a458a | 654eb36a68c0 | 0 | 0 | 0 |
| 654eb36a68c0 | 690936173283 | 0 | 0 | 0 |
| 690936173283 | 0f498e0afb30 | 0 | 0 | 0 |
