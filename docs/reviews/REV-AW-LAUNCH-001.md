---
branch: codex/rev-aw-launch-001
head: refs/heads/codex/rev-aw-launch-001
head_kind: final-pushed-branch-ref
source_base: ae10d65a520d25958197f77e6cf784e6b8d177ce
trellis_head: 3d7a8411834208d5e27d9c3fc36aa8a6b5c63ab8
fillin_head: 803afe777c405b0054ab707d7494774e1afef7d1
tree_plan_head: 83afac0fbc52f470aeb09523dd3351d8cdeed29f
main_pin: b7ab96fa5632b4b2b05e1a4a69d474c255b3ddfb
platform_pin: 2f12736ffdac13024825c848b3909e7ccacad98f
---

# RPP-REV-AW: independent launch-pack review

| Target in anywave/anywavecreations.com | Verdict | Findings |
|---|---|---|
| codex/aw-fillin-pack at fillin_head | **NOT-READY** for the claimed complete runtime-marker check | 1 MEDIUM, 1 LOW |
| codex/aw-smain-tree-plan at tree_plan_head | **READY for planning/preparation only** | No retained findings |

Fill-in can report PASS while a newly added public document or route still
holds the marker. It needs the narrow discovery repair and tests below before
approval. No wrong-target or static-link write was demonstrated. The tree plan
preserves the five mandatory source trees and fails closed on pending choices;
it does not approve promotion or deployment.

The live site is the retained **10/19 sales site**, neither pinned main nor
the platform. No live content, URLs, hosting, backup or deployment was checked.
RADIX owns the values and dates; this review does not assess or supply them.

## Scope, independence and execution

Read codex/LESSONS.md first, then pulled trellis-channel main to trellis_head
and read its newest RPP-REV-AW entry. Read the target AGENTS.md and the two
cards/reports. Fetched the two named targets, main and platform read-only;
their heads exactly match the four pins above. Searches stayed inside the
named anywavecreations.com, trellis-channel and rpp-spec repositories.

Three read-only subagents covered fill-in write safety, test/mutation evidence,
and tree preservation. All returned. The main thread checked their claims,
ran all probes, wrote the report and alone pushed. The split helped find two
distinct scanner misses. Per-agent time/token cost was not exposed.

Anywave's checkout stayed clean at 53f21c6ef8a48caf2f858c7911328299b6b106b4;
target source was read with git show/ls-tree/cat-file, without switching it.
Only the reviewed scripts/tests, public targets and their import dependencies
were exported to external scratch fixtures. Tests, mutations and applies ran
there or in disposable synthetic trees. No real source apply, install, build,
service, browser, network request from a tool under review, or private-content
publication occurred. The only committed change is this RPP report.

Independent focused runs used Node v24.19.0, installed Vitest 5.0.5 and Zod
4.6.7. Node differs from the targets' pinned 24.22.2: these are local review
probes, not a pinned release-gate pass. No toolchain/configuration was changed.

## AW-01 - MEDIUM: discovery can miss served text and still apply with PASS

Files at fillin_head: scripts/radix-fill-in.ts:67, :72, :185 and :220;
docs/deployment/RADIX_FILL_IN.md:11 and :46. Discovery skips directories by
basename at every depth and omits .htm. The final marker check covers only
template.files, so it cannot catch an unmapped file which discovery skipped.

Executed failing cases, using the unchanged script and actual seven-row
template/four target snapshots in an external tree, with synthetic valid fills:

| Added file, containing RADIX_TO_SUPPLY | checkFill | applyFill | Result |
|---|---|---|---|
| apps/web/app/dist/page.tsx, a normal page export | PASS | PASS, four files written | New route's marker remains |
| apps/web/public/notice.htm | PASS | PASS, four files written | Public document's marker remains |
| apps/web/public/notice.html, discovery control | BLOCKED | BLOCKED, zero files written | Unmapped marker detected |

Leave the four hashed targets and the trusted template unchanged, add either
missed file, and fill only the seven value fields. No stale-target, metadata,
link or malformed-value trick is needed. public/notice.htm is served as a
static document; it needs no import. A directory called dist under app is
not inherently generated output.

Refutation tried: the docs exclude generated/dependency trees, all seven
current slots use recognized files, the checkout must be reviewed/quiescent,
and later diff/release gates remain mandatory. Thus this is no observed live
exposure, consent bypass or deployment approval. Those limits reduce impact
but do not refute PASS with an unmapped runtime marker intact. The tool and
doc promise to catch that drift, so retain MEDIUM for fill-in completeness.

