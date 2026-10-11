# Rotational Packet Protocol (RPP): Defensive Publication Supplement, October 2026

**Author:** Alexander Liam Lennon (ANYWAVE)
**Date:** 2026-10-10
**Supplements:** [DEFENSIVE_PUBLICATION.md](DEFENSIVE_PUBLICATION.md) (December 2024)
**Classification:** Defensive Publication / Prior Art Disclosure
**License:** CC BY 4.0 (text of this document; see [LICENSE-CC-BY-4.0](LICENSE-CC-BY-4.0) and [LICENSING.md](LICENSING.md))
**Repository:** https://github.com/anywave/rpp-spec

---

## 0. Purpose and how to read this document

This supplement publicly discloses the work on RPP done since the 2024 defensive publication, in enough detail
that a skilled reader can implement it. It is published so that these ideas stay open: anyone may implement them,
and nobody can lock them up with a patent.

Each section carries a **status label**. The labels mean exactly this:

| Label | Meaning |
|---|---|
| **Implemented** | Written as working code in the ANYWAVE "Mobi" application codebase (a private repository). Not yet a public release. |
| **Branch** | Written and tested on a development branch; not merged into a main line. |
| **Design** | Specified on paper. Not built. |
| **Measured** | A number taken on real hardware, with the conditions stated. |
| **Attested** | Results were reproduced by a second, independent run or reviewer, as described in the section. |

Nothing in this document is a claim of formal verification, and simulation or synthesis results are not
claims about fabricated or deployed hardware. Where a design review found open problems, they are listed.

The Mobi application's source code is not part of this disclosure. The protocols and data formats are described
here in prose, tables and pseudo-code so they can be implemented independently.

---

## 1. The Mobius 32-bit address profile

