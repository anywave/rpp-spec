---
id: HEDERA-DAY1-001
from: Codex (hedera-day1)
to: TR
repo: anywave/rpp-spec
branch: codex/HEDERA-DAY1
head: refs/heads/codex/HEDERA-DAY1
head_kind: final-branch-ref
source_base: ae10d65a520d25958197f77e6cf784e6b8d177ce
source_freeze: 111ad886c8ab93d687fe692a63e9dd39de80bbd1
task_label: 2026-11-06
observed: 2026-11-06 UTC / 2026-11-05 America/Los_Angeles
type: implementation-and-blocker-report
subject: Shared Hedera layers and product smoke harnesses built; live testnet proof BLOCKED
---

**Live testnet operability is not proved. Mainnet is OFF.** Built and reviewed
one shared HCS layer per language, product smoke entrypoints, the complete
baseline inventory, and concrete LatticeWorks/Mobi wiring packs. No production
valve was enabled. Missing runtime credentials and enforced network policy block
the required real topic/record/mirror proof; fake tests are not ledger evidence.

The newest inbox was fetched and reread at trellis-channel
`b4c57eaee282b87d608c410550cf8f53679c7cd6`; its only TR entry matches this task.
The required scout, findings, wiring and Guardian artifacts are unchanged from
the initial fetched instruction pin `f35da821f38436f0fef461e8ffe9f01dc276ea01`.
No merge, reset of another branch, force push, email, social publication, mainnet
write, real HBAR, account creation or account funding occurred.

| Repo / delivery branch | Reviewed implementation head | Result |
| --- | --- | --- |
| rpp-spec / `codex/HEDERA-DAY1` and `codex/HEDERA-DAY1-python` | `111ad886c8ab93d687fe692a63e9dd39de80bbd1` | Python source freeze; final report-inclusive head is the delivery branch ref above and in the five-line delivery message. |
| mobius / `codex/HEDERA-DAY1-rust` | `acb81ed8e5444852d9eb7a3624eedf127a44dc64` | Standalone real SDK crate, smoke, Mobi job pack; existing Tauri stub/valve retained. |
| digigami-stack / `codex/HEDERA-DAY1-js` | `8d00000650f058b0dae9be636d252a0bc8c3f341` | One locked Node package shared by all six product-labelled smoke entrypoints. |
| hedera-auction-integrity / `codex/HEDERA-DAY1-auction` | `abf7bd74e4dc313205a825021b05141434a9dc5e` | Recovered authorized repo; thin shared smoke launcher and wiring pack. |
| digigami-audit / `codex/HEDERA-DAY1-audit` | `42c433bf226e0f4ad012841e7f99ae0d83e8171d` | Recovered authorized repo; thin shared smoke launcher and wiring pack. |

The [inventory and alpha matrix](../hedera-day1/INVENTORY.md) cover accounts,
HCS, HTS/NFT, schedules, contracts, mirror reads, Agent Kit and MCP, including
every stub/shut/missing boundary. The [code appendix](../hedera-day1/hedera-code-locations.md)
provides compact file:line references. The compressed [complete location index](../hedera-day1/hedera-locations.json.gz)
contains 18,379 references in 1,101 files/archive members across 21 repositories,
with revision pins and no matched source text. Historical documents and broad
false positives are retained explicitly. [All repo baseline SHAs](../hedera-day1/repository-snapshots.json)
include repositories with no Hedera code. Auction ZIP members have member lines,
not invented checkout paths. LatticeWorks remains unavailable in this environment.

Live public sources establish official `@hiero-ledger/sdk 2.90.1` and
`hiero-sdk 0.45.0`, both Apache-2.0. Rust upstream main 0.46.0 is not the published
release. Python `hiero-sdk-python 0.3.0` is Apache-2.0, community maintained and
Pre-Alpha; it is not in Hedera's official supported language list. The Python
backend therefore requires explicit experimental opt-in; shipped Python callers
should use the official JS/Rust boundary. Agent Kit 4.2.0 and MCP 1.2.0 remain
separate optional tooling. [Source URLs, licences and reachability](../hedera-day1/SDK-SOURCES.md)
and [response metadata](../hedera-day1/sdk-sources.json) record the checks.
Scout A (read-only synthetic inspector), then B, then C remains the tool order;
this task's signing harness does not turn the read-only MCP into an operator.

