# Fleet addressing and endpoint selection — CX-010

`rpp-fleet` is a provisional, unpublished Rust library for Connect and device
callers. It adds caller-owned identity/address bindings and endpoint records to
the existing `rpp-core`, `rpp-link` and `rpp-control` workspace. The library uses
`no_std` with `alloc` where collections are needed and forbids unsafe code. It
does not discover devices, open URIs, implement transports, authenticate identities,
implement cryptography, run a board or supply a radio/vendor HAL.

Base: `0d262bf`. Authority: the CX-010 card in `anywave/trellis-channel`,
`codex/inbox/rpp-spec.md`, blob `ef08b75300b454e5cc432972e8b90ca2112a6637`.
The specification, Python runtime, existing address layouts, consent header,
golden vectors and published constants are unchanged.

## What the current specification defines

References below are to the base tree, before the proposed addition:

| Source | Existing contract | Consequence for this library |
|---|---|---|
| `spec/SPEC.md:32–41` | Semantic-layer addresses are temporal routing states; resolve at point of access | A configured fleet binding is not permanent object identity or a promise of future validity |
| `spec/RPP-CANONICAL-v2.md:35` and `:219–244` | Canonical fields, constructor checks and their 32-bit encoding | Reuse `rpp-core`; do not allocate new identity bits or invent a compact-address hash |
| `spec/RPP-CANONICAL-v2.md:165–185` | Normalized radius and encoded-byte mapping | Preserve the existing quantizer and address bytes |
| `spec/RESOLVER.md:82–88`, `:97`, `:156` | Modality choice/discovery input, authentication delegated to identity layer, attempted modalities | Endpoint records are inputs; resolution is not enrollment or authentication |
| `spec/RESOLVER.md:739–802` | Informative/proposed overlay profile and reuse direction | Reuse existing policy and externally verified bindings; do not claim a deployed tunnel |
| `spec/NETWORK.md:83–98` | A separate `NodeRecord` with a 32-byte `SHA-256(public_key)` node ID | This does not define an identity-to-canonical-address derivation or authorize truncation into a fleet ID |

No identity-to-canonical-address derivation rule was found in the canonical
address specification, resolver or `rpp/address_canonical.py`. In particular,
the existing NodeRecord ID and resolver audit URI hash are not such a rule.
CX-010 therefore uses the explicitly labelled informative assignment proposal
below. It does not represent an already adopted identity/address standard.

## Explicit caller assignment

The named policy is `explicit-caller-assignment-v1`, represented by
`AssignmentPolicy::ExplicitCallerAssignmentV1` with no `Default`. An
`AddressBinding` associates one exact opaque identity with a caller-supplied
`rpp_core::canonical::CanonicalAddress`. Construction from fields and decoding
from an encoded word use the existing core address implementation.

The fleet identity is the full pair of a 16-byte opaque lender-key identifier
and a 16-byte opaque device identifier. These are identifiers, not key material.
The full pair has a deterministic 64-hex-character policy label. The device's
16-byte identifier is also the explicit control-frame ID used by this fleet;
it is not implicitly computed from the lender identifier. The local registry
requires unique full identities, encoded canonical words and device/control IDs.
This prevents ambiguity inside that registry, not across all deployments.

`derive(identity, binding)` requires the owner binding and an exact identity
match. Missing binding is `Unassigned`; supplying another identity's binding
fails. The operation is deterministic from those explicit inputs. It does not
compute an address from identity bytes alone, hash or truncate an identity,
claim collision resistance, prove control of a lender key, or make the 32-bit
address a globally unique machine identifier.

The same binding retains its canonical bytes when endpoint readings change.
Registry insertion rejects duplicate identities, addresses, control IDs and
attempted remapping without changing the existing registry. A future reassignment
or ownership-transfer lifecycle is outside this proposal.
Address collision checks use the encoded word, so distinct float inputs that
quantize to the same canonical bytes still collide.

An `AddressBinding` can preserve any core-accepted canonical object. Machine
registration separately requires the existing `CanonicalAddress::is_valid()`
predicate, rejecting null/wildcard/reserved field codes with `InvalidAddress`.
There is no copied range table or new reserved-bit policy; accepted reserved
bits are retained. Registration still does not prove routability, authorization
or ownership by a signer. It creates no membership, consent or admission grant.

