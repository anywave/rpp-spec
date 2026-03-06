# RPP Primer — What It Is, Why It Exists, How It Works

**Version:** 1.0.0
**Status:** Canonical
**Audience:** Senior engineers evaluating RPP for the first time

Read this before looking at any code or spec. This document answers three questions:
what problem RPP solves, what the underlying theory is, and what it is actually useful for.

---

## The Problem

Every addressing scheme in widespread use today is **spatial**. An IPv4 address says
where a host lives on the network. A memory address says where a byte lives in RAM. A
database row ID says where a record lives in a table. A URL says where a resource lives on
a server.

All of them answer WHERE. None of them answer:

- **When** — how long should this data be routable? When does its permission expire?
- **Who** — who has consent to receive it? Under what conditions?
- **What** — what kind of data is this? What routing priority does it carry?
- **How urgently** — does this need to arrive in 25 nanoseconds, or can it wait 30 days?

These properties exist in every real system. They are just attached separately:

| Property | How it is attached today |
|----------|--------------------------|
| Expiry | TTL field in a DNS record; Cache-Control header in HTTP; exp claim in JWT |
| Access control | ACL on the file; firewall rule on the subnet; scope claim in OAuth |
| Data type | MIME type header; schema registry; out-of-band agreement |
| Priority | QoS DSCP bits in IP header; queue configuration; SLA document |

Each layer is **maintained separately**. Each layer can drift out of sync with the others.
A GDPR erasure request requires coordinating all four layers simultaneously: delete the
record, revoke the ACL entry, expire the cache, update the schema registry. If any step
fails silently, the data is still routable even though it should not be.

**RPP's answer:** collapse all four properties into the address itself. The 28-bit address
integer encodes data type, consent level, temporal scope, and routing mode. The address IS
the policy. You cannot hold the address without holding the policy. They are the same bits.

---

## The Torus — Why Geometry?

The RPP address is a coordinate, not a counter. Specifically, it is a coordinate on a
four-dimensional torus: two angular dimensions (theta, phi), a radial depth (shell), and a
harmonic component encoding routing mode.

A torus is the right structure for three concrete reasons.