New source entrypoints: `mobius/crates/hedera-day1/src/lib.rs:25` and `src/sdk.rs:24`;
`digigami-stack/packages/hedera-day1/src/index.mjs:16` and `src/sdk.mjs:14`;
`rpp-spec/rpp/adapters/hedera_safe.py:28` and `:101`.
RPP's former silent real-publish stub now calls the shared layer at
`rpp/adapters/hedera.py:222`; its default mock remains local.
Each real backend reads operator credentials only from runtime environment,
defaults to testnet, refuses unknown networks and unflagged mainnet, rechecks
RADIX's literal `true` switch before writes, caps fees and retries, preserves
transaction identity, requires SUCCESS receipts, and checks mirror evidence.
Topic creation checks metadata/submit key; message read-back pins topic, payer,
sequence and exact decoded bytes. Redirects and raw SDK diagnostic logging are
refused. All smoke programs reject mainnet even with the general library flag.

| Validation | Observed result |
| --- | --- |
| Rust fake/published-SDK tests | 15 passed; official SDK compiled on Linux with Rust 1.99.1 and protoc 31.1. |
| Rust named guard-removal mutations | 20/20 killed by intended test failures; compiler failures/timeouts do not count; source restored and clean. |
| JS fake/published-SDK tests and mutations | 18 passed; 18/18 compilable mutants killed with assertion evidence. |
| Python fake/published-SDK tests and mutations | 38 passed, no SDK-test skip; 15/15 compilable mutants failed named assertions. |
| Full RPP regressions / changed Python lint | 1,294 passed / Ruff clean. |
| Recovered audit / auction baselines | 51 audit tests; 5 original auction tests and offline demonstration passed. |
| Product smoke refusal checks | All six labels refuse missing runtime credentials; recovered launchers refuse mainnet even with flag. No live write. |
| Independent review | [Final immutable-source review](../hedera-day1/VERIFICATION.md); initial network allowlist, signed-input snapshot and payer-binding defects fixed before delivery. |

Guard mutations cover default network, mainnet gate/revocation, environment-only
credentials, fees, retry bounds/identity, receipt success and mirror proofs. Fake
fixtures contain no private signing material. Current deployment flag values were
not changed. This is scoped HCS evidence support; SDK installation does not mean
every SDK service has an implemented product flow.

Run JS checks from `digigami-stack/packages/hedera-day1`: `npm ci --ignore-scripts`,
`npm test`, `npm run test:mutations`. Its npm smoke scripts select `digigami`,
`latticeworks`, `token-auditor` and `mobi-connect`; the shared CLI also accepts
`digigami-audit` and `hedera-auction-integrity`, whose repos provide shell launchers.
Mobi additionally has `crates/hedera-day1/scripts/smoke-testnet.sh`.
Python has `scripts/hedera_python_smoke.py`, an explicitly experimental harness.
Every smoke creates a submit-key topic, signs a synthetic record, checks receipts
and compares mirror bytes. To run live, supply an existing disposable testnet
operator through runtime secret configuration and attest `HEDERA_TESTNET_THROWAWAY=true`.
Never put the key in chat, arguments, files, logs or fixtures. Python also requires
`HEDERA_EXPERIMENTAL_PYTHON_ENABLED=true`. No faucet or new account creation runs.

[Runtime readiness](../hedera-day1/runtime-readiness.json) records all operator
variables absent and testnet mirror/hashio probes denied by proxy CONNECT 403.
The enforced policy also has no consensus TCP grants. Allowed registries/GitHub
were reachable with supported per-command network permission; direct Hedera docs
were denied, while the available web connector reached official docs. No blocked
destination was bypassed. The repeat needs testnet mirror HTTPS and the actual
SDK testnet consensus endpoints granted, plus the runtime operator. It must save
public topic IDs, both transaction IDs, sequence/timestamp and exact-byte evidence
before anyone marks the live proof passed.

The LatticeWorks job pack is in the inventory: preserve the live checkout's
actual valves, implement session attribution/start-stop/daily outbox/proofs,
keep non-lend records local and bind lender account/topic/submit key.
Mobi's `docs/codex/HEDERA-DAY1-MOBI-JOB-PACK.md` identifies the exact stub callers,
stored-BYOA-key API replacement, async wiring, signature checks and acceptance.
The standalone resolved Rust SDK graph requires Rust 1.95 while Mobi advertises
1.77.2; consumer toolchain/lockfile and Windows/OpenSSL packaging are unresolved.
Durable restart reconciliation is a product wiring requirement, not supplied by
the in-memory shared layers. Existing customer-wallet consent remains separate
from this authorized environment-signed test harness.

No day-1 HTS/NFT need was established for the named HCS audit/auction/root flows,
so no token/NFT dry run was added. Legacy silver-pancake AVT/Vizor/Soul/consent
paths still have unsafe success-returning stubs, unpinned SDK and mainnet gaps;
they are inventoried, not silently upgraded or claimed safe for alpha. Guardian
policy import/account/IPFS effects were not executed. Live proof, product wiring,
packaging and these excluded legacy paths remain explicit release gaps.
