# Revision round 1 — validation record

Implementation revision: `5424e95d4db56d3ca0c6cb892f243d1c4755d548`. Frozen specification/baseline revision: `0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e`.
Authority: TR inbox `anywave/trellis-channel`, `main`, `codex/inbox/rpp-spec.md`, observed
commit `7735c29f33e25188c8adc9a76561dc1ebf4a3522` (verified answer #2 and Q1/Q2). Only tooling and outbox files changed.
Application source, original tests, spec, address layouts, consent header and golden vectors
remain unchanged. Previously published outbox `CX-001-001.md` remains unchanged.

Commands ran from `/workspace/rpp-spec` with the retained Python 3.12 environment:

| Exact command | Observed result |
|---|---|
| `python -m pytest tools/drift/tests/ -q -o addopts=` | 168 passed |
| `python -m tools.drift.mutation_check` | SUMMARY killed=22 survived=0 |
| `python -m pytest tests/ -q` | 1256 passed, 1 pre-existing legacy-format deprecation warning |
| `python tests/test_golden_vectors_mobius32.py` | SUMMARY pass=5 fail=0 |
| `python -m tools.drift.snapshot` | SUMMARY scanned_paths=75 open_baselines=243 open_steward_items=4 open_advisories=2 |
| `python -m tools.drift.history --master 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --output-dir tools/drift` | SUMMARY commits=30 high=13 medium=209 low=3 |
| `git diff --cached --check` | exit 0 before implementation commit |

The snapshot reconstruction precedes the final source-survey render; catalog metadata also
records 2,281 full-meaning source-survey units. That count is not executable rule coverage.
Every one of the 22 executable rules has positive and clean-control fixtures; deleting each
detector in memory makes its positive assertion fail. No production source is mutated.

Existing pytest-asyncio fixture-loop-scope notices remain visible. Warnings were not suppressed.

## Windows portability evidence and limits

All file text I/O and subprocess text captures use explicit UTF-8. Git blob/path captures remain
explicit binary (`text=False`), decoded explicitly as UTF-8 to preserve Git blob bytes. POSIX
Git argv uses UTF-8 bytes under an ASCII filesystem codec; Windows keeps native Unicode argv.
The executable-bit fixture uses `git update-index --chmod=+x` with `core.filemode=false`.

The regression test launches the actual checker and history writers with `PYTHONUTF8=0`,
`-X utf8=0`, locale coercion disabled, C locale and default-encoding warnings promoted to errors.
It exercises a Unicode filename and UTF-8 report/history text. A static audit covers all tooling
text reads/writes and subprocess capture modes. Another test confirms catalog CRLF/JSON formatting
does not change report identity. These tests ran in Linux; native Windows 11/Python 3.13 was not run
in this cloud environment. TR can rerun the same commands on Windows; no Windows result is invented.

## Verified semantics exercised

- Passage-based Boundary F scope and exact physics/normative/qualifier lists; no file-based
  core/substrate classification. Markdown fences/list items/table rows and Python comments/
  docstrings are distinct. Arbitrary executable string values are excluded.
- Complete frozen scan: 75 paths and all 243 matching passages, reconstructed from Git blobs.
  LF, NFC, collapsed whitespace, trimmed UTF-8 SHA-256 identity; line is a hint. Moves and
  whitespace-only rewrapping remain separate from changed text, including cross-file moves.
- All seven software-MUST anchors are guarded. Baseline removal/nonphysics rewriting produces
  MEDIUM BND-F-BASELINE-REMOVED with old id/path/hint/hash; anchor loss independently stays HIGH.
- Open baseline count 243, separate MEDIUM steward count 4, LOW advisory-group count 2. All
  remain unresolved for RADIX, routed [RFC] via TR. Unchanged items do not dirty the exit status;
  changed cited passages are normal diff findings.
- v2 radius API and encoded contracts are SOURCED. The half-to-even clause is IMPOSED and has
  all three requested vectors: 1/510→0, 5/510→2, 0.5→128. GEOMETRY minor radius/Mobius32 are
  outside that scope; parl is separately checkable: no. All six LOW wording sites and the
  True/-0.0/negative-zero URI advisory are recorded without editing their sources.

## Two identical-input runs

```bash
python -m tools.drift check --base 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --head 5424e95d4db56d3ca0c6cb892f243d1c4755d548 --output-dir /tmp/cx001-round1-run-one
python -m tools.drift check --base 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e --head 5424e95d4db56d3ca0c6cb892f243d1c4755d548 --output-dir /tmp/cx001-round1-run-two
sha256sum /tmp/cx001-round1-run-one/drift-report.json /tmp/cx001-round1-run-two/drift-report.json /tmp/cx001-round1-run-one/drift-report.md /tmp/cx001-round1-run-two/drift-report.md
cmp /tmp/cx001-round1-run-one/drift-report.json /tmp/cx001-round1-run-two/drift-report.json
cmp /tmp/cx001-round1-run-one/drift-report.md /tmp/cx001-round1-run-two/drift-report.md
```

Both check runs: exit 0, diff high=0 medium=0 low=0; rules_run=22, rules_not_checkable=2281;
open_baselines=243, open_steward_items=4, open_advisories=2. Both cmp commands returned 0.

| File | First SHA-256 | Second SHA-256 |
|---|---|---|
| drift-report.json | 9599653757c54ed3a727ebc2273291795501908b5c133e9f2020c2a992f152a9 | 9599653757c54ed3a727ebc2273291795501908b5c133e9f2020c2a992f152a9 |
| drift-report.md | ed17025111a6669b4f9d820f39bbc40dcd0fe7af565798a35ec291834b29791d | ed17025111a6669b4f9d820f39bbc40dcd0fe7af565798a35ec291834b29791d |

Canonical catalog SHA-256: `ddf33ab9f33c6adc02486a3d99247f84627ab86c4cb1aa2f3696140d32172019`. Canonical JSON makes this identity
independent of the catalog worktree's CRLF/LF or pretty-print layout. The reviewed head is the
implementation commit before this validation record and outbox report are added; changing the
reviewed range changes commit metadata and therefore its report hashes.

## Historical findings and remaining limitations

[HISTORY.md](HISTORY.md) lists every HIGH/MEDIUM with its commit; [history.json](history.json)
retains full evidence, baseline events and unresolved items. The last 30 reachable commits include
merges, each against its first parent; counts can repeat merged changes and are not unique defects.
No historical target code was run and no historical finding was fixed.

Hosted Actions was not observed. FPGA/Verilog, Haskell/Clash, LaTeX and live substrate/network
integrations were not run: this revision changes standalone static tooling only. The existing
advisory read-only CI workflow remains unchanged. No api.github.com access, environment settings
change, lattice write, new PR, PR comment or PR-body update was performed by Codex.

No unanswered stop-and-ask remains. The four steward topics, two advisory groups and lifecycle
precedence remain unresolved as directed; no entry was accepted or silently closed. TR owns PR #4's
body update and any later RFC/steward decisions.