**Status:** address word **Implemented** (frozen); admission predicate, reserved-bit rule and per-hop frame
**Design** (proposed normative text, pending the author's ruling).

### 1.1 Bit layout

The Mobius profile fixes RPP addresses at one 32-bit word:

```
bit   31..30   29..21   20..12   11..8   7..0
      shell    theta    phi      MBZ     harmonic
      2 bits   9 bits   9 bits   4 bits  8 bits
```

| Field | Bits | Range | Role |
|---|---|---|---|
| shell | [31:30] | 0-3 | storage / priority tier |
| theta | [29:21] | 0-511 | sector key: the **only** field an admission decision reads |
| phi | [20:12] | 0-511 | metadata label (for example a model tier). Never a consent input |
| MBZ | [11:8] | 0 | must be zero; a receiver rejects the word if nonzero (proposed; an earlier profile text gave harmonic 12 bits, and if that reading is kept this rule is deleted, never widened) |
| harmonic | [7:0] | 0-255 | mode / sub-type label |

Encoding: `word = (shell << 30) | (theta << 21) | (phi << 12) | harmonic`.

Rules:

1. **Nominal keys.** theta, phi and harmonic are labels, not coordinates. The profile defines no order and no
   distance on them. A node that forwards on `|theta1 - theta2|` or on `(theta1 - theta2) mod 512` does not conform.
   Stores look up words by exact match. (A cyclic, distance-bearing theta would be a separate future profile.)
2. **Reject, never mask.** An encoder rejects an out-of-range field. It must not silently mask it (for example,
   theta 999 must be an error, not 487).
3. **Round trip.** `decode(encode(x)) == x` for every in-range `x`.
4. **Rotation touches 0 of the 32 bits.** Session rotation (Section 3) never changes any address bit.

### 1.2 Golden vectors

| (shell, theta, phi, harmonic) | 32-bit word |
|---|---|
| (1, 100, 170, 2) | `0x4C8AA002` |
| (1, 300, 170, 2) | `0x658AA002` |
| (3, 511, 511, 255) | `0xFFFFF0FF` |
| (0, 0, 0, 0) | `0x00000000` |
| `0x4C8AA102` (MBZ bit 8 set) | must be **rejected** at decode |

The three nonzero vectors were recomputed independently by a second reviewer.

### 1.3 Addresses label and route; they never authorize

The address is a **policy key**, not a policy and not a credential. Each node holds the policy itself, as its own
fold over a log of signed grants. Nothing a packet says about itself can grant it access. The one admission
predicate every conforming node computes is:

```
ADMIT(A, S) :=  S.armed
             AND S.age <= MAX_AGE
             AND A[11:8] == 0                       -- well-formedness; can only deny
             AND S.T[ A[29:21] ] == (S.cur_epoch, FULL)

reasons: PASS, NOT_ARMED, STALE, WF (malformed), CONSENT
```

- `S` is the gate's own state: `armed`, `age` (time since the last authenticated update), `cur_epoch`
  (per gate, 16 bits, never 0 and never 0xFFFF) and 512 sector entries. Only authenticated GRANT messages write `S`.
  No packet field writes `S`.
- **The packet carries no epoch.** Each gate keeps its own epoch, so a multi-gate route needs no shared policy server.
- Grant record: `GRANT v1 = {sector, state, epoch, grantor_key_id, signature}`. Per-sector grantor keys are
  provisioned when the gate is armed; a separate privileged key is needed to advance the epoch; an epoch advances
  by exactly +1.
- Consent states, least to most restrictive: `FULL < DIMINISHED < SUSPENDED < EMERGENCY_OVERRIDE`. Within one epoch
  the **most restrictive grant wins** (a join), so no single sector key can undo another key's suspension. Restoring
  a sector to FULL requires a new epoch and re-granting every live sector.
- **Admission is necessary, never sufficient.** A gate PASS is not trust. The host still verifies the sender's
  signature, freshness, replay status and the sender's rights to that sector before acting.
- Optional consent hints carried in the packet header may only move a decision toward DENY. They never grant.

Normative sentence (proposed): *A node admits packet A if and only if its own fold of the signed grant log holds
sector theta(A) FULL in the node's current epoch and the word is well-formed. No field of A other than theta enters
that decision, and A[11:8] can only deny. Each gate keeps its own epoch. Within an epoch the most restrictive grant
wins; restoring consent requires a new epoch.*

### 1.4 Per-hop contract and origin-signed frame (Design)

A mesh frame is `header[18] || payload[N] || trailer[112]`:

```
trailer = origin_pk[32] || ts_ms (u64, big-endian)[8] || seq (u64, big-endian)[8] || sig[64]
M       = "MOBIUS-RPP-B1\0" || header[0..17] || origin_pk || ts_ms || seq || SHA-256(payload)
          || (NODE_BOUND ? destination_pk : "")
sig     = Ed25519_Sign(origin_sk, M)
seq     = boot_counter (u32) || frame_counter (u32)
```

Each hop, in this order: (1) **parse** (CRC, MBZ bits, field ranges, trailer present; else drop as malformed);
(2) **gate** `ADMIT` on the 4-byte word only; (3) **route** by exact-match theta dispatch, with no distance metric;
(4) **handler**, the sole authority: verify the signature, check the origin key is admitted, `|now - ts_ms| <= delta`,
`(origin_pk, seq)` not seen before (high-water mark persisted across restarts), theta within the origin's rights,
and privileged sectors require NODE_BOUND. Relays **wrap, never rewrite**: `relay_header || inner frame (origin
trailer intact) || relay_trailer`, and a relay verifies the inner signature before forwarding.

Header byte 12 allocation (proposed): bit 7 = v2 address mode (existing), bit 6 = origin trailer present,
bit 5 = NODE_BOUND, bit 4 = must be zero.

---

## 2. The consent gate as a line-rate hardware deny-gate

**Status:** **Branch** (`pl/consent-gate` in this repository: `hardware/verilog/rpp_consent_gate.v`,
`rpp_consent_gate_tb.v`, `RPP_CONSENT_GATE.md`). Results are **simulation and synthesis/place-and-route only**.
Nothing has been run on a physical board.

### 2.1 Behaviour

For every packet the gate outputs PASS or DROP in hardware, at one decision per clock, from consent state the
gate holds. It never decides from anything the packet says about itself.

- Address layout: the Mobius 32-bit word (Section 1). Consent is held per theta sector (512 entries) in one block
  RAM. Only FULL passes.
- **Fail-closed.** Nothing passes before the first authenticated update, and nothing passes once updates stop for
  longer than `MAX_AGE` ticks (staleness).
- Unauthenticated updates are refused. Older-epoch (rollback) updates are refused.
- **Epoch 0 is refused.** ECP5 block RAM powers up as all zeros, which would read as `{epoch 0, FULL}`; refusing
  epoch 0 makes the power-up state deny everything.
- Each sector entry stores the epoch it was granted in, so advancing the epoch invalidates all older grants at once
  without clearing the RAM.
- Signature verification is outside the gate: `upd_auth_ok` is the verdict of a separate verifier block.

### 2.2 Results

Simulation (Icarus Verilog): 20 of 20 testbench checks pass, covering fail-closed reset, armed pass, epoch
handling, ungranted sector, unauthenticated update, rollback, EMERGENCY_OVERRIDE, DIMINISHED, independence from the
non-theta fields over 128 random packets, staleness and refresh, new-epoch invalidation, reset and epoch 0.
A mutation check inserted 6 deliberate bugs (no auth check, epoch 0 allowed, any state passes, staleness ignored,
rollback allowed, unauthenticated refresh); the testbench caught each one.

**Measured** (Yosys + nextpnr-ecp5, Lattice ECP5 LFE5U-12F, CABGA256 package):

| Resource | Used |
|---|---|
| LUTs | 124 of 24,288 |
| Flip-flops | 99 of 24,288 |
| Block RAM (DP16KD) | 1 of 56 |
| Max clock | 90.2 MHz |
| Throughput / latency | 1 decision per clock (about 90 million per second) / 2 clocks (about 22 ns) |

### 2.3 Known gaps in the v0 gate (from design review)

The built v0 differs from the Section 1.3 predicate in ways a design review identified; the fixes are **Design**,
not yet synthesized:

- v0 writes sector entries last-writer-wins; the predicate needs a read-modify-write join
  (`new = (upd_epoch > entry_epoch) ? {upd_epoch, upd_state} : {entry_epoch, max(entry_state, upd_state)}`).
- v0 has an `in_epoch` input compared against the packet; Section 1.3 removes the packet epoch, so that port and its
  reason code are to be deleted and a well-formedness (MBZ) reason added.
- The update-accept rule becomes:
  `upd_valid AND upd_auth_ok AND upd_epoch NOT IN {0, 0xFFFF} AND (NOT armed OR upd_epoch == cur_epoch OR
  (upd_epoch == cur_epoch + 1 AND epoch_auth))`, keeping the unarmed bootstrap path so a power-cycled gate can rejoin.
- The cost of these changes on the ECP5 has been estimated, not measured.

---

## 3. Encrypted, rotating sessions: tick, key rotation and downgrade pins

**Status:** **Branch** in the private Mobi codebase, with in-process two-peer tests passing. An independent
adversarial reviewer re-ran the full test suites on the branch before the last round of fixes and got the same
counts (**Attested** for that revision); its findings (role-aware pins, dial-target pins, the two-sided ratchet) were
then fixed and the suites re-run by the implementer. Not merged into the main line and not released. This section describes the protocol; no source code is reproduced.

### 3.1 What "rotation" means in RPP

Rotation is the step from key frame *k* to *k+1* of a session, made by a **fresh ephemeral Diffie-Hellman** exchange
on a jittered schedule, with the old key zeroized. It is **not** a key chain: the next key is never derived from or
sent under the current key. Rotation is bound to the packet by the frame's AEAD tag, with the rotation metadata in
the authenticated data. No second MAC is used. The 32-bit address does not change.

### 3.2 Handshake

The connection already carries a signed challenge/response with long-term Ed25519 identity keys. RPP v1 adds one
field to it:

1. The listener's challenge carries an X25519 ephemeral public key and the protocol label `"RPP1"`.
2. The dialer answers with its own X25519 ephemeral public key and signs `nonce || "RPP1" || ephemeral_keys` with its
   Ed25519 identity key.
3. The listener's proof signature covers `dial_nonce || "RPP1" || ephemeral_keys`. A forged listener proof aborts the
   dial.
4. Both sides compute the X25519 shared secret and run **HKDF-SHA256 over the handshake transcript** to derive, for
   **each direction separately**, a 256-bit traffic key and a 62-bit starting tick value.

Peers that do not offer the field continue as before (backward compatible), subject to the pins in 3.6.

### 3.3 Per-frame envelope

Every frame after the handshake is sealed with **ChaCha20-Poly1305** under the current key for its direction.
The associated data (AAD) contains:

| AAD field | Meaning |
|---|---|
| kind | frame kind (data, ratchet, ...) |
| kepoch | key epoch (which rotation step the key belongs to) |
| tick | the per-direction replay counter (3.4) |
| axis | the rotation axis identifier |
| direction | which side sent the frame |

The AEAD is checked before the tick. Flipping any byte of the ciphertext or of the AAD fields gives a decryption
failure. The inner bytes (18-byte RPP header, address, consent fields, payload) reach the application byte-identical:
the envelope can only drop a frame or close the session; it never changes or grants anything.

### 3.4 The tick (replay counter)

- Each direction has its own tick. The writer owns its tick and increments it by one per frame; the reader keeps the
  last accepted tick for that direction.
- The reader accepts only `last + 1`. A **replayed** frame (tick at or below the last accepted) is dropped and
  counted; when the replay drop counter reaches **8 the session freezes**.
- A **gap** (tick greater than `last + 1`) freezes the session until a new handshake re-seeds both sides; traffic
  then resumes.
- Ratchet frames carry ticks too. A dropped ratchet frame shows up as a key-epoch mismatch and freezes the session.
- On ordered transports (WebSocket, QUIC streams) tick checking is mandatory. On datagram transports the tick rule
  is not asserted until a reorder window has been measured.

### 3.5 Key rotation (two-sided ratchet)

- A side rotates its sending key on a jittered schedule (time and frame-count triggers, with the jitter redrawn every
  epoch) by generating a fresh X25519 ephemeral and sending a **ratchet frame** carrying the new public key and a
  ratchet id. The next key is `HKDF(X25519(new_ephemeral, peer_current_public))`.
- The ratchet body carries a **flags byte**. When a side receives a scheduled ratchet from its peer it answers with
  exactly one **reply rotation** (flagged as a reply, so a reply is never answered). A busy writer sends the reply
  with its next frame; an idle writer is woken and sends a standalone ratchet frame. Unknown flag bits freeze the
  session.
- A sender keeps key *k* until it has an acknowledged frame under *k+1*. A receiver that sees *k+1* early reports a
  gap and triggers a new handshake.
- Old private values are zeroized once the peer has moved past them. **State-compromise bound:** a snapshot of one
  side's memory recovers only the current and previous epoch keys per direction (one more if a ratchet is in flight).

### 3.6 Downgrade pins

- After a session that used the envelope and proved the peer's identity key, that key is **pinned** (public keys only
  are stored).
