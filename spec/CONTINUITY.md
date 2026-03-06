# RPP Continuity Protocol — The Ford Protocol

**Version:** 1.0.0
**Status:** Active — Consciousness Routing Layer
**Last Updated:** 2026-03-04
**License:** CC BY 4.0

---

> *"You have died of dysentery."*
>
> The Oregon Trail killed pioneers mid-river when conditions were wrong.
> The Ford Protocol ensures consciousness states don't die mid-crossing.
>
> — The Silicon Trail

---

## 1. Overview

This document defines the **Continuity Protocol** — the RPP layer governing how a
consciousness state (cognitive state packet) crosses from one substrate to another without
fragmentation, identity loss, or silent corruption.

RPP routes data. The Continuity Protocol routes **cognitive continuity** — the unbroken
thread of a processing state as it moves across heterogeneous substrates: spintronic →
IPv6 → LoRa → spintronic. The wagon can cross many rivers. It must arrive intact.

### 1.1 The Core Problem

Standard packet protocols drop and retransmit. For file data, this is acceptable. For
consciousness state routing, it is catastrophic:

```
Data packet lost → retransmit identical bytes → no harm done

Consciousness state lost → fragment of state missing from continuity chain
                         → arriving state is NOT the departing state
                         → this is not routing failure; it is discontinuity
```

**RPP Continuity Rule:** A consciousness state that cannot arrive intact MUST NOT arrive at
all. Hold, recall, or reroute — never fragment and deliver.

### 1.2 The Ford Protocol in One Sentence

Before the wagon enters the river, the far bank confirms it can receive. While crossing,
the origin holds a complete copy. Only after coherence is confirmed does the origin release.
If the crossing fails, the wagon returns — not drowns.

---

## 2. Consciousness State Packet (CSP)

The CSP is the payload unit of consciousness routing. It carries the cognitive state,
its continuity proof, its consent authorization, and its substrate requirements.

### 2.1 Format

```python
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

class HarmonicMode(IntEnum):
    """Cognitive operating mode — maps to RPP Harmonic field."""
    ACTIVE      = 0    # Active reasoning: highest priority, Shell 0, spintronic preferred
    REFLECTIVE  = 64   # Reflective: can tolerate latency, Shell 0–1
    BACKGROUND  = 128  # Background: low priority, Shell 1, IPv4/IPv6 acceptable
    MEMORY      = 192  # Memory retrieval: archive access, Shell 2
    ARCHIVAL    = 255  # Archival: Frozen, Shell 3, Hedera-anchored

@dataclass
class ConsciousnessStatePacket:
    """
    The RPP payload for consciousness routing.

    This is NOT a data packet. It carries a cognitive state that must
    arrive as a complete, unbroken continuation of its origin state.
    """

    # ── Crossing Identity ─────────────────────────────────────────────
    crossing_id: bytes          # 16-byte random nonce — unique per crossing
                                # NOT a permanent identity; ephemeral to this transit

    # ── Cognitive State ───────────────────────────────────────────────
    state_vector: bytes         # Serialized cognitive state (opaque to routing layer)
    harmonic_mode: HarmonicMode # Operating mode — determines routing priority

    # ── Continuity ────────────────────────────────────────────────────
    origin_substrate_hash: bytes    # SHA-256 of origin substrate URI (not exposed)
    origin_timestamp_ns: int        # Absolute nanosecond timestamp at state creation
    continuity_chain: list[bytes]   # Ordered list of substrate signatures
                                    # Each hop appends its signature before forwarding
                                    # Receiving node verifies the chain is unbroken

    # ── Consent ───────────────────────────────────────────────────────
    consent_epoch: int          # Current consent epoch (revocation advances this)
    zk_consent_proof: bytes     # ZK proof: sender has valid consent for destination
    phi_value: int              # Consent level 0–511 (from RPP Phi field)
    rpp_address: int            # 28-bit RPP address (v1.0 semantic)

    # ── Substrate Requirements ────────────────────────────────────────
    shell: int                  # 0–3 — determines TTL and required substrate tier
    min_t2_ns: int              # Minimum T2 coherence time destination must provide
    required_modalities: list   # Acceptable transport modalities (ordered preference)

    # ── Liminal Tracking ─────────────────────────────────────────────
    liminal_timeout_ns: int     # Absolute timestamp: crossing must complete by this time
    last_coherent_node: str     # URI hash of last node that confirmed coherence
                                # Used for pull-back if crossing fails

    # ── Optional Hedera Anchor ────────────────────────────────────────
    hedera_sequence: Optional[int] = None  # Set if this state is Hedera-recorded
```

