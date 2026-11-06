# HEDERA-DAY1-FIX-2-001

Closes F3-R, F4-R and N1 from
`docs/codex/OUTBOX/R-HEDERA-DAY1-2-001.md`, read at review branch
`b17a13ca048f5cfe472d132186a8bda4fb130756`. The governing inbox was re-read
at trellis-channel `209752c5f7f5226d486bf836a566eacdb624c714` on 2026-11-06;
HEDERA-DAY1-FIX-2 remains the latest instruction. This is an HCS foundation
correction, not certification of complete products or release readiness.

| Commit | Finding closed / resulting behavior |
| --- | --- |
| rpp-spec `f86360fc865817b7b3ff5e6f0ee6cc0415bcef7e` | F3-R public-state correction: signer instance state contains only its public key; serialization, reductions and copying refuse. The original SDK signing callback is retained behind an opaque CPython capsule, with balanced ownership, rollback and stale-handle refusal. This commit alone did not close diagnostic disclosure; see its child below. |
| rpp-spec `4d8a65d09e561f804116a50f6e3c79873ca79f04` | Completes F3-R: callback and initialization failures clear sensitive locals, discard original SDK exception/context graphs and release partially installed signing operations. Rich traceback/context serialization remains safe; interruption/cancellation types and safe integer/None exit codes survive. |
| digigami-stack `2904d82907eb8dae1bf8fcb0663ec2370ce11b9c` | F4-R: snapshot requested absent admin and typed submit key before preparation, check the actual SDK request agrees, and compare both against strict mirror evidence. Missing, malformed or unexpected admin/submit evidence refuses confirmation. |
| mobius `2d8d036792aa97548b51d04491ee9b2afe337d83` | F4-R: preserve and strictly parse both mirror key states; require explicit absent admin and matching requested submit key. N1: retain validated configuration and enforce its network-fee ceiling at shared entry, direct SDK prepare and actual prepared-body send, including a handle transferred from a higher-cap backend. |

This report's containing commit on `codex/HEDERA-DAY1` adds documentation and
evidence only; Python source is frozen at the reviewed `4d8a65d0` commit above.
The final five-line delivery reports the report-inclusive remote head. Only
`codex/HEDERA-DAY1`, `codex/HEDERA-DAY1-js` and `codex/HEDERA-DAY1-rust`
are pushed in this round, once each to their existing anywave origins.

| Unchanged remote delivery | Status from the independent re-review |
| --- | --- |
| hedera-auction-integrity `codex/HEDERA-DAY1-auction` — `c06f501d9d3b25dcd14461f8f042e4916f682fa6` | READY in thin launcher/offline job-pack scope; no change or push this round. |
| digigami-audit `codex/HEDERA-DAY1-audit` — `82184a31f14b8bac97f31d46f49ea931de400208` | READY in that same scope; F5 remains closed; no change or push this round. |

PR #47 duplicates #46's earlier implementation and is now closed, unmerged,
outside this follow-up. Its `codex/HEDERA-DAY1-python` alias is left at remote
`ce24da0d0be4fcedb6b988a9d8a5d44155b60a2b`; it does not inherit #46's new
fixes. No merge, rebase, force push, tag, other branch push or PR metadata write
is included. Prepared replacement descriptions for #46/#291/#2 are in
[PR-DESCRIPTIONS.md](../hedera-day1/fix-2/PR-DESCRIPTIONS.md).

The final Python implementation is at `rpp/adapters/hedera_safe.py:29`, with
capsule invocation at line89, signer state/protocols at line129, runtime
initialization at line428 and record-signing diagnostics at line511. The source
SHA-256 is `42d855c179f8c4747d1344e6ce5ed1518f9d094d1ea3046060bbc56e480182ac`.
JS key expectations/confirmation are at
`packages/hedera-day1/src/index.mjs:52` and line112; SDK agreement is at
`packages/hedera-day1/src/sdk.mjs:75`. Rust mirror parsing is at
`crates/hedera-day1/src/sdk.rs:79`; fee validation/prepare/send are at
lines174/187/220 and shared confirmation at `src/lib.rs:144`.