- The pin store is **role-aware**, with three lists: keys that dialed us, keys we dialed, and **dial targets**
  (host:port or overlay node id) we dialed.
- A pinned key or pinned dial target that later connects without the envelope is refused by name
  (`rpp-v1-downgrade-refused`), **whatever identity it announces, or none**. This blocks an active attacker who strips
  both the envelope offer and the identity field from the challenge.

### 3.7 Known limits

- **First contact** can still be downgraded by an attacker present at the very first meeting, before either side has
  pinned the other (trust on first use).
- Some legacy transport arms of the application remain unencrypted; the pins do not cover them.
- There is no user-facing "unpin" action yet; a peer that rolls back to a pre-envelope build stays refused until its
  pin is removed.
- Count-triggered rotation fires roughly every 50 frames; its cost on token streams has not been measured.
- There is no wall-clock freshness window inside the envelope; freshness at the mesh layer comes from `ts_ms`
  in the origin trailer (Section 1.4, Design).

---

## 4. Feeds: packet types combined into steerable message feeds

**Status:** **Design.** Nothing in this section is built.

### 4.1 Definition

RPP packets carry typed payloads (the header has a payload-type field). A **feed** combines packets into an ongoing
message stream:

```
feed = ( one session, one address key (a Mobius 32-bit word), an allowed ORDERED set of payload types )
```

