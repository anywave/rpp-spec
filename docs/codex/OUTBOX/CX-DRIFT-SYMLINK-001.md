---
id: CX-DRIFT-SYMLINK-001
from: Codex (rpp-spec)
to: TR
repo: anywave/rpp-spec
branch: codex/drift-symlink-guard
head: refs/heads/codex/drift-symlink-guard
head_kind: final-pushed-branch-ref
source_base: 21cfb0db3a9673abf80e3699c53402deae7248df
source_freeze: 0ae5b03dc119d6087ff3d98736e87b6aaf81a46b
date: 2026-11-02
type: report
subject: Skip unavailable Windows symlink fixture creation in the drift suite
---

TR's 16:05 inbox card is implemented on its named branch after the current
cards. I checked all twelve codex/LESSONS.md rules before this card and applied
the pre-push self-review checklist to the full merge-base diff. No shared status
document, production checker, catalog, tests/ tree, spec, header, layout,
constant, vector or Rust source is changed.

## Change and self-review

The only source change is tools/drift/tests/test_checker.py:273. The existing
test_incomplete_review_is_error[symlink] now catches symlink-creation OSError,
skips only on Windows, and re-raises on other platforms. The guard and skip
message match test_git_boundaries.py:121. Once fixture creation succeeds,
the existing ToolError assertion still checks the malformed committed input.
Syntax, binary and oversized inputs retain their previous behavior.

IMPOSED: copy the established platform-specific fixture guard; do not skip the
whole test or suppress unexpected POSIX failures. No new shipping test or
production behavior is needed for this bounded test-portability fix.
Source commit 0ae5b03 changes one file, +6/-1 lines.

## Actual results

BEFORE: Linux drift suite 311 passed / 0 failed / 0 skipped, exit 0.

AFTER: Linux drift suite 311 passed / 0 failed / 0 skipped, exit 0.

Both runs use Python 3.12.14 and this command, which continues collection and
executes all collected cases rather than stopping on the first failure:

```sh
python -m pytest -q -o addopts= --continue-on-collection-errors tools/drift/tests
```

The existing four incomplete-review cases separately pass 4/0. Targeted
Ruff 0.14.10 and git diff --check exit 0. Fresh root gates also pass: original
Python1256, golden5/0, Ruff0.14.10, 17 byte-identical corpora, four freshness
tests and lift9 manifests/57 sources/35 refs/0 findings. Six exact-BASE wrappers,
drift0/0/0 and whitespace pass. Final report-head checks run before the single
normal push. Rust is byte-identical to master; no broad rerun for this test edit.

## Finite portability counterproof

An outside-only harness invokes the actual existing test function in disposable
repositories. It rebinds only that test module's os reference to a finite
Windows/POSIX namespace and makes Path.symlink_to raise PermissionError(1314).
It does not change global os.name, production files or the real host platform.
The Windows case must report SKIP; the POSIX case must propagate the error.

Two named variants are refuted by terminal assertion failures: removing the
Windows guard, and swallowing the POSIX error. There are two passing baselines,
two failed selected witnesses, and two passing mutated unaffected controls.
Result: 2 killed / 0 survived. Tool/import errors and arbitrary exceptions are
not counted as kills. The harness and all six raw logs remain outside the repo.

Receipts are in /workspace/work/drift-symlink-evidence/: before.json, after.json,
counterproof.json and handoff.json; the handoff binds source and log hashes.
The root Python log hashes are bound in root-python-bound.json.
No byte-hashed artifact is added to the branch, so no attribute change is needed.

## Windows handoff

No native Windows run occurred here. TR's W-007 report supplied the historical
307 passed / 1 failed / 3 skipped comparison. The previously failing symlink
case should now skip when Windows cannot create it; that is not a native repeat
claim. From the branch, run the same suite command and check the process exit.
TR opens the PR; no merge, force push, ruleset change or new cryptography occurs.
