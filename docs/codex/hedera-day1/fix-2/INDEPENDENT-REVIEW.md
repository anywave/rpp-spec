# HEDERA-DAY1-FIX-2 independent gate

**READY within the F3-R, F4-R and N1 corrective scope.** No remaining finding
was identified at the immutable source revisions below. This verdict covers
shared HCS foundations and their stated diagnostic/security boundaries; live
testnet execution and complete product/release readiness remain unproved.

| Repository | Immutable source revision | Corrective gate |
| --- | --- | --- |
| rpp-spec | `4d8a65d09e561f804116a50f6e3c79873ca79f04` | F3-R closed |
| digigami-stack | `2904d82907eb8dae1bf8fcb0663ec2370ce11b9c` | F4-R closed |
| mobius | `2d8d036792aa97548b51d04491ee9b2afe337d83` | F4-R and N1 closed |

The Python source SHA-256 is
`42d855c179f8c4747d1344e6ce5ed1518f9d094d1ea3046060bbc56e480182ac`.
Current source files were compared with those committed revisions. Any later
rpp-spec report-only commit must preserve these reviewed source blobs.

## Findings

**F3-R:** Actual pinned Python SDK client/operator/signer/transaction state no
longer exposes the raw SDK signing callback through normal state protocols,
repr/str/JSON/logging/pickle/copy, public bound-method/default/closure inspection
or rendering of function globals. The signer holds only public key state and
explicitly refuses serialization protocols. Native capsules retain the signing
capability; tombstoning, allocation rollback and ownership cleanup are tested.

Normal rich error logging is included: `TracebackException(...,
capture_locals=True)`, formatted tracebacks, serialized diagnostic contexts and
public exception fields remain free of synthetic signing material. SDK callback
and constructor failures clear raw operation/key/credential locals, close partial
signers and raise fresh sanitized failures outside the original handler. Control
exceptions propagate safely, including integer SystemExit code 7; untrusted
SystemExit text is discarded. Both Ed25519 and ECDSA were exercised. Real SDK
signing interrupted with SIGALRM also passes the independent diagnostic probe.

**F4-R:** JS captures immutable requested key metadata and checks it against the
actual SDK create request. JS mirror confirmation requires explicit absent admin
and the exact typed submit key. Rust preserves admin evidence in its real mirror
parser and compares absent admin and the requested submit key captured before
async preparation. Missing, malformed, unexpected or altered evidence refuses.
Actual SDK frozen create bodies, JSON decoding and shared confirmation
policy were exercised together, rather than replacing the production parser.

**N1:** Rust retains the configured network-fee cap and validates caller fees
before direct preparation, preflight reads or signing. Shared entry and direct
send also validate it. Send checks the actual frozen transaction fee against the
receiving backend's configured cap and the 100,000,000-tinybar global ceiling:
a handle prepared at the higher cap cannot bypass a receiver configured for one
tinybar. One-tinybar and global-boundary positive cases remain usable.

## Executed gates and removal controls

| Scope | Independent execution at the pinned revision | Additional supplied evidence inspected |
| --- | --- | --- |
| Python | 212 focused tests; all 49 current named mutations; public SDK graph probe; seven actual-SDK/fake-RPC policy cases and public routing refusal; 12 rich-diagnostic signer/record cases, unavailable-API/missing-ID initialization and actual SDK interruption | 1,468 full tests, zero skipped; specialist graph/lifecycle/88-case rich-diagnostic matrix, all passed |
| JS | 39 package tests; 28 paired actual-SDK-wire/mirror-key cases; nine actual-SDK/fake-RPC policy cases; four separate admin/submit/type/byte comparison deletion controls | All 45 current supplied mutations killed; locked install passed |
| Rust | 27 regular tests and one opaque-API compile-fail doctest; three added actual-SDK production-path tests including 24 paired key-state cases; four separate prepare-cap/send-cap/admin/submit comparison deletion controls | All 50 current supplied mutations killed in one complete run |

Python's independently rerun mutation log contains exactly the 49 current unique
rule labels. Its runner compiles every mutation first and requires the intended
named pytest assertion or DID-NOT-RAISE failure, with exit 1. JS checks syntax and
requires ERR_ASSERTION, including named F4-R failures. Rust's four independent
controls compiled and failed the intended named behavioral assertions. The
opaque-API compile-fail doctest is a separate API-visibility check and is not
counted as an assertion-killed mutation. Independent scratch mutations were
restored and the positive tests rerun. No owner source was edited by this review.

The specialist public-state probe visits 584 retained graph objects, makes 103
protocol calls and captures 1,952 formats. Its lifecycle probe covers 256
create/sign/verify/GC cycles, allocation/store rollback, saved-capsule and repeated
close, unsupported runtime/API and concurrent close. Its 88 diagnostic cases
cover ordinary SDK errors, retained initialization errors and five control
variants across six stages and both key algorithms. All report zero key leaks
and zero socket connections; original getstate and older diagnostic defects are
retained as detecting negative controls. The additional general public-state
probe observed 2,741 contexts with zero detected signing-material markers.

## Preserved boundaries and limits

F1/F2 remain intact in the probes: unreadable/missing/malformed/nonempty topic
fee schedules refuse, every message has a nonempty actual-payer zero-HBAR
allowance with no HTS denomination, and network-fee limits remain separate.
Only testnet routing is constructible through the shipping adapters; legacy
activation flags cannot enable another network. JS/Python pin actual initialized
routing and guard concrete RPC dispatch, with hidden native retries disabled.
Rust keeps its client private, pins one testnet node and one SDK attempt, and
checks fresh network choice before each SDK send. Already-started in-flight RPCs
are not cancelled, and no Rust concrete tonic interceptor is claimed.

Python remains an explicitly experimental CPython transport. The tested public
state and normal diagnostic boundary does not isolate against deliberate native
pointer/C-API dereference, arbitrary process-memory inspection or explicit
process-environment access. Unsupported native-signing environments refuse.
Official JS/Rust boundaries remain the shipping choice for Python consumers
requiring an official SDK. No broader process-isolation claim is made.

No live ledger call, mainnet access, real credential, funded account, merge,
force push or reviewer push occurred. Synthetic keys were generated in memory
only; diagnostic outputs contain fixed labels, booleans and counts. Testnet live
proof, complete product wiring, restart durability, Windows/MSRV packaging and
release valves remain outside this corrective gate. Auction/audit scope is
unchanged. Closed duplicate rpp-spec #47 is outside this gate and must retain its
old head rather than inherit #46's fixes.

Evidence: `/workspace/work/hedera-fix2-review-python-mutants.log`,
`/workspace/work/hedera-fix2-review-js-tests.log`,
`/workspace/work/hedera-fix2-review-rust-tests.log`,
`/workspace/work/hedera-fix2-review-rust-independent-restored.log`,
`/workspace/work/hedera-fix2-f3-review.md`, and the independent probe scripts and
boolean-only results under `/workspace/work/hedera-fix2-*`.