| Final source validation | Result |
| --- | --- |
| Python actual pinned SDK/fake focused suite | 212 passed, zero skipped. |
| Python full RPP suite, including the focused suite | 1,468 passed, zero skipped; one pre-existing legacy-address deprecation warning. Ruff and diff checks clean. |
| Python compiled named guard-removal controls | 49/49 killed by the intended assertion/exception. No import, syntax, timeout or native crash counts as a kill. |
| Python independent public-object probe | 584 graph objects, 103 protocol calls and 1,952 captured formats; no key disclosure, zero sockets; both original getstate leak controls detected. |
| Python independent lifecycle and diagnostics | 256 create/sign/verify/GC cycles plus rollback, stale-handle and concurrent-close checks; 88/88 rich diagnostic/control cases passed at the final immutable head, including Ed25519/ECDSA. The earlier `f86360fc` diagnostic baseline failed 28/28 and is explicitly superseded. |
| CPython native ownership review | 21 independent ABI/lifecycle checks passed on CPython 3.12.14; final-head lifecycle probes rerun after diagnostic cleanup. |
| JS policy/SDK/fix suites | 39 passed, zero skipped; 45/45 named behavioral mutations killed. Paired actual SDK wire/mirror matrix covers 70 admin/submit combinations; only exact requested evidence passes. |
| JS independent paired regressions | 28 actual-wire/mirror cases and four independent removal controls; prior routing/custom-fee/dispatch probes preserved. |
| Rust SDK-enabled suite | 27 regular tests passed, including 15 core policy tests, plus one compile-fail opacity doctest; no failed/ignored tests. |
| Rust compiled named guard-removal controls | 50/50 killed in a complete run, including configured/global/positive fee limits, direct prepare, shared entry and lower-cap receiving-backend send. |
| Rust independent paired regressions | 24 actual SDK wire/parser/policy key cases, three archived-source cap/key tests and four independent removal controls passed. |

Reproduce Python with the optional pinned experimental dependency installed:
`python -m pytest -q tests/test_hedera_safe.py tests/test_hedera_sdk_security.py`,
`python -m pytest -q`, `python scripts/hedera_python_mutations.py`, and
`ruff check rpp/adapters/hedera_safe.py tests/test_hedera_sdk_security.py scripts/hedera_python_mutations.py`.
JS commands in `packages/hedera-day1`: `npm test` and `npm run test:mutations`.
Rust commands: `cargo test --offline --manifest-path crates/hedera-day1/Cargo.toml --features sdk`
and `python crates/hedera-day1/scripts/mutation_check.py`. Mutation runners restore
source; key-bearing tests and children disable core dumps and use only synthetic
keys generated in memory, never logged or written. No actual account or credential
is required by these offline regressions. Dependencies and locks are unchanged.

Evidence is committed under [fix-2/](../hedera-day1/fix-2/): source-pinned
validation manifest, independent reviews and boolean-only state/lifecycle/
diagnostic results, Python logs, and JS/Rust validation summaries. Independent
reviews cover ordinary public state, bound callbacks, rendered function globals,
serialization and normal rich error diagnostics. They do not claim a sandbox
against deliberate native C-API pointer dereference, arbitrary process-memory
inspection, debugger access or explicit environment reads. This CPython-specific
experimental boundary fails closed when capsule support is unavailable;
free-threaded builds, subinterpreters and other platforms remain unverified.
Client close is not claimed to erase retained signing memory immediately.

Both RADIX rulings remain enforced. Application layers have only testnet
constructors and fixed testnet mirror endpoints; no mainnet node list, mirror
URL or activation flag exists. Runtime network choice is re-read at each send;
changed selection refuses. Only topics with explicit readable empty custom-fee
schedules are accepted. Every message carries one actual-payer allowance with
one zero-HBAR FixedFee and no token denomination. Network transaction fees have
their separate bounded ceiling. Existing receipt, frozen retry identity and
exact mirror-byte readback controls remain passing.

**Live testnet proof remains UNPROVED:** no runtime throwaway credentials and
previous Hedera endpoint 403 restrictions; no credentials were added and no
ledger/account/funding operation was attempted. No mainnet, real HBAR, key file
or email was used. Actual SDK wire with fake RPC/mirror verification does not
establish deployed consensus enforcement. Official JS 2.90.1 and Rust 0.45.0
pins remain; Python 0.3.0 remains community Pre-Alpha/experimental, with shipping
Python callers directed to the official JS/Rust boundary. Production product
valves/wiring, durable restart reconciliation, Mobi Windows/MSRV packaging and
#291's divergent base remain outside these corrections; no merge is requested.