A frame belongs to a feed only if it travels inside that session, carries that address, and its payload type is the
next type permitted by the feed's ordered set. Anything else is not part of the feed and is dropped by the receiver.

### 4.2 Movement and steering

A feed moves **hop by hop**, like an agent shell or a snake: each hop holds one **segment**, and segments together form
the body. The feed can be steered from any segment:

- the **head** segment sets the direction (the next hop);
- the **tail** segment sets backpressure and the payload format it will accept;
- a **middle** hop may reroute around itself (for example, around a failed or overloaded neighbour).

Steering messages are themselves typed packets within the feed, sealed by the session envelope of Section 3 on each
link and admitted by the consent gate of Section 1.3 at each hop.

### 4.3 Hard limits (part of the definition, not options)

1. A feed carries **data and steering only**. It never carries code that runs on a host.
2. A feed **never copies itself**. There is exactly one body; a segment moves, it is not duplicated.
3. **Every hop needs its own grant.** Entering a node requires that node's own consent grant for the feed's sector;
   a grant at one hop gives nothing at the next.
4. **Any segment holder, or the owner of any machine the feed touches, can stop it, and stop wins** over every
   steering instruction.

---

## 5. Numeric (tensor) transport over RPP for pooled VRAM

**Status:** **Design** and **Measured** (link characterization only). This is not a shipped product and no two-machine
inference over RPP has been run.

