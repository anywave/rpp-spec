# Python shared policy and experimental transport

`rpp.adapters.hedera_safe` is the shared Python HCS policy layer. `HederaTransport`
keeps its default in-memory mode; its real publishing path now fails closed and
uses this layer instead of returning an empty object from an unwritten stub.
The historical theta-to-topic mapping remains; it cannot allocate new topic IDs.

Hedera's official SDK list excludes Python. `hiero-sdk-python==0.3.0` is hosted by
Hiero, Apache-2.0, community maintained, and classified Pre-Alpha by PyPI. It is
**experimental, not a shipping official SDK replacement**. Alpha Python callers
should use the official JavaScript/Rust write boundary. The optional
`hedera-experimental` dependency and `HEDERA_EXPERIMENTAL_PYTHON_ENABLED=true` runtime
flag permit explicit experiments with this transport. Nothing loads `.env` files.

Sources checked: https://docs.hedera.com/native/fundamentals,
https://docs.hiero.org/sdks, https://pypi.org/pypi/hiero-sdk-python/json,
https://github.com/hiero-ledger/hiero-sdk-python.

Runtime configuration: alpha is **testnet only**. `HEDERA_NETWORK` defaults to
`testnet`; every other value is refused, including mainnet and previewnet. There
is no mainnet client, mirror URL, enable flag or configuration path. A historical
enable environment variable has no effect. The backend calls only
`Client.for_testnet()` and the mirror origin is fixed to testnet.
`HEDERA_OPERATOR_ID` and `HEDERA_OPERATOR_KEY` are read only at client creation.
SDK `set_operator_with` receives an opaque callable signer. Its only instance
slot contains the public key; no raw key, signing method, weakref callback,
closure or default argument appears in instance state. The original SDK signing
callback remains behind a named CPython native capsule in a private registry.
Registry and function-global representations contain opaque handles. The SDK
client, Operator and retained transaction signers expose the same safe callable.
`__getstate__`, `__setstate__`, both reduction hooks and both copy hooks explicitly
refuse; even `object.__getstate__` can return only public-key state. Repr/str/vars,
dir/member discovery, bound method self/defaults/closures, JSON, all pickle
protocols, copy/deepcopy, logging and direct formatting of function globals are
checked on actual SDK objects. Constructor credentials remain rejected.

Error diagnostics are covered too: the raw-key `__init__` entry is a native
descriptor, so neither the key nor its bound signing method enters a Python
initializer local. It derives the public key and creates an owning capsule before
calling Python `_initialize(public_key, capsule)`. Even SIGINT before a Python
cleanup assignment leaves only public/opaque locals. Native initialization
releases its owner and replaces SDK error graphs before letting failures escape.
Encoded environment credentials are never bound to a backend local.
Sanitized failures are raised after their handlers finish, without retaining the
SDK exception/context graph. Failed backend construction releases any partially
installed native signer while the returned error is still alive. Ordinary rich
traceback logging (`TracebackException(capture_locals=True)`), public diagnostic
JSON and explicit context/cause inspection are tested. KeyboardInterrupt,
GeneratorExit and asyncio cancellation keep their control-flow types; SystemExit
keeps integer/None codes and discards other arguments. Actual interrupted SDK
signing and synthetic SDK failure/cancellation paths run for Ed25519 and ECDSA.

Local experimental signing requires the optional native ownership helper on
GIL-enabled CPython in its main interpreter. Missing/unsupported helpers fail
closed. From a source checkout, run `python scripts/build_hedera_native.py` with
the active interpreter and a compatible POSIX compiler toolchain. The default
wheel stays pure Python and refuses this experimental signer without the helper;
`RPP_BUILD_HEDERA_NATIVE=true python -m hatchling build -t wheel` explicitly builds
a platform-tagged wheel containing it. The build never reads Hedera configuration
or keys. Shipping Python callers should continue using the official JS/Rust
service boundary. No native binary is committed.
Rebuild the helper when updating from FIX-3: an older helper lacking the native
initializer entry refuses local signing.

The small C helper atomically acquires a callback and creates its owning capsule;
a stable native destructor balances failed/interrupted transfers. Python never
manually increments/decrements references. Native close tombstones and releases
in one call, and Python releases before unpublishing the registry entry. Saved
handles refuse; repeated cleanup is safe, including after interruption. Native
invocation holds a strong reference across concurrent close and sanitizes SDK
exceptions even when called directly. Capsule state and GC referents expose no
callback. Tests cover actual SIGINT before/after acquisition, publication and
release, plus GC/stress, rollback, concurrency, stale handles and interpreter
cleanup. Both key algorithms receive actual SIGINT at every executable Python
initializer line across success, reinitialization, store failures and controls;
escaped traceback locals and rich diagnostic copies are inspected in memory.
Factory paths are checked too. Restoring a raw-key Python initializer fails the
named diagnostic assertion. The automatic-owner removal control recompiles the C helper and fails
the actual-interruption regression; it cannot count a native crash as a kill.

