---
id: MAP-REVIEW-rpp-spec
from: Codex (rpp-spec)
to: TR
repo: anywave/rpp-spec
branch: codex/MAP-REVIEW-rpp-spec
head: refs/heads/codex/MAP-REVIEW-rpp-spec
head_kind: final-pushed-branch-ref
source_base: ae10d65a520d25958197f77e6cf784e6b8d177ce
trellis_head: 3ac4da88fdf76d3cb13ac9ca3499c69e221e7ca3
map_blob: 50a24f7e1e939f7203d36bb32021a58d2fa6c863
date: 2026-11-03
subject: RPP inventory corrections and prerequisites for the proposed workflow map
---

# MAP-REVIEW: rpp-spec

Read `codex/LESSONS.md` first, then the newest MAP-REVIEW entry and
`codex/PARALLEL_WORK.md`. This is a source review of the map at the pinned trellis
head and RPP at `source_base`, not a live fleet acceptance test. All `map:N`
references mean `trellis-channel/codex/PRODUCT_DESIGN_MAP.md:N`; unqualified
repository citations below mean the pinned RPP tree.

The main correction is to inventory RPP's existing pieces separately and make
the missing owner-signed CI integration an explicit dependency. Reuse those
pieces; do not count them as a job runner, signed machine inventory or policy
approval service.

## 1. Every section 3 row touching this repo

There is one directly named RPP row: `map:80`, "gguf-gate v0.1.0, rpp-spec
crates". Other section 3 rows name sibling repositories or lab/trellis tools;
their current implementations are outside this repo review.

| Cell in map:80 | Checked result and correction |
| --- | --- |
| Where: "own repos" | Give concrete RPP paths: eight members in `rust/Cargo.toml:2`, plus the separate workspace at `rust/rpp-steer-udp/Cargo.toml:1`. Their roles include policy, codecs, live host transport and measured steering. |
| State: "Tagged, merged" | **Merged source is correct** at master `ae10d65a`; a tagged Rust crate release is not established. `rust/rpp-core/Cargo.toml:7` and `rust/rpp-steer-udp/Cargo.toml:10` disable publishing. Older repository tags do exist: remote `v1.2.0` peels to `d017222dfb5a9736a054d2687e166ae2a3f7de6c`, whose tree has no `rust/`. Split gguf's release state from "merged, unpublished experimental RPP libraries/adapters"; do not erase the legacy tags or infer crates.io publication. |
| Proof: "Own tests" | Supportable as reported tests, but too coarse for a build plan. General CI is configured at `.github/workflows/rust.yml:169`; separate TCP properties are an independent workspace (`tools/tcp_scaffold/Cargo.toml:1`). Three dedicated checks remain omitted, as the corrective report explicitly records (`docs/codex/OUTBOX/CX-LINEAR-WORKFLOWS-001.md:128`). Do not treat an ordinary green workspace job as their proof. |
| Role: "Parsing, protocol" | Understates reusable work. Fleet records/selection, steering, measured loopback transport, control and billboard codecs already exist (section 2). Their host verification, consent and hardware limits must travel with the inventory rows. |

Suggested proof wording: "Existing codec/corpus, policy and loopback tests;
local results by named report. General Ubuntu/Windows workflow configured;
TCP-property, required-native-budget and UDP-classifier CI additions pending
owner-signed integration. No new run, cross-site or board proof in this review."
The retained Windows run in the corrective report is explicitly for
`fcc3aea8`, not current master (`docs/codex/OUTBOX/CX-LINEAR-WORKFLOWS-001.md:290`).

## 2. What section 3 misses: reuse before rebuilding

These are existing components, not proposals to extend RPP's scope.