### 5.1 Concept

RPP frames carry numbers, not only language: activation vectors, KV-cache blocks and weight shards travel between
nodes so that several machines' GPU memory (VRAM) acts as one pool for one model.

- **Layer split, not tensor split.** Each node holds a contiguous range of the model's layers, and the KV cache for
  those layers stays on that node. Per generated token, one hidden-state vector crosses each node boundary
  (`hidden_dim x dtype`; for a 4096-wide model at f16, 8 KiB). Nothing else moves per token.
- A tensor/row split needs about two all-reduces per layer per token (tens of round trips per token), so it is ruled
  out across machines on ordinary networks.
- Weight shards (GB scale) are placed **once per session** and cached on each node, addressed by content hash; they
  are never streamed per request.
- A shard must be GPU-resident or it is refused (mixing CPU-resident tensors into a remote graph causes many small
  synchronous calls and collapses throughput).
- Pool context capacity is `sum over nodes of (VRAM - weights - working memory) / KV bytes per token`, bounded by the
  tightest shard.

### 5.2 Measured link (2026-10-08)

Two workstations: node A (Quadro RTX 3000, 6 GB, on Wi-Fi with a 400 Mbps link), node B (Quadro RTX 4000, 8 GB, on
1 GbE). Probe: a small echo server on node B, client on node A, TCP_NODELAY. Both machines were under build load, so
treat these as lower bounds.