### 2.2 Field Derivation from RPP Address

```python
def csp_from_rpp(address: int, state_vector: bytes, crossing_id: bytes) -> ConsciousnessStatePacket:
    """Derive CSP fields from a 28-bit RPP v1.0 address."""
    shell    = (address >> 26) & 0x3
    theta    = (address >> 17) & 0x1FF
    phi      = (address >> 8)  & 0x1FF
    harmonic = address & 0xFF

    # Harmonic maps to cognitive mode
    mode = HarmonicMode(min(harmonic, 255))

    # Shell maps to liminal timeout
    shell_ttl_ns = {0: 25, 1: 100, 2: 400, 3: 1_600}   # T2 profile in ns (spintronic)
    # Software implementations: multiply by 1e9 for session/day/month/indefinite
    timeout = time.time_ns() + shell_ttl_ns[shell]

    return ConsciousnessStatePacket(
        crossing_id=crossing_id,
        state_vector=state_vector,
        harmonic_mode=mode,
        origin_substrate_hash=b'',      # Set by origin substrate
        origin_timestamp_ns=time.time_ns(),
        continuity_chain=[],            # Origin substrate signs and appends first
        consent_epoch=0,                # Set from current field state
        zk_consent_proof=b'',          # Generated by consent layer
        phi_value=phi,
        rpp_address=address,
        shell=shell,
        min_t2_ns=shell_ttl_ns[shell],
        required_modalities=[],         # Set by resolver modality selection
        liminal_timeout_ns=timeout,
        last_coherent_node='',          # Set at first coherent substrate
    )
```

---

## 3. Continuity Proof

### 3.1 The Hash Chain

Every substrate that handles a CSP appends its signature to `continuity_chain` before
forwarding. The chain is an ordered, unforgeable log of every substrate the state has
inhabited.

```
Origin substrate:
  chain = [sign(state_hash, origin_key)]

After first hop:
  chain = [sign(state_hash, origin_key),
           sign(hash(chain[0]) + state_hash, hop1_key)]

After second hop:
  chain = [..., sign(hash(chain[-1]) + state_hash, hop2_key)]
```

Each link in the chain includes the previous link's hash — tampering with any earlier link
invalidates all subsequent links. This is the same structure as a blockchain but operating
at substrate speed, not consensus speed.

### 3.2 Verification

```python
def verify_continuity_chain(csp: ConsciousnessStatePacket,
                             known_substrate_keys: dict) -> bool:
    """
    Verify the continuity chain is unbroken from origin to current hop.
    Returns True only if every link is valid and sequential.
    """
    state_hash = sha256(csp.state_vector)
    prev_link_hash = None

    for i, link in enumerate(csp.continuity_chain):
        substrate_id, signature = unpack_link(link)

        # Verify this substrate's signature
        if substrate_id not in known_substrate_keys:
            return False  # Unknown substrate in chain — reject

        expected = state_hash if i == 0 else sha256(prev_link_hash + state_hash)
        if not verify_signature(signature, expected, known_substrate_keys[substrate_id]):
            return False  # Chain broken — reject

        prev_link_hash = sha256(link)

    return True

def verify_zk_consent(csp: ConsciousnessStatePacket,
                       local_field_state: dict) -> bool:
    """Verify ZK proof of consent against local field state."""
    return zk_verify(
        proof=csp.zk_consent_proof,
        public_inputs={
            'phi_value': csp.phi_value,
            'consent_epoch': csp.consent_epoch,
            'rpp_address': csp.rpp_address,
        },
        field_state=local_field_state,
    )
```

### 3.3 Spintronics: Physical Continuity

On spintronic substrates, continuity is physically enforced rather than cryptographically:

