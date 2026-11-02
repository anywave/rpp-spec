---
id: CX-TRUSTED-LINEAR-001
from: Codex (rpp-spec)
to: TR
repo: anywave/rpp-spec
branch: codex/drift-symlink-guard
head: refs/heads/codex/drift-symlink-guard
head_kind: final-pushed-branch-ref
source_base: 21cfb0db3a9673abf80e3699c53402deae7248df
implementation_branch: codex/ops3-trusted-linear
implementation_head: 8f19ec3f78ca55a83bc1c679173ff86e4a32a95b
date: 2026-11-02
type: report
subject: Republish the reviewed trusted gate as an exact linear stack
---

TR's 12:30 history ruling is implemented after the CX-026 integration push.
I checked all twelve rules in codex/LESSONS.md before this card and the full
BASE..HEAD diff using the anywave pre-push review skill. Existing BASE gate
code, allowlist, ruleset and shared status documents are unchanged.

The new branch starts at frozen master `21cfb0db3a9673abf80e3699c53402deae7248df`.
It adds only the eleven reviewed Git blobs from `678ada8f03ca5ad4f1cb8c2307944ce9b8cc0666`.
The owners file is the exact two-comment reviewed blob; no signer/key is added.
All base blobs, modes, Rust source, protected data and inherited reports remain
unchanged. Both introduced historical outboxes are preserved byte for byte.

IMPOSED report delivery: the exact eleven-file/1,472-line requirement leaves no
permitted new report path on the implementation branch. Editing either old
published outbox would also violate immutability. This NEW report therefore ships
on the later authorized portability-fix branch named in its front matter; the
implementation branch and exact head are recorded separately above. Nothing is
posted directly to trellis-channel. This is a delivery-format exception required
by the exact scope, not a size waiver or a request to change an old report.

## Linear commits

| Commit | Files | Added lines | Deleted lines |
| --- | --- | --- | --- |
| `8e139fbceb8900387def227d0baf14592da262cd` | 3 | 302 | 0 |
| `19660ef1a5c55b51c26ac8ece52f0f9bedd88537` | 1 | 310 | 0 |
| `e92340f9a1763b2faa9cc9b8b4d06e80ea2d7430` | 2 | 219 | 0 |
| `c852a0afc3fbb1f664c9afdfc7e21118a1125c34` | 2 | 340 | 0 |
| `8f19ec3f78ca55a83bc1c679173ff86e4a32a95b` | 3 | 301 | 0 |

There are exactly five new commits, each with one parent, zero merge commits,
and a unique merge base equal to the frozen master. Each is within 10 files /
400 changed lines. The full PR is exactly 11 added paths / 1,472 added lines.

## Requested equality output

This command compares the exact eleven paths, not unrelated newer master files:

```sh
git diff 678ada8 8f19ec3 -- .github/codex-gate-owners.txt .github/workflows/codex-gate-trusted.yml docs/codex/OUTBOX/CX-022B-001.md docs/codex/OUTBOX/CX-022C-001.md scripts/ci/test_gate_data_security.py scripts/ci/test_gate_graphs.py scripts/ci/test_gate_rules.py scripts/ci/test_merge_provenance.py scripts/ci/test_trusted_gate.py scripts/ci/test_trusted_workflow.py scripts/ci/trusted_gate.py
```

Verbatim stdout (zero bytes; successful exit 0):

```text
```

The empty output is saved as `trusted-linear-evidence/equality.log`; SHA256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Requested merge-base diff stat

```sh
git diff --stat 21cfb0db3a9673abf80e3699c53402deae7248df 8f19ec3f78ca55a83bc1c679173ff86e4a32a95b
```

Verbatim stdout:

```text
 .github/codex-gate-owners.txt            |   2 +
 .github/workflows/codex-gate-trusted.yml |  73 ++++++++
 docs/codex/OUTBOX/CX-022B-001.md         |  84 +++++++++
 docs/codex/OUTBOX/CX-022C-001.md         | 123 ++++++++++++
 scripts/ci/test_gate_data_security.py    | 193 +++++++++++++++++++
 scripts/ci/test_gate_graphs.py           | 147 +++++++++++++++
 scripts/ci/test_gate_rules.py            |  94 ++++++++++
 scripts/ci/test_merge_provenance.py      |  79 ++++++++
 scripts/ci/test_trusted_gate.py          | 310 +++++++++++++++++++++++++++++++
 scripts/ci/test_trusted_workflow.py      | 146 +++++++++++++++
 scripts/ci/trusted_gate.py               | 221 ++++++++++++++++++++++
 11 files changed, 1472 insertions(+)
```

The frozen master is the actual unique merge base; the eleven names above are
the complete net diff. Every introduced blob and file mode also equals 678ada8.

## Fresh validation and self-review

The exact composed gate suite freshly passes **60 tests / 0 failures**:

```sh
python -m unittest discover -s scripts/ci -p test_*.py -v
ruff check scripts/ci --ignore E501
```

The unit run uses the existing hash-pinned PyYAML environment. Ruff is exactly
0.14.10 and exits 0. The exact BASE-owned six wrappers, drift 0/0/0, whitespace
and 11/1472 cap checks pass on the frozen implementation head (root receipt).
This is local validation. The trusted hosted runner cannot approve its own
introduction; operator bootstrap and owner/App activation remain separate.

Fresh root Python gates pass: original1256, golden5/0, Ruff0.14.10, 17 fresh
corpora, four freshness tests and lift9 manifests/57 sources/35 refs/0 findings.
The main Rust tree equals master exactly. Its 94 blobs match the freshly tested
CX-026 main workspace:196/209/102/194 profiles, fmt, two Clippy and two RISC-V
builds pass. That is shared byte-identical source evidence, not a second run.

No new behavior or test was added. All prior named mutation witnesses are
preserved; this replay claims no new mutation executions or crypto proof.
Self-review checked the five parent relations, complete diff, exact blob/mode
identity, bounded commits, immutable reports and unchanged activation boundary.

Outside evidence:

| Receipt | SHA256 |
| --- | --- |
| `trusted-linear-evidence/replay.json` | `60e8d237bda3858f6df8e5b4292b6d88efa4f24a81143939d55131f4ac03270b` |
| `trusted-linear-evidence/focused-summary.json` | `b44c49e0222e4d77cf5698e151fd261a4da4406278b570f101d678605d516df5` |
| `trusted-linear-evidence/root-python-bound.json` | `33b7dbf7fa474c742a3cf6a726c857d37b980cc352198ba161995b944df8c0b8` |
| Independent replay source audit | `7996a39c2171a0064c7276737624ea0eb9e269764f5f1abf3db4cb8300d86f14` |
| Root equality/stat/Rust-source binding | `4318b0ddd5291ec39a7f04eb17c91e975648b125d365e282be708467031ef1a8` |

The normal push succeeded; git ls-remote verified remote head
`8f19ec3f78ca55a83bc1c679173ff86e4a32a95b`. TR opens the new PR as `[SUPERSEDES #35]`
and closes old #35 only after review. No force push, branch deletion, PR opening,
PR merge, signing operation or settings change is performed by this replay.
