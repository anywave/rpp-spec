# CX-007 catalog revision 2 — validation

Date: 2026-11-01. Branch: `codex/catalog-rulings-2026-11-01`.
Base and ruled-source revision: `5677ea21b5ba3320109dc7dcb61d4b4c22b5881a`.
Authority: RADIX's CX-007 release in `anywave/trellis-channel`,
`codex/inbox/rpp-spec.md` at `c098c20e`, inbox blob
`1b01db5d154c6b237324f7fe5ad779b3ea1154c7`.

The original 75-path scan remains pinned to `0a12c8d`. The deterministic snapshot
reconstructs that original catalog and layers only the released CX-006 decisions
over it. No specification, application Python, layout, header, golden vector,
published constant or existing outbox changes.

## Status and scope

- **239 review-pending/open baseline entries** preserve every original field,
  including the raw `unresolved - steward decision (RADIX)` status. The external
  review register supplies the review-pending label; there is no bulk status change.
- **4 ruled baseline entries** retain their complete original objects and gain
  current text/hash, pinned source revision and exact RFC decision references.
- **4 decided steward items**, **A1 decided**, **A2 open**. Their updated cited
  passages stay watched; decided status never skips a detector.
- **7 software-MUST anchors unchanged**; 22 rules and the original 2281
  not-checkable survey count remain unchanged.
- Exactly **2 A1 guard blocks** change only approved wording. Source table
  assertions preserve fields, shifts, widths and min/max ranges.
- All **20** CX-006 findings are retained as a ruling ledger with exact old/new
  passages and `DECISIONS.md` section text/hash, ID, line, authority and date.

The canonical restored-foundation fingerprint is
`b69bc6f3d30eff3add7ba530942d4082cc3ac1d79727fee665ab16dd735df6ce`;
the canonical approved-overlay fingerprint is
`fae35d63cce3e11f363cba32fb7617c112040e3e819aefe4ff33c39c870e4868`.
These hash logical canonical JSON, so checkout CRLF/formatting does not alter
their identity. The first rejects any unrelated re-baseline or status change;
the second rejects altered approvals, after-identities or decision provenance.

## Exact finding → ruling ledger

These are recorded historical consequences, not current diff findings or global
waivers. Source line hints identify the CX-006 finding; decision lines identify
the pinned RFC record.

| Severity | Rule | Finding path:line | RADIX ruling / exact RFC reference |
|---|---|---|---|
| HIGH | `VER-FORMAT-1` | `VERSION_POLICY.md:70` | `CX-006-A1` — `DECISIONS.md:170` |
| HIGH | `VER-FORMAT-1` | `VERSION_POLICY.md:83` | `CX-006-A1` — `DECISIONS.md:170` |
| MEDIUM | `BND-F-2` | `DECISIONS.md:78` | `CX-006-D3` — `DECISIONS.md:76` |
| MEDIUM | `BND-F-2` | `spec/SPINTRONIC.md:288` | `CX-006-D3` — `DECISIONS.md:76` |
| MEDIUM | `BND-F-2` | `spec/SPINTRONIC.md:311` | `CX-006-D3` — `DECISIONS.md:76` |
| MEDIUM | `BND-F-BASELINE-REMOVED` | `rpp/continuity.py:276` | `CX-006-D4` — `DECISIONS.md:86` |
| MEDIUM | `BND-F-BASELINE-REMOVED` | `spec/CCQPSG.md:108` | `CX-006-D2` — `DECISIONS.md:58` |
| MEDIUM | `STEWARD-CLAIM-1` | `rpp/continuity.py:276` | `CX-006-D4` — `DECISIONS.md:86` |
| MEDIUM | `STEWARD-RADIUS-DERIVATION` | `spec/ADDRESSING-LAYERS.md:142` | `CX-006-D1` — `DECISIONS.md:19` |
| MEDIUM | `STEWARD-RADIUS-DERIVATION` | `spec/RPP-CANONICAL-v2.md:347` | `CX-006-D1` — `DECISIONS.md:19` |
| MEDIUM | `STEWARD-T2-1` | `spec/SPINTRONIC.md:288` | `CX-006-D3` — `DECISIONS.md:76` |
| MEDIUM | `STEWARD-T2-1` | `spec/SPINTRONIC.md:311` | `CX-006-D3` — `DECISIONS.md:76` |
| MEDIUM | `STEWARD-TTL-1` | `spec/CCQPSG.md:108` | `CX-006-D2` — `DECISIONS.md:58` |
| MEDIUM | `STEWARD-TTL-1` | `spec/SPEC.md:94` | `CX-006-D2` — `DECISIONS.md:58` |
| LOW | `WORD-RADIUS-1` | `VERSION_POLICY.md:70` | `CX-006-A1` — `DECISIONS.md:170` |
| LOW | `WORD-RADIUS-1` | `VERSION_POLICY.md:74` | `CX-006-A1` — `DECISIONS.md:170` |
| LOW | `WORD-RADIUS-1` | `VERSION_POLICY.md:83` | `CX-006-A1` — `DECISIONS.md:170` |
| LOW | `WORD-RADIUS-1` | `spec/ADDRESSING-LAYERS.md:114` | `CX-006-A1` — `DECISIONS.md:170` |
| LOW | `WORD-RADIUS-1` | `spec/PMA-SCHEMA-v1.md:116` | `CX-006-A1` — `DECISIONS.md:170` |
| LOW | `WORD-RADIUS-1` | `spec/README.md:92` | `CX-006-A1` — `DECISIONS.md:170` |

