# HEDERA-DAY1-FIX-3-001

Closes N2 LOW from `R-HEDERA-DAY1-3-001.md`, read at review branch
`4b9a4efe0560c48fea7609a04dba646f51c0242e`. The finding at
`rpp/adapters/hedera_safe.py:143` of the reviewed `42e7c75a` head identifies
an orphan native callback reference when SIGINT lands after incrementing its
reference count and before entering the rollback block.

Source commit: **`28f0335aab6626fe3d3a73f937449642fd6a4a12` closes N2**.
The containing report commit changes only documentation/evidence and preserves
that source. Delivery is one ordinary push to rpp-spec `codex/HEDERA-DAY1`;
the final response records its report-inclusive remote head. No other rpp-spec
branch, duplicate #47, tag, merge or force push is included.

The optional native helper now increments and creates the owning capsule in one
C call, with a native destructor and allocation rollback. Python cannot strand
a pin before assigning/publishing the result. Release tombstones and decrements
atomically; Python releases before unpublishing, so interrupted cleanup remains
discoverable. In-flight signing owns a separate C reference across concurrent
close. This also covers the adjacent allocation/publication and pop/release
windows. A Python boolean or moving `try` alone cannot atomically track the old
native increment and would risk either an orphan or an extra decrement.

Implementation: `rpp/adapters/_hedera_signer_native.c:102` (release), line124
(destructor), line135 (creation), line184 (invoke);
`rpp/adapters/hedera_safe.py:57` (fail-closed loading), line126 (owned creation)
and line162 (release before unpublishing). No operation/key accessor or GC
referent is exposed. Direct native invocation also discards SDK exception graphs
before raising fixed errors or fresh supported control exceptions; safe
SystemExit integer/None codes are preserved.

The default package/wheel remains pure Python. Experimental local signing now
requires an explicit native build: `python scripts/build_hedera_native.py`, or
`RPP_BUILD_HEDERA_NATIVE=true python -m hatchling build -t wheel`. Missing helper,
non-CPython, free-threaded builds and non-main interpreters refuse. The local
builder supports the tested POSIX compiler path; Windows and other CPython
versions remain unverified. Native binaries are ignored, never committed. The
official JS/Rust service boundary remains the shipping path for Python callers.

| Validation on the corrected source | Result |
| --- | --- |
| Focused actual pinned SDK/fake suite | 244 passed, zero skipped. |
| Full RPP suite, including focused tests | 1,500 passed, zero skipped; one existing legacy-address deprecation warning. |
| Named compiled removal controls | 49/49 killed by intended assertions/expected exceptions. Includes recompiling the C helper without its destructor and detecting the retained callback after actual SIGINT, native diagnostic sanitization removal, and release-before-unpublish reversal. No crash, timeout, compile/import failure counts as a kill. |
| Actual SDK interruption regression | Ed25519/ECDSA at six acquisition/publication/release points, including the native return before Python STORE_FAST; receiver released, registry empty, saved handles closed and repeated cleanup safe. |
| Independent ownership matrix | 270/270 actual SIGINT line/opcode cases passed; original baseline reproduced four orphan-reference windows. |
| Independent preserved F3 boundary | Public graph/serialization, 106 rich diagnostic/control cases, and 256 SDK lifecycle cycles passed; no key disclosure or sockets. |
| Independent native checks | 3,008 lifecycle/error observations, 45 direct control/error checks, allocation-failure rollback and subinterpreter refusal passed. Capsule GC referents remain empty. |
| Packaging | Default pure wheel excludes native binaries; explicit native wheel has correct platform/CPython tag. Extracted-wheel imports, source distribution and CLI build commands passed. |
| Formatting | Ruff and git diff checks clean. |

Reproduce using the pinned experimental SDK environment: build the helper, run
`python -m pytest -q tests/test_hedera_safe.py tests/test_hedera_sdk_security.py`,
`python -m pytest -q`, and `python scripts/hedera_python_mutations.py`.
Evidence/source hashes are under [fix-3/](../hedera-day1/fix-3/).
Synthetic keys exist only in memory; failure assertions emit booleans. Core
dumps and sockets are disabled in the key-bearing security probes.

F3-R remains closed within the reviewed public-state/normal-diagnostic boundary.
No arbitrary same-process native-memory isolation is claimed. Testnet-only
routing, fresh send checks, refusal of all topic custom fees, zero custom-fee
allowances, bounded retries/fees, receipts and mirror-byte readback are retained.
**Live testnet remains UNPROVED**: no credentials added or ledger/account/funding
operations attempted. No mainnet, real HBAR, key file or email was used.
The subsequently authorized Mobius base-branch merge is a separate queued task;
this report does not change or merge any Mobius branch.
