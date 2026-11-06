# R-HEDERA-DAY1-2-001

Independent security re-review requested by TR on 2026-11-06, completed after
R-DIGI-STACK-2. Baseline: [R-HEDERA-DAY1-001](R-HEDERA-DAY1-001.md) at
`078843ad27d4855791c949c7ba1cb3b14b368782`. Another thread wrote the fixes.
The newest inbox entry and both later RADIX rulings govern this review:
the alpha is testnet only, with no mainnet activation path; every topic with
custom fees is refused and every message submit carries a zero custom-fee limit.

No ledger writes, live smoke, account funding/creation, real credential access,
merge, force push or PR-branch changes occurred. Additional regression tests
and temporary mutations ran in isolated detached worktrees and were restored.
Synthetic signing keys were generated only in memory; no key or key-bearing
object representation was printed or saved. This report is the only delivery
file added to `codex/R-HEDERA-DAY1`.

## PR decisions

READY means no remaining finding in the reviewed scope. READY WITH FIXES means
the listed medium issues still need correction before merge. NOT READY marks
the remaining high-severity credential disclosure. These decisions cover HCS
foundations and thin job packs, rather than complete product/release readiness.

| Repository / PR | Exact reviewed head | Verdict | Remaining findings |
| --- | --- | --- | --- |
| rpp-spec #46 | `ce24da0d0be4fcedb6b988a9d8a5d44155b60a2b` | **NOT READY** | F3-R: HIGH, public signer serialization leaks the private key. |
| mobius #291 | `ecbfcd04412a967f5b35e9b9c5de0b97416f7b83` | **READY WITH FIXES** | F4-R: MEDIUM, admin-key readback omitted; N1: MEDIUM, direct SDK backend bypasses the network-fee ceiling. |
| digigami-stack #2 | `a297f018be71cb3ce467b0fbfe2b48cbe67a1a33` | **READY WITH FIXES** | F4-R: MEDIUM, admin-key readback omitted. |
| hedera-auction-integrity #1 | `c06f501d9d3b25dcd14461f8f042e4916f682fa6` | **READY** | None within its unchanged thin launcher/offline job-pack scope. |
| digigami-audit #1 | `82184a31f14b8bac97f31d46f49ea931de400208` | **READY** | None within that same scope; original F5 is closed. |

The READY launchers do not certify the affected general JS topic-confirmation
API or complete product anchoring. GitHub still reports #291 as not automatically
mergeable against its divergent `fp/v081-usable` base; the writer must resolve
that branch/base issue separately. No merge simulation or resolution was done.
Duplicate rpp-spec #47 is now closed, unmerged, at its old `04da17a6` head; it is
outside this follow-up and does not inherit #46's fixes or verdict.

## Remaining findings

### F3-R — HIGH — Python's public serialization state still exposes the signer key

**rpp-spec #46: `rpp/adapters/hedera_safe.py:43`**, with the retained bound method
at `rpp/adapters/hedera_safe.py:34` and signer slots at line31.

The new signer redacts its own representation and refuses `__reduce_ex__`, so
the original ordinary client/operator repr and pickle leaks are repaired.
However, Python 3.12's inherited public `object.__getstate__()` returns slot
state containing the bound `PrivateKey.sign` method. The pinned SDK's private-key
representation includes raw signing material inside that method's representation.

Using the production backend and actual pinned SDK with a runtime-generated
synthetic key, both of these expressions contained the key:

```python
state = backend.client.operator.signer.__getstate__()
repr(state)
json.dumps(state, default=str)
```

This uses the public serialization protocol, without mangled-slot access or
process-memory inspection. The independent regression has **1 pass / 1 assertion
failure, pytest exit1**; only a leak boolean is asserted or logged. Ordinary
signer repr remains redacted. The existing 103 focused tests and signer-repr
mutation do not cover this protocol.

**Required correction:** explicitly refuse or redact `__getstate__` and verify
public state serialization on the actual SDK signer/client. Retain the current
repr, logging, pickle and exception checks. This belongs with the original F3
signer/serialization fix, rather than a new credential format or SDK replacement.

### F4-R — MEDIUM — JS and Rust ignore an unexpected topic admin key

| Affected PR | Location at reviewed head |
| --- | --- |
| digigami-stack #2 | `packages/hedera-day1/src/index.mjs:102`; requested absent admin at `packages/hedera-day1/src/sdk.mjs:74` |
| mobius #291 | `crates/hedera-day1/src/lib.rs:140`; parser discards admin at `crates/hedera-day1/src/sdk.rs:180`; `TopicView` omits it at `crates/hedera-day1/src/lib.rs:68` |

