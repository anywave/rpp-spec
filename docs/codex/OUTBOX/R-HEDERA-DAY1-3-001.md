# R-HEDERA-DAY1-3-001

Independent security re-review under TR's newest 2026-11-06 inbox entry, blob
`674f633c880e530785bd85e06bb4164e71b4897f`. R-DIGI-STACK-3 was reported first
at `506c7714e7b0b5422fada8cd7690340aaeacd3ba`, as requested. Baseline:
[R-HEDERA-DAY1-2-001](R-HEDERA-DAY1-2-001.md) at
`b17a13ca048f5cfe472d132186a8bda4fb130756`. Another thread wrote FIX-2.

**F3-R, F4-R and the earlier Rust N1 are closed. Python is READY WITH FIXES for
one new LOW native-reference cleanup issue; Rust and JavaScript are READY in
the reviewed HCS foundation scope.** No remaining key-disclosure, mainnet-route,
custom-fee or incorrect-confirmation defect was established in this pass.

No merge, force push, PR-branch changes, ledger writes, live smoke, account
funding/creation or real credential access occurred. Only rpp-spec, mobius,
digigami-stack and trellis-channel were used. Tests used fake discovery/RPC/mirror
transports and runtime-generated synthetic keys; key-bearing values and object
representations stayed in memory. Native probes disabled core dumps. Temporary
controls ran in isolated detached worktrees/copies and were restored. This
report is the only delivery file added to `codex/R-HEDERA-DAY1`.

## PR decisions

| Repository / PR | Exact reviewed head | Verdict | Result |
| --- | --- | --- | --- |
| rpp-spec #46 | `42e7c75a4f742e830adc7c37fe2b6a504c97a6ee` | **READY WITH FIXES** | F3-R closed; N2 LOW callback-reference retention after interruption. |
| mobius #291 | `2d8d036792aa97548b51d04491ee9b2afe337d83` | **READY** | F4-R and N1 closed; no remaining code finding established. |
| digigami-stack #2 | `2904d82907eb8dae1bf8fcb0663ec2370ce11b9c` | **READY** | F4-R closed; no remaining code finding established. |

READY covers these standalone testnet HCS foundations, rather than complete
product/release readiness. GitHub still reports #291 as not automatically
mergeable against its divergent `fp/v081-usable` base. Resolve integration in
the writer's lane and verify any resulting change; no merge simulation or
conflict resolution was performed. Closed duplicate #47 and the unchanged
auction/audit job packs are outside this three-PR follow-up.

## N2 — LOW — Interrupted native pinning can leave an unregistered callback reference

**rpp-spec #46: `rpp/adapters/hedera_safe.py:143`**, before the rollback-protected
block at line144 (capsule allocation is line145). This is a resource/key-lifetime
issue, distinct from the repaired F3-R print/serialization disclosure.

_Signer increments the native reference count of the bound signing operation,
then enters the try block that rolls back failed capsule allocation. A
KeyboardInterrupt delivered after that increment but before entering the block
leaves no capsule or registry entry owning the extra reference. The outer
handler clears key/operation locals and raises a fresh interruption, but cannot
balance the orphan reference. GC and _close_signers cannot find/release it if
the calling process catches the interruption and continues.

Independent probes confirmed this in three ways, including an unchanged-source
trace that delivers **actual SIGINT at line144** after the real Py_IncRef. The
harmless receiver remains alive after caller references are dropped and GC
runs; the registry is empty; _close_signers does not release it. One exact
balancing unpin in review cleanup releases it. A separate actual-SDK synthetic
key weak-reference probe agrees and its required-release assertion exits1.
The trace does not retain frame-local snapshots or alter product code.

No printable/serialized key, stale-handle signing, unauthorized send or native
crash was demonstrated. Normal process termination reclaims memory; the issue
is retained callback/key memory in a process that continues after interruption.
Ordinary allocation/registry rollback and concurrent invocation controls pass.

**Correction:** make native ownership transfer/rollback cover the post-increment
interruption window without introducing unbalanced decrements. Add an actual
interruption regression that verifies receiver release, an empty registry and
safe repeated cleanup. Preserve the existing opaque public state and stale-handle
guards. This correction belongs with Python's native ownership/cleanup tests;
no JS/Rust correction is needed for it.