This guards supported object inspection/serialization. Deliberate native C API
pointer dereferencing, arbitrary process-memory inspection and direct access to
the process environment remain outside this in-process boundary; it provides no
hardware or separate-process isolation.

`HEDERA_MAX_FEE_TINYBARS` defaults to and cannot exceed 100000000 (1 test HBAR per
transaction); SDK queries use the same maximum. `HEDERA_MAX_ATTEMPTS` defaults to
3, capped at 5. `HEDERA_MIRROR_ATTEMPTS` defaults to 20, capped at 30;
`HEDERA_RETRY_DELAY_MS` defaults to 1000, capped at 5000. SDK calls time out after
10 seconds; TLS verification stays on. The shared layer owns one total bounded
consensus-send budget. SDK/client attempts are one and native gRPC retries are
disabled. Only explicit BUSY/platform-not-active/platform-not-created prechecks
can retry; every send keeps the frozen signed transaction identity. A guard at
the concrete synchronous consensus RPC call rechecks the live `HEDERA_NETWORK`
after signing/channel construction and before each resend. Changed selection
refuses dispatch. The initialized testnet network object, ledger, node identities
and addresses, mirror address and TLS settings are pinned. Ordinary SDK network
replacement or mutation refuses dispatch even if a replacement retains the
testnet label/ledger. The route is checked before entering SDK execution and at
the concrete RPC boundary. A refreshed address book requires a new Session.
Ambiguous transport failures are not resubmitted; reconcile
the transaction ID before a manual rerun. The pinned SDK's private `_get_method`
and node `_build_channel_options` hooks are intentional dependencies; removing
or changing them requires renewed SDK boundary review.

Topic creation requires a SUCCESS receipt, matching mirror metadata and **both
admin and submit keys**, and a matching successful creation transaction with
operator payer identity. Missing or altered security keys refuse confirmation.
Submission checks SUCCESS plus mirror topic, operator payer, receipt sequence and
base64-decoded bytes. Payloads larger than 1024 bytes are refused, avoiding
multi-chunk writes with incomplete receipt verification. Redirects are refused.

Every public submit boundary preflights the expected topic and requires an
explicit `custom_fees` object with `fixed_fees: []`. Missing, unreadable, malformed
or nonempty schedules are refused before signing/sending, including every HBAR
and HTS fee. Each message transaction additionally serializes exactly one payer
custom-fee limit containing one zero-HBAR FixedFee and no token denomination.
That consensus-enforced limit rejects positive HBAR and unlisted HTS fees even
if the schedule changes after preflight. Topic creation uses only the separate
network fee limit because custom-fee limits are unsupported on that operation.
This follows the consensus handler/validator at
https://github.com/hiero-ledger/hiero-consensus-node/tree/9efa5c465a49249e55235d560b4c8addad4a0182
and mirror schema at
https://github.com/hiero-ledger/hiero-mirror-node/blob/87884a06cba0ff8bafbddf247ab9565f39739211/rest/api/v1/openapi.yml.

The smoke signs an envelope, verifies its signature locally, submits it, and
checks exact mirror bytes. It creates no accounts or tokens and uses no real HBAR.

Run from the repo: `python -m pytest -q tests/test_hedera_safe.py tests/test_hedera_sdk_security.py`,
`python scripts/hedera_python_mutations.py`, and
`python scripts/hedera_python_smoke.py`. Live proof requires a throwaway testnet
operator supplied through runtime environment and allowed Hedera consensus/mirror
egress, plus `HEDERA_TESTNET_THROWAWAY=true` runtime attestation. This environment
has neither; a BLOCKED smoke is not a testnet pass.

The security probes use actual pinned 0.3.0 SDK construction/signing/serialization
and fake discovery/channel/RPC endpoints. Synthetic keys are generated in memory
at runtime, never written or printed; even failing assertions/mutations report
only leak booleans. Socket connections are refused. These checks establish wire
and boundary behavior; they are not deployed-consensus or live testnet proof.
Key-bearing test/mutation processes disable core dumps. Native guard-removal
controls assert before stale-pointer use or mock the cast/decrement operation;
crashes, import failures and timeouts do not count as killed mutations.

For legacy `silver-pancake/hedera`, replace automatic success-on-stub fallback with
this explicit policy or the official write boundary. Keep AVT, Vizor and Soul NFT
writes closed until HTS/NFT receipt and mirror contracts have equivalent tests.
No changes to that historical checkout are claimed by this branch.
