# Record RADIX's ruled catalog identities while retaining future drift checks

CX-006's approved wording changes still produce 20 findings against the original
frozen catalog. Revision 2 records each consequence with its exact RADIX RFC
reference, updates only two A1 guard blocks and four ruled baseline identities,
and marks the four steward items plus A1 decided. A2 and the other 239 baseline
entries retain their open/review-pending state; all original metadata is preserved.

The revised catalog replays the approved CX-006 range cleanly. Permissions bind
to exact old→new passage identities and exact file creation, while future edits,
deletions, duplicate copies, wrong paths and HIGH classifications still report.
Snapshot reconstruction and schema fingerprints prevent unrelated re-baselining.
No spec, package behavior, layout, header, vector, constant or outbox changes.

Validation and exact 20-finding/decision mapping:
`tools/drift/CX007_VALIDATION.md`. Branch
`codex/catalog-rulings-2026-11-01` → `master`; merge before the Rust crate branch.
TR owns PR creation and merge.
