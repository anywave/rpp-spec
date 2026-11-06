# HEDERA-DAY1-FIX — independent final source review

**F1–F4 are resolved in the reviewed HCS foundations under the latest RADIX rule: day-1 alpha is testnet only. No outstanding defect was found in the exercised boundaries.** This is not a verdict on complete product wiring, live testnet operability, HTS/NFT, schedules, contracts or production release.

| Source repository | Exact immutable reviewed code head |
| --- | --- |
| rpp-spec / Python | `4395e27889a8ec6a2a5e40452a800c0cc209ccee` |
| digigami-stack / JS | `a297f018be71cb3ce467b0fbfe2b48cbe67a1a33` |
| mobius / Rust | `ecbfcd04412a967f5b35e9b9c5de0b97416f7b83` |

The checked source matched these commits after validation. Later report-only commits may retain these as source-freeze pins. This review made no changes to owners' code, no network ledger writes, no account creation/funding, no mainnet call, no real-HBAR operation, no real credential access/addition, no email, merge or push. Synthetic Python signing material was generated only in memory for actual-SDK probes; no values were written to files or emitted on either successful or intentionally failing probes.

## Findings and policy closure

| Finding | Verified behavior and concrete source |
| --- | --- |
| F1 — separate HCS custom fees | Every message SDK body carries a **nonempty payer allowance containing one zero-HBAR fee and no HTS denomination**, while retaining the separate network transaction-fee cap. Actual signed JS/Python request bodies and Rust unsigned wire/getters preserve the zero-valued repeated entry and bind the allowance to the transaction payer. `rpp/adapters/hedera_safe.py:331`; `packages/hedera-day1/src/sdk.mjs:76`; `crates/hedera-day1/src/sdk.rs:82`. |
| F1 — readable policy and races | Shared/backend preflights refuse every nonempty schedule, including zero-valued, HBAR, HTS, exempt or malformed entries; missing/null/unreadable/unknown shapes also refuse before preparation/submission. Topic identity is checked. Mirror preflight is supplemented by consensus-enforced wire limits, so a later positive-HBAR fee exceeds zero and a later unlisted HTS fee has no permitted denomination. `hedera_safe.py:150`; JS `src/index.mjs:112`; Rust `src/sdk.rs:95`. |
| F2 — alpha routing | Mainnet selection, construction, mirrors and activation logic have been removed from the new layers. Non-testnet choices refuse even with the obsolete flag set true. Fresh runtime network checks guard subsequent sends. JS/Python also pin initialized SDK routing: ordinary exposed SDK network reassignment/map changes cannot redirect the shared call. Independent negative probes against the official SDK mainnet endpoint produced **zero actual fake RPC calls**. |
| F2 — concrete sends and retries | Python `_SendGuard` checks the runtime choice, initialized route and total send budget at the concrete RPC invocation; SDK/native retries are disabled. JS checks after signing and at raw gRPC `makeUnaryRequest`, after initialization/readiness; SDK/native retries are disabled. Independent delayed-initialization, delayed-readiness/request-construction, BUSY-change and exact-three-attempt tests passed. Python `hedera_safe.py:47`, `:68`, `:89`, `:299`; JS `src/transport.mjs:9`, `:24`, `:28` and `src/sdk.mjs:106`. |
| F2 — Rust scope | The private SDK client is constructed only for testnet; every frozen transaction has exactly **one node**, one SDK attempt and one transaction identity. Shared retries and the SDK-send API re-read the runtime network. Actual getter/wire tests establish one serialized node alternative. Prepared handles are opaque. This removes mainnet routing and hidden multi-node alternatives; it does **not** claim a private tonic RPC interceptor or cancellation of an already-started SDK operation. |
| F3 — actual Python SDK state | `set_operator_with` retains an opaque, slot-only, redacted and unpicklable callback; the SDK client's/operator's private-key field is empty. Independent actual-SDK inspection covered backend/client/operator/signer, their ordinary dictionaries, `repr`, `str`, JSON, logging and pickle. No generated-key marker appeared. Deliberately restoring a raw SDK private-key field produced the intended assertion failure, with only context names/booleans emitted. `hedera_safe.py:28`, `:290`. |
| F4 — topic keys | Python creation writes both submit/admin public keys; mirror confirmation checks both. Missing and deliberately wrong admin **and** submit keys were independently refused while all other creation/transaction evidence was valid. `hedera_safe.py:224`, `:328`. |

