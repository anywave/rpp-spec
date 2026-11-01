# Multi-channel overlay proposal

CX-005 v2 · 2026-10-31 · base `95c67ef` · proposal for RADIX review.
This document does not adopt specification text, deploy a network, enroll a peer,
or change any RPP address, consent header, constant, or published vector. Tunnels
and signature verification in the accompanying simulator are abstract fixtures;
there is no cryptographic implementation or generated key.

## Goal and layers

RADIX asked for “traversing both mesh and traditional internet channels ... use
wifi and LAN and bluetooth to steer channels”, “vpn-like self creation
capability”, and tunnel billboards carrying “rules for agents and interactions”.
The useful engineering interpretation is one stable RPP destination across
changing paths, with automatic connectivity among **already authorized** peers.
Self-forming paths do not imply self-authorizing membership.

```text
RPP address: who/what the application requests, with existing consent checks
        |
        v
Authenticated address -> authorized overlay identity binding
        |
        v
Existing encrypted overlay: discovery -> direct tunnel -> authorized relay
        |
        v
Live link readings -> eligible path ranking -> selected underlay(s)
        |
        +-- LAN / Wi-Fi / internet: IP-capable carriers
        +-- Bluetooth: GATT control adapter, or separately reviewed IP adapter
        +-- LoRa: separately reviewed constrained-carrier adapter
```

An RPP address identifies a protocol destination; it is not a public key or proof
of identity. An authenticated binding records the destination, overlay peer
identity, allowed operations and current authorization epoch. A peer may discover
an endpoint before it is authorized, but neither discovery nor receiving an
advertisement admits it. Administrative enrollment, credential provisioning,
revocation and the user's consent action remain existing trust-layer duties.
This task does none of them.

Use the selected overlay's reviewed tunnel protocol unchanged. Peers discover
current endpoints, attempt a direct authenticated encrypted path, and use an
authorized relay if a direct path cannot be established. A relay forwards the
existing end-to-end protected payload and cannot grant access or manufacture an
RPP identity. The overlay's own existing handshake is below these application
traffic classes; application control messages do not transport its credentials.
Revocation invalidates both direct and relay paths, and cached bindings are
checked against current authorization before use.

“Any underlay” means an eligible carrier with a compatible reviewed adapter.
LAN and Wi-Fi are access links; the internet is a routed IP path that may use
either. They are not inherently independent failure domains. WireGuard and
Tailscale do not natively turn BLE GATT or bare LoRa into an IP tunnel. GATT has
MTU, connection and notification constraints; LoRa has airtime, rate and local
operating constraints. The simulator's non-IP tunnel capability is an explicitly
hypothetical adapter flag, never evidence that such an adapter ships. Bulk model
or prompt/answer traffic is not justified on a low-rate carrier merely because
the destination can be named.

## Mapping to the frozen resolver

Line references below refer to `spec/RESOLVER.md` at `95c67ef`.

| Existing hook | Extension proposed here | Missing from the current text |
|---|---|---|
| :82 modality selection | Filter by consent/trust/capability, then rank current eligible paths | Timestamped latency, loss, jitter and availability; stale-reading policy; stable tie break |
| :88 modality discovery | Discover adapters/endpoints for previously authorized overlay peers | Authenticated identity binding, bootstrap provenance, tunnel lifecycle and relay policy |
| :156 `tried_modalities` | Preserve every attempt and reason across direct/relay fallback | Per-attempt meter records, circuit state, retry boundary and terminal no-path outcome |
| :76 `bt://`; :129 `BLUETOOTH` | Resolve a characteristic through an explicit adapter | GATT framing/capacity, authenticated control envelope, expiry and independent-path policy |
| :92-103 identity outside resolver | Consume an authenticated binding from that identity layer | No new membership or consent authority is added to the resolver |
| :173-187 ordered preferences | Apply policy preferences only after current eligibility checks | Static preference order alone cannot establish current best measured path |

The current `available_modalities()` hook and fallback list are useful starting
points. They do not establish an encrypted mesh or specify how peers discover,
authenticate, rank or reconnect to one another. Existing Shell TTL, address
validity and consent conflicts remain in the steward packet. None is silently
settled by this overlay proposal.

## Live selection and failure handling

