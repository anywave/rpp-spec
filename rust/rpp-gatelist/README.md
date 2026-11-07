# Experimental signed gate lists and application admission

`rpp-gatelist` is an unpublished, standalone Rust 1.85.1 crate, `no_std`,
allocation-free, with no I/O, key generation, signer, clock or persistence in
the library. Ed25519 verification uses published `ed25519-dalek = 2.2.0`
(BSD-3-Clause); its pinned transitive packages are in Cargo.lock. Our wrapper,
tests and example are original Apache-2.0 code; no third-party source is vendored.
This is host software, not an FPGA signature-verification circuit.

The experimental local envelope is separate from every RPP address, control
frame and consent header. It signs a 16-byte domain/version, 32-byte signer
public identity, 32-byte host audience, big-endian u64 sequence, big-endian u64
exclusive Unix-seconds expiry, and 64-byte theta-sector bitmap. An Ed25519
signature follows those 160 bytes. Only exact 224-byte packets are accepted.
The bitmap replaces all 512 Mobius32 sector grants; it is not canonical-v2
addressing. Public keys are runtime inputs, never generated trust roots from a
received packet. No committed key, signed fixture, credential or certificate.

Provision the trusted pin and audience independently, and restore the durable
sequence floor to `GateKeeper::new`. `update` accepts only a strict signature
under that pin, this audience, a sequence greater than the floor and an expiry
strictly after the trusted host time. Rejected updates change no list, sequence
or clock. Accepted lists remain active until replacement or their own expiry;
rejecting an update does not extend the old deadline. Expired data is retained
for inspection but authorizes nothing in enforce mode. A u64::MAX sequence
cannot wrap: reprovisioning requires an owner decision outside this API.

`dispatch` is the protected call boundary. Supply current consent, a validated
Mobius32 address, trusted time, an audit/checkpoint callback and the operation.
It checks the optional update and current list before calling the operation.
An invalid supplied update refuses that request in enforce mode; subsequent
requests can still use the last good list. Log-only emits the same refusal but
allows the operation. Both modes always refuse absent consent and audit failure.
The audit row includes mode, intended dispatch, refusal and sequence. It records
permission to dispatch, not proof that the operation subsequently completed.

There is no mode default. Log-only must be explicitly selected and displayed
using `Mode::label`; the callback receives the mode on every request. No spec
text mandating an installation default was located. Proposed owner change:
new installations select enforce, existing log-only installations retain an
explicit visible warning until the owner changes them. This proposal is not
applied to any install configuration.

The host must persist the accepted sequence before effects (the callback can
checkpoint `Admission.sequence` and return false on failure), load it on restart,
obtain trusted nondecreasing time, acquire consent independently, and protect
pin/audience/configuration changes. Restart starts with no active list and
requires a newer list than the supplied floor. This conservative policy can
require the issuer to send a new list after restart. No durable store or desktop
app was available here, so crash-safe persistence and deployment wiring remain
host integration work. Even in log-only mode the host must not mistake a
rejected update for an accepted replacement.

## Try and verify offline

From the repository root, after obtaining the locked crates from an approved
package cache (`cargo fetch --manifest-path rust/rpp-gatelist/Cargo.toml --locked`
on a development host if needed):

```sh
cargo +1.85.1 run --manifest-path rust/rpp-gatelist/Cargo.toml --offline --locked --example admission -- enforce
cargo +1.85.1 run --manifest-path rust/rpp-gatelist/Cargo.toml --offline --locked --example admission -- log-only
cargo +1.85.1 fmt --manifest-path rust/rpp-gatelist/Cargo.toml -- --check
cargo +1.85.1 clippy --manifest-path rust/rpp-gatelist/Cargo.toml --all-targets --offline --locked -- -D warnings
cargo +1.85.1 test --manifest-path rust/rpp-gatelist/Cargo.toml --offline --locked
python tools/gatelist_scaffold/mutation_check.py --output /tmp/rpp-gatelist-mutations.json
```

The example generates one throwaway key in memory and performs local print-only
operations. It prints neither keys nor signatures. It requires an explicit mode
and demonstrates valid update, replay, last-good retention and active expiry.
Tests also generate throwaway keys with OS entropy. No Hedera client, network,
mainnet, account or payment exists in this component.

The crate is standalone because the existing workspace CI enforces an offline,
previously dependency-free build; it does not fetch the new verification deps.
The commands above are required separate gates, not a claim of hosted CI
coverage. No protected workflow is modified. Integration into CI needs an
owner-approved fetch plus these gates, then the embedded build if deployed.