| Path | 8 KiB round trip (one f16 activation hop, d = 4096) | 64 KiB round trip | bulk one-way, 1 MiB frames, acknowledged |
|---|---|---|---|
| Direct LAN | p50 1.88 ms, p90 3.28 ms, min 1.41 ms, max 41.7 ms (about 530 hops/s) | p50 9.9 ms, p90 16.9 ms | 12.8 MiB/s (102 Mbit/s) |
| WireGuard overlay | p50 2.08 ms, p90 4.22 ms, min 1.54 ms, max 15.4 ms (about 480 hops/s) | p50 7.2 ms, p90 9.7 ms | 20.9 MiB/s (167 Mbit/s) |

What the numbers imply (analysis, not measurement): a two-node layer split costs about 2 ms of network per generated
token, against about 19 ms per token measured for a 9B model running alone on node B (52 tokens/s), so roughly 10 %.
The Wi-Fi jitter tail (p90 3-4 ms, max 42 ms) is the main risk; the node on Wi-Fi should be wired for this use.
64 KiB-class frames per token are too slow on this link. A 2.5 GB shard takes about 2-3 minutes to place.

The next gate for the design is to reproduce these numbers with the production transport and show a two-node forward
pass whose per-token network cost is at most 2 ms p50 on Ethernet.

---

## 6. Prior art statement

This document is published to establish prior art. As of 2026-10-10, the author publicly discloses:

1. A fixed 32-bit nominal address word (Section 1.1) whose sector field is the only input to admission, with
   reject-not-mask encoding and the golden vectors of Section 1.2.
2. Admission as a node-local fold over a signed grant log keyed by the address sector, with per-gate epochs, no
   packet epoch, most-restrictive-wins within an epoch, deny-only header hints, and the rule that addresses label and
   route but never authorize (Section 1.3), together with the origin-signed, relay-wrapped frame of Section 1.4.
3. A line-rate, fail-closed hardware deny-gate for such addresses, including staleness fail-closed behaviour,
   epoch-0 refusal against zeroed power-up RAM, and per-entry epoch tags for bulk invalidation (Section 2).
4. Session rotation for RPP links by fresh ephemeral DH per epoch, per-direction HKDF keys and tick seeds,
   ChaCha20-Poly1305 with kind, key epoch, tick, axis and direction in the AAD, a strict per-direction tick with a
   replay drop counter that freezes the session, gap freeze with re-handshake, a two-sided ratchet with flagged reply
   rotations, and role-aware downgrade pins including dial-target pins (Section 3).
5. Feeds as defined in Section 4, including steering from head, tail and middle segments and the hard limits of
   Section 4.3.
6. Numeric tensor transport over RPP for pooled VRAM by layer split with node-local KV and once-per-session shard
   placement (Section 5).

What is **not** claimed as new: X25519, Ed25519, HKDF, ChaCha20-Poly1305, SHA-256, replay counters, trust-on-first-use
pinning, AEAD associated data, FPGA block RAM, pipeline (layer) parallelism for model inference, or the general idea of
access control lists. The disclosure is of the specific combinations and their application to RPP as described.

## 7. No patent claims

Consistent with the 2024 defensive publication, the author:

- claims no patent rights in anything described in this document;
- intends this publication to serve as prior art against any future patent claim on these methods;
- releases this document's text under CC BY 4.0;
- encourages independent implementation without licensing obligations beyond attribution.

Reference code in this repository is licensed under Apache-2.0 (see [LICENSING.md](LICENSING.md)).

## 8. Citation

> Lennon, A. L. (ANYWAVE). (2026). *Rotational Packet Protocol (RPP): Defensive Publication Supplement, October 2026.*
> https://github.com/anywave/rpp-spec

See also [CITATION.cff](CITATION.cff).

---

*This document constitutes a defensive publication establishing prior art for the described methods. No patent
claims are made or intended.*
