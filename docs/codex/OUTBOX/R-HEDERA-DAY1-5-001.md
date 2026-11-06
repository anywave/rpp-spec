# R-HEDERA-DAY1-5-001

Independent reviewer-only re-read requested by TR on 2026-11-06; the reworded
instruction is the newest inbox entry, blob
`04a0079b6872fc946050099c5b0c5f9eed486702`. Baseline:
[R-HEDERA-DAY1-4-001](R-HEDERA-DAY1-4-001.md) at
`4b602c7affe0a18bb332d94acd03c4b04bc1b6fa`. Another thread wrote FIX-4.

**rpp-spec #46 at `b6e82c511456baa661ef4041e25d2a175701f650`: READY.
N3 LOW is closed. No new actionable finding was demonstrated.** This verdict
covers the experimental Python HCS boundary and this initialization repair,
not live testnet acceptance or complete product release readiness.

No merge, force push, PR-branch change, ledger write, funding operation, live
smoke or real credential access occurred. Only rpp-spec and trellis-channel
were used. Diagnostic probes used generated in-memory keys or harmless receiver
objects; key-bearing diagnostic strings stayed in memory. Saved output contains
fixed labels, booleans and counts. Core dumps were disabled. Temporary compiled
controls were isolated. This report is the only delivery file added to the
existing `codex/R-HEDERA-DAY1` review branch.

## Exact diff and scope

Reviewed old head: `2e0020c0eef4349480658add57f47bfa2427a70e`.
Source fix: `679e14d0f22161e882f249481835221614c51a8d`.
Report-inclusive reviewed head: `b6e82c511456baa661ef4041e25d2a175701f650`.
The history is linear: old head, source fix, documentation/evidence commit.
GitHub identified #46 as an open draft at the requested head.

The old-to-new comparison changes exactly 15 files:

- Two production files: `rpp/adapters/_hedera_signer_native.c` and
  `rpp/adapters/hedera_safe.py`.
- Three test/control files: `tests/test_hedera_sdk_security.py`, new
  `tests/hedera_initializer_sigint_probe.py`, and
  `scripts/hedera_python_mutations.py`.
- Ten documentation/evidence files: Python README, FIX-4 report and eight
  files in `docs/codex/hedera-day1/fix-4/`.

An AST comparison confirms the only changed existing top-level Python
definitions are _native_signer_api and _Signer. The new top-level binding gives
_Signer its native initializer. Configuration, network routing, transaction
authorization, fees, retries, mirror verification and backend construction are
unchanged. No dependency, lockfile, build script, packaging hook or committed
binary changed. The mutation runner's timeout rises from 30 to 90 seconds;
this is a test-process limit, not a runtime transport/retry change. The final
commit after the source fix changes only nine report/evidence documents.

## N3 — LOW — Closed: interrupted initializer diagnostics

Original finding: `rpp/adapters/hedera_safe.py:132` at `2e0020c0`.
Replacement boundaries: `rpp/adapters/_hedera_signer_native.c:180` and
`rpp/adapters/hedera_safe.py:118`/`:186` at `b6e82c51`.

_Signer.__init__ is now a C method descriptor. The C entry receives the raw
key, derives its public key and creates an owning capsule. It clears the
temporary bound signing operation before calling Python. The Python
continuation's arguments are exactly self, public_key and capsule; it has no
raw-key or bound-signing-operation local, and there is no raw-input cleanup
assignment left for SIGINT to interrupt.

The backend's existing inline SDK key construction is unchanged. The claim
verified here concerns the adapter's public object state, Python frame locals
and escaped diagnostics; it does not claim that credentials are absent from
the process, caller-owned fixture frames, SDK implementation frames, native
stacks or deliberate process-memory/native-pointer inspection.

## Ownership and error handoffs

| Boundary | Review and observed result |
| --- | --- |
| C acquisition, `_hedera_signer_native.c:169` | The callback increment and owning capsule creation remain in one native call. Capsule allocation failure decrements the callback before return. The initializer's temporary operation reference is independently cleared at line212. |
| Python publication, `hedera_safe.py:121` | Only public/opaque state crosses into Python. The registry acquires its capsule reference under the existing lock. Reinitialization refuses the new owner without disturbing the previous registry owner. |
| Failed continuation, `_hedera_signer_native.c:216` | A NULL result explicitly invokes signer_destructor even if an interruption prevented Python's finally from releasing its capsule. The C-held capsule is then decremented. |
| Release, `_hedera_signer_native.c:124` | Release tombstones the pointer before decrementing the callback. Python finally, the explicit C rollback, automatic capsule destruction, object destruction and repeated close can all visit it; only the first visit drops the owned operation reference. |
| Destructor, `_hedera_signer_native.c:146` | It preserves the pending failure around release, so cleanup does not replace or accidentally consume the original failure before sanitization. |
| Error replacement, `_hedera_signer_native.c:13` | sanitize_error fetches and drops the original exception/type/traceback graph before creating a fixed error or fresh supported control exception. SystemExit retains only an exact integer or None, never a key-bearing string/object. |

The native initializer initializes all owned-reference locals to NULL, skips
dependent calls after a failure, and decrements its acquired public-key,
factory/API/module and capsule references on the common exit path. The parsed
key is borrowed from the C call arguments. A successful continuation leaves
the registry owning its live capsule; a failed continuation leaves any saved
capsule closed. Existing concurrent invocation retains its own strong callback
reference until invocation returns.

