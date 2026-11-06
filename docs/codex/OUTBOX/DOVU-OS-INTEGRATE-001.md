# DOVU-OS-INTEGRATE-001

Card: TR / RADIX DOVU-OS-INTEGRATE, 2026-11-06. Research, an integration plan and
one closed fake prototype. **Recommend DOVU only downstream of existing evidence,
initially for a public daily-root reference. Do not make it an agent authority,
token counter, energy verifier, settlement authority or RPP verifier.** Verdicts
below are engineering recommendations; they do not lift existing release gates.

## Sources and reproducibility

Every `ALIAS:path:line` citation below uses the immutable tree in this table.
Post IDs identify trellis-channel posts in T. DESIGN denotes a proposed choice;
UNVERIFIED means not established by accessible sources or this run.

| Alias | Repository / immutable head read |
|---|---|
| T | [anywave/trellis-channel](https://github.com/anywave/trellis-channel/tree/17ec5e41798035f887807236af6b4f6e2da40e41) `17ec5e41798035f887807236af6b4f6e2da40e41`, after pull of main |
| CLI | [dovuofficial/dovu-os-cli](https://github.com/dovuofficial/dovu-os-cli/tree/8776789e0e83e5eda54bb987091cb92294681f02) `8776789e0e83e5eda54bb987091cb92294681f02` |
| PHP | [dovuofficial/guardian-php-sdk](https://github.com/dovuofficial/guardian-php-sdk/tree/a11df837cec43886df211e280f7432f50aaeceed) `a11df837cec43886df211e280f7432f50aaeceed` |
| MW | [dovuofficial/guardian-middleware-api](https://github.com/dovuofficial/guardian-middleware-api/tree/43fb482004fc7eadc69d09eb0224d05f15432f24) `43fb482004fc7eadc69d09eb0224d05f15432f24` |
| SPEC | [dovuofficial/dovu-os-specs](https://github.com/dovuofficial/dovu-os-specs/tree/5e561ae345f1e6119f9ff1e19f1c9da2562a8186) `5e561ae345f1e6119f9ff1e19f1c9da2562a8186` |
| PAAS | [dovuofficial/dovu-app-paas](https://github.com/dovuofficial/dovu-app-paas/tree/ad49e2d98a5a82c0f61a752772468255fae20a70) `ad49e2d98a5a82c0f61a752772468255fae20a70` |
| A | [anywave/digigami-audit prototype](https://github.com/anywave/digigami-audit/tree/617beedb5cb008621a784e02a4d2ac4d515eb5ff) `617beedb5cb008621a784e02a4d2ac4d515eb5ff`; base `4253f7510a7eb6ab728acf04810eb78da3663a40` |
| R | rpp-spec report branch based on `ae10d65a520d25958197f77e6cf784e6b8d177ce`; no spec or implementation edits |

Read the named boundary, both October research reports, Guardian policy/run plan,
HCS plan and FP-1901 before public-source review. Three read-only subagents
audited boundary precedence, public SDKs and public docs; the boundary worker
then independently reviewed the prototype. Root checked their source leads,
wrote the prototype/report/packs, ran tests and alone pushed. Per-agent token
costs are not exposed by this interface; no cost figure is invented.

### Reachability and limits

Official GitHub sources were reachable and cloned without installing or executing
them. These direct requests all failed: `https://docs.dovu.earth/llms.txt`,
`https://docs.dovu.earth/workflow-engine/the-engine.md`,
`https://docs.dovu.earth/workflow-engine/charger-protocol.md`, and
`https://dovu.earth/en/dovuos/`. Exact result: curl exit 56, HTTP status `000`,
`curl: (56) CONNECT tunnel failed, response 403`. This is the environment proxy's
refusal, not evidence the sites are down. No bypass was attempted. Fetch receipts
remain in `/tmp/dovu-integrate/public-docs/fetch.json` in this cloud session.

No hosted API was authenticated, no actor created, no DOVU test suite executed,
and no HCS/IPFS/HTS operation submitted. Thus hosted availability, deployed OS and
Guardian versions, network backing each hosted endpoint, custody contract,
service terms, current prices and daily-root schema acceptance are **UNVERIFIED**.
Source API names below describe code, not a successful live integration.

## 1. What is visible today

| Surface | What the accessible source establishes | Version, licence and limits |
|---|---|---|
| Hosted DOVU OS workflow engine | October research described a credits/RWA workflow engine with actors, schemas, workflow blocks, audit trails and issuance, not agent authorization (`T:artifacts/fp/dovu-guardian-research-2026-10-18/FINDINGS.md:5-20`; FP-1901 section 4). CLI currently targets `https://test-os.dovu.earth/api/v1/` and adds a bearer token (`CLI:src/helpers/api.js:3-9`). | Current hosted release/version, full server source/licence and actual backend network are UNVERIFIED. A test-host name is not a demonstrated testnet transaction. Historical Developer Preview status is not independently re-established here. |
| OS CLI | GET workflows/schemas/blocks; register/login; workflow publish; attach actor to instance; POST a block's schema-shaped payload to `workflow-block-instances/{id}`; schema-fields/validation helpers (`CLI:src/helpers/tasks.js:9-25,32-45,58-63,79-109,136-150`). | Package 1.0.0; root Apache-2.0 but package says ISC (`CLI:package.json:2-19`; `CLI:LICENSE:1-3`). Licence metadata conflict. Axios, commander, cli-table3, kleur; Node, not a Rust shipping dependency. `npm test` deliberately exits 1 (`CLI:package.json:7`). |
| Guardian PHP SDK | A configurable Guardian wrapper: bearer and configurable HMAC headers; account/login/profile/role calls, block submission and trustchain lookup (`PHP:src/BaseAPIClient.php:19-31`; `PHP:src/HttpClient/HttpClient.php:47-62,80-123`; `PHP:src/Service/AccountService.php:10-25,61-78`; `PHP:src/Service/BlockService.php:69-71`; `PHP:src/Service/TrustchainService.php:7-14`). | Head is tag v3.0.12; MIT (`PHP:composer.json:2-8`; `PHP:LICENSE.md:1-13`). PHP ^8.1, Guzzle ^7.4, Carbon ^3.0, dotenv ^5.6 (`PHP:composer.json:21-31`). This is not the hosted OS server or a Rust SDK. |
| Guardian middleware | Older self-hosted Guardian bridge: HMAC configuration, network/operator client and actor/account/profile creation (`MW:src/config/index.ts:20-24`; `MW:src/hashgraph/hashgraphClient.ts:7-10,35-66`; `MW:src/handler/accounts/createAccountHandler.ts:36-49`). MRV approval can lead to automatic minting (`MW:README.md:165-183`). | Package/tag 0.1.0; Apache-2.0 (`MW:package.json:2-4`; `MW:LICENSE:1-3`). OpenAPI 3.0.2/info 0.1.0 is for this middleware, not current OS (`MW:src/spec/openapi.json:2-17`). Depends on older JS Hedera/Next/React packages (`MW:package.json:32-42`). |
| OS public specifications | Blueprint registry, instance notary and asset-model intentions; publisher calls IPFS-first the current production context and HCS-first the specification backbone (`SPEC:README.md:1-28`). Treat the production statement as the publisher's claim. | Registry working draft v1.0.0; sync remains next phase (`SPEC:specs/0001-blueprint-registry-hcs/README.md:79-83`). Instance-notary and asset-metadata READMEs are empty files at this pin. Root MIT conflicts with README's licence-TBD wording (`SPEC:LICENSE:1-13`; `SPEC:README.md:60-61`). |
| HCS registry example | JS/Bun example can create topics and submit messages; it is a registry experiment, not a generic external audit-root verifier (`SPEC:src/hcs-registry-example/utils/hedera.js:14-55`; `SPEC:src/hcs-registry-example/utils/operations.js:9-16,37-54`). | Private package 0.1.0, @hashgraph/sdk ^2.69.0 plus dotenv/yargs/zod (`SPEC:src/hcs-registry-example/package.json:1-20`). Its `encodeCanonical` is `JSON.stringify`, not evidence of a reviewed canonical signing protocol (`SPEC:src/hcs-registry-example/utils/messages.js:30-33`). |
| Adjacent app PaaS | Separate trusted-team MCP upload/deploy/status/logs/destroy system, not demonstrated OS agent authority (`PAAS:README.md:3-13,197-217`). | Private package has no version/licence field; no tracked LICENSE or NOTICE found in the pinned tree (`PAAS:package.json:2-17`). MCP SDK/ssh2 are dependencies. Do not copy or deploy it for this card. |

No separate NOTICE was found in any of the five pinned public trees. Source
licences do not establish hosted-service permissions or price. No vendor code
or dependencies were copied into the prototype. No official Rust OS SDK was
identified in this inspected public set; that is a bounded search finding.

### Testnet, mainnet and costs

- CLI's fixed test host is useful documentary evidence, not a network lock on
  every DOVU component. MW supports testnet, previewnet and mainnet. PHP trustchain
  reads default to the mainnet mirror unless `forTestnet()` is selected; IPFS
  uses public gateways (`MW:src/hashgraph/hashgraphClient.ts:7-10`;
  `PHP:src/Trustchain/Mirrornode.php:18-21,35-52`; `PHP:src/Trustchain/IPFS.php:8-12,54-63`).
- The HCS example defaults testnet but accepts `mainnet` and reads an operator
  account/key from the environment (`SPEC:src/hcs-registry-example/utils/hedera.js:14-24`).
  Its README describes isolated unit tests, yet the actual tests invoke real
  topic creation/register/submission without that advertised opt-in guard
  (`SPEC:src/hcs-registry-example/README.md:102-105`;
  `SPEC:src/hcs-registry-example/__tests__/registry-core.test.js:15-105`). We did not run them.
- Likewise PHP's ELV tests create actors and advance real workflows; its audit
  test follows NFT/HCS/IPFS linkage, not environmental truth
  (`PHP:tests/TestnetElvClientTest.php:180-219,339-367`;
  `PHP:tests/TokenAuditTrailTest.php:24-53`). None was executed.
- Current subscription, per-workflow, per-root, schema-onboarding, AI-operation,
  credit, hosting, storage and pass-through Hedera charges are **UNVERIFIED**.
  October's report recorded a starting quote of **$0.125 per credit**, primarily
  fiat fees and later DOVU-token settlement; this is historical, not a current
  tariff or a price for our root submission
  (`T:artifacts/fp/dovu-guardian-research-2026-10-18/FINDINGS.md:13-14,45-49`).
  A possible future payment link in the registry example is not today's price
  (`SPEC:src/hcs-registry-example/README.md:49-53`).
- DESIGN cost comparison: direct HCS needs transaction fees plus our transport,
  mirror and operational work; direct Guardian adds hosting, policy and key
  operations; DOVU could add workflow/onboarding/service charges on top. Obtain
  an owner-approved quote before any spending; no current total is calculable
  from the accessible sources. This run used only local fake calls, with no
  transaction or hosted-service charge incurred by the prototype.

### Reuse decision

Borrow the workflow-boundary idea, not these clients. CLI logs payloads and raw
errors and persists actor credentials/tokens in plaintext
(`CLI:src/helpers/tasks.js:100-119`; `CLI:src/create-user.js:18-38`;
`CLI:src/config.js:57-59,76-78,194-205`). The PHP SDK has an optional Slack error
sender disabling peer TLS verification (`PHP:src/Notifications/SlackNotifier.php:13-21`).
Do not import these mechanisms. SDK source is evidence for API shape, not an
approved implementation, agent authority or a root-only DOVU contract.

## 2. Product fit: one row per requested product

| Product | Verdict and reason | Compared with direct HCS / Guardian |
|---|---|---|
| LatticeWorks token auditor: signed stage rows and settlement statement | **USE — closed fake Tier-1 prototype only.** Keep all stage rows, counts, settlement contents and verification locally; send only the public daily-root reference after existing gates. The boundary already defines this seam (`T:artifacts/fp/dovu-access-boundary/BOUNDARY-v1.md:38-49,87-95`). | HCS is the original anchor; DOVU can add a downstream workflow record. Guardian is unnecessary just to retain a reference. Neither establishes engine honesty or correct counts. Do not route settlement decisions through DOVU (FP-1901 section 4; TR-1057 sections 3-4). |
| Energy auditor, anywave/digigami-audit | **LATER.** Current repo is a counts-only meter/reconciler, with energy next and signing/anchoring absent (`A:README.md:3-21`). No energy data leaves under Tier 1; Tier 2 remains blocked (`T:artifacts/fp/dovu-access-boundary/BOUNDARY-v1.md:49-60`). | Direct HCS could later commit an approved digest, not certify a meter. Direct Guardian can host a selected methodology, but a suitable computing workflow and independent measurements are not established. October's methodology search is historical, not a fresh exhaustive registry survey (`T:artifacts/fp/carbon-research-2026-10-18/FINDINGS.md:23-30,100-110`). |
| Agent authority, Guardian step 3 | **NO.** Keep the existing direct Guardian VC verification/admission design; DOVU actor roles are not authority to act for a person (FP-1901 section 4). | Direct Guardian policy approves, registry-signs, publishes and revokes a credential without minting (`T:artifacts/fp/guardian-step3/lw-agent-authorization-policy/README.md:39-63`). HCS alone has no application authorization semantics. The documented checker still has explicit limits and run gates (`T:artifacts/fp/guardian-step3/step3-testnet-run-plan.md:11-38,44-59`). |
| Digigami Secretary's approved actions | **LATER — only an explicitly approved workflow handoff.** No new autonomy, account, send or wallet privilege. Existing action approval rules remain; DOVU cannot authorize the action (FP-1901 section 4; `T:codex/PRODUCT_DESIGN_MAP.md:523-526`). | Direct HCS could retain a permitted digest; Guardian could encode a purpose-specific credential, but neither substitutes for local approval. There is no demonstrated Secretary/DOVU schema or action adapter here: UNVERIFIED. No Secretary code changed. |
| Public Hedera tools, directive 1 | **LATER.** Existing proposal starts with synthetic read-only inspection, testnet digest preparation and unsigned payout preview, with no public release approval (`T:artifacts/cloud/hedera-tools-scout/SCOUT-r0.md:68-93`). | Direct Hedera tools have a smaller boundary for those jobs. Add DOVU only if a particular approved workflow needs it. DOVU's separate deployment MCP does not satisfy this directive or confer agent authority (`PAAS:README.md:3-13`). |
| RPP proofs | **NO.** No DOVU dependency in RPP. A stored digest cannot establish protocol, RTL, consent or layout correctness (`R:BOUNDARIES.md:16-39,59-110`). | Optional external HCS evidence can identify unchanged artifacts; the actual tests/formal checks remain the evidence. Guardian adds no demonstrated value to the protocol's fixed routing core. No spec, header, vector, constant or RPP implementation change. |
| Mobius | **LATER.** Inventory/review the existing DovuSink v2 and its release valve before any new exporter; avoid the old per-call sink (`T:artifacts/pl-research/integration-program/trust-wave-1/t3-dovu-built.md:1-18`; FP-1895; PL-519; PL-520). | Reuse the public HCS reference design only after current lane validation. Direct HCS supplies anchoring; DOVU is optional workflow bookkeeping. Neither is an independent compute check. No new Mobius transport or code in this card. |

## 3. USE design: token-auditor public-reference handoff

**DESIGN, downstream only.** Signed rows and the auditor/settlement statement
stay within the existing participating-machine evidence path, never in DOVU.
Stage ownership is asker: request/placement/settle,
solver: claim/run/result in PL's design; engine usage must be present or labelled
missing, never invented as zero (`T:artifacts/pl/tr-cards-2026-11-03/ship-lanes/lend-stage-rows.md:25-61`).
That document is a lane design/report, not a live result independently established
here. DOVU acceptance must never change those rows or the auditor's verdict.

| Boundary question | Integration decision and acceptance evidence |
|---|---|
| Crossing data / tier | Tier 1 **only**: `{topic_id, sequence_number, consensus_timestamp, root}`. No wrapper metadata or extra correlation fields. Public consensus time is the permitted anchor field, not a person's timing value. Exact projection and grammar are tested (`A:04_dovu_fake/src/lib.rs:49-83`; BOUNDARY-v1). |
| Never list | No prompts/answers/files/transcripts; salts; session/run IDs; start/stop commitments or inclusion paths; per-call/session timing; non-lend traffic; keys; machine/user/network identities; energy totals. Fixture tests add each forbidden key and require refusal (`A:04_dovu_fake/tests/boundary.rs:104-134`; `T:artifacts/fp/dovu-access-boundary/BOUNDARY-v1.md:51-60`). |
| Who signs | Existing machine owners sign stage evidence locally. The lender's own account/topic anchors the daily lend-only root; borrower submits nothing, per amended HCS plan (`T:artifacts/fp/hcs-anchor-wiring/PLAN-v0.md:37-44`). DOVU uses the customer's actor/vault token only after release; no machine or wallet key crosses. No signer or credential exists in the fake prototype. |
| What proves what | Pinned local signature/auditor checks support provenance and consistency, not independent truth of engine usage. A confirmed matching HCS message establishes the public commitment/order, not the computation. A DOVU block acknowledgement adds only local sent/accepted/unknown status. No signed DOVU verification receipt or independent recomputation is demonstrated (TR-1057; `T:artifacts/fp/dovu-access-boundary/BOUNDARY-v1.md:38-41`; `A:04_dovu_fake/src/lib.rs:166-219`). |
| Gates inside sender | Tier 0 default; owner opt-in plus release/customer/schema gates; exact test host; testnet mirror; pinned topic; exact matching reference; one chunk; confirmed lend-only daily publication; post-publication and opt-in lower bounds. No outbound call before all checks (`A:04_dovu_fake/src/lib.rs:230-282`). |
| Attempt handling | Atomically reserve before a live POST; never automatically resend after a lost response or malformed acknowledgement; unreadable state refuses (FP-1895 / FP-1896). Fake set tests that ordering and duplicate policy only. Real durable locking/fsync/restart semantics are a lane prerequisite, not implemented in the fake (`A:04_dovu_fake/src/lib.rs:130-158,273-280`). |
| Vendor contract | DESIGN endpoint seam is the CLI's block-instance POST, not a demonstrated accepted daily-root schema. A schema requiring text, provider/model identities or other fields is incompatible. Do not widen the payload to fit it. Contact/schema work belongs to RADIX; this run contacted nobody (`CLI:src/helpers/tasks.js:100-109`; `T:artifacts/fp/dovu-access-boundary/BOUNDARY-v1.md:3-7`; historical PL T3 report). |
| Rollback | Off stops the next send; already published/sent references cannot be recalled. No DOVU response grants access, mutates settlement or enables an action (`T:artifacts/fp/dovu-access-boundary/BOUNDARY-v1.md:72-76`). |

### Precedence and held work

FP-1874 is RADIX's recorded approval of the proposed boundary with conditions:
Tier 0 until cleared, then Tier 1/customer actor; Tier 2 and minting need separate
rulings. TR-958 corrects the old boundary's TR-901 attribution: TR-901 concerns
outreach, not itself a data-send gate. TR-987 changes barebones **HCS** testnet
default, not DOVU release. TR-1057 leaves DOVU enablement, terms and the actual dev
network unresolved; an offered developer account is not release approval.
This card's fake work does not resolve any of those items.

Do not repeat October's no-caller finding as current product status:
`T:artifacts/fp/hcs-anchor-wiring/PLAN-v0.md:3-9` is historical;
`T:codex/PRODUCT_DESIGN_MAP.md:119` now says HCS is merged, valve shut, never run,
and first write needs RADIX approval, W8 commit and a new build. Likewise,
FP-1896's historical duplicate-send finding is followed by PL-519's fixes and
PL-520's reported tests; this card did not reproduce those old branch gates.

## 4. Built prototype, tests and publication

Repository/branch: `anywave/digigami-audit`, `codex/DOVU-tier1-fake`.
Remote head: **`617beedb5cb008621a784e02a4d2ac4d515eb5ff`**.
Seven new files under `04_dovu_fake/`, **830 additions / 0 removals**.
No existing meter, reconciler or publishing code changed.

The crate is Rust-only, no dependencies, `publish = false`, unsafe forbidden,
library only. The concrete fake client/mirror cannot be replaced with an HTTP
transport through its API. No I/O, env read, account, credential, signer, crypto,
email, chain write or money operation exists. Booleans mean assumed synthetic
conditions, not owner approval. `FakeJournal` is explicitly memory-only; it does
not survive a process loss or provide interprocess locking. It cannot be used as
a production sender (`A:04_dovu_fake/Cargo.toml:1-11`;
`A:04_dovu_fake/src/lib.rs:1-8,87-158,220-282`;
`A:04_dovu_fake/README.md:37-50`).

| Gate, Linux cloud | Result / reproducible command |
|---|---|
| New Rust boundary tests, Rust/cargo 1.85.1 | **23 passed / 0 failed**, `cargo test --offline --manifest-path 04_dovu_fake/Cargo.toml` |
| Named rule-removal mutants | **29 compiled / 29 killed / 0 survived**, `python 04_dovu_fake/mutation_check.py`; compilation errors never count as kills |
| Original Python suite, Python 3.12 / pytest 8.4.2 | **51 passed / 0 failed**, `python -m pytest -q` |
| Formatting / clippy | exit 0: `cargo fmt --manifest-path 04_dovu_fake/Cargo.toml -- --check`; `cargo clippy --offline --manifest-path 04_dovu_fake/Cargo.toml --all-targets -- -D warnings` |
| Development scaffold | ruff **0.14.10**, exit 0: `ruff check 04_dovu_fake/mutation_check.py` |
| Claims lint | **0 problems**, `python 10_publishing/claims_lint.py 04_dovu_fake/README.md 04_dovu_fake/VALIDATION.md` |
| Whitespace / scope | `git diff --check` exit 0; prototype changes only the new directory; report branch changes only this report and lane packs |
| RPP regression suite | **1256 passed / 0 failed**, `python -m pytest tests/ -q -o addopts=`; one existing legacy-format deprecation warning |
| RPP golden vectors | **5 passed / 0 failed**, `python tests/test_golden_vectors_mobius32.py` |
| RPP lint | ruff **0.14.10**, exit 0, `ruff check rpp/ tests/ --ignore E501` |
| Report diff drift | **0 HIGH / 0 MEDIUM / 0 LOW**, exit 0, `python -m tools.drift check --base ae10d65a520d25958197f77e6cf784e6b8d177ce --head <report-commit-SHA> --output-dir <scratch-dir>`; 239 pre-existing pending baselines and 1 advisory retained |
| Citation/link audit | **75 explicit source citations**, paths and line ranges valid; local pack links resolve; vocabulary, clock-value and private-key marker scans clear |

Exact mutant groups, initial surviving test weakness and the final correction
are in `A:04_dovu_fake/VALIDATION.md:19-46`. This is rule-level mutation coverage,
not exhaustive parser/fault coverage. Fixed test names identify their mutations;
no titles are generated from unbounded input. A native Windows run was not
available; TR can repeat the same offline cargo and Python commands. No vendor
test pass or hosted CI result is claimed. No LatticeWorks product checkout was
used or changed in this card; current lane code validation is deliberately
assigned to the packs. RPP code is unchanged; its gates are listed separately
from the fake prototype's tests.

## 5. Lane packs and next steps

- [FP / PL: LW Tier-1 boundary and existing-code inventory](../packs/DOVU-LW-TIER1/JOB.md).
  Fake work first; live work held on current release/W8/schema gates. Reuse the
  existing authority and evidence checks; no new authority/minting feature.
- [FP / Mobius: DovuSink v2 inventory and boundary parity](../packs/DOVU-MOBIUS-INVENTORY/JOB.md).
  Review before new code; retain Tier 0, no per-call sends. The pack is not
  permission to change canon, keys, schemas, networks or the release valve.
- Energy auditor, Secretary and public tools remain later work with the row's
  prerequisites. No packs silently delegate accounts, contact, production
  transactions or authority changes. No lane or lattice message was posted.

**IMPOSED conservative choices:** first USE is the public-reference seam only;
prototype lives in digigami-audit despite energy still being unbuilt; fake-only
closed API, no vendor SDK; no live testnet step; no credential input; no new
cryptography; memory journal explicitly disqualifies live use; retain all owner
holds; distinguish October reports, current source and unverified hosted state.
Do not merge in this card. Review the prototype independently before the report
is used to commission any lane implementation. Both branches are normal pushes,
one each; no PR, merge, force push or shared status-document edit.
