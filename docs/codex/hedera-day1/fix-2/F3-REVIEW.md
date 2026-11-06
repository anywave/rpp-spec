# Independent F3-R review

Status: **F3-R closed within the tested object-state and normal diagnostic
boundary at immutable source head
`4d8a65d09e561f804116a50f6e3c79873ca79f04`.** All three independent probes were
rerun successfully at that exact head. No further finding was identified in
the inspected scope. The earlier bounded closure at `f86360fc` was reopened
when normal rich diagnostics exposed signing references; that head does not
inherit this final verdict.
Source SHA-256 reviewed:
`42d855c179f8c4747d1344e6ce5ed1518f9d094d1ea3046060bbc56e480182ac`.

The reviewed Python SDK is the actual pinned `hiero-sdk-python==0.3.0`.
Generated synthetic keys and all inspected representations remained in memory;
the scripts emit only booleans, counts, fixed labels and source identities.
Core dumps are disabled in both independent probes. Socket connections are
forbidden. No real runtime credential, account, ledger or repository source was
changed by this review.

The original production signer at `ce24da0d` is reproduced as a negative control:
its inherited `__getstate__` leaks through both repr and JSON default=str. Both
controls detect the synthetic key without exporting its value. An intermediate
raw-operation registry was also rejected because direct rendering/logging of
the public function globals exposed the raw SDK bound method. A proposed weak
registry was rejected after its public weakref callback/defaults path recovered
the raw method.

Additional independent review at `f86360fc` found ordinary
`TracebackException.from_exception(error, capture_locals=True)` formatting and
public diagnostic-context serialization expose the `_invoke_capsule.operation`
and underlying SDK `PrivateKey.sign.self` fields after malformed-input errors.
Unsupported signer initialization also retains the constructor's raw `key`
argument in diagnostics; missing-account initialization retains a DER local.
Those error paths are now corrected by clearing raw references on every exit,
closing the partial signer's native operation on failed backend initialization,
and discarding raw SDK contexts before raising fixed errors outside the original
exception handler. No key-bearing diagnostic string is written or printed.
The immutable old-head diagnostic baseline has 28/28 failing cases. The final
head passes those 28 cases plus 60 interruption/control cases, 88/88 total.
Both Ed25519 and ECDSA are covered. Captured standard traceback text and public
diagnostic/context JSON reveal no synthetic key, and failed initialization
retains no operation while the actual error and traceback are still alive.
KeyboardInterrupt, SystemExit, GeneratorExit and CancelledError types propagate;
untrusted SystemExit text is discarded while integer exit code 7 is preserved.

The accepted replacement stores only opaque native capsules in the registry.
Signer instance/base slot state contains only a public key. Protocol hooks for
state, reductions, copying and pickling refuse. Actual SDK client/operator state
holds the opaque callable, with no SDK private-key member, and signed transaction
retained callbacks use that same boundary. The native invoke helper returns a
signature rather than a raw operation. No ordinary state/serialization helper
returns the underlying key or callback.

The independent attack covers actual retained backend/client/operator/signer/
transaction state and capsule objects: str/repr/pprint, JSON default=str and
default=vars, logging, vars/dir/getattr, state/reduction hooks, pickle protocols
0–5, copy/deepcopy, object base protocol fallbacks, bound-method self, function
defaults/closures, and direct rendering of public function globals. It retains
walked objects to prevent identity reuse and treats native method wrappers as
bound methods to avoid artificial recursive wrapper growth.
The final run visits 584 unique graph objects, 575 dir-generated attributes,
469 bound-method-self paths and 194 function closure/default checks, with 103
protocol calls and 1,952 captured formats. It reports zero detected key leaks
and zero socket connection attempts. Both original getstate negative controls
detect the old defect. These counts describe the bounded probe, not exhaustive
proof over arbitrary same-process Python execution.

The independent lifecycle probe verifies 256 create/sign/verify/GC cycles,
idempotent repeated close, saved-capsule invalidation, allocation and registry
insertion rollback, unsupported runtime/API refusal, and concurrent close while
a signature is active. Registry size returns to baseline and weak references
show that raw SDK key objects are released after their owning operation ends.

This is an inspection/serialization boundary within experimental CPython code.
It does not claim isolation against ctypes/C-API pointer dereference, arbitrary
process or module-memory traversal, or explicit process-environment access.
Native reference ownership requires the tested CPython API; unsupported
environments refuse local signing. Official JS/Rust service boundaries remain
the shipping choice for Python callers requiring an official SDK.

Probe scripts and boolean-only evidence:

- `/workspace/work/hedera-fix2-f3-attack.py`
- `/workspace/work/hedera-fix2-f3-attack-result.json`
- `/workspace/work/hedera-fix2-f3-lifecycle.py`
- `/workspace/work/hedera-fix2-f3-lifecycle-result.json`
- `/workspace/work/hedera-fix2-f3-diagnostics.py`
- `/workspace/work/hedera-fix2-f3-diagnostics-result.json`
- `/workspace/work/hedera-fix2-f3-diagnostics-baseline-f863.json`