Maintain measurements per directed link, peer and adapter: sample time,
availability, latency in milliseconds, packet loss, jitter in milliseconds,
capability, authorization status and failure domain. A reading is evidence about
a path at a time, not an admission credential. Reject missing/stale observations
according to an explicit configured profile. Production probe authenticity,
sampling cadence, hysteresis, privacy budget and rate limits need an adopted
profile and deployment validation; this proposal invents no wire measurement
protocol.

At an operation boundary, first reject paths that lack current consent, trust,
adapter capability, fresh availability or closed/eligible circuit state. Rank
eligible paths using the declared measurement profile and stable identifier tie
breaks. All of latency, loss and jitter participate; a fixed modality preference
does not override ineligibility. A route with no direct path may use an
authorized relay whose complete path is available. Report `NO_CHANNEL` when no
eligible route exists. “Always picks an available channel” is conditional on at
least one eligible route; it is not a promise of connectivity during a partition.

An operation may try a different path only before its first token is emitted.
After the first token, a transport failure produces an explicit partial/failed
result for the caller; it does not automatically replay the operation. Token
state is operation-wide, including across relays. A circuit breaker temporarily
excludes a failed link, with deterministic cooldown/probe behavior in the demo.
Availability and authorization are rechecked when retrying. Record all attempts,
including failure, denial, circuit exclusion, partial delivery and no-path
outcomes, without dropping previous meter rows. Billing or retry of non-idempotent
side effects needs an application-level policy beyond this simulation.

## Three traffic classes

All three classes use the same current peer authorization, consent and trust
checks. A different radio or relay never admits a peer, conveys an admission
grant, restores revoked consent or substitutes for a consent click. Production
signing and verification must use an existing reviewed library/protocol; the demo
accepts only an explicit verification fixture and cannot establish authenticity.

| Class | Allowed payload and path | Required limits |
|---|---|---|
| Data | Existing authorized application data over the best measured eligible path; direct or relay | Current consent on every attempt; compatible reviewed tunnel adapter; no membership grant or credential provisioning |
| Control | Small signed `ALIVE`, `MEMBER-CHANGED`, `STOP`, `PAUSE`, `ROUTE-AROUND`, `RESUME`; Bluetooth may provide a separate path | Closed schema and size bound; issuer authorization, replay/sequence checks and an independent failure domain when available |
| Billboards | Signed scoped facts/rules in the six-field schema below, over an eligible path | Authorized issuer, verified receipt, schema/type/size checks, replay protection and validity checked again at application time |

Control uses a closed operation enum and a bounded envelope of identifiers and
sequence metadata. It never carries `START`, a grant, consent, a key, a model,
prompt text or answer text, including through an extra field or nested payload.
`MEMBER-CHANGED` is an invalidation/revalidation notice; it cannot add membership.
`RESUME` may lift a temporary pause on a still-authorized, already running
operation after current consent revalidation. It cannot start a new operation,
undo `STOP`, undo revocation, or authorize an operation. `ROUTE-AROUND` changes
eligible routing only. Delivery of any notice is separate from authorization to
apply it.

Prefer a control path with a distinct physical failure domain from the data path
when such a path is eligible. Two IP names sharing one Wi-Fi interface are not
independent. Bluetooth can be independent of a wired/IP outage; it still needs
its authorized adapter and existing identity binding. If no independent path
exists, expose that limitation instead of calling the control path independent.
No path is a guarantee that STOP arrives under a complete partition; local
revocation/stop behavior remains necessary.

Billboard payload:

```json
{"machine":"node-a","kind":"rule","fact":"avoid-link-7","since":10,"until":20,"receipt":"fixture-receipt-1"}
```

The semantic schema is exactly `{machine, kind, fact, since, until, receipt}`.
Signature, verified issuer and authorization scope belong to the authenticated
envelope/receipt verification result; arbitrary extra semantic fields are
rejected. The example is a deterministic simulation fixture, not a real signed
receipt. `machine` identifies the subject within the issuer's authorized scope;
`kind` selects an allowlisted, non-executable fact/rule type; `fact` is bounded
typed data for that type; `since` and `until` define a half-open interval
`since <= now < until`; `receipt` binds the exact payload and authorized issuer.
Reject inverted/empty intervals, unknown kinds, unverified receipts,
unauthorized issuers and replays. A future fact may be retained as inactive and
cannot be applied before `since`. Expired facts leave the active set, and expiry is checked
on every application as well as on arrival. Relaying or caching does not extend
`until`. Clock synchronization/skew bounds and persistent replay storage are
production profile decisions; the demo uses only integer logical time.