Small repair: use path-scoped exclusions for actual generated trees and
include .htm, or a bounded scan of served public text. Do not claim this
covers every possible format. Add tests named for the two misses, each
requiring check/apply BLOCKED, written: [], and all four originals unchanged;
retain the .html control. A basename-skip or omitted-.htm mutant must fail.
No repair is made by this read-only review.

## AW-02 - LOW: key refusal/rollback rules lack regression witnesses

Files at fillin_head: tests/radix-fill-in.test.ts:20-227, versus
scripts/radix-fill-in.ts:90, :220, :229, :242 and :252. Existing tests cover
preflight inputs but never inject a rename/rollback failure or give a wording
value containing the marker. Mutation execution below confirms the gap.

Concrete failing protection: deleting the rollback loop at :252-261 leaves
all 23 shipped tests green. The independent second-rename fault oracle then
fails its original-byte assertion: the first target remains changed. With
unmodified code, that same fault yields BLOCKED/APPLY_REFUSED and restores
all originals. This is a missing regression test, not a current rollback bug.

Also, removing only the marker-value clause at :90 lets check return PASS for
marker-bearing wording, while all 23 tests pass; apply's last guard still
refuses. Removing both checks (:90 and :220-221) still passes all 23, and the
independent witness then gets apply PASS with a marker in the written target.

Refutation: layered guards can be redundant, so a surviving deletion alone
does not prove unsafe production code. The marker and rollback counterexamples
above show changed behavior, while the live implementation still protects
those paths. The original report claims regression tests, not an executed
mutation campaign; no false mutation claim is alleged. Keep LOW. Add bounded
marker-value and injected commit/rollback tests; do not promise crash atomicity.

## Executed checks and mutations

The two unmodified focused suites passed: **23/23 fill-in**, **31/31 tree**.
Used node with the installed vitest/vitest.mjs, run --config vitest.config.ts
--root <external-fixture> --cache=false. The scratch config selected only the
exported test file, with one worker and no file parallelism. Initial fill-in
scratch attempts lacked an imported module; after exporting the target's
relative import closure, all 23 ran and passed. No target source was patched
to get that result. Full project lint/typecheck/build/release/browser/CI were
not run; the authors' historical results are not new evidence from this review.

Nine bounded fill-in mutations, each applied only to the external script and
restored afterwards. Killed means an existing assertion failed, not a load error:

| ID | Removed rule at original script lines | Existing 23-test result | Witness |
|---|---|---|---|
| F01 | Metadata equality, :157-158 | 22 pass / 1 fail | DUPLICATE_OR_CHANGED_METADATA |
| F02 | Whole-file hash, :162 | 22 / 1 | MOVED_OR_OTHER_EDIT |
| F03 | Exact target/range check, :173-181 | 22 / 1 | MOVED_OR_OTHER_EDIT |
| F04 | Source walker link refusal, :64 | 22 / 1 | SOURCE_SYMLINK |
| F05 | Marker clause in validValue, :90 | 23 / 0, survived | Added witness: check PASS; apply throws at final guard |
| F06 | Marker clause AND final marker guard, :90 + :220-221 | 23 / 0, survived | Added witness: check/apply PASS with written marker |
| F07 | Pre-stage snapshot recheck, :229-230 | 23 / 0, survived | No isolated staged-edit test in shipped suite |
| F08 | Post-stage snapshot recheck, :242-244 | 23 / 0, survived | No isolated staged-edit test in shipped suite |
| F09 | Rollback loop, :252-261 | 23 / 0, survived | Added rename-fault oracle fails; unmodified control passes |

Fill-in total: **4 killed / 5 survived** in its existing suite. F06 is explicitly
a two-guard policy mutation. F07/F08 survival alone does not establish an
unsafe success, since the other snapshot guard remains. No equivalence claim
or exhaustive mutation coverage is made.

Three tree-checker mutations were all killed by its existing 31-test suite:

| ID | Removed rule at original script lines | Existing result | Failing test names |
|---|---|---|---|
| T01 | KEEP hash/presence block, :238-244 | 28 pass / 3 fail | EDITED_SGS_FILE; MISSING_RPP; KEEP_EXTRA_OR_SYMLINK |
| T02 | Protected source in export check, :274-275 | 30 / 1 | KEEP_IN_UPLOAD |
| T03 | NEEDS_RADIX block, :237 | 30 / 1 | UNRESOLVED_OWNER_DECISION |

Fifteen additional cases ran with unchanged scripts: the three discovery
cases above; stale-target refusal with no writes; target and ancestor-link
refusals with outside bytes unchanged; second-rename and rollback faults;
one clean five-KEEP fixture; each of its five missing-root cases; one synthetic
private-root-in-export case. Every asserted observation matched. This count
includes the demonstrated defects; it is not fifteen safety passes.