## Four changed baseline identities

| ID | Decision | Original normalized SHA-256 | Ruled normalized SHA-256 |
|---|---|---|---|
| F-BASE-0038 | CX-006-D4 | `84bc5af82f68997c5e0e251d1d1ff0c3b37003b80ae16d5ff0292f1ec05e06e7` | `a5b6c65570eaa7456b7400c643b55ea30a9100c47a02c67010fccb4d9b2d04ca` |
| F-BASE-0049 | CX-006-D2 | `024c464c986d77c9bdd2f4b61aa331159768bbaf658e564f85737782d221421a` | `4b85a4f897d8dac0374d7a97163cbed175a393b04c9c1052712cf92e34bb6a07` |
| F-BASE-0213 | CX-006-D3 | `8a2a066b677d950d4661a0671345bead846191322a0ab5364b4ee29a9829ea5c` | `bcb5e2a19df7fd9b29c6e2496ab7441136d2b35284028fe0eb6474f3d2dbebca` |
| F-BASE-0221 | CX-006-D3 | `124aecf1190b58305bd84549f29a7dc0743644d8ea8e76a31e1ad8d7ad841bbc` | `cacde5d4566e7a262c9ae68cf01285821371b704072421e09163fc55de2bfd25` |

The remaining 239 objects and all seven protected anchors compare exactly with
`5677ea2:tools/drift/catalog.json`. Each ruled object is still IMPOSED; its ruling
records the approved wording/policy change and accepts no physical claim.
Original objects retain historical routes; current ruled/decided routes cite
their exact RFC record and decision date. A2 bool/negative-zero/
URI behavior remains a separate proposal, not an implementation change.

## Exact replay permission and future coverage

Updating the two guards, the four baseline identities and decided watched
passages naturally removes their obsolete-identity findings. Only the three
recorded `BND-F-2` additions require explicit historical-transition recognition:

1. The current classification must be `BND-F-2`; a HIGH classification cannot
   inherit a MEDIUM permission.
2. Exact path and approved new normalized hash must match; exactly one new
   occurrence may exist and no approved occurrence may already exist in base.
3. A replacement must be the actual unique same-kind/same-owner old→new passage
   pair with its exact recorded old hash. Same-file membership is insufficient.
4. The new DECISIONS paragraph additionally requires an absent Git tree entry
   in base and the exact complete approved target-file hash. An existing empty
   file is not a creation; content truthiness is insufficient.
5. The three approved after-identities remain watched for later loss. Future
   DECISIONS deletion or nonphysics rewrite still reports; duplicates, copies,
   reverse transitions, modified creation and later changes receive no waiver.

The duplicate case uses the conservative rule: ambiguous multiplicity permits
no historical exemption. Status alone is never a permission. No rule/severity
is downgraded, detector disabled or path excluded.

## Executed commands