Evidence: `work/hedera-review3-evidence/capsule/pin_interrupt_probe.py`,
`pin-interrupt-results.json`, Python's `test_pin_interrupt_regression.py` and
the independent `cross/native_pin_sigint_probe.py`/JSON. All report only
booleans/counts/fixed labels, without key bytes.

## Requested fixes rechecked

### Python F3-R: public state and key-bearing diagnostics

**Closed within the tested ordinary public-object/diagnostic boundary.**
Signer slots contain only the public key at `rpp/adapters/hedera_safe.py:132`.
The operation registry contains opaque native capsules, rather than a raw bound
SDK private-key method. Explicit state/reduction/pickle/copy/deepcopy protocols
refuse at lines187–203. Base object state/reduction helpers, vars, JSON, repr,
logging, bound callback inspection and public function-global rendering do not
recover key bytes in the tested actual SDK objects.

Key-bearing signing callback failures clear the operation local at line107 and
raise the replacement outside the original handler at line112. Constructor
inputs/operations clear at line158, with replacement errors at line162. Backend
initialization handles partial signers at lines453–463; record signing replaces
its failure graph at lines521–527. Both Ed25519 and ECDSA were exercised,
including malformed inputs, control-flow exceptions, cancellation, exception
groups and safe SystemExit codes.

Independent supplementary probes passed **28 public-protocol/error-graph cases**
and **6 actual-SDK execution-error cases**. They capture formatted traceback
locals, context/cause chains, fields and serialized diagnostic objects in memory
and check for synthetic key bytes before reporting booleans. Some non-key-bearing
SDK precheck errors still remain reachable through the `__context__` of errors
raised by `_execute`; no natural key-bearing object was found there after the
signer correction. We do
not claim every SDK exception graph is universally detached.

An independent harmless ownership probe also passed **34 lifecycle checks**,
including 1,000 GC cycles, plus **3 shutdown assertions**. It covers balanced
ordinary pins/releases, allocation/registry rollback, saved-capsule invalidation,
repeated close and concurrent close. N2 is the separate interruption gap above.
This is experimental CPython code, not isolation against arbitrary same-process
native-pointer access, debugger/memory inspection or explicit environment reads.
Free-threaded CPython, subinterpreters and other platforms remain unverified.

### Rust F4-R and N1: strict topic keys and retained fee ceilings

**Closed.** `crates/hedera-day1/src/sdk.rs:79` parses both admin and submit key
states, distinguishing missing evidence from explicit null admin. Supported
types require their appropriate raw-hex lengths; malformed shapes/types/bytes
refuse. Shared creation snapshots the expected submit key before preparation
at `crates/hedera-day1/src/lib.rs:108` and checks absent admin plus that key at
line144. Hex case normalization preserves byte identity.

SdkBackend retains the validated private Config at `sdk.rs:46`. The positive,
configured and global network-fee ceilings are checked at `sdk.rs:174`, shared
entry at `lib.rs:107`, direct prepare at `sdk.rs:189`, and actual prepared-body
send at `sdk.rs:226`. A handle prepared by a higher-cap backend cannot bypass
the lower receiving backend's cap. Zero/negative/excess values refuse before
mirror reads or dispatch; changing environment values later does not loosen
the retained ceiling. Custom-fee limits remain a separate zero allowance.

Independent Rust probes passed **3 tests**: 72 key-representation cases across
Ed25519/ECDSA using actual SDK wire plus the production parser/shared
confirmation, portable message-handle/lowered-cap checks and 12 invalid
create/message fee cases, and key-safe malformed-input/public-output checks.
SdkBackend and Prepared expose no Debug/Display/Serialize implementation; their
private signer state is not accessible through those public types. Upstream
PrivateKey itself can format key material. Public errors remain fixed categories.

Coverage follow-up: removing only the raw-length comparison leaves the supplied
topic-key regression passing; the independent valid-owner-bytes/other-supported-
key-type case detects that removal with an assertion failure. The guard is
present and correct at this head, and supplied removals of the F4-R fix are
caught. Retain this additional reviewer case in the shipped regression suite.