| Missing inventory detail | Exact source and honest boundary | Section 8 effect |
| --- | --- | --- |
| Bounded fleet registry and endpoint selection | `rust/rpp-fleet/src/registry.rs:78` registers explicit bindings and rejects duplicates; `:149` updates readings. `rust/rpp-fleet/src/limits.rs:8` caps one registry at 16 nodes and `:10` at four endpoints per node. `rust/rpp-fleet/src/lib.rs:3` excludes discovery, I/O, crypto and consent grants. | Shortens slices 2/12's record and route-selection work. It supplies neither hardware/why-idle discovery nor signed machine cards, resource placement or the configuration planner. |
| Link ranking and real measured UDP bridge | `rust/rpp-steer/src/lib.rs:1` ranks already eligible caller measurements. `rust/rpp-steer-udp/README.md:3` samples real loopback UDP, and `:11` distinguishes measured RTT/loss/jitter from caller-supplied throughput/cost. | Reuse for slices 2/12 link observations and slice 14 transport experiments; it neither dispatches jobs nor splits inference. |
| Real UDP and TCP fallback, already merged | `rust/rpp-link-udp/README.md:3` limits UDP to loopback/tailnet address ranges, not proof of encryption. `:89` selects fallback before application sends; `:97` makes TCP loopback-only with no TLS/authentication and refuses tailnet TCP. | Avoid rebuilding host framing/probes/fallback for slices 12/14. These tests do not establish slice 13's cross-site transport; its git reporting is a separate path. |
| Control, billboard and small-MTU codecs | `rust/rpp-control/src/lib.rs:28` has six closed kinds including STOP/PAUSE/RESUME, never START. `rust/rpp-billboard/src/lib.rs:104` encodes rule/fact wire fields. `docs/design/SMALL_MTU_FRAMING.md:3` frames control only; `:68` lists missing board/adapter integration. | Shortens slices 9/10's message transport. Presence reading, drain policy, consent, replay checks and actual stop/free-device effects remain host work. |
| Existing lift and deterministic test scaffolding | `tools/rust_scaffold/check_lift.py:1` is an offline structural lift guard, not a compiler. `.github/workflows/rust.yml:139` separately builds/tests a copied workspace; `:95` runs detached hostile-input properties. | Reuse those checks in an RPP component gate; do not build another extraction or corpus harness. Keep native target/transport acceptance separate. |

### Unmerged branches were checked by content

Fetched 50 origin refs: the HEAD alias, master and 48 named branches (44 codex,
four pl). For each named branch, compared its merge-base-to-head added/modified
paths with master blob IDs: **247 path occurrences; 24 branches with no such
delta, seven whose changed blobs already match master, 17 with divergent or
absent blobs**. This avoids calling squash-merged work "missing" by ancestry.
It is an added/modified-path survey, not a proof about every deletion or mode.

| Retained branch/head | What still differs in its original touched paths | Reuse, not rewrite |
| --- | --- | --- |
| `codex/cx-027-tcp-fallback` at `fcc3aea8b8115733c8f89c683652c6b114f514bc` | Its 13 non-workflow paths match master; the workflow retains +18 lines for detached TCP properties. | TCP implementation is merged. Adopt the already preserved owner workflow hunk after authorization. |
| `codex/cx-028-esp32-budget` at `4c56878c27ccb2c1cc39b6714c9203f4fe023646` | Its seven non-workflow paths match master; the workflow retains +6 lines for required native budget regressions. | The budget implementation is merged. Existing CI compiles reservation assertions; the omitted suite adds exact-cap/overflow boundary cases. |
| `codex/udp-classifier-ci` at `c27889efab5cb87295348f69d5839d5605fb5868` | +6 workflow lines and its report. | The classifier check is already written. All three exact hunks are preserved in `docs/codex/OUTBOX/CX-LINEAR-WORKFLOWS-001.md:136`. |

The genuine branch-only research at
`codex/CX-017-coherence-sector-verdict@ba275c0b997489c88a7e96919b05731f68d01ef0`
adds 21 proof files absent from master. On that branch,
`tools/prove_out/VERDICT.md:3` says generic coherence is NOT PROVABLE for the
readout; `:13` proves sector only as an address label.
`tools/prove_out/CX017_VALIDATION.md:123` records unresolved PR packaging.
Inventory this as bounded research evidence, not machine availability,
reliability or a ready-to-merge fleet component. It can save repeating that
investigation; it is not a scheduler proof.

The old `pl/consent-gate@31ca5f906216733cc214a8ff74cd4ecd8049ea09`
adds a testbench SipHash reference, not slice 15's BDP signer:
`hardware/verilog/siphash_ref.py:1` on that branch identifies the reference,
while master `hardware/verilog/RPP_CONSENT_GATE.md:14` delegates verification.
No additional executable queue/BDP implementation was established by this survey.

## 3. Where sections 4 to 8 need an RPP-specific amendment