These SDK create calls request a submit key and **no admin key**. Their mirror
confirmation checks topic ID, memo and submit key but never compares `admin_key`
with that expected absence. An otherwise matching response containing an
unexpected admin key still reports successful confirmation. That contradicts
the requested immutable administration state and the new explicit requirement
to compare both security keys.

JS: actual SDK wire decoding confirms the requested admin is absent; the
unmodified shared API accepts the contradictory fake mirror response. The
independent suite has **2 passes / 1 assertion failure, node exit1**.

Rust: `TopicView` cannot represent the admin field. A review-only probe extracted
the existing mirror decode expression without changing it and passed its result
through the existing `Hedera::create_topic` confirmation predicate and a fake
backend. It returned `Ok(Confirmed)` for an unexpected admin. The assertion
requiring `MirrorMismatch` fails. This was an offline parser/policy probe, not a
live mirror or consensus test; source was restored afterward.

**Required correction:** preserve and compare the expected admin state, including
an explicit check for absent admin when none was requested. Retain submit-key
comparison; add unexpected-admin and malformed/missing-evidence tests, followed
by removal controls. The equivalent JS/Rust corrections and their regressions
can be fixed together. Original Python F4 is closed: Python now writes and
compares both keys, with meaningful altered/missing-key tests.

### N1 — MEDIUM — Rust's public SDK prepare boundary ignores configured network-fee limits

**mobius #291: `crates/hedera-day1/src/sdk.rs:127`**, with ignored configuration
at line28 and unchecked fee assignment at lines75/135.

`SdkBackend::from_env(&config)` discards the config. Its public `Backend::prepare`
accepts an arbitrary `i64 max_fee` and freezes/signs it without enforcing either
the configured maximum or the global 100,000,000-tinybar ceiling. Opaque prepared
handles prevent transaction injection, but this supported direct-backend path
can itself mint an over-limit handle. The normal `Hedera` wrapper does pass its
validated cap, so this is a lower-level API boundary defect, not a bypass through
the existing smoke's default parameters.

An actual offline `SdkBackend::from_env` + `prepare(CreateTopic, fee)` probe used
a configured cap of **1 tinybar** and a generated in-memory signer. It decoded
signed transaction bodies with network fees **100,000,001** and
**9,223,372,036,854,775,807** tinybars. No execute/send call occurred. The security
assertion requiring the configured ceiling fails. The custom-fee zero limit and
direct message preflight remain intact; this concerns the separate network fee.

**Required correction:** retain the validated cap in the SDK backend and reject
caller amounts outside it before freezing/signing, or remove unsupported direct
construction/prepare access behind a validated capability. Add an actual SDK
wire test for both a lowered configured cap and the global ceiling. This can
share the Rust corrective commit with F4-R, but needs its own regression.

## Earlier findings and the two rulings

| Rule / original finding | Re-review result |
| --- | --- |
| Testnet-only alpha | **Pass in the application adapters.** Only testnet constructors and fixed testnet mirror origins remain. No runtime mainnet node list, mirror URL, activation flag or environment-selectable mainnet constructor was found. Non-testnet selection is rejected even with the retired RADIX flag set. General-purpose third-party SDK implementations are not claimed to have removed their unrelated network support. |
| F1: refuse all custom-fee topics | **Closed across Python/JS/Rust.** Every public message boundary requires a readable expected-topic schedule with an explicit empty fixed-fees array. Missing, malformed, unknown, nonempty, zero-valued, HBAR, HTS and exempt fee entries refuse. |
| F1: zero allowance on every submit | **Closed at the constructed wire boundary.** Actual pinned SDK wire/getter tests verify one actual-payer limit containing one zero-HBAR fee and no token denomination, rather than an empty outer list. This remains separate from the network-fee ceiling. |
| F2: send/retry authorization | **Closed within the testnet-only scope.** JS/Python guard concrete consensus dispatch, pin initialized testnet routing and disable hidden gRPC retries; SDK attempts are one. Rust's private client and single-node transactions have no mainnet route, with fresh checks before prepare/shared send/SDK send. Bounded retries retain frozen transaction identity. |
| F3: no printable/serialized keys | **Still open only as F3-R above.** Original Python repr/pickle paths now redact; JS facade inspection/JSON and malformed-input errors remain safe in the probes. Rust backend/signer fields stay private and have no Debug/Serialize implementation. No committed private-key literals were found. |
| F4: admin and submit readback | **Python closed; JS/Rust need F4-R.** Mirror message confirmation still compares decoded payload bytes, topic, payer and sequence; unsuccessful receipts, mismatches and incomplete writes do not pass the tested confirmation gates. |
| F5: audit wording | **Closed.** Current claims lint exits0 with zero findings; independently restoring each of the three old phrases makes the real linter exit1. |

