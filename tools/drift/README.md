# Deterministic drift coordinator

This extension reviews two Git trees against explicit rules. It proposes review
candidates and never edits the specification. It uses Python 3.12, Git and the
standard library. Pytest is needed only for the coordinator's tests.

From the existing repository checkout (no new worktree is needed):

```bash
source /workspace/venvs/rpp-spec/bin/activate
cd /workspace/rpp-spec
python -m tools.drift check --base BASE_SHA --head HEAD_SHA --output-dir /tmp/drift-review
```

Replace the two placeholders with hexadecimal commit IDs. The default output
directory is the current directory. The command writes `drift-report.json` and
`drift-report.md`, overwriting only those two named report files. A new invocation
removes its previous reports before evaluation so an error cannot leave stale
successful output. Use a dedicated output directory.

Exit statuses: 0 means no HIGH/MEDIUM candidates; 1 means drift candidates; 2
means an incomplete review or tool error. LOW findings still appear with exit 0.
An empty finding list means no configured predicates matched, not full semantic
compliance. Findings sort HIGH/MEDIUM/LOW, then rule ID, path and line. Deletion
coordinates belong to the base; addition coordinates belong to the head.

The JSON object contains the finding list, summary, resolved commit IDs and the
catalog hash. Each finding has `rule_id`, `severity`, `path`, `line`, exact diff
`evidence`, `source`, and `tag`. Evidence may include a separately labelled
coordinator explanation. Markdown includes the same information with escaped
diff text. No timestamps, network, inference, randomness, target imports, target
test execution or checkout changes participate in evaluation.

[RULES.md](RULES.md) inventories the source statements, exact scopes, regexes,
AST projections, interpretation limits and unresolved baseline passages.
`catalog.json` is the machine-readable set of rules, source guards and baselines.
All implemented rules are IMPOSED: the syntactic predicate is an interpretation,
even when its source is quoted exactly. The radius API and encoded field have
separate rules. The v1.0 deprecation disagreement remains unresolved, with no
precedence selected. Existing Boundary F tensions remain unresolved for RADIX.

Only documented path classes are content-reviewed. Unclassified files, including
PDFs and other assets, have no content predicates. Reviewed source must be UTF-8;
malformed Python in protected AST paths, nonregular review blobs, oversized
review sources (>4 MiB) or reviewed diffs (>16 MiB) cause exit 2. Word-claim
review excludes `tools/drift/` because its inventory, fixtures and reports quote
source claims rather than making product claims. Physical terms in unclassified
documents are inventory-only. These are explicit limits, not inferred exemptions.

Tests and detector-deletion checks:

```bash
python -m pytest tools/drift/tests/ -q -o addopts=
python -m tools.drift.mutation_check
python -m pytest tests/ -q
python tests/test_golden_vectors_mobius32.py
```

Every executable rule has a positive source mutation and a clean control in
`tests/test_checker.py`. For example, changing a core address shift without a
specification major increase triggers VER-FORMAT-1; changing only its comment
does not. The mutation runner suppresses one detector's findings in memory and
requires that rule's positive test to fail with an assertion. It never modifies
core files, tests, vectors or the checker on disk. Additional tests cover baseline
edits/deletions/moves, exact software-MUST weakening, major-version treatment,
golden-vector renames/mode changes, deterministic files, escaping and errors.

Historical self-check, pinned to the requested master snapshot:

```bash
python -m tools.drift.history \
  --master 0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e \
  --output-dir /tmp/drift-history
```

[HISTORY.md](HISTORY.md) contains all 30 commit counts and every HIGH/MEDIUM
candidate with its commit. [history.json](history.json) retains complete evidence
for all findings. The selection is the last 30 reachable commits in `git rev-list`
order, including merges, each against its first parent. Merged changes can be
counted twice; this is not a unique-defect count. No historical finding was fixed.

`.github/workflows/drift.yml` runs on PRs into master with SHA-pinned actions,
read-only repository permissions and no stored checkout credentials. It uses the
actual PR base/head SHAs and publishes Markdown to the job summary. It does not
post comments, create issues or enforce a merge gate. Tool errors are explicitly
shown as incomplete review; neither findings nor errors block the advisory job.
The CI job also runs the coordinator fixtures. Hosted CI execution must be
observed separately from the local checks.

When adding a rule, record the source sentence and scope, add an explicit positive
and negative mutation fixture, update the catalog, and rerun the detector-deletion
check. Do not rewrite the specification or widen a predicate silently. New source
baselines require a new reviewed source revision and updated exact citations.