Billboards are untrusted input until verified. An accepted billboard can affect
only its declared operational scope (for example, avoiding an otherwise eligible
link). It cannot alter agent instructions, expand capabilities, execute code,
create a grant, bypass consent or override STOP/revocation. A signature proves
origin/integrity under an existing trust policy; it does not prove the fact true
or give its issuer unlimited authority. Conflicting rules use an explicit adopted
precedence policy; absent that policy, reject the conflict and report it.

## Read-only prior-art comparison

The GitHub connector was online for read-only upstream inspection on 2026-10-31.
No software was installed, run, enrolled or connected for this comparison.
The table describes inspected upstream source/documentation, not a fresh audit,
performance benchmark or guarantee of protocol review. License statements are
for the pinned implementations below; protocol names do not have one universal
implementation license. In particular, do not substitute remembered older
ZeroTier or Reticulum license labels for the fetched texts.

| Project | Underlays and scope | NAT traversal / relay | Identity model | Inspected license | Fit for this goal |
|---|---|---|---|---|---|
| WireGuard [W] | Encrypted IP tunnel over UDP/IPv4/IPv6; works over LAN, Wi-Fi and routed internet | Endpoint roaming and keepalive; no bundled peer discovery, rendezvous or relay service | Configured public-key peers and allowed IPs | `wireguard-go`: MIT; kernel/tool implementations have separate licenses | Reuse tunnel primitive; insufficient alone for self-forming connectivity or BLE/LoRa |
| Tailscale / Headscale [T,H] | WireGuard overlay on IP-capable LAN/Wi-Fi/internet; Tailscale client with self-hosted Headscale coordination | NAT discovery/traversal; direct paths; DERP encrypted-packet relay when direct fails | Node keys distributed by control plane; administrator/user/identity-provider enrollment | Inspected client and Headscale: BSD-3-Clause; some platform GUI wrappers and hosted service are separate | Recommended IP starting point: working discovery/direct/relay structure without inventing a tunnel or handshake |
| Nebula [N] | UDP/IP overlay across LAN/Wi-Fi/internet | Lighthouse discovery and UDP hole punching; inspected relay config is labelled experimental | CA-signed host certificates bind IP/name/groups | MIT | Strong alternative for operator-managed PKI/groups; assess relay behavior for target deployment |
| ZeroTier [Z] | Secure peer network plus virtual Ethernet over IP | Peer-to-peer paths and root/relay infrastructure; slow fallback relay documented | Key-derived 40-bit node identity; network controller authorizes membership | Current inspected core/agent MPL-2.0; `nonfree/` controller/related components use source-available license with commercial-use conditions; `ext/` separate | Useful L2 option; component/license boundaries and controller dependency need an explicit adoption decision |
| Yggdrasil [Y] | Self-arranging encrypted IPv6 overlay over IPv4/IPv6; inspected links include TCP, TLS, QUIC, SOCKS and Unix | Multicast local discovery; configured peer links forward traffic; no claim here of built-in general NAT hole punching | Persistent key-derived node identity/address; peering is not an application access-control boundary | LGPLv3 with linking exception | Good self-arranging routed-mesh reference; application admission and privacy still need separate policy |
| Reticulum [R] | Heterogeneous non-IP/IP stack: Ethernet, TCP/UDP, serial, packet radio, LoRa/RNode; Wi-Fi/IP and RNode host Bluetooth connection | Self-configuring multi-hop transport; reachable TCP/UDP interfaces can bridge networks; no general NAT traversal service verified | Cryptographic identity/destination addressing and announced paths | Current fetched custom Reticulum License, with harmful-use and model-training restrictions; not plain MIT | Closest radio/heterogeneous-carrier candidate; evaluate exact version/license and reviewed backend before any adapter adoption; Bluetooth host transport is not proof of arbitrary BLE GATT support |
| libp2p [L] | Application P2P stack; inspected Go defaults include TCP, QUIC, WebSocket, WebTransport and WebRTC | AutoNAT, rendezvous/mDNS, circuit relay and direct connection upgrade protocols | Peer IDs derived from public keys; application authorization separate | Inspected Go implementation MIT; other implementations/specs separate | Reuse when application streams/discovery matter more than a virtual IP network; requires explicit protocol/profile selection |
| BLE GATT / BlueZ [B] | Local Bluetooth LE services and characteristics; negotiated MTU, reads/writes/notifications | No internet NAT traversal or global relay in GATT itself | Bluetooth device/link identity and pairing; application overlay identity must be bound separately | GATT is a Bluetooth specification with separate qualification terms; inspected BlueZ GATT server source GPL-2.0-or-later; implementation components vary | Bounded independent control adapter; no automatic encrypted global overlay or RPP membership authority |