No native leak, double release, open escaped failed-initialization handle, or
key-bearing chained error was observed in the tests below. Rich diagnostic
tests retain the actual exception and inspect context/cause as well as formatted
copies; merely suppressing printed chaining would not satisfy them.

## Executed validation

CPython **3.12.14**, Linux, GIL enabled; reused installed
**hiero-sdk-python 0.3.0** and pytest 9.2.0. No dependency installation or SDK
upgrade was performed. The Python SDK remains the documented experimental
community boundary.

| Independently executed command/scope | Result |
| --- | --- |
| `python scripts/build_hedera_native.py` | Exit0; helper rebuilt from this exact head. |
| `python -m pytest -q tests/test_hedera_safe.py tests/test_hedera_sdk_security.py` | **251 passed**, zero skipped, exit0. |
| `python -m pytest -q` | **1507 passed**, zero skipped, exit0; focused tests included; one existing legacy-address deprecation warning. |
| `python scripts/hedera_python_mutations.py` | **48/48 killed**, exit0, by the required named assertions/expected exceptions. Compile, import, crash and timeout failures do not count as kills. |
| Standalone unchanged lane SIGINT probe | **486 actual SIGINT cases**: 78 direct and 165 factory cases per algorithm, Ed25519/ECDSA. All signals escaped as KeyboardInterrupt; zero product-local/escaped-diagnostic key detections, zero open escaped handles, registry empty. |
| Reviewer line/opcode extension of that probe | **2610 actual SIGINT cases**: 434 direct and 871 factory cases per algorithm. Same zero-disclosure/closed-handle results while retaining the actual errors and their graphs. |
| Independent harmless-receiver ownership matrix | **374 actual SIGINT cases**, all receivers released exactly once, saved handles closed and registries empty: 261 ordinary initialization/call/invoke/release/destructor/shutdown cases plus 113 interrupted post-store-failure cases. |
| Additional native lifetime checks | **2004 checks**: 1000 repeated create/close/GC cycles, automatic destruction, concurrent invoke/close, and an isolated compiled helper forcing the real capsule-allocation failure branch. All pass. |
| Fresh-package missing/older-helper probes | **12 refusals**: positional/keyword direct construction and backend construction for both algorithms, with no helper and with the old compiled helper. Pure-package imports remain usable; no signing fallback or registry entry appears; product diagnostics contain no key. |

The line probe interrupts all 20 executable Python continuation lines through
success, reinitialization, refused store, post-store failure and control flow.
Factory probes cover 19 lines plus backend initialization; the remaining
reinitialization-only guard is covered by direct probes. Opcode probes expand
the same scenarios. Direct line-probe escaped product-frame counts are zero
because the native boundary replaces the original graph; live-local checks
and the negative controls below prevent that from being a vacuous result.

For a negative baseline, the unchanged old head was run with the same lane
probe: **178 direct cases**, 89 per algorithm. Each algorithm reports 98
escaped-diagnostic and 1714 live-local detections. Key values and diagnostic
text were neither printed nor saved. This reproduces N3 before the fix.

The native-initializer-boundary mutation restores a Python raw-key initializer
and must fail the escaped-product-local assertion specifically. Separate
compiled controls detect private-state handoff, removal of the C failed-setup
rollback, removal of temporary-operation release, and removal of initializer
error-graph replacement. Existing native-owner, repeated-close, serialization,
callback diagnostics and runtime policy controls also pass. The current total
is 48 versus the prior 49 because controls were rewritten for the moved native
boundary; the corresponding SDK/control diagnostic regressions remain.

The allocation-refusal path never enters the Python continuation and therefore
contributes no traced continuation point in the independent ownership matrix;
it is tested separately by the compiled allocation-failure check. Counts above
are completed checks, not unobserved tracing targets. No traced product frame
was cleared before the diagnostic inspection. The separate reference-balance
matrix clears Python-owned exception frames before testing for orphan native
references.

## Rulings and limits

Testnet-only Config validation/fixed mirror, testnet client construction and
concrete dispatch route checks remain unchanged and pass. Custom-fee schedules
must still be explicitly readable and empty; every submit still carries the
actual payer's zero-HBAR allowance with no token denomination. Their removal
controls fail as intended. Bounded retries/fees, receipt status, topic key
readback and exact mirrored payload checks also remain passing. No alternate
mainnet constructor, node list, mirror URL or enabling flag was added.

No Hedera endpoint was exercised. Generated-key probes disabled sockets, and
the SDK tests use fake transports. Native C instruction sequences that do not
dispatch Python are assessed through reference ownership and compiled failure
controls, not described as separately signal-interruptible Python steps.
Repeated arbitrary interrupts, hardware failure, hostile native code and
process-memory extraction are outside these results. Wheel-building evidence
from the author was read but wheels were not independently rebuilt in this
re-read. Windows, other runtimes and complete distribution acceptance were not
tested; unsupported native support continues to refuse local signing.

Reviewer evidence is retained under `work/hedera-review5-evidence/`, including
baseline/mutation logs, diagnostic counts, ownership results and native-absence
checks. Both tracked trees remained clean after execution. **No fix remains
requested for N3; no changes to combine are needed.**
