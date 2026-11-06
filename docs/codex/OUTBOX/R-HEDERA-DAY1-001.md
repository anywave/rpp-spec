# R-HEDERA-DAY1-001

Security review requested by TR's newest R-HEDERA-DAY1 inbox entry dated
2026-11-06. Another thread wrote these changes. Reviewed the author report at
`rpp-spec@04da17a6a13b49733bef441e2b991c9c3d161222`,
`docs/codex/OUTBOX/HEDERA-DAY1-001.md`, and the exact heads below.

All transaction tests used fake transports or credential-free SDK construction.
No ledger write, live smoke, account creation/funding, real credential access,
merge, force push, or PR-branch change occurred. Registry/package downloads and
GitHub reads were the only external service work. The requested review document
is the only file added on the review branch.

## PR decisions

These decisions cover the added HCS foundations and the stated scope of each
PR. They do not certify complete product wiring, live testnet operation, HTS/NFT,
schedules, contracts, or a production launch.

| Repository / PR | Exact reviewed head | Verdict | Findings / scope |
| --- | --- | --- | --- |
| rpp-spec #46 | `04da17a6a13b49733bef441e2b991c9c3d161222` | **NOT READY** | F1–F4. Experimental Python boundary needs security corrections. |
| rpp-spec #47 | `04da17a6a13b49733bef441e2b991c9c3d161222` | **NOT READY** | Identical commit and findings to #46; not a separate implementation or independent test run. |
| mobius #291 | `acb81ed8e5444852d9eb7a3624eedf127a44dc64` | **NOT READY** | F1. Standalone Rust HCS crate; production Mobi wiring remains absent. |
| digigami-stack #2 | `8d00000650f058b0dae9be636d252a0bc8c3f341` | **NOT READY** | F1, F2. General shared JS write boundary needs correction. |
| hedera-auction-integrity #1 | `abf7bd74e4dc313205a825021b05141434a9dc5e` | **READY** | Thin testnet-only launcher and honest wiring job pack; no direct security defect found. |
| digigami-audit #1 | `42c433bf226e0f4ad012841e7f99ae0d83e8171d` | **READY WITH FIXES** | F5, documentation lint only. Same limited smoke/job-pack scope; no direct launcher security defect found. |

The two launchers pass fixed product labels to the shared JS smoke, which
rejects mainnet before constructing a client, even when the general library
flag is set. Its newly created topics have no custom fees. Their READY status
does not approve general use of the affected JS API, implement product
anchoring, or authorize any ledger write during this read-only review.

GitHub also reports #291 as not automatically mergeable. Its declared
fp/v081-usable base diverges from the main lineage used by the implementation;
the PR includes earlier main merges as well as the new crate. Resolve that
branch/base issue in the writer's lane. No merge or conflict resolution was
attempted here.

## Findings

### F1 — HIGH — All three adapters leave HCS custom fees uncapped

| Affected PR | Location at reviewed head |
| --- | --- |
| rpp-spec #46/#47 | `rpp/adapters/hedera_safe.py:227`; network fee assignment at `rpp/adapters/hedera_safe.py:209` |
| mobius #291 | `crates/hedera-day1/src/sdk.rs:105` |
| digigami-stack #2 | `packages/hedera-day1/src/sdk.mjs:81` |

The adapters limit the network transaction fee to at most 100,000,000 tinybars
and accept arbitrary valid topic IDs. They do not serialize a payer custom-fee
allowance for HCS submissions. Network fees and topic-assessed HBAR/token custom
fees are separate charges.

The official pinned HAPI `services/transaction.proto:708` documents the
max_custom_fees field: **"If left empty, the users are accepting to pay any
custom fee."** The bundled JS protocol and Rust SDK documentation agree.
An existing fee-bearing topic can therefore assess fees outside the advertised
one-HBAR ceiling. The single-chunk restriction does not address this charge.

Independent offline SDK evidence:

- Python: decoded the actual protobuf used by the real pinned SDK's fake RPC
  sends. Network fee was 100,000,000; max_custom_fees had zero entries.
- JavaScript: decoded actual prepareSdkTransaction bytes. Every per-node
  alternative had that network fee and an empty maxCustomFees list. A regression
  assertion requiring a custom-fee bound fails.
- Rust: applied the production transaction policy macro and the message-building
  calls to the official SDK transaction. Getter evidence was
  `network_fee_tinybars=100000000 custom_fee_limits=0 max_chunks=1`.

**Required fix:** set explicit consensus-enforced payer custom-fee limits,
including allowed denominations, or use a transaction policy that refuses
unapproved custom fees. Test the SDK wire/getter values, excess HBAR/token fees
and the removal of those limits. A mirror preflight alone is insufficient if a
fee schedule can change before consensus. Keep the network fee ceiling too.
This is one shared policy fix across Python, JS and Rust.

### F2 — HIGH — JS and Python can send after RADIX's flag is revoked