**Recommendation — REUSE.** Start with Tailscale clients and a self-hosted
Headscale coordinator plus an explicitly authorized DERP relay for IP-capable
LAN, Wi-Fi and internet paths. They already supply the discovery, NAT handling
and relay shape needed for the VPN-like requirement while reusing WireGuard.
Keep the RPP binding, consent gate and live measurement policy above that
implementation. Use an existing platform GATT API only for the bounded independent
control adapter after an identity/signature profile is approved. Investigate
Reticulum as a separate constrained-radio adapter candidate, with its exact
license/backend and target-device behavior reviewed before selection. None of
these choices ships in this task; none is claimed to meet every non-IP carrier
requirement without an adapter. Nebula is the simpler alternative if RADIX
prefers a private CA/lighthouse model and accepts the evaluated relay profile.

Inspected immutable source references (commit pins; paths are the files read):

- [W] [wireguard-go README and MIT notice](https://github.com/WireGuard/wireguard-go/blob/b3bc704ef0ee21a36298601a9e1e5ff90377ac52/README.md),
  [UDP/IPv4/IPv6 binding](https://github.com/WireGuard/wireguard-go/blob/b3bc704ef0ee21a36298601a9e1e5ff90377ac52/conn/bind_std.go).
- [T] [Tailscale README](https://github.com/tailscale/tailscale/blob/49aa9c859c4d193b5ecd5f4ccda7b65979837fd8/README.md),
  [LICENSE](https://github.com/tailscale/tailscale/blob/49aa9c859c4d193b5ecd5f4ccda7b65979837fd8/LICENSE),
  [magicsock paths/NAT handling](https://github.com/tailscale/tailscale/blob/49aa9c859c4d193b5ecd5f4ccda7b65979837fd8/wgengine/magicsock/magicsock.go),
  [DERP purpose](https://github.com/tailscale/tailscale/blob/49aa9c859c4d193b5ecd5f4ccda7b65979837fd8/derp/derp.go).
- [H] [Headscale README](https://github.com/juanfont/headscale/blob/7721d8c29978b65b68269bb58391fcd25a8c1085/README.md),
  [DERP/STUN configuration](https://github.com/juanfont/headscale/blob/7721d8c29978b65b68269bb58391fcd25a8c1085/config-example.yaml),
  [LICENSE](https://github.com/juanfont/headscale/blob/7721d8c29978b65b68269bb58391fcd25a8c1085/LICENSE).
- [N] [Nebula technical overview](https://github.com/slackhq/nebula/blob/fb4ef139cbb4af67d142c72083fb735f56460e50/README.md),
  [relay configuration](https://github.com/slackhq/nebula/blob/fb4ef139cbb4af67d142c72083fb735f56460e50/examples/config.yml),
  [LICENSE](https://github.com/slackhq/nebula/blob/fb4ef139cbb4af67d142c72083fb735f56460e50/LICENSE).
- [Z] [ZeroTier README](https://github.com/zerotier/ZeroTierOne/blob/899352e38405968516bb12a770f0ac02f6058fa8/README.md),
  [identity](https://github.com/zerotier/ZeroTierOne/blob/899352e38405968516bb12a770f0ac02f6058fa8/node/Identity.hpp),
  [MPL](https://github.com/zerotier/ZeroTierOne/blob/899352e38405968516bb12a770f0ac02f6058fa8/LICENSE-MPL.txt),
  [nonfree terms](https://github.com/zerotier/ZeroTierOne/blob/899352e38405968516bb12a770f0ac02f6058fa8/nonfree/LICENSE.md).
- [Y] [Yggdrasil README](https://github.com/yggdrasil-network/yggdrasil-go/blob/2c7f050fc5398ecd8ac5f77e9bb5bd91aa2e9e35/README.md),
  [peer/discovery configuration](https://github.com/yggdrasil-network/yggdrasil-go/blob/2c7f050fc5398ecd8ac5f77e9bb5bd91aa2e9e35/src/config/config.go),
  [carriers](https://github.com/yggdrasil-network/yggdrasil-go/blob/2c7f050fc5398ecd8ac5f77e9bb5bd91aa2e9e35/src/core/link.go),
  [LICENSE](https://github.com/yggdrasil-network/yggdrasil-go/blob/2c7f050fc5398ecd8ac5f77e9bb5bd91aa2e9e35/LICENSE).
- [R] [Reticulum README: capabilities/interfaces and backend limits](https://github.com/markqvist/Reticulum/blob/e40191b3d193b46b7f2d8a44424a594cd758839b/README.md),
  [current LICENSE](https://github.com/markqvist/Reticulum/blob/e40191b3d193b46b7f2d8a44424a594cd758839b/LICENSE).
- [L] [Go libp2p transports](https://github.com/libp2p/go-libp2p/blob/03349944847387886bf06b65993b2a03c1e6d12d/defaults.go),
  [LICENSE](https://github.com/libp2p/go-libp2p/blob/03349944847387886bf06b65993b2a03c1e6d12d/LICENSE),
  [protocol index](https://github.com/libp2p/specs/blob/c750236de43cd8b246a824b377dfdb26bae686db/README.md),
  [Peer IDs](https://github.com/libp2p/specs/blob/c750236de43cd8b246a824b377dfdb26bae686db/peer-ids/peer-ids.md).
- [B] [BlueZ GATT service](https://github.com/bluez/bluez/blob/14bd6ab65f4a647302edbd6df27f6faa91bee8a8/doc/org.bluez.GattService.rst),
  [characteristic/MTU/security flags](https://github.com/bluez/bluez/blob/14bd6ab65f4a647302edbd6df27f6faa91bee8a8/doc/org.bluez.GattCharacteristic.rst),
  [GATT server license header](https://github.com/bluez/bluez/blob/14bd6ab65f4a647302edbd6df27f6faa91bee8a8/src/gatt-database.c).

## Simulator and limits of the evidence

`tools/overlay_sim/` supplies the stdlib-only deterministic reference simulation,
property/mutation checks, scripted node/link scenarios and CSV/Markdown output.
Use its README for exact commands, policy parameters and observed counts. A
scripted sample is a live reading at its logical timestamp inside the model; it
is not a physical radio observation. The model's link reading is symmetric;
forwarding consent remains directed. Its path cost is the sum of
`1000 * (latency_ms + 2 * jitter_ms) + loss_ppm`, then hop count and link-ID tuple
for deterministic ties. Readings are fresh for ticks 0 through 5 after sampling;
two failures open a link circuit for two ticks. It returns an explicit
`NO_INDEPENDENT_CHANNEL` when control cannot avoid all data failure domains.
Control additionally requires a nonempty route snapshot previously selected by
this simulator for the same endpoints, and a verified tunnel verdict on every
control hop; default or unknown references are denied. These are fixture
verification results, not an implementation of signatures or tunnels. Rejected,
invalid and no-channel operations do not advance accepted scenario time. Only
accepted operations/application queries advance time; recipient validation comes
before application-time advancement. Replay storage uses `(issuer, receipt)`, so
one issuer cannot consume another issuer's receipt ID. The scenario CLI requires
an explicit output directory and never chooses an in-tree default destination.
Billboard `kind` is restricted to `fact` or `rule`; both are inert records in
this demo, and no fact is executed or installed as an agent instruction.
Numeric ranking weights, breaker cooldown,
message-size bounds and clock policy are IMPOSED demonstration choices, not RPP
constants or adopted specification values. The simulator demonstrates routing
and traffic-policy invariants under its assumptions. It cannot validate NAT
interoperability, a cipher, a signature, radio independence, adversarial clocks,
packet delivery, throughput or a deployable overlay.

Conditions before deployment: RADIX adopts an overlay/profile and the proposed
resolver contract through governance; an existing reviewed implementation is
version-pinned; enrollment/revocation/consent bindings are reviewed; target OS and
device adapters are exercised; real direct/NAT/relay/failure/revocation cases are
measured; control independence is demonstrated on actual failure domains; and
billboard issuer, schema, replay, clock-skew and conflicting-rule policies are
specified. These are steward/deployment work, not claims completed by this task.

## Exact proposed resolver addition — NOT APPLIED

RADIX options: (A) keep the current resolver unchanged and retain this design as
an experiment; (B) adopt the following additive contract through an RFC, keeping
implementations/profile values separate; (C) request a narrower or different
profile. Recommended default: **B for review, with deployment still gated**,
because it records consent and traffic invariants without changing any address
or wire header. No option is selected by this document.

The exact unified diff below applies to `95c67ef:spec/RESOLVER.md`. It adds only
the contract; it intentionally leaves all existing steward conflicts unresolved.
The same bytes are reproduced in `docs/codex/STEWARD_PACKET.md`.

<!-- RESOLVER_PROPOSAL_BEGIN -->
````diff
--- a/spec/RESOLVER.md
+++ b/spec/RESOLVER.md
@@ -735,6 +735,57 @@
 }
 ```

+### 11.3 Optional Authenticated Multi-Channel Overlay Profile
+
+An implementation MAY resolve an RPP address through an existing encrypted
+overlay. The RPP address identifies the requested destination; an authenticated
+binding from the existing identity layer identifies the authorized overlay peer.
+Discovery and automatic tunnel formation MUST NOT create membership, carry an
+admission grant, replace a consent action, or bypass current consent and trust
+checks. The same checks apply to every direct, relay and underlay path.
+
+The overlay MUST reuse an existing reviewed tunnel protocol and implementation;
+this profile defines no cipher, handshake or key exchange. Peers MAY discover
+endpoints and form direct tunnels among already authorized members, or use an
+authorized relay when no direct path exists. Non-IP carriers require an explicit
+compatible adapter; a Bluetooth URI alone does not establish tunnel capability.
+
+Path selection MUST first filter by current authorization, consent, adapter
+capability, fresh availability and circuit state. It MUST then use timestamped
+latency, loss and jitter readings under a declared measurement/ranking profile
+with a deterministic tie break. The profile MUST state freshness, hysteresis,
+probe and circuit-breaker policies. No eligible path yields an explicit
+NO_CHANNEL result. An alternate path MAY be retried only before the operation's
+first emitted token; after that boundary, automatic replay MUST NOT occur.
+Every attempt and terminal outcome MUST retain a meter row, including denial,
+failure, partial delivery and no-path outcomes. Existing tried_modalities MUST
+retain the attempted modality history across direct and relay fallback.
+
+Implementations MUST distinguish three application traffic classes:
+
+- Data uses the best measured eligible path for the authorized operation.
+- Control contains only small signed ALIVE, MEMBER-CHANGED, STOP, PAUSE,
+  ROUTE-AROUND or RESUME notices in a closed, bounded envelope. It MUST NOT carry
+  START, grants, consent, keys, models, prompt text or answer text. Bluetooth MAY
+  provide an independent control path; independence MUST be assessed by failure
+  domain, not by URI or modality name alone. MEMBER-CHANGED invalidates/rechecks
+  membership and cannot admit a peer. RESUME cannot start an operation, undo
+  STOP/revocation or restore consent; current authorization is checked again.
+- Billboards contain signed scoped facts/rules with exactly the semantic fields
+  {machine, kind, fact, since, until, receipt}. Signature/issuer verification is
+  performed by an existing reviewed mechanism. Implementations MUST validate
+  issuer authority, receipt binding, type/size limits, kind allowlist and replay
+  state, and apply a fact only while since <= now < until. Expiry MUST be checked
+  on arrival and every application; caching or relaying cannot extend until.
+  A billboard cannot change agent instructions, execute code, expand authority,
+  create a grant, bypass consent or override STOP/revocation. The adopted profile
+  MUST specify time/skew handling, replay persistence and conflict precedence;
+  an unspecified conflict is rejected and reported.
+
+These traffic rules do not provision credentials or alter the consent header,
+address formats, Shell TTLs, published constants or existing trust decisions.
+
+
 ---

 ## 12. Version History
````
<!-- RESOLVER_PROPOSAL_END -->