Published pinned protobuf documentation corroborates that an empty custom-fee
outer list accepts any fee, an absent denomination means HBAR, and unlisted or
exceeded fee allowances are refused. The author's pinned consensus research
documents zero-allowance validity. We verified the SDK wire shape and rejection
controls, but did not execute a consensus node or query a deployed testnet
version. Thus this is source/wire evidence, not live fee-enforcement proof.

Official JS `@hiero-ledger/sdk=2.90.1` and Rust `hiero-sdk=0.45.0` pins are
unchanged. Python `hiero-sdk-python==0.3.0` remains explicitly experimental,
community Pre-Alpha rather than an official supported shipping SDK. Apache-2.0
licence records remain. New explicit gRPC/protobuf/prost pins are published
Apache-2.0 packages; all 87 existing JS dependency/integrity records are unchanged.

## Independently executed verification

| Exact head / scope | Baseline tests | Removal controls / additional regressions |
| --- | --- | --- |
| rpp-spec `ce24da0d` | Focused **103 passed**; full RPP **1,359 passed**, zero skipped, exit0. Focused count is included in full. | **24/24** supplied mutations killed by named assertions/expected exceptions; no syntax/import/collection failures. Independent F3-R regression: **1 pass / 1 assertion failure**, exit1. |
| mobius `ecbfcd04`, standalone HCS crate | Core **15 passed**; SDK-enabled **23 regular passed total**, including those core tests, plus **1 compile-fail doctest passed**, exit0. Zero failed/ignored. | **36/36** supplied mutations killed by intended named failures. Independent admin/cap regressions: **2 assertion failures**, cargo exit101, no compilation failure. |
| digigami-stack `a297f018`, shared HCS package | **35 passed**: 15 policy + 3 SDK + 17 fix tests, zero failed/skipped, exit0. Locked install passed. | **38/38** supplied mutations killed, including intended assertions for new fixes. Independent admin/wire/key checks: **2 passes / 1 assertion failure**, exit1. |
| auction `c06f501d` | **5 passed**, exit0; offline demo and shell syntax passed. | **6/6** credential-free launcher refusal checks passed using exact shared JS head. |
| audit `82184a31` | **51 passed**, zero skipped, exit0; shell syntax and claims lint passed. | **6/6** launcher refusals passed; **3/3** separate F5 phrase reversals detected by the real linter. |

The launcher refusals cover absent throwaway opt-in, missing operators, mainnet
with/without the retired flag, previewnet and an excess network fee. Each exits1
with no stdout. Their revisions change documentation only; baseline tests cover
the existing offline products, while the separate refusals exercise launchers.
Two current documentation-policy checks also pass, and three restored old-policy
variants fail separate review-only text checks. Those text checks are not
represented as shipped runtime regressions.

Commands included Python `pytest` focused/full and
`scripts/hedera_python_mutations.py`; Rust `cargo test --offline --manifest-path
crates/hedera-day1/Cargo.toml` with/without `--features sdk` and its committed
mutation runner; JS `npm ci`, `npm test`, `npm run test:mutations`; the auction
unittest/demo, audit pytest/claims lint and both launcher refusal matrices.
Mutation totals are separate from baseline counts. Passing existing mutations
does not establish the missing F3-R/F4-R/N1 coverage: the independent assertions
above fail at these exact heads.

Evidence is retained under each scoped repository's
`work/hedera-review2-evidence/`, with supply-chain evidence at
`rpp-spec/work/hedera-review2-supply/`. Worktrees are clean after all temporary
controls. Full Mobi product/packaging tests and live testnet execution were not
run; this review does not close production wiring, durable restart reconciliation,
Windows/MSRV packaging or release-valve work.

Fix grouping: Python F3-R and serialization tests together; JS/Rust F4-R and
matching admin-state tests together; Rust N1 can accompany its F4-R correction
with a separate fee-cap test. F1/F2/testnet-only and F5 need no demonstrated code
correction in this pass. PR descriptions still describe the superseded flag
policy and should be aligned with the current rulings by the writer.