**JS:** `packages/hedera-day1/src/index.mjs:81`, with sends at
`packages/hedera-day1/src/index.mjs:86` and
`packages/hedera-day1/src/sdk.mjs:34`, digigami-stack #2.

The flag is checked before asynchronous preparation. It is not checked again
after signing/preparation or before each retry. Two fake-only regressions fail:
revoking the flag during prepare still executes once; revoking it during retry
delay records send authorization states `[true, false]` and permits completion.

**Python:** `rpp/adapters/hedera_safe.py:213`, rpp-spec #46/#47.

The wrapper validates at line 207, then delegates sends/retries to the SDK.
Using the real 0.3.0 SDK with every discovery/channel/RPC boundary replaced by
fakes, the first BUSY response removed the flag. The second fake consensus send
observed no flag, and the backend returned SUCCESS status 22. The observed send
authorization states were `[true, false]`. There is also a gap between the
initial check and execution while preparing/signing.

These are revocation bypasses after an initially permitted construction, not a
claim that a fresh unflagged mainnet configuration is accepted. Defaults and
initial mainnet refusal tests pass. Test flags existed only in isolated fake
processes; no deployed authorization was changed.

**Required fix:** recheck the actual runtime authorization at the concrete send
boundary and before each resend. Have the shared boundary own a single bounded
retry budget, retain the frozen transaction identity, and prevent hidden SDK
retries from bypassing revocation. Add delayed-preparation and mid-retry
revocation tests against both the shared API and actual SDK boundary. Rust's
adapter already checks before prepare and each send.

### F3 — HIGH — Python's exposed SDK objects print private signing material

**Location:** `rpp/adapters/hedera_safe.py:198`, rpp-spec #46/#47.

set_operator retains the parsed key inside the public SDK client. In the pinned
0.3.0 SDK, the PrivateKey repr includes to_string_raw(); client.operator is a
NamedTuple containing that key, and the client's attribute dictionary also
contains operator_private_key. Ordinary object formatting can disclose the
operator credential despite fixed exception text and a silent logger.

With a generated, ephemeral synthetic key, independent checks confirmed the key
was present in both repr(backend.client.operator) and repr(vars(backend.client)).
Only booleans were printed; no key text or representations were saved in logs.
Clearing the local secret variable at line 204 leaves these retained copies.

**Required fix:** keep credential-bearing SDK state behind a non-revealing
signer boundary and ensure ordinary operator/client formatting redacts private
keys. Test the actual pinned SDK objects, not just a fake exception marker or
the outer Session repr. If the experimental Python SDK cannot meet this
boundary, retain the documented official JS/Rust service boundary for shipping
callers. JS layer inspection/JSON and Rust's non-Debug backend did not expose
keys in this review.

### F4 — MEDIUM — Python confirms topic creation without checking the written admin key

**Location:** `rpp/adapters/hedera_safe.py:136`, rpp-spec #46/#47;
the admin key is written at `rpp/adapters/hedera_safe.py:223`.

Creation sets both submit and admin keys to the operator public key. Mirror
verification checks topic ID, memo and submit key but omits admin key. A fake
mirror response with a different admin key and otherwise matching metadata and
creation transaction returned mirror_confirmed=True. Thus the confirmation can
assert the written security metadata is verified while a deliberate field
contradicts it.

Compare the admin key before confirming and add an altered/missing-admin-key
negative control. This is Python-specific; the JS and Rust create calls here do
not set an admin key.

### F5 — LOW — Audit job-pack wording fails its claims linter

**Locations:** digigami-audit #1, `docs/HEDERA-DAY1.md:41`,
`docs/HEDERA-DAY1.md:54`, `docs/HEDERA-DAY1.md:79`.

The repository's claims-lint command exits 1 with three PROOF_WORD findings on
the new document. These sentences accurately distinguish synthetic testnet or
inclusion evidence from completed product anchoring; no false anchored-success
claim was established. Adjust the wording to the accepted vocabulary and rerun
the linter. This is a documentation/check cleanup, not a launcher key or network
defect, and accounts for the READY WITH FIXES verdict.

## Independent validation

| Exact source scope | Tests run and result | Mutation / negative evidence |
| --- | --- | --- |
| rpp-spec #46/#47, one unique head | Focused 38 passed, zero skipped; full suite 1,294 passed, zero skipped, exit 0. The focused tests are included in the full count. | 15/15 supplied named mutations killed. Additional real-SDK/fake-RPC probes reproduce F1–F3; wrong-admin mirror probe reproduces F4. |
| mobius #291 standalone crate | Core 12 passed; SDK-enabled run 15 passed total, including those 12 and 3 SDK tests, exit 0. No failed/ignored tests. | 20/20 supplied named mutations killed. Additional credential-free production-policy probe confirms empty custom-fee limits. |
| digigami-stack #2 | 18 passed: 15 policy/fake + 3 official-SDK offline tests; zero skipped, exit 0. | 18/18 supplied mutations killed. Additional four security tests: 1 pass / 3 assertion failures, exit 1; the failures reproduce F1 and both F2 timings. |
| auction #1 | Five original offline tests and demo passed; shell syntax check passed. | Six credential-free launcher refusal cases passed; every refusal exits 1 with no stdout. |
| audit #1 | All 51 baseline tests and shell syntax check passed. | Same six refusal cases passed. New-document claims lint exits 1, three findings, F5. |