**1. No edges, no corners.** A flat address space (IPv4's 0 to 2^32) has a beginning and
an end. The address 0.0.0.0 and 255.255.255.255 are qualitatively different from
192.168.1.1. Corner addresses require special handling. A torus has no corners. Every
point on a torus has the same local neighborhood — the same number of adjacent addresses,
reachable by the same angular arithmetic. There is no "maximum consent level" that needs a
special routing rule, and no "first data type" that is topologically privileged.

**2. Two independent angular dimensions.** Theta and phi are independently cyclic. Theta
encodes data type: which sector of the address space does this data belong to? Phi encodes
consent: at what level of authorization should this data be routed? These two properties
are genuinely orthogonal — changing the consent level of a record does not change what kind
of data it is. The torus encodes this orthogonality structurally. Modular arithmetic on
theta and phi is independent. A routing node can compare consent levels with a single
integer comparison on phi, without touching theta.

**3. Rotation is the natural operation.** Moving a point on a torus means rotating it
around one or both axes. Rotation preserves the topology. This makes rotation a natural
primitive for encryption: rotating the payload by an amount derived from the local routing
field produces encrypted output without any key exchange, because the key IS the local
field state. This is the basis of rotational encryption (described below).

Compare to alternatives:

- IPv4 uses a **linear** address space. Distance is subtraction. No geometric structure is
  encoded in the address.
- Kademlia DHT uses a **hypercube** with XOR distance. The metric works but encodes nothing
  about the data — XOR distance is a routing convenience, not a semantic property.
- RPP uses a **torus** because the two properties it encodes (data type, consent) are
  genuinely cyclic. There is no maximum consent value that is qualitatively different from
  any other. The address space wraps, and that wrap is physically meaningful.

The field mapping:

| RPP Field | Bits | Geometric Role | Range |
|-----------|------|---------------|-------|
| Shell     | 2    | Major radius (storage tier depth) | 0–3 |
| Theta     | 9    | Azimuthal angle (data type sector) | 0–511 |
| Phi       | 9    | Poloidal angle (consent level) | 0–511 |
| Harmonic  | 8    | Minor radius (routing mode / frequency) | 0–255 |

Total: 28 bits. Maximum address: `0x0FFFFFFF`. Address space: 268,435,456 concurrent
routing states.

---

## Consent as Address

The most consequential design decision in RPP: consent is not a gate outside the address.
Phi IS a component of the address.

In a conventional system, an address names a resource and an ACL says who can access it.
The address and the permission are separate objects. You can hold the address without having
the permission, and the address continues to exist even if the permission is revoked.

In RPP, a packet with phi=300 can only be routed by nodes whose consent field accepts
phi=300. A node with a lower consent threshold simply cannot route the packet — not because
it is blocked by a firewall, but because it cannot construct the correct routing coordinate.
The consent level is baked into the integer it is trying to forward.

Consequences:

**Revocation is address change.** Revoking consent means changing phi. Changing phi changes
the address. The old address becomes unresolvable — not because a revocation message was
broadcast, but because the routing target no longer exists at those coordinates. No
propagation delay. No revocation list. The address simply stops resolving.

**No central authority.** Every routing node enforces consent by the same two-line
comparison: does this packet's phi value fall within my configured consent range? If yes,
forward. If no, drop. Consent enforcement is distributed across every node in the mesh.
There is no policy server to compromise, no ACL database to corrupt.

**GDPR Art. 17 compliance is structural.** The right to erasure requires that a data
subject's information become unreachable after a deletion request. In RPP, this is address
expiry: the address stops routing at the TTL. No DELETE cascade. No propagation to
downstream caches. The routing coordinate ceases to exist. Data stored at that coordinate
is unreachable by construction.

---

## Temporal Addressing

The shell field encodes retention scope IN the address bits. Not in a header. Not in a TTL
field attached to the address. The same 28-bit integer that says "route this to the Memory
sector with consent level 300" also says "this is a 5-minute session-scoped record."

Shell values and their temporal scope:

| Shell | Name   | Lifetime   | Physics |
|-------|--------|------------|---------|
| 0     | Hot    | 25 ns      | Spintronic T2 decoherence — the address physically ceases to exist |
| 1     | Warm   | 5 minutes  | Session scope — transaction-bounded routing permission |
| 2     | Cold   | 24 hours   | Daily archive — agreement-scoped |
| 3     | Frozen | 30 days    | Long-term archive — until explicit intervention |

The critical property: you cannot separate the data from its retention policy. They are the
same integer. A system cannot accidentally store a shell=0 address and reuse it an hour
later — the address self-expires. The data retention policy is enforced by the address
arithmetic, not by a separate policy engine that could be misconfigured.

On spintronic hardware, this enforcement is physical rather than logical. A shell=0 address
routes permissions encoded as spin states. Spin states decohere into thermal noise at T2
time (approximately 25 nanoseconds for current spintronic substrates). The routing
permission is not just expired — it has decohered. Software implementations must enforce
equivalent TTL semantics per shell tier, simulating in software what spintronics enforces
in physics.

This also gives RPP an important security property: stolen addresses go stale. An adversary
who captures a valid shell=1 address at t=0 and attempts to use it at t=301 seconds gets
nothing. The address has not been revoked — it does not exist anymore.

---

## Rotational Encryption (Pong)

In conventional encryption, a key is generated, exchanged, stored, and managed. The key
material is a separate artifact from the data and the routing path. If the key is
compromised, the encrypted data is compromised.

RPP's rotational encryption eliminates the separate key artifact. The cipher IS the route.

Each routing node holds a live consent field state — a dynamic value that reflects the
current local consent configuration. When a packet transits a node, the node applies a
rotation to the packet's state vector: a geometric transformation derived from the node's
current field state. The rotation is not stored anywhere. It is not transmitted anywhere.
It is not negotiated. It exists only in the node's live field state at the moment of
transit.

Correct decryption requires replaying the exact rotation applied at each node, in reverse
order, using the same field state values. This is only possible if:

1. You know the sequence of nodes the packet transited (the route).
2. You know each node's field state at the exact moment of transit.

An attacker who captures a packet mid-route has an encrypted state vector with no key to
decrypt it. The key material — the sequence of rotation values — decohered at each node as
the field state advanced. On spintronic hardware, this decoherence is physical: the
rotational key exists for T2 time and then becomes thermal noise.

The "pong" metaphor comes from the packet's trajectory. Each routing node's field deflects
the packet's angular position slightly — like a ball deflecting off a paddle. The
accumulated deflections across all hops IS the encryption. The trajectory IS the cipher.
There is no separate crypto layer. Routing and encryption are the same operation.

---

## The Ford Protocol — Why "Hold Not Drop"

TCP and UDP treat packets as copies of data. If a packet is lost, the sender retransmits an
identical copy, because the sender still has the original data. The network is allowed to
drop packets because dropping is recoverable.

The Ford Protocol addresses a fundamentally different problem: routing a live cognitive
state that exists in exactly one place. A consciousness state packet (CSP) carries the
current state of a running cognitive process. There is no retransmit buffer at the origin.
The origin IS the only copy. If the packet is lost mid-transit, the state is lost — not
delayed, not degraded, but gone.

This is why Ford Protocol has five phases instead of TCP's three:

| Phase | Name      | What Happens |
|-------|-----------|--------------|
| 1     | SCOUT     | Origin probes destination: does it have capacity? Correct T2? Modality support? |
| 2     | HANDSHAKE | Full consent verification: ZK consent proof, continuity chain, epoch freshness |
| 3     | TRANSIT   | Wagon enters the river: CSP serialized to LiminalState and transmitted. Origin holds complete copy. |
| 4     | ARRIVAL   | Destination receives LiminalState, verifies timeout and signatures, instantiates state |
| 5     | RELEASE   | Origin receives CoherenceConfirmed, verifies destination signature, then dissolves its copy |

The extra phases (TRANSIT hold and RELEASE confirmation) exist because the packet cannot be
retransmitted. TCP can skip directly from "send" to "acknowledge" because retransmit is
always an option. Ford Protocol cannot. It must hold the complete origin copy during
crossing, verify coherence at the destination, and only release after confirmed arrival.

The wagon metaphor: the wagon can cross many rivers. It must arrive intact. If the crossing
fails, the wagon returns to the near bank — it does not drown mid-river. "You have died of
dysentery" is not a valid outcome for a consciousness state crossing.

Recovery if a crossing fails escalates through five levels: reroute, steering, pull-back,
copy-and-collect, and abort. Abort means the shell TTL expired and the state is
irrecoverable without re-origination. This is the Ford Protocol equivalent of the TCP
connection timeout — but it is the last resort, not the first response.

---

## Use Cases

**GDPR and CCPA compliance.** Consent is baked into the address. Revoking consent changes
phi, which changes the address. The old address stops routing immediately. No DELETE
cascade. No downstream cache invalidation. No propagation message. The data is unreachable
by construction at the moment phi changes.

**Healthcare (HIPAA).** Records above phi=450 are self-enforcing: only nodes configured
with high-trust consent fields can forward them. A misconfigured downstream node that does
not meet the phi threshold cannot route the packet even if it tries. Consent enforcement is
distributed to every node in the mesh, not centralized in a policy server that could be
compromised or misconfigured.

**IoT data sovereignty.** Shell=0 session-scoped tokens expire in T2 time. A stolen token
from a sensor network decoheres before it can be replayed to a different context. The
security property is enforced by physics on spintronic hardware and by TTL arithmetic on
conventional hardware.

**Multi-substrate AI routing.** The ConsciousnessStatePacket carries a cognitive state
across heterogeneous substrates: spintronic, IPv4, IPv6, LoRa, satellite links. Ford
Protocol guarantees that the state either arrives intact or does not arrive at all.
Substrate boundaries are transparent to the state being routed.

**Distributed consent mesh.** There is no routing table mapping "this data" to "this
address" because addresses are temporal. There is no central authority because consent
enforcement is distributed to every node. The network self-organizes around consent state
without a coordinator.

---

## What RPP Is Not

RPP is the address and routing layer only.

It does not replace your database. It routes to your existing storage.
It does not replace your authentication system. It encodes consent level in the address, but
the consent value itself comes from your existing identity and authorization infrastructure.
It does not replace your encryption. Rotational encryption is a routing-layer primitive; it
complements, not replaces, application-layer cryptography.
It does not require spintronic hardware. Software implementations enforce equivalent TTL and
consent semantics. Spintronic hardware amplifies the physical enforcement properties but is
not a prerequisite.

RPP adds one thing to your stack: an address layer where data type, consent level, temporal
scope, and routing mode are inseparable from the address integer. Everything else — storage,
auth, encryption above the routing layer — remains yours.

---

## Quick Reference

| Question | Short Answer |
|----------|-------------|
| What is an RPP address? | A 28-bit integer encoding shell, theta, phi, harmonic — simultaneously a route, a consent level, and a TTL |
| What is theta? | Data type sector — which of 8 named sectors this data belongs to |
| What is phi? | Consent level — who can route this; revoke consent by changing phi |
| What is shell? | Temporal scope — 25ns / 5min / 24hr / 30day retention tiers |
| What is harmonic? | Routing mode — priority, operating mode, frequency of access |
| What is the torus for? | It is the geometry that makes theta and phi independently cyclic with no privileged corners |
| What is the Ford Protocol? | A 5-phase substrate-crossing protocol for cognitive state packets that cannot be retransmitted |
| What is rotational encryption? | Encryption where the route IS the cipher; no separate key material |
| How many addresses? | 268,435,456 — representing concurrent routing states, not permanent object identities |
| What does RPP replace? | Nothing. It is the address layer. It routes to your existing stack. |

---

*See [SPEC.md](SPEC.md) for the full address format specification.*
*See [GEOMETRY.md](GEOMETRY.md) for the toroidal state vector and rotational encryption detail.*
*See [CONTINUITY.md](CONTINUITY.md) for the Ford Protocol five-phase algorithm.*
*See [ADDRESSING-LAYERS.md](ADDRESSING-LAYERS.md) for the v1.0/v2.0 two-layer architecture.*