Python is `/workspace/work/cx005/venv/bin/python` (3.12.14) with `PYTHONPATH=.`;
Ruff is pinned 0.14.10. Commands run from this branch checkout.

| Command / check | Observed result |
|---|---|
| `python -m pytest tools/drift/tests/ -q -o addopts=` | **287 passed**. |
| `python -m tools.drift.mutation_check` | **47 killed / 0 survived**, controls **47/0**. |
| `python -m tools.drift.snapshot`, repeated with byte comparison | 75 original paths; **239 open / 4 ruled** baselines; **0 open** steward items; **1 open** advisory; same catalog bytes on both rebuilds. |
| `python -m tools.drift check --base 275a115 --head 5677ea2 --output-dir <scratch>` | Historical approved CX-006 replay: **exit 0; 0/0/0** under revised catalog. |
| `python -m tools.drift check --base 5677ea2 --head <resolved-branch-head> --output-dir <scratch>` | Own diff/revised master tree: **exit 0; 0/0/0**. |
| `python -m pytest tests/ -q` | **1256 passed**, one pre-existing legacy-format warning; existing pytest-asyncio notice retained. |
| `python tests/test_golden_vectors_mobius32.py` | **SUMMARY pass=5 fail=0**. |
| `ruff --version`; `ruff check rpp/ tests/ <changed drift Python files> --ignore E501` | **0.14.10; exit 0**. |
| `git diff --check 5677ea2 HEAD`; `git diff --cached --check` | **exit 0**. |

There are no new package tests; the 1256 total is unchanged. New coordinator
regressions have fixed bounded titles and docstrings naming their failing
mutations. Actual mutation witnesses compile only trusted coordinator copies in
memory. Invalid catalog/source/collection errors do not count as killed mutants;
each witness also requires its unmodified control to pass.

The full coordinator suite increased from 269 to **287** cases: **18** new
bounded ruling/provenance regressions. The mutation total increased from 40 to
**47**: 22 detector deletions and 25 branch witnesses, all with clean controls.
The seven new executed witnesses are:

| Mutation | Positive regression | Clean control |
|---|---|---|
| `ruling_path_scope` | Wrong-path transition still reports | Exact historical transition |
| `ruling_before_identity` | Wrong paired old hash still reports | Exact historical transition |
| `ruling_created_file_identity` | Modified decision-file creation still reports | Exact decision-file creation |
| `ruling_empty_file_creation` | Existing empty file is not a creation | Exact decision-file creation |
| `ruling_future_identity_loss` | Later decision-paragraph deletion reports | Exact historical transition |
| `ruling_high_severity_permission` | A current HIGH classification is not exempt | Exact historical transition |
| `ruling_nonruled_status` | Unauthorized pending-entry status is rejected | Valid catalog control |

The invalid-status witness uses an explicit assertion on rejection, matching the
runner's rule that unexpected exceptions or non-assertion failures cannot count
as kills. The final provenance-route cleanup changes only the four ruled and
five decided current routes; complete originals retain historical routes. A
focused rerun passes **57** new-regression/catalog-corruption cases. Snapshot
comparison uses parsed initial metadata plus **two generated outputs**, so it
never compares initial Windows CRLF bytes with a new LF output.

## IMPOSED choices and remaining limits

Preserve the 239 raw statuses rather than relabeling them en masse; interpret
the unchanged unresolved state as review-pending. Keep historical source scan,
IDs, rules, route text and all original objects. Pin both catalog layers so no
matching-hash rewrite silently expands approval. Treat duplicate identities as
ambiguous and keep existing-empty distinct from absent files. These are stricter
implementation choices within the released scope, not new steward decisions.

No physical/device claim, A2 fix, extra spec cleanup or broader source scan is
introduced. Earlier CX-006 reports remain immutable; they correctly describe
the then-unsuppressed 2/12/6 result with the previous catalog revision.

Native Windows was not run here. TR should repeat the drift tests, mutation
runner, snapshot/idempotence, own-diff and historical replay commands on Windows
11 / Python 3.13, followed by package/golden/Ruff gates. Use resolved hexadecimal
heads; normal PowerShell `(git rev-parse HEAD)` supplies the branch head. The
existing two POSIX-specific drift cases are expected to skip on Windows; report
observed platform counts rather than claiming a native run here.
