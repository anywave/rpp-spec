# Deterministic drift coordinator

This extension reviews two Git trees against explicit predicates. It emits review
candidates and never changes the specification, imports target code, executes
target tests, calls a model or performs network operations. Use Python 3.12+ and
Git; pytest is needed only for coordinator tests. Use the existing checkout;
cloud tasks are already isolated and need no new worktree.

```bash
source /workspace/venvs/rpp-spec/bin/activate
cd /workspace/rpp-spec
python -m tools.drift check --base BASE_SHA --head HEAD_SHA --output-dir /tmp/drift-review
```

Use hexadecimal commit IDs. The default output directory is the current working
directory. The command owns and replaces only `drift-report.json` and
`drift-report.md`; use a dedicated directory. Old reports are removed before a
new review so a tool error cannot leave stale successful output.

Exit 0 means no HIGH/MEDIUM **diff findings**, 1 means HIGH/MEDIUM diff findings,
and 2 means incomplete review/tool error. LOW findings remain visible with exit
0. Unchanged unresolved baselines, steward items and advisories never silently
make the diff dirty. An empty finding list means no configured predicate matched,
not universal semantic compliance. Findings sort HIGH/MEDIUM/LOW, then rule ID,
path and line. Deletion lines belong to base, addition lines to head.

The JSON report includes findings, summaries, resolved commit IDs, normalized
baseline movement/change events, separate unresolved items and a catalog hash.
The catalog hash uses canonical JSON, so worktree CRLF and JSON formatting do not
change it. Markdown retains the findings and unresolved item information with
escaped diff text. There are no clocks, random values or absolute working paths.

[RULES.md](RULES.md) contains the verified source/interpretation inventory,
exact matching lists, all software-MUST anchors, all 75 scanned paths and the
complete 243-passage Boundary F baseline at `0a12c8d`. `catalog.json` is its
machine-readable companion. These numbers describe the frozen scan, not coverage
of every possible future change.

Boundary F is **passage-based**, not file-based: root Markdown, spec Markdown,
and Python comments/docstrings under `rpp/`. Markdown passages include separate
paragraphs, list items, table rows and complete code fences. Other files and
executable Python string values have no Boundary F predicate. The verified
physics/normative/qualifier lists are explicit in RULES.md. Bare quantum,
coherence, resonance, substrate, hardware and physical do not count as physics
terms. Lowercase “must” alone is not a normative marker.

Baseline hashes come from Git blobs: LF, Unicode NFC, collapsed whitespace,
trimmed, then SHA-256 of UTF-8. Equal hashes match by occurrence, including moves
across scanned files. Moves are reported separately from changed text and do not
count as drift. Deleting/rewriting a known baseline without physics wording emits
MEDIUM `BND-F-BASELINE-REMOVED`, with its old id/path/line hint/hash. Loss of a
software-MUST anchor is independently HIGH. All entries remain IMPOSED,
`unresolved - steward decision (RADIX)`, routed `[RFC]` via TR under
GOVERNANCE.md:63-71. The open count is printed every check; no entry is accepted.

Four separate MEDIUM steward items cover Shell-0 software TTL, T2 bounds,
conventional-hardware physical claims and conflicting v1→v2 radius derivation.
They appear under “Open steward items (unchanged)” and in the open count. Editing
one of their cited passages yields a normal diff finding. Two LOW advisory groups
cover six radius wording sites and the True/-0.0/negative-zero URI behavior.
Neither grouping changes application code or resolves the steward's decision.

The v2 normalized radius and encoded byte contracts are **SOURCED**. The separate
Python half-to-even clause is **IMPOSED**, with vectors `1/510 -> 0`, `5/510 -> 2`,
`0.5 -> 128`. Scope excludes GEOMETRY's minor radius, Mobius32 and unbundled parl.
The v1.0 deprecation disagreement remains unresolved / checkable: no.

Other syntactic predicates retain their explicit text/AST/vector-path scopes.
Reviewed blobs must be UTF-8 and regular Git files; protected Python syntax
errors, unreadable objects, reviewed blobs over 4 MiB and reviewed diffs over
16 MiB are tool errors. Unclassified assets such as PDFs have no content predicate.
Word-claim review excludes `tools/drift/`, whose inventory/fixtures quote sources.

All text file I/O and subprocess text captures use explicit UTF-8. Git blobs and
NUL-delimited path lists use explicit binary transport and explicit UTF-8 decoding,
preserving Git blob bytes; POSIX Git argv uses UTF-8 bytes even with an ASCII
filesystem codec, and Windows uses native Unicode argv. Reports/history use LF.

```bash
python -m pytest tools/drift/tests/ -q -o addopts=
python -m tools.drift.mutation_check
python -m pytest tests/ -q
python tests/test_golden_vectors_mobius32.py
```

Each executable rule has a positive source mutation and a clean control. The
mutation runner deletes each detector in memory and requires its positive test
to fail. Fixtures use disposable local Git repositories and do not modify original
source or golden vectors. Portability tests use index mode changes with
`core.filemode=false`, explicit UTF-8 I/O auditing, and a subprocess with
`PYTHONUTF8=0`, locale coercion disabled and default-encoding warnings as errors.
Unicode report/history files are exercised; this is not a claim of a native
Windows execution in the Linux cloud environment.

```bash
python -m tools.drift.snapshot
python -m tools.drift.history \
  --master 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e \
  --output-dir /tmp/drift-history
```

The snapshot command reconstructs the complete frozen scan and updates only
`tools/drift/catalog.json`. Its tests compare every path and entry with Git blobs.
Review updated rule/source metadata and RULES.md before committing catalog edits.
[HISTORY.md](HISTORY.md) lists counts for all 30 reachable commits and every
HIGH/MEDIUM finding with its commit; [history.json](history.json) retains evidence,
baseline events and unresolved items. Merges use first parent and can repeat
changes already counted on their branches. Historical target code is never run.
[VALIDATION.md](VALIDATION.md) records the actual tested range, counts and hashes.

The SHA-pinned read-only `.github/workflows/drift.yml` remains advisory. It posts
only the Markdown job summary, makes no PR comments and does not enforce a merge
gate. Hosted CI results must be observed separately from local commands.

## TR inbox and immutable outbox

At the start of every task, and before acting on a stop-and-ask answer, read
`anywave/trellis-channel`, branch `main`, `codex/inbox/rpp-spec.md` using read-only
Git access. The newest dated TR entry wins over older entries and chat. If the
file is absent, follow chat. Never write to trellis-channel or change environment
network settings for this task. No api.github.com access is needed; TR maintains
PR #4's description.

For each substantive report, finished step or stop-and-ask, add one new
`docs/codex/OUTBOX/CX-001-<nnn>.md` on `codex/drift-coordinator`, using the standing
frontmatter format. Include exact commands/counts, the described commit and open
questions. Commit and push only that branch. Never edit/delete a pushed outbox
file; issue a new numbered correction. TR relays outbox files to the lattice.