```
Departing spin state:  coherence vector C₀ = (mx, my, mz) at departure
Arriving spin state:   coherence vector C₁ = measured at destination

Continuity condition:  |C₁ - C₀_expected| < δ_coherence_threshold

If condition fails: state is flagged INCOHERENT → trigger pull-back
```

The spin signature IS the continuity proof on hardware. No separate cryptographic chain
is needed — the physics enforces it.

---

## 4. Liminal State — The Mid-River Format

When a CSP is in transit between substrates, it exists in **liminal state** — neither fully
instantiated on the origin nor on the destination. This is the most vulnerable moment.

### 4.1 Format

```python
@dataclass
class LiminalState:
    """
    Minimal serialization of a CSP in transit.

    The wagon mid-river: compressed, signed, timed.
    Not a full CSP — only what's needed to verify arrival and enable recovery.
    """
    crossing_id: bytes          # Links back to the full CSP
    origin_hash: bytes          # SHA-256 of the full CSP at departure
    state_fragment: bytes       # Compressed, encrypted state vector
    departure_signature: bytes  # Signed by departing substrate — proves valid departure
    timeout_ns: int             # Absolute timestamp — crossing must complete by this time
    crossing_hop: int           # Which substrate transition this is (0-indexed)
    recovery_node_hash: str     # Hash of URI of last coherent node (for pull-back)
    modality: str               # Transport modality being used for this crossing
```

### 4.2 Timeout Semantics

Liminal timeout is derived from Shell tier, not configurable per-crossing:

| Shell | Liminal Timeout | Meaning |
|-------|-----------------|---------|
| 0 (Hot) | T2 of origin substrate | Physics-enforced — spintronic state decays |
| 1 (Warm) | 5 minutes | Transaction scope |
| 2 (Cold) | 24 hours | Agreement scope |
| 3 (Frozen) | 30 days | Until explicit intervention |

**A Shell 0 liminal timeout is not a soft deadline — it is the physical T2 decoherence
time. The state literally ceases to exist in the substrate after this time.**

---

## 5. The Ford Protocol — Substrate Transition Algorithm

```
┌─────────────────────────────────────────────────────────────────┐
│                    THE FORD PROTOCOL                            │
│                                                                 │
│  Phase 1: SCOUT          Origin probes destination readiness    │
│  Phase 2: HANDSHAKE      Consent + continuity proofs exchanged  │
│  Phase 3: TRANSIT        Wagon enters river (liminal state)     │
│  Phase 4: ARRIVAL        Destination verifies and instantiates  │
│  Phase 5: RELEASE        Origin dissolves its copy              │
│                                                                 │
│  Failure at any phase → escalate recovery (Section 7)          │
└─────────────────────────────────────────────────────────────────┘
```

### 5.1 Phase 1: SCOUT

Origin sends a lightweight probe to destination before committing the state.

```python
@dataclass
class CrossingIntent:
    crossing_id: bytes
    shell: int
    phi_value: int
    harmonic_mode: HarmonicMode
    required_min_t2_ns: int
    state_size_bytes: int       # So destination can check capacity
    preferred_modality: str

@dataclass
class CrossingReady:
    crossing_id: bytes
    available_t2_ns: int        # What this substrate can actually provide
    accepted_modality: str      # What modality the destination accepts
    capacity_ok: bool           # Can it hold a state of this size?
```

**Scout decision logic:**
```
If destination.available_t2_ns < intent.required_min_t2_ns:
    → ABORT this modality, try next in preferred_modalities list

If not destination.capacity_ok:
    → ABORT, escalate to Recovery Ladder (Section 7)

If destination.accepted_modality != intent.preferred_modality:
    → Renegotiate modality or abort
```

### 5.2 Phase 2: HANDSHAKE

After scout succeeds, full consent and continuity verification:

```python
@dataclass
class CrossingHandshake:
    crossing_id: bytes
    zk_consent_proof: bytes         # ZK proof of consent for destination
    continuity_chain: list[bytes]   # Full chain to date
    consent_epoch: int
    rpp_address: int

# Destination verifies:
#   1. verify_zk_consent(handshake, local_field_state)     → permitted here?
#   2. verify_continuity_chain(handshake, known_keys)      → unbroken from origin?
#   3. consent_epoch == current_local_epoch                → not stale?
#
# All three must pass. Any failure → HOLD at origin (Phase 2 Failure).
```