This is one configured binding per registered machine, not a permanent routing
permission. Hosts still resolve at point of access and check current consent,
membership and trust. The semantic layer's temporal address contract is not
replaced by storing a canonical assignment in this registry.

## Endpoint records

Each registered node has endpoint records identifying a possible route and its
latest host-supplied reading. Logical record fields include a distinct endpoint
ID, kind, URI, `rpp_link::LinkReading`, a failure domain and explicit control,
tunnel/observation and reviewed-adapter capabilities. Data eligibility remains
the existing core kind/tunnel/reviewed-adapter decision, not a new data-allow
override. Additional identifiers and
capability booleans are application metadata, not new address/header fields or
an authentication implementation. Their values are claims the caller has
already checked using its existing trust layer.

The concrete capabilities are `tunnel_verified`, `reviewed_adapter`,
`observation_verified`, `control_capable` and a numeric `failure_domain`.
The four booleans default to false; failure domain zero is shared/unknown,
not evidence of independence. Endpoint `u32` IDs are unique **within a node**;
another node may use the same endpoint ID. The core link name combines the
registered encoded address word and endpoint ID as
`nAAAAAAAA-epEEEEEEEE`, with eight hexadecimal digits for each value. This
reversible 20-character label preserves core breaker/path identity within the
registry without hashing or truncating the full node identity. Registry address
word uniqueness prevents two nodes from aliasing that link name; it does not
make an address globally unique. URI text is not used as a route delimiter or
identity. An available
WebSocket voice gateway is not control-capable unless the host separately
attests a compatible control adapter.

| Endpoint kind | Policy underlay | Interpretation |
|---|---|---|
| LAN | LAN | An endpoint reachable over the caller's local IP path |
| Wi-Fi | Wi-Fi | An endpoint using that measured access path |
| Internet | Internet | An endpoint over a routed IP path |
| BLE | Bluetooth | Control-capable only unless the existing data policy and an explicitly reviewed adapter permit data |
| LoRa | LoRa | Constrained-carrier endpoint requiring its declared adapter/capability profile |
| WebSocket gateway | LAN | A Xiaozhi-use-case gateway with a `ws://` URI; selection identifies the LAN gateway and opens no WebSocket |

The URI is routing metadata. A `ws://` string does not prove encryption,
authentication, reachability, LAN locality or a compatible Xiaozhi firmware.
No gateway, device model or deployed server is asserted to exist by a fixture.
Existing encrypted-path requirements still need an externally established,
reviewed tunnel and a truthful capability assertion. BLE and LoRa names alone
do not provide an IP tunnel or authorize a new transport adapter.

`LinkReading` supplies integer latency/jitter in milliseconds, loss in parts per
million, availability and observation tick. These are live inputs to a selection
request, not measurements made by this library. The host supplies the current
tick, validates the observation source and maintains the meaning of each failure
domain. A different endpoint ID or URI does not establish an independent path.

## Reuse the existing policy

The fleet resolver projects eligible endpoint records into the existing core
overlay model as parallel direct endpoint links and delegates route selection
and ordering. This record model does not supply a multi-hop relay topology.
It does not introduce
another score formula, freshness window, consent matrix, circuit breaker,
clock rule or retry policy. Core deterministic tie breaks and live
latency/loss/jitter/availability behavior remain the source of ordering.
A resolver exclusively borrows one registry for its lifetime. Structural
registration/replacement cannot substitute an unrelated binding or endpoint
context while that borrow is active; only its validated `update_reading` method
forwards reading changes. The resolver's `registry()` view is read-only.

Data resolution reports the selected endpoint and failover order. Lack of an
eligible route is explicit no-channel, including a complete partition. A BLE
endpoint cannot carry data merely because it is present or control-capable;
the existing policy must also accept its declared data/tunnel/reviewed-adapter
capabilities. Advertised endpoints do not grant access.
Data selection is a query: it does not advance the real core send clock or add
actual data-send meter rows. Its rollback check is relative to accepted core
control state, not a separate history of every query tick. Hosts supply current
readings/ticks and integrate actual sends and outcomes through the existing
adapter/policy boundary.
`ControlResolution::failover_order` likewise lists endpoint IDs selected by
fresh clones of the pre-call core policy. Previewing alternatives creates no
extra real meter rows or sequence consumption; only the primary checked route
is returned for dispatch.

