# Deterministic, advisory RPP drift review

Changes to addressing, routing and scope claims currently have no automated review against the
repository's written boundaries. This adds an independent `tools/drift/` coordinator with 15 explicit
syntactic/AST/source-guard rules, a source inventory, changed-only Boundary F baselines, deterministic
JSON/Markdown reports and report-only PR CI. It proposes review candidates, never changes the spec,
and leaves `rpp`, original tests, address layouts, the consent header and golden vectors unchanged.

## Validation

Exact commands and observed counts are recorded in [VALIDATION.md](https://github.com/anywave/rpp-spec/blob/codex/drift-coordinator/tools/drift/VALIDATION.md):

- `python -m pytest tools/drift/tests/ -q -o addopts=` — 66 passed.
- `python -m tools.drift.mutation_check` — SUMMARY killed=15 survived=0. Each rule has both a
  positive mutation and a clean control; suppressing each detector makes its positive assertion fail.
- `python -m pytest tests/ -q` — 1256 passed, 1 pre-existing legacy-format deprecation warning.
- `python tests/test_golden_vectors_mobius32.py` — SUMMARY pass=5 fail=0.
- `python -m tools.drift.history --master 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --output-dir tools/drift`
  — SUMMARY commits=30 high=8 medium=84 low=3.
- Two `python -m tools.drift check` runs for base `0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e`
  and head `b50609e6d69957e24dfd3d2df2325e4127cd05f5` returned exit 0 and no candidates.
  `cmp` returned 0 for both files. Both JSON SHA-256 values:
  `56ab51719da2643b6e53172e338dcd111077faa503bb3f8c80b8588893942fc7`.
  Both Markdown SHA-256 values:
  `2d791e039fbe0592667945c998bc70dc515bd4bd33aabeef05f893a42c7badbc`.
- `git diff --cached --check` — exit 0.

Hosted Actions was not observed. Hardware synthesis/simulation, Haskell/Clash, LaTeX and live
substrate/network integrations were not run because this is standalone static tooling. No target
historical code was executed. Existing pytest-asyncio scope notices remain visible.

## Interpretation limits and open questions

- Every implemented predicate is IMPOSED. The 2,280 full-meaning source-survey units (including
  explanatory statements/table rows) are listed as checkable: no; this is not semantic coverage
  of every possible change. Named rules check explicit syntactic subsets only.
- Radius API 0.0–1.0 and encoded 8-bit 0–255 have separate IMPOSED rules, as TR directed.
  The LOW range-label wording advisory is recorded without editing the policy.
- RADIX still owns the unresolved Boundary F baseline claims. Pure moves do not re-report them;
  text changes do. New physical dependency/claim wording uses explicit core/substrate file classes.
- The active-layer/deprecated-format lifecycle disagreement remains unresolved / checkable: no,
  with no document precedence selected, as TR authorized.
- Should later rollout widen the explicit file classes or rule predicates? This draft does not
  infer classes, enforce a merge gate, or resolve semantic questions automatically.

## Step 3 — historical self-check

Selection: last 30 reachable commits in Git rev-list order (including merges). Each is
compared with its first parent. Merged changes can therefore appear more than once.
Current coordinator rules apply retrospectively; findings are syntactic review candidates,
not adjudicated defects. Existing specifications and historical commits were not changed.

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
| a1b5ee6fd23b | 725347ed702a | 4 | 82 | 1 |
| 725347ed702a | f87314c0fd1f | 1 | 0 | 1 |
| f87314c0fd1f | 4eff1f96e2b2 | 0 | 0 | 0 |
| 4eff1f96e2b2 | 39d5fe351a80 | 0 | 0 | 0 |
| 39d5fe351a80 | 2082675e1a3a | 0 | 0 | 0 |
| 2082675e1a3a | c5d83b647a8a | 1 | 0 | 0 |
| c5d83b647a8a | c62d94183052 | 0 | 0 | 0 |
| c62d94183052 | a56fdf5b5ee6 | 0 | 0 | 0 |
| a56fdf5b5ee6 | 920aff68733a | 0 | 0 | 0 |
| 920aff68733a | 438f049178f4 | 0 | 0 | 0 |
| 438f049178f4 | ca1006d60934 | 0 | 0 | 0 |
| ca1006d60934 | ebf1f9a46ea9 | 0 | 0 | 0 |
| ebf1f9a46ea9 | ec58568980fd | 0 | 2 | 1 |
| ec58568980fd | 1dd4cc2fc14f | 0 | 0 | 0 |
| 1dd4cc2fc14f | 0486750a458a | 0 | 0 | 0 |
| 0486750a458a | 654eb36a68c0 | 0 | 0 | 0 |
| 654eb36a68c0 | 690936173283 | 0 | 0 | 0 |
| 690936173283 | 0f498e0afb30 | 0 | 0 | 0 |

## Every HIGH/MEDIUM finding

Full exact diff excerpts and source references are retained in `history.json`.

| Commit | Severity | Rule | Path | Line | Source | Tag |
|---|---|---|---|---:|---|---|
| 0a12c8dc311e | HIGH | VEC-1 | tests/test_golden_vectors_mobius32.py | 1 | VERSION_POLICY.md:299 | IMPOSED |
| 08721b89d546 | HIGH | VEC-1 | tests/test_golden_vectors_mobius32.py | 1 | VERSION_POLICY.md:299 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/CCQPSG.md | 24 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/CCQPSG.md | 335 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/NETWORK.md | 223 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | NET-INV-2 | rpp/network.py | 41 | spec/NETWORK.md:721 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 25 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 223 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 234 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 269 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 276 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 379 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 413 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 514 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 523 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 765 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 789 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 797 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 811 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 834 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 3 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 15 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 17 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 19 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 21 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 29 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 31 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 35 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 38 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 44 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 46 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 56 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 62 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 64 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 72 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 76 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 78 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 80 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 82 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 84 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 108 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 112 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 114 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 122 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 124 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 128 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 132 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 154 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 158 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 160 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 169 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 171 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 186 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 196 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 205 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 207 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 209 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 211 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 243 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 245 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 247 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 249 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 251 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 257 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 259 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 261 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 263 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 265 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 267 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 275 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 277 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 281 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 285 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 287 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 296 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 311 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 319 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 321 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 323 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 327 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 331 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 333 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 335 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 340 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 351 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 353 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 359 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 372 | spec/SPINTRONIC.md:21 | IMPOSED |
| 725347ed702a | HIGH | BND-F-1 | spec/SPEC.md | 54 | BOUNDARIES.md:98 | IMPOSED |
| 2082675e1a3a | HIGH | BND-F-1 | spec/ADDRESSING-LAYERS.md | 95 | BOUNDARIES.md:98 | IMPOSED |
| ebf1f9a46ea9 | MEDIUM | BND-F-2 | spec/SPEC-EXTENDED.md | 23 | spec/SPINTRONIC.md:21 | IMPOSED |
| ebf1f9a46ea9 | MEDIUM | BND-F-2 | spec/SPEC-EXTENDED.md | 617 | spec/SPINTRONIC.md:21 | IMPOSED |