### JavaScript F4-R: requested key states frozen before preparation

**Closed.** `packages/hedera-day1/src/index.mjs:112` snapshots absent admin and
the typed submit key into frozen outer/inner objects before preparation. Mirror
confirmation at line115 requires both fields explicitly, compares null admin,
and checks the exact typed key object. SDK agreement at `src/sdk.mjs:74` checks
the snapshot against the actual key used to construct the transaction.

The committed actual-wire/mirror matrix covers both signing algorithms and 70
key-state combinations. Four independent tests also pass: adapter mutations
during preparation/mirror cannot replace the original expected key; a mirror
matching only the changed key refuses; nested/outer mutation attempts fail;
normal inspection, JSON, property enumeration, errors/causes and captured logs
reveal no generated key across prepare/receipt/mirror/sign/verify failures.

## RADIX rulings and retained controls

All three application adapters still have only testnet constructors and fixed
testnet mirror origins. No runtime mainnet node list, mirror URL, enabling flag
or environment-selectable mainnet client was found. Non-testnet requests refuse
even with the retired RADIX flag set. General-purpose third-party SDK network
support is outside that application boundary.

Every submit retains the strict readable-empty topic custom-fee preflight and
one actual-payer allowance containing one zero-HBAR FixedFee, with no HTS
denomination. Missing/malformed/nonempty schedules, including zero-valued and
exempt fee entries, refuse. SDK wire/getter and removal controls still pass.
Prepared retry identity, bounded attempts, concrete JS/Python dispatch guards,
receipt success and exact mirror message bytes/topic/payer/sequence controls
remain passing. No deployed-node or live testnet fee-enforcement claim is made.

SDK and dependency pins are unchanged: official JS2.90.1 and Rust0.45.0;
experimental community Pre-Alpha Python0.3.0. Existing Apache-2.0 licence records
remain. All 87 JS dependency/integrity records match the prior lock. Rust's
proto/prost pins and the JS gRPC pin are unchanged. No new private-key literal
candidate was found in the changed source, tests or evidence documents.

## Independently executed tests

| Exact scope | Baseline | Supplied removal controls | Additional review checks |
| --- | --- | --- | --- |
| rpp-spec `42e7c75a` | **212 focused passed; 1,468 full passed**, zero skipped, exit0. Focused included in full; one existing legacy-address warning. | **49/49 killed**, runner exit0; compiled mutants must fail the intended named assertion/expected-exception check. | 28 cross-protocol/error cases + 6 execution-error cases passed; 34 lifecycle checks + 3 shutdown assertions passed; N2 release regression fails as intended. |
| mobius `2d8d0367`, standalone HCS crate | **15 core passed; 27 SDK-enabled regular passed total + 1 compile-fail doctest passed**, zero failed/ignored, exit0. | **50/50 killed** by intended named assertion failures, runner exit0. | 3 independent tests passed, including the 72-case key matrix and retained-cap checks. |
| digigami-stack `2904d829`, shared HCS package | **39 passed** (15 policy + 3 SDK + 17 fix + 4 topic-key tests), zero failed/skipped, exit0. | **45/45 killed**, including all 7 new F4-R controls, runner exit0. | 4 independent tests passed, exit0. |

Commands: Python `pytest -q tests/test_hedera_safe.py
tests/test_hedera_sdk_security.py`, `pytest -q`,
`python scripts/hedera_python_mutations.py`; Rust `cargo test --offline
--manifest-path crates/hedera-day1/Cargo.toml` with/without `--features sdk` and
`python crates/hedera-day1/scripts/mutation_check.py`; JS `npm test` and
`npm run test:mutations` in packages/hedera-day1. Existing pinned dependency and
toolchain installations were reused. Mutation totals and supplementary probes
are separate from baseline counts; syntax/import/timeout/native-crash failures
were not counted as kills.

Evidence is under each scoped repository's `work/hedera-review3-evidence/`:
`python/`, `cross/`, `capsule/` in rpp-spec; `rust/` in mobius; `js/` in
digigami-stack. Tracked worktrees are clean after controls. Product wiring,
durable restart reconciliation, live testnet proof, Mobi Windows/MSRV packaging
and full product/release gates remain outside this read-only security re-review.