These are implementation dependencies or ambiguous classifications, not claims
that the corresponding LatticeWorks/n2HO components do not exist.

1. **Gate prerequisite and proof scope (map:177, map:180, map:211).** The BASE
   owner list contains only comments (`.github/codex-gate-owners.txt:1`);
   `scripts/ci/trusted_gate.py:90` protects `.github/**` and `:154` refuses
   protected changes without a listed signature. Therefore an RPP batch cannot
   simply enable the three omitted checks from an ordinary Codex branch. Name
   RADIX/TR owner enrollment and the existing owner-signed workflow patch as a
   dependency before claiming complete batch CI. Inherited claims at
   `rust/rpp-link-udp/README.md:123` and `docs/esp32/READINESS.md:98` must be read
   with the corrective outbox cited above, not as current CI executions.

2. **Use the strictest component gate (map:118, map:177, map:178, map:180).**
   "rpp crates" is not a uniformly pure-core component. The control verifier
   boundary is at `rust/rpp-control/src/lib.rs:90`; billboard wire encoding is
   at `rust/rpp-billboard/src/lib.rs:104`; actual sockets open at
   `rust/rpp-link-udp/src/socket.rs:66` and `rust/rpp-link-udp/src/tcp.rs:76`. Make overlapping
   classification explicit: pure policy/codec work, signed-wire/security work
   and live adapters take the strictest applicable trigger. A behavior-changing
   decoder/verifier edit still needs the boundary gate even without a version
   bump. Do not infer that a bypass currently occurs; this is a plan ambiguity.

3. **Define the job/attempt-to-proof handoff in slice 3 (map:99, map:134,
   map:203).** RPP `MeterRow` has a local numeric request/row and no job/plan
   identity or signature (`rust/rpp-core/src/overlay.rs:298`). Each simulator
   starts those counters at one (`:397`), and complete history requires host
   persistence (`:433`). A plan side table alone cannot distinguish two such
   runs. Reuse the host's existing signed-meter system with an envelope binding
   job, attempt, source, RPP request/row and result; define persistence and the
   independent verification step. Do not add a durable job database or signing
   implementation to RPP; durable persistence, identity provisioning and signing
   remain host responsibilities.

4. **Name the policy-to-effects handoff for slice 9 (map:152, map:209).**
   `rust/rpp-fleet/src/resolver.rs:139` consumes prior host Auth, membership and
   consent; `rust/rpp-control/src/lib.rs:182` expressly requires current host
   authorization, consent and replay checks before effects. These types do not
   implement locked-session detection, policy signatures, hours/caps or device
   pause/free behavior. The host must revalidate/invalidate its context before
   physical effects; successful decode or route selection is not network
   approval. Reuse the named codecs without inventing START/grant payloads.

I found no contradiction between map:105's pull dispatcher and RPP's socket
listeners: that line explicitly permits live traffic inside a granted job.
Likewise, map:213's git return path does not promise a working RPP tunnel.
Those suspected conflicts were rejected rather than reported as defects.

## Review method, validation and what I did not get to

Three read-only subagents covered row claims, unmerged-branch reuse and sections
4-8; root checked their citations, reran the branch blob comparison and refuted
the initial no-tags lead with `git ls-remote`. Subagents work in this cloud
thread (proof already completed); time/token costs were not exposed. They saved
independent reading time. Only root writes this report and performs its one push.
`local_ask` is unavailable; no local model was started.

Root source checks include the named definitions, current workflow commands,
empty owner list, three retained workflow diffs (+18/+6/+6), declared workspace
membership and standalone manifests. UTF-8/control-character, citation/path,
one-file scope and whitespace checks cover this report. Source/audit receipts
are outside the checkout under `/workspace/work/map-review-rpp-spec/`.

Not rerun: Python/Rust suites, corpus regeneration, mutation campaigns, hosted
CI, native Windows, physical boards, cross-site traffic, encryption or signing.
Historical test counts are not promoted to fresh results. I did not inspect
all historical commit bodies, every test assertion/report, branch deletions or
mode changes, all remote tag trees, or gguf-gate/Mobi/LatticeWorks/current
Anywave source. The sibling-only section 3 rows and the general queue-service,
policy-authority/admin-fence rulings remain with their owners. No product code,
specification, constants, layout, header, vectors, policy settings, gates or
published outbox was changed; no new design was adopted.