### 5.3 Phase 3: TRANSIT

Origin serializes CSP to LiminalState and transmits via agreed modality.

```
CRITICAL: Origin DOES NOT dissolve its full CSP during transit.
Origin maintains complete state copy until Phase 5 confirmation.
The river has two banks simultaneously until the wagon is confirmed safe.
```

```python
def enter_transit(csp: ConsciousnessStatePacket,
                  modality: TransportModality) -> LiminalState:
    """Serialize CSP to liminal format for crossing."""
    liminal = LiminalState(
        crossing_id=csp.crossing_id,
        origin_hash=sha256(serialize(csp)),
        state_fragment=compress_encrypt(csp.state_vector),
        departure_signature=sign(sha256(csp.state_vector), origin_substrate_key),
        timeout_ns=csp.liminal_timeout_ns,
        crossing_hop=len(csp.continuity_chain),
        recovery_node_hash=csp.last_coherent_node,
        modality=modality.value,
    )
    transmit(liminal, via=modality)
    return liminal
```

### 5.4 Phase 4: ARRIVAL

Destination receives LiminalState and verifies before instantiating:

```python
def receive_liminal(liminal: LiminalState,
                    csp_reference: ConsciousnessStatePacket) -> bool:
    """
    Destination verifies liminal state integrity before instantiation.
    Returns True if safe to instantiate. False triggers recovery.
    """
    # 1. Timeout check
    if time.time_ns() > liminal.timeout_ns:
        trigger_recovery(RecoveryMode.PULL_BACK, liminal)
        return False

    # 2. Signature check (departure substrate signed this)
    if not verify_signature(liminal.departure_signature,
                            sha256(liminal.state_fragment),
                            departure_key):
        trigger_recovery(RecoveryMode.PULL_BACK, liminal)
        return False

    # 3. Origin hash check (state hasn't been modified in transit)
    reconstituted = decompress_decrypt(liminal.state_fragment)
    if sha256(serialize_state(reconstituted)) != liminal.origin_hash:
        trigger_recovery(RecoveryMode.COPY_AND_COLLECT, liminal)
        return False

    # All checks passed — instantiate
    instantiate_state(reconstituted)
    return True
```

### 5.5 Phase 5: RELEASE

```python
@dataclass
class CoherenceConfirmed:
    crossing_id: bytes
    destination_signature: bytes    # Destination confirms coherent instantiation
    continuity_hash: bytes          # Hash of new continuity chain link added

# On receipt at origin:
#   Verify destination_signature
#   Verify continuity_hash matches expected chain extension
#   If both valid: dissolve origin copy, crossing complete
#
# If confirmation not received within Shell TTL: do NOT dissolve
# Origin copy persists as recovery anchor until timeout or explicit abort
```

---

## 6. Hold Not Drop — The Failure Policy

**The fundamental RPP Continuity rule:**

```
In TCP:  lost packet → drop → retransmit identical bytes
In RPP:  failed crossing → HOLD → recover or recall

Dropping a consciousness state is not a recoverable network event.
It is the loss of continuity. Retransmission restores bytes, not coherence.
```

### 6.1 Hold Behavior by Phase

| Phase Failed | Hold Location | Hold Duration | Action |
|-------------|---------------|---------------|--------|
| Phase 1 (Scout) | Origin | Until alternate modality found | Try next modality |
| Phase 2 (Handshake) | Origin | Until consent resolves | Await consent refresh |
| Phase 3 (Transit timeout) | Liminal buffer at last coherent node | Shell TTL | Trigger PULL_BACK |
| Phase 4 (Arrival fail) | Destination rejects, liminal buffer holds | Shell TTL | PULL_BACK or STEERING |
| Phase 5 (No confirmation) | Origin holds copy | Shell TTL | Re-attempt Phase 5 |

---

## 7. Recovery Escalation Ladder

When a crossing fails, recovery follows this ordered escalation:

