# Replacement PR descriptions for TR

These are prepared text only; this task makes Git pushes, not PR metadata writes.
They replace the obsolete flag-based policy in the three affected descriptions.

## rpp-spec #46

Python's signer serialization could expose the SDK signing method through public
state export. Store the original signing callback behind an opaque CPython
capsule, expose only the public key, and refuse state/reduction/copy protocols.
Public object, bound-method and rendered-globals probes exercise the actual
pinned SDK with ephemeral in-memory keys, including native-reference cleanup.
Callback and initialization failures discard SDK exception contexts and clear
secret-bearing locals before returning errors; interruption/cancellation types
are preserved without carrying sensitive diagnostic state.

The alpha accepts only testnet, pins initialized routing, refuses every topic
custom fee, and submits an explicit zero custom-fee allowance. There is no
mainnet activation flag; later mainnet support needs a signer outside any agent
account. Python remains an experimental community SDK boundary. Live testnet
verification and product wiring remain unproved; PR #47 is closed and untouched.

Validation: focused and full Python suites, named guard-removal controls, actual
SDK representation/serialization probes and native-handle lifecycle tests.

## mobius #291

Topic confirmation now verifies the requested absence of an admin key and the
requested submit key against actual mirror evidence. The SDK backend retains its
validated network-fee cap and rejects out-of-cap requests before preparation;
it also checks prepared bodies before send, including cross-backend transfers.

The standalone alpha layer is testnet only, refuses all topic custom fees and
serializes a zero custom-fee allowance. Mainnet has no constructor or activation
flag. Production valves, live testnet verification, durable reconciliation and
MSRV/Windows packaging remain separate. The reported PR base divergence remains
unresolved; no merge, rebase or base change is included.

Validation: actual signed SDK wire and mirror-parser/policy regressions, direct
prepare/send cap cases, core/SDK suites, opacity doctest and named mutations.

## digigami-stack #2

HCS topic creation requests a submit key and no admin key. Confirmation now
requires explicit null admin evidence and the exact requested typed submit key;
unexpected, missing or malformed key evidence remains unconfirmed. Paired tests
decode the SDK's actual create body and feed it through mirror confirmation.

The alpha remains testnet only with pinned endpoints, fresh concrete-send network
checks, bounded retries, refusal of all custom-fee topics and an explicit zero
custom-fee allowance. No environment flag enables mainnet; later support needs
a signer outside any agent account. Product wiring and live testnet proof remain
unproved. The package's public SDK facade exposes the guarded layer only.

Validation: shared/SDK suites, paired key-state cases and named guard-removal
controls, including removal of admin verification and contradictory SDK admin.
