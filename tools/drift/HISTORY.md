# Historical drift review

Master snapshot: `0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e`.

Open baseline: 243; open steward items: 4; open LOW advisory groups: 2. All remain unresolved.

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

## Every HIGH/MEDIUM finding

Full exact diff excerpts and source references are retained in `history.json`.

| Commit | Severity | Rule | Path | Line | Source | Tag |
|---|---|---|---|---:|---|---|
| 0a12c8dc311e | HIGH | VEC-1 | tests/test_golden_vectors_mobius32.py | 1 | VERSION_POLICY.md:299 | IMPOSED |
| 08721b89d546 | HIGH | VEC-1 | tests/test_golden_vectors_mobius32.py | 1 | VERSION_POLICY.md:299 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/CONTINUITY.md | 321 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/CONTINUITY.md | 463 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/NETWORK.md | 734 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/SPINTRONIC.md | 19 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/SPINTRONIC.md | 108 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/SPINTRONIC.md | 275 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/SPINTRONIC.md | 287 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/SPINTRONIC.md | 288 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/SPINTRONIC.md | 298 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | BND-F-1 | spec/SPINTRONIC.md | 311 | BOUNDARIES.md:98 | IMPOSED |
| a1b5ee6fd23b | HIGH | NET-INV-2 | rpp/network.py | 41 | spec/NETWORK.md:721 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | CHANGELOG.md | 21 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | CHANGELOG.md | 22 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | CHANGELOG.md | 23 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | CHANGELOG.md | 24 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | CHANGELOG.md | 25 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | CHANGELOG.md | 26 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | CHANGELOG.md | 71 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | INTELLIGENCE_RIGHTS.md | 76 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | INTELLIGENCE_RIGHTS.md | 146 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | INTELLIGENCE_RIGHTS.md | 166 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | INTELLIGENCE_RIGHTS.md | 384 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | INTELLIGENCE_RIGHTS.md | 463 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | INTELLIGENCE_RIGHTS.md | 544 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | README.md | 35 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | README.md | 37 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | README.md | 420 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | RELATED_WORK.md | 243 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/continuity.py | 29 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/continuity.py | 30 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/continuity.py | 33 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/continuity.py | 40 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/continuity.py | 46 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/continuity.py | 65 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/continuity.py | 181 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/continuity.py | 269 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/geometry.py | 351 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/geometry.py | 719 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/network.py | 51 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/network.py | 100 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/network.py | 102 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/network.py | 134 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | rpp/network.py | 420 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CCQPSG.md | 102 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CCQPSG.md | 108 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CCQPSG.md | 303 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CCQPSG.md | 335 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 25 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 60 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 119 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 223 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 225 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 234 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 271 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 276 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 301 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/CONTINUITY.md | 502 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/DEPLOYABLE.md | 17 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/DEPLOYABLE.md | 396 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 379 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 417 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 514 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 525 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 530 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 604 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 699 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 771 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 772 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 786 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 789 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 797 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 803 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 804 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 811 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 835 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/GEOMETRY.md | 838 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 50 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 61 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 70 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 107 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 135 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 144 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 201 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 203 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 223 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 260 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 288 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 289 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 291 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 542 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/NETWORK.md | 690 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/PRIMER.md | 81 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/PRIMER.md | 141 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/PRIMER.md | 143 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/PRIMER.md | 153 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/PRIMER.md | 187 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/PRIMER.md | 215 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/PRIMER.md | 250 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/PRIMER.md | 255 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/PRIMER.md | 271 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/README.md | 68 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/README.md | 177 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/RESOLVER.md | 10 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/RESOLVER.md | 72 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/RESOLVER.md | 109 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/RESOLVER.md | 314 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/RESOLVER.md | 343 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/RESOLVER.md | 387 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/RESOLVER.md | 390 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/RESOLVER.md | 576 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/RESOLVER.md | 590 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/RESOLVER.md | 598 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 3 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 15 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 17 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 21 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 29 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 31 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 35 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 36 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 38 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 42 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 44 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 46 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 49 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 53 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 54 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 56 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 58 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 62 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 64 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 72 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 76 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 78 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 80 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 82 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 84 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 94 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 112 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 115 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 116 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 118 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 122 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 124 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 125 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 126 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 128 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 132 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 134 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 158 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 160 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 161 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 162 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 163 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 169 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 171 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 172 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 173 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 174 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 176 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 180 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 182 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 186 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 196 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 198 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 207 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 209 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 211 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 243 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 245 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 247 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 249 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 251 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 253 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 257 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 259 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 261 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 263 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 265 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 267 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 278 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 281 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 285 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 289 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 290 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 296 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 297 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 304 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 306 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 319 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 323 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 324 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 325 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 327 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 331 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 333 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 335 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 336 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 340 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 344 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 345 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 346 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 347 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 351 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 353 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 359 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 361 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 363 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 364 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 367 | spec/SPINTRONIC.md:21 | IMPOSED |
| a1b5ee6fd23b | MEDIUM | BND-F-2 | spec/SPINTRONIC.md | 372 | spec/SPINTRONIC.md:21 | IMPOSED |
| 725347ed702a | MEDIUM | BND-F-2 | spec/ADDRESSING-LAYERS.md | 28 | spec/SPINTRONIC.md:21 | IMPOSED |
| 725347ed702a | MEDIUM | BND-F-2 | spec/SPEC.md | 54 | spec/SPINTRONIC.md:21 | IMPOSED |
| 725347ed702a | MEDIUM | BND-F-2 | spec/SPEC.md | 92 | spec/SPINTRONIC.md:21 | IMPOSED |
| 725347ed702a | MEDIUM | BND-F-2 | spec/SPEC.md | 102 | spec/SPINTRONIC.md:21 | IMPOSED |
| 2082675e1a3a | MEDIUM | BND-F-2 | spec/ADDRESSING-LAYERS.md | 95 | spec/SPINTRONIC.md:21 | IMPOSED |
| 438f049178f4 | MEDIUM | BND-F-2 | MIGRATION_V2.md | 103 | spec/SPINTRONIC.md:21 | IMPOSED |
| 438f049178f4 | MEDIUM | BND-F-2 | MIGRATION_V2.md | 104 | spec/SPINTRONIC.md:21 | IMPOSED |
| 1dd4cc2fc14f | MEDIUM | BND-F-2 | MIGRATION_V2.md | 101 | spec/SPINTRONIC.md:21 | IMPOSED |
| 1dd4cc2fc14f | MEDIUM | BND-F-2 | MIGRATION_V2.md | 102 | spec/SPINTRONIC.md:21 | IMPOSED |