The rename fault restored originals. With both rename and rollback writes
faulted, a partial set remained and the result was BLOCKED/ROLLBACK_INCOMPLETE.
This answers the half-set question honestly: no multi-file crash transaction
is provided. Doc :50 discloses crash non-atomicity, attempted ordinary rollback,
and the quiescent-copy/diff-review requirement. No silent partial PASS was found.
Concurrent malicious directory swaps remain outside that stated working-copy
condition; static target/ancestor links were refused in the executed controls.

Wrong-place writes: the CLI pins its own repository root and adjacent template
(script :283-290); caller metadata must equal that template (:157-158).
Changed target metadata fails before apply writes; F01's existing assertion
catches removal of that rule. Whole-file hashes and exact ranges independently
catch stale edits (:162, :173-181; F02/F03). No redirection through an ordinary
fill-file path change was found. The library's root/template inputs are trusted
caller inputs, unlike the owner file's value fields.

## Tree-plan preservation, merge and privacy

Independently recomputed hashes from opaque Git blob bytes, modes and sorted
relative names, without displaying or materializing private content:

| Mandatory KEEP root | Files | Bytes | Digest against pinned main |
|---|---:|---:|---|
| .digigami-oa | 18 | 159071 | Matches |
| SGS | 18 | 14725838 | Matches |
| digigami | 2 | 16455 | Matches |
| rpp | 144 | 2281157 | Matches |
| seamlessgutterslayers | 154 | 33275518 | Matches |

All protected tracked modes are 100644. Main's **66** top-level names match
the manifest and stored fixture exactly. Counts are **5 KEEP, 4 REPLACED,
6 REMOVE, 51 NEEDS-RADIX**. All three pinned replacement hashes match the
reviewed source. Stored tests also check the document's complete name table.

Can a missing mandatory tree pass? Not with the reviewed manifest: script
:238-244 adds KEEP_UNREADABLE for absence and checks changed/extra/missing
content by hash. Synthetic tests removed each of the five roots separately;
all blocked. T01 proved the shipped SGS/RPP assertions detect losing the rule.
Today's real policy cannot return PASS merely by deleting other paths either:
all 51 NEEDS-RADIX rows block even when absent (:237; T03).

The recommended main-rooted unrelated-histories merge explicitly preserves
both histories and restores these five trees from pinned main (plan :123-131).
It requires individual conflict decisions, a verified backup, and final tree
hash checks; a blanket platform-tree replacement is forbidden. Intentional
REMOVE/REPLACED rows are enumerated, and undecided losses remain blocked.
No actual merge/candidate promotion tree was made, so no completed merge or
lossless resolution is certified here.

Private source preservation is not permission to publish it. The plan flags
.digigami-oa privacy separately (:15, :22); all five Docker exclusions are
required, and original protected root names in the upload artifact block
(:273-275; synthetic control and T02). Plan :101-103 discloses the current
Docker-context work still needed. No demonstrated private-file exposure or
upload occurred. The checker is not a universal secret scanner: arbitrary
renamed private content is outside its path inventory. No private document,
configuration, conversation, binary or subscriber content was quoted.

Merge integration note, not a defect: keeping both packs' package commands
changes package.json relative to the tree manifest's replacement hash. That
will fail closed until a reviewed replacement-hash update (plan :145;
tests/smain-tree.test.ts:204-210). Preserve all three commands, review that update,
and keep all five KEEP hashes pinned to main. Never derive them from a candidate.

The plan's :5-15 live-site caveat is accurate: source URLs cannot establish
10/19 compatibility. Owner/private-file decisions, live routes, .htaccess,
backup, deploy_ref/OIDC and the normal release gates remain blockers. Those
known limits are not new checker defects and are not silently approved here.

## Publication and limits

No source fix, owner-value application, workflow/gate/allowlist change, PR,
merge, tag, deployment, provider call, legal decision or new disclosure is part
of this review. Report-only checks: ASCII/LF/control bytes, git diff --check,
the BASE-side trusted gate and drift on the final report commit before one
normal push; resolve its front-matter head with git ls-remote.

Could not confirm native Windows, pinned Node 24.22.2 behavior, real owner-value
apply, all project gates/CI, crash recovery, host bytes/private access controls,
live route compatibility or an actual merge. An optional RPP fetch was rejected
by automatic approval review, which interpreted scope as anywave-only. It was
not retried; this single report uses the stated known local RPP base instead.
No required review step depends on refreshing that base.
