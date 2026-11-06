# HEDERA-DAY1-FIX-4-001

N3 LOW is addressed by source commit
**`679e14d0f22161e882f249481835221614c51a8d`**. Read the finding at
`rpp/adapters/hedera_safe.py:132` in `R-HEDERA-DAY1-4-001.md`, review head
`4b602c7affe0a18bb332d94acd03c4b04bc1b6fa`, against primary head
`2e0020c0eef4349480658add57f47bfa2427a70e`. The inbox re-read at trellis-channel
`0e52bca069b619f2ebc849d58f86d6b4547d1452` still names FIX-4 as the newest task.

`_Signer.__init__` is now a native method descriptor. It accepts the original
positional/keyword key argument in C, derives the public key, creates its owning
capsule, and releases its temporary bound-method reference before calling Python.
Python `_initialize(self, public_key, capsule)` has no key, signing-operation or
encoded-credential local. There is no raw-key cleanup assignment to interrupt.
The native entry closes its capsule even when Python cleanup is interrupted,
then discards the original exception graph and raises fresh supported controls
or fixed errors. MemoryError/TypeError and safe SystemExit integer/None behavior
are preserved. N2's atomic owner, native destructor and idempotent close remain.

The source commit contains the native entry, public/opaque Python continuation,
actual-SDK regressions, mutation controls and rebuild instructions. This report's
containing commit adds evidence/docs only and preserves those source blobs.
Delivery is one ordinary push to rpp-spec `codex/HEDERA-DAY1`; the final response
records its report-inclusive remote head. Closed duplicate #47 and its alias
remain untouched. No merge, force push, tag or other branch push is included.

| Validation on the corrected source | Result |
| --- | --- |
| Focused pinned SDK/fake suite | 251 passed, zero skipped. |
| Full RPP suite, including focused tests | 1,507 passed, zero skipped; one existing legacy-address deprecation warning. |
| Actual SIGINT diagnostics | 486 cases: 78 direct and 165 factory cases per algorithm, Ed25519/ECDSA. Every signal fired and escaped as KeyboardInterrupt; zero live-local or escaped-traceback key disclosures, zero escaped open handles, registry empty. |
| Executable initializer lines | Direct cases interrupt all 20/20 Python continuation lines per algorithm across success, reinit, failed store, post-store failure and controls. Factory cases cover 19 lines plus the backend factory; the reinit-only guard is covered directly. The raw-key entry itself has no Python frame. |
| Original-head negative baseline | Both algorithms disclose key bytes from the unchanged old Python initializer: 98 escaped-diagnostic detections and 1,714 live-local detections each. Only booleans/counts are retained. |
| Compiled named removal controls | 48/48 killed by intended assertions/expected exceptions. Restoring a raw-key Python initializer must fail the actual escaped-key-disclosure assertion, not coverage/collection. Native public-key handoff, interrupted rollback, temporary callback release and error-graph replacement have their own controls. No crash, timeout, compile/import failure counts as a kill. |
| Native packaging | Default pure wheel contains no binary and refuses local signing without the helper. Rebuilt native wheel has the correct CPython/platform tag; isolated wheel imports, both algorithms, positional/keyword construction, sign/verify and key release pass. |
| Static checks | Ruff, git diff checks and AST checks for absence of a Python raw-key initializer/local pass. |

The SIGINT probe inspects live initializer locals before interruption, retains
the actual escaped error and traceback, checks `capture_locals=True` copies and
actual frame locals/context chains in memory, then repeats cleanup. This prevents
native exception replacement from concealing a raw Python local. Comparisons
include product-package frames and exclude caller-held fixture keys. The normal
direct native boundary removes the inner Python error frames before escape;
live-local checks and the old-head/removal failures keep the test non-vacuous.

The two old Python constructor context/control mutations are retired because
their safety boundary moved into native initialization. Their SDK/control
regressions remain; native error replacement and raw-input handoff have compiled
removal controls. A new temporary-operation release control catches an extra
native callback/key reference. The current total is 48, versus 49 before N3.

Reproduce with the pinned experimental SDK and rebuilt helper:
`python scripts/build_hedera_native.py`, focused/full pytest and
`python scripts/hedera_python_mutations.py`. The child probe is
`tests/hedera_initializer_sigint_probe.py`. Evidence/source hashes are in
[fix-4/](../hedera-day1/fix-4/). Synthetic keys and diagnostic strings stay in
memory; no key values are written or printed, and core dumps/sockets are disabled
in key-bearing probes. **Rebuild the helper after updating from FIX-3.** Missing
or older helpers fail closed; pure-Python imports remain usable.

Testnet-only routes, fresh send authorization, refusal of all custom fees,
zero custom-fee allowances, bounded retries/fees, receipts and exact mirror bytes
remain passing. **Live testnet remains UNPROVED**; no credentials were added,
no ledger/account/funding operation or other network write was attempted beyond
the explicitly authorized Git push. No mainnet, real HBAR, key file or email.
The helper remains experimental GIL-enabled main-interpreter CPython; validation
used CPython 3.12.14/Linux. Windows/other runtimes and complete product release
readiness are not claimed. Explicit native-pointer/process-memory inspection
remains outside this object-state and diagnostic boundary.