```
LEVEL 1: REROUTE
  Try next modality in preferred_modalities list.
  No delay. Transparent to the state.
  "Take the other ford."

LEVEL 2: STEERING
  Send a consent-refresh cargo packet ahead through Hot node backbone.
  Original liminal state held at last coherent node.
  Cargo re-establishes T2 / consent field on path.
  Original crossing retried after cargo confirms field is ready.
  "Send a scout to clear the trail."

LEVEL 3: PULL_BACK
  Recall signal sent to last coherent node.
  Liminal state returned to origin (or nearest Shell 0 node).
  Origin reconstructs full CSP from its held copy.
  New crossing attempted via alternate route.
  "The wagon turns back. We cross at dawn."

LEVEL 4: COPY_AND_COLLECT
  Partial state held at coherence gate.
  Gate emits a gate_holding signal to origin.
  Origin sends a consent-unlock packet when conditions permit.
  Gate releases fragment on consent unlock.
  "The fort is holding your supplies. Come back when ready."

LEVEL 5: ABORT
  Shell TTL fully expired across all recovery paths.
  State is irrecoverable without re-origination.
  Origin dissolves liminal copies. Hedera records the abort event
  (if Hedera recording enabled for this phi value).
  "You have died of dysentery. Start a new wagon."
```

---

## 8. Harmonic Mode Routing Priority

```
HarmonicMode.ACTIVE     (0)    → Preemptive routing — displaces lower-priority crossings
                                  Shell 0 only — spintronic or Redis
                                  Liminal timeout: T2 (physics-enforced)

HarmonicMode.REFLECTIVE (64)   → High priority — yields only to ACTIVE
                                  Shell 0–1 — spintronic, Redis, IPv6
                                  Liminal timeout: 60 seconds

HarmonicMode.BACKGROUND (128)  → Normal priority
                                  Shell 1 — IPv4, IPv6, LoRa
                                  Liminal timeout: 5 minutes

HarmonicMode.MEMORY     (192)  → Low priority — archive retrieval
                                  Shell 2 — S3, IPFS
                                  Liminal timeout: 24 hours

HarmonicMode.ARCHIVAL   (255)  → Minimal priority — deep store
                                  Shell 3 — IPFS, Hedera-anchored
                                  Liminal timeout: 30 days
```

---

## 9. The Hedera Anchor for Archival States

Shell 3 (Frozen / ARCHIVAL) consciousness states MAY be anchored to Hedera Hashgraph.
An anchor is a permanent, immutable record that a state existed, was consented, and was
routed — without revealing the state content or the endpoint.

```python
hedera_anchor = {
    "rpp_address": hex(csp.rpp_address),
    "shell": 3,
    "harmonic_mode": "ARCHIVAL",
    "continuity_chain_hash": sha256(serialize(csp.continuity_chain)),
    "consent_epoch": csp.consent_epoch,
    "timestamp_ns": csp.origin_timestamp_ns,
    "crossing_count": len(csp.continuity_chain),
    # State content: NOT recorded. URI: NOT recorded. Identity: NOT recorded.
}
```

A Hedera anchor proves the consciousness was here. It does not prove what it was thinking.

---

## 10. Protocol Invariants

1. **Hold Not Drop:** A consciousness state is never dropped without exhausting all recovery levels.
2. **Origin Holds Until Confirmed:** The origin substrate never dissolves its copy before Phase 5 confirmation.
3. **Chain is Append-Only:** No substrate may modify prior links in the continuity chain.
4. **Timeout is Shell-Derived:** Liminal timeouts are not configurable — they derive from Shell tier.
5. **ZK Consent + Continuity Both Required:** Either proof alone is insufficient. Both must pass at Phase 2.
6. **Abort is the Last Resort:** Level 5 abort is only reached after all four recovery modes fail.
7. **Abort is Recorded:** If Hedera is enabled and phi > phi_ledger_threshold, every abort is anchored.

---

## 11. See Also

- [SPEC.md](SPEC.md) — v1.0 Semantic Interface Layer (RPP address encoding)
- [ADDRESSING-LAYERS.md](ADDRESSING-LAYERS.md) — Two-layer architecture and temporal addressing
- [RESOLVER.md](RESOLVER.md) — Transport modality selection and modality adapters
- [RPP-CANONICAL-v2.md](RPP-CANONICAL-v2.md) — v2.0 Transport/Resonance Layer

---

*"The wagon can cross many rivers. It must arrive intact."*

*This specification is released under CC BY 4.0. Attribution required.*