Control resolution uses the closed `rpp-control` vocabulary and a known data-path
reference from the same policy context. It restricts candidates to control-capable
paths and delegates failure-domain independence to core policy. It does not let
a caller invent an empty or unrelated data path to claim independence. Verification,
membership, consent, recipient/identity binding and sequence/replay freshness
remain necessary; no endpoint flag creates them. ALIVE, MEMBER-CHANGED or RESUME
does not start work, admit a node, undo STOP/revocation or restore consent.

The known data reference is the latest successful primary's **historical failure
domain**, not evidence that the data link is currently available. It is retained
until a successful replacement selection or the resolver/registry context is
discarded. No new reference TTL or eligibility probe is imposed. This permits
STOP/PAUSE on a fresh independent control path during a long data outage. The
current control-path readings still satisfy existing core freshness and
eligibility checks; stored data history does not exempt those checks.

The library chooses a route; real adapters remain responsible for sends,
outcomes and boundary errors. Reuse the existing first-token retry boundary and
meter rows when integrating those outcomes. Do not turn a new URI, fallback,
gateway or radio into a way to send a grant, key, model or prompt/answer content
on the control path. Billboards retain their existing scoped, verified and
expiring-fact policy; this task supplies no new billboard wire protocol.

`VerifiedControlRoute` retains the checked frame and selected endpoint. Its
consuming `dispatch` method rejects an adapter-kind mismatch through
`ControlDispatchError` before handing the frame to the caller's `LinkAdapter`
using the existing typed control path. Matching kind is not matching device:
the caller still binds the supplied adapter to the selected endpoint and real
failure domain. A Rust reference or URI cannot prove which physical device an
external adapter drives.
Core control acceptance/sequence consumption is a policy result, not proof of
transport receipt or remote execution.

## Evidence, reproduction and limits

The fleet scenarios cover LAN availability, a Wi-Fi latency spike, a BLE control
path, and a partition with explicit no-channel. Their committed golden outputs
are deterministic tables. They are not observations of a board or network.
Tests name mutations for wrong failover order, data on BLE and control on a data
path; exact commands, counts and hashes are in
[`CX-010-001.md`](../docs/codex/OUTBOX/CX-010-001.md).

From `rust/`, the workspace gates include:

```sh
cargo +1.85.1 fmt --all -- --check
cargo +1.85.1 clippy --workspace --all-targets --offline --locked -- -D warnings
cargo +1.85.1 clippy --workspace --all-targets --all-features --offline --locked -- -D warnings
cargo +1.85.1 test --workspace --offline --locked
cargo +1.85.1 test --workspace --features rpp-link/sim --offline --locked
cargo +1.85.1 test --workspace --no-default-features --offline --locked
cargo +1.85.1 test --workspace --no-default-features --features alloc --offline --locked
cargo +1.85.1 build --workspace --no-default-features --target riscv32imc-unknown-none-elf --offline --locked
cargo +1.85.1 build --workspace --no-default-features --features alloc --target riscv32imc-unknown-none-elf --offline --locked
```

The no-heap codecs remain available without `alloc`; fleet collections and
policy need the `alloc` profile. A library cross-build is not linked firmware
or a board run. It provides no HAL, radio, allocator, device discovery,
WebSocket client, certificate validation or identity enrollment. Actual board
models, firmware/runtime, memory limits, transports and reviewed verification
backends remain later integration work. The Rust workspace stays liftable and
uses no path dependency outside `rust/`; Python scaffolding remains development
support and is not required by final Rust builds.

## Exact informative proposal — NOT APPLIED

The additive proposal in
[`FLEET_ADDRESS_PROPOSAL.diff`](../docs/design/FLEET_ADDRESS_PROPOSAL.diff)
targets `0d262bf:spec/RESOLVER.md`. It is proposed/informative text only: the
file is evidence for steward review, not an applied specification change or an
adopted global identity/address scheme. Applying it requires a separate decision.
The same exact diff is intended for the CX-010 report.