The launcher refusals cover absent throwaway opt-in, missing operators,
unflagged mainnet, flagged mainnet, unknown network, and excess network fee.
No live smoke was run. Baseline auction/audit tests exercise their existing
offline products; the separate refusal checks exercise the new launchers.

Supplied mutation runners were inspected. JS requires syntax success and
assertion/TAP failure, Python compiles mutants and requires pytest exit 1 plus
the named failed test, and Rust requires the intended named failed test and
rejects compiler failures/timeouts. Some Rust source-boundary assertions
supplement behavioral tests. The counts establish those tested checks; they
do not cover the omitted custom-fee, in-flight revocation, Python repr or admin
readback cases demonstrated above.

Removing one redundant inner JS error sanitizer left the tests green, but outer
public-boundary sanitizers still preserved the rule. This was not counted as a
key-leak finding or a failed safety mutation.

Representative commands from the respective detached worktrees:

```text
python -m pytest -q tests/test_hedera_safe.py
python scripts/hedera_python_mutations.py
python -m pytest -q
npm ci --ignore-scripts
npm test
npm run test:mutations
cargo test --offline --manifest-path crates/hedera-day1/Cargo.toml
cargo test --offline --manifest-path crates/hedera-day1/Cargo.toml --features sdk
python3 crates/hedera-day1/scripts/mutation_check.py
bash -n scripts/hedera-testnet-smoke.sh
python 10_publishing/claims_lint.py docs/HEDERA-DAY1.md
```

Python used an isolated 3.12 venv and the pinned SDK. Rust used 1.99.1 and
protoc 31.1; public build dependencies/tool artifacts were downloaded before
offline tests. Node was 24.19.0. Install scripts were disabled for Node setup.
Only disposable worktrees/scratch were changed for negative controls; tracked
source was restored and all five exact-head worktrees finished clean.

Logs and independent probes remain in each repository's
`work/hedera-review-evidence/`; registry/signature-scan evidence is in
`rpp-spec/work/hedera-supply-evidence/`. Neither is a PR-branch change.

## SDK, key and confirmation conclusions

- Official JS `@hiero-ledger/sdk` 2.90.1 and Rust `hiero-sdk =0.45.0` are exact
  pins. Fresh npm/crates metadata reads confirmed the published identities and
  Apache-2.0 licences. The JS lock has registry integrity hashes, including the
  pinned SDK. Rust's reusable crate leaves its transitive lock uncommitted; this
  is disclosed rather than a reproducible product-package claim.
- Python `hiero-sdk-python==0.3.0` is exact pinned but **community Pre-Alpha**,
  not an official-supported Python SDK. The optional dependency at
  `pyproject.toml:39`, experimental runtime opt-in, and
  `docs/codex/hedera-day1/SDK-SOURCES.md:11` disclose that accurately. It must not
  be described as a shipping official SDK. Apache-2.0 is recorded for all three
  direct SDK packages; full transitive distribution notices remain separate.
- No operator/private-key literal was found in the added source, fixtures or
  inventory. New adversarial probes generated synthetic keys only at runtime
  and suppressed their values. Fixed public errors and silent SDK logging are
  useful, but Python's printable retained key is the concrete exception, F3.
- Message confirmation checks SUCCESS, topic, payer, sequence and exact decoded
  bytes. Mismatches/exhausted polling and failed receipts do not become message
  success in the exercised paths. Topic metadata is read back; F4 identifies
  the missing Python field. One <=1024-byte chunk and a fixed transaction ID
  avoid multi-chunk partial-success and new-ID retries in the shared calls.
- Retry/poll counts are finite. JS has both outer and SDK attempt budgets:
  configured N can allow up to N-squared SDK execution attempts (at most 25),
  rather than N total network attempts. Its documentation says bounded
  SDK/wrapper attempts. Rust sets SDK attempts to one; Python uses the SDK's
  bounded loop. F2 shows why finite internal retries still need revocation.
- No real consensus/mirror round trip or end-to-end timing proof was performed.
  Ambiguous writes remain unconfirmed. Restart-safe durable reconciliation,
  retained failure transaction identity, consumer MSRV/Windows packaging and
  production product valves/wiring are still release work, as the author
  report acknowledges. An SDK installation or product-labelled smoke does not
  establish those capabilities.

Fix F1 across all three adapters with shared wire-level regressions. Fix F2 in
the JS/Python concrete send paths with delayed/retry revocation tests. F3/F4
can share one Python hardening change. F5 is independent wording cleanup.
Keep #46/#47 as duplicate review entries; applying or merging both is not needed.
No merge or execution of the proposed live follow-up was authorized or performed.