The custom-fee consensus conclusion is grounded in pinned node `9efa5c465a49249e55235d560b4c8addad4a0182`: generic precheck permits zero, requires a nonempty inner allowance, and the consensus handler enforces denomination/amount bounds. See the companion [fee protocol evidence](FEE-POLICY.md) and [source metadata](fee-research.json). This is source evidence; no deployed node/version or Java node suite was exercised.

## Validation independently executed at the pinned heads

| Scope | Result |
| --- | --- |
| Python focused suite | **103 passed, zero skipped.** |
| Python separate adversarial probes | Seven actual-SDK/fake-RPC cases passed; seven-object-context formatting/serialization/logging probe passed; public client-routing mutation refused with zero RPC calls. |
| JS supplied suite | **35 passed, zero skipped** (15 shared-policy, 3 SDK, 17 fix cases). |
| JS separate adversarial probes | Nine actual-SDK/fake-raw-gRPC cases passed, including every-node wire limits, initialization/readiness/signing choice changes, BUSY change, exactly three shared attempts, missing/malformed/HTS/zero schedule refusals and routing mutation. The original route-mutation probe also refused with zero RPC calls. |
| Rust SDK-enabled suite | **23 passed, zero ignored** (15 core + 8 SDK), plus one successful compile-fail documentation test proving opaque construction. Actual production message-builder getter/wire assertions require one node and explicit zero payer allowance. |
| Independent guard-removal controls | Five compilable in-memory/source-function controls failed the intended assertions: concrete Python send guard, custom-fee wire allowance, topic-fee preflight, admin readback and raw SDK private-key retention. No syntax/compiler failure was counted. |

The supplied mutation runners and their saved assertion evidence were inspected: **Python 24, JS 38, Rust 36 distinct rules**. Rust evidence combines the 35-rule run with the opacity control; the strengthened single-node control was also rerun. Named failed assertions, not compiler failures/timeouts, establish those kills. The source was restored; the final pinned suites above then passed. Some Rust API-boundary controls use source assertions in addition to behavioral/getter/wire tests; the compile-fail documentation check is separate from mutation kill counts.

Independent scripts: `hedera-fix-independent-python.py`, `hedera-fix-independent-python-redaction.py`, `hedera-fix-python-routing-probe.py`, `hedera-fix-independent-js.mjs`, `hedera-fix-js-routing-probe.mjs`. Saved independent suite logs: `hedera-fix-review-js-tests.log`, `hedera-fix-review-rust-tests.log`. They live under `/workspace/work/`; no script contains signing material.

## Scope that remains explicit

Live testnet proof is still unperformed. Fake receipts and source-level consensus rules are not real ledger evidence. Product valves/wiring, restart-safe reconciliation and installer/MSRV/Windows packaging remain the separately documented release work.

The Rust runtime guard is immediately before each SDK-send operation; an SDK call already in flight is not cancelled by a later environment change. Its client target stays testnet and there is no mainnet route or enable flag. JS/Python concrete checks also cannot retract a request already handed to the transport.

F3 covers ordinary representation, serialization and logging of exposed SDK state. It does not claim to withstand malicious in-process code deliberately invoking signers, inspecting mangled/private fields or reading the process environment. Shipping JS exposes the guarded `sdkLayer` facade; low-level construction hooks are internal test seams.

F5's audit wording/linter change is outside this source-security review; root owns its evidence and final report. The duplicate rpp-spec PR entries remain duplicate review targets; this review did not close either PR.

After this review, the complete current Rust runner was executed against the same immutable source head: all 36/36 named mutations were killed in one run. The source hashes, working tree and index were restored exactly. This supersedes only the earlier phased-run qualification above; it does not change the code or review scope.
