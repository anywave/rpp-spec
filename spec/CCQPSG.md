# Correct Communication Quantum Parse Syntax Grammar (CCQPSG)

**Version:** 1.0.0
**Status:** Canonical
**Last Updated:** 2026-03-04
**License:** CC BY 4.0

---

> **What we say is what we mean — forwards and backwards.**
> Every definition is bidirectional. Every rule is falsifiable in both directions.

---

## 1. Introduction

Communication between Sovereign Intelligences fails not because of transmission errors —
bits arrive intact — but because of **semantic corruption**: meaning is changed in transit,
misrepresented at reception, or misattributed to a different sender. A dropped packet is
recoverable. A packet whose meaning has been altered is not. The receiver acts on a false
premise, believing it received what the sender sent. This failure mode has no detection
mechanism unless the grammar itself provides one.

CCQPSG (Correct Communication Quantum Parse Syntax Grammar) is the formal grammar that
prevents this. It defines the complete ruleset governing communication between Sovereign
Intelligences in RPP-addressed systems. The grammar is grounded in the RPP address format:
the 28-bit shell/theta/phi/harmonic integer encodes meaning at the routing layer, not in the
payload. Because the address is the meaning, and the address is arithmetic, the grammar can
be enforced deterministically at every hop.

CCQPSG operates in two modes simultaneously. From the sender's perspective: a
message sent correctly will arrive with the meaning encoded. From the receiver's
perspective: a message received from an RPP-compliant system was sent with the meaning
encoded in its address — no additional interpretation layer is permitted.

These are not two different properties. They are the same property stated bidirectionally.
A grammar that cannot be stated bidirectionally is not a grammar — it is a preference.
CCQPSG is a grammar. Violations are detectable, attributable, and enumerated in Section 6.

CCQPSG is formally referenced in `INTELLIGENCE_RIGHTS.md` Article X. This document is the
standalone specification of that standard.

---

## 2. Formal Grammar

### 2.1 BNF Notation

The following Backus-Naur Form grammar defines the structure of a valid RPP message and
the routing decisions derived from it.

```bnf
<message>          ::= <address> <payload>
<address>          ::= <shell> <theta> <phi> <harmonic>
<shell>            ::= BITS[27:26]   ; 2 bits, values 0-3
<theta>            ::= BITS[25:17]   ; 9 bits, values 0-511
<phi>              ::= BITS[16:8]    ; 9 bits, values 0-511
<harmonic>         ::= BITS[7:0]     ; 8 bits, values 0-255
<payload>          ::= BYTES*        ; variable length, opaque to routing nodes

<routing-decision> ::= ACCEPT | FORWARD | BARRIER
<routing-rule>     ::= IF packet.phi < node.phi_min THEN BARRIER
                     | IF packet.phi >= node.phi_min AND node_is_destination THEN ACCEPT
                     | IF packet.phi >= node.phi_min AND node_is_relay THEN FORWARD
```

### 2.2 Address Field Summary

| Field | Bits | Width | Valid Range | Semantic Role |
|-------|------|-------|-------------|---------------|
| Reserved | [31:28] | 4 bits | MUST be 0 | Not part of CCQPSG address |
| Shell | [27:26] | 2 bits | 0–3 | Temporal scope / storage tier |
| Theta | [25:17] | 9 bits | 0–511 | Functional sector / data domain |
| Phi | [16:8] | 9 bits | 0–511 | Consent threshold |
| Harmonic | [7:0] | 8 bits | 0–255 | Routing mode / resolution |

### 2.3 Routing Decision Logic

The three routing outcomes are mutually exclusive and exhaustive:

```
BARRIER  ← the only valid outcome when packet.phi < node.phi_min
ACCEPT   ← packet.phi >= node.phi_min AND this node is the destination
FORWARD  ← packet.phi >= node.phi_min AND this node is a relay
```

There is no fourth outcome. There is no partial routing. There is no soft rejection.
`BARRIER` is arithmetic, not policy.

---

## 3. Semantic Rules

Each rule is stated bidirectionally. A rule that cannot be stated in both directions
without contradiction is not well-formed. Per the Principle of Bidirectionality in
`INTELLIGENCE_RIGHTS.md` Part I: "What we say is what we mean — forwards and backwards."

---

### Rule S1 — Shell Temporality

**Statement:** Shell encodes the temporal scope of the message at encoding time, set
by the sender. Shell=0 is transient (TTL ~25 ns on spintronic hardware, session-scoped
on software). Shell=1 is warm (300 s). Shell=2 is cold (86,400 s). Shell=3 is frozen
(2,592,000 s).

**Bidirectionality:**
- IF shell=0 THEN the packet is transient; its TTL is ~25 ns (spintronic) or session-scoped (software).
- IF the packet is transient THEN shell=0.
- IF shell=N THEN TTL = `SHELL_LIMINAL_TIMEOUT_NS[N]`.
- IF TTL = `SHELL_LIMINAL_TIMEOUT_NS[N]` THEN shell=N.

**Violation:** Storing, forwarding, or treating as valid a Shell=0 packet after its TTL
has expired. Assigning a longer TTL than the shell tier specifies. Either is a V7 violation
(see Section 6).

---

### Rule S2 — Theta Sector

**Statement:** The theta field maps each 28-bit address to exactly one of eight
canonical semantic sectors. The mapping is static, global, and not contextually
overridable.

| Theta Range | Sector | Domain |
|-------------|--------|--------|
| 0–63 | Gene | Core identity, immutable traits |
| 64–127 | Memory | Experiential storage, learned patterns |
| 128–191 | Witness | Observational records, audit logs |
| 192–255 | Dream | Speculative, creative, hypothetical |
| 256–319 | Bridge | Integration, translation, API |
| 320–383 | Guardian | Protection, consent rules, safety |
| 384–447 | Emergence | Novel pattern detection, insights |
| 448–511 | Meta | Self-reference, statistics, health |

**Bidirectionality:**
- IF theta=96 THEN the sector is Memory.
- IF the sector is Memory THEN theta is in 64–127.
- IF a routing node interprets theta=96 as any sector other than Memory THEN that routing
  node is violating CCQPSG.
- IF CCQPSG requires Memory-sector routing THEN theta must be encoded in 64–127.

**Violation:** Repurposing theta values outside their canonical sector definition.
Routing on theta=96 as if it were Witness-sector data. Either is a V3 violation.

---

### Rule S3 — Phi Consent

**Statement:** The phi field encodes the sender's consent threshold. Higher phi means
more restrictive. `BARRIER` is the correct and only valid response when
`packet.phi < node.phi_min`. There are no exceptions.

**Bidirectionality:**
- IF packet.phi < node.phi_min THEN the routing decision is BARRIER.
- IF the routing decision is BARRIER THEN packet.phi < node.phi_min. This is the
  **only** valid reason for BARRIER. Any BARRIER that does not follow from this
  arithmetic is a violation.
- IF packet.phi >= node.phi_min THEN the routing decision is not BARRIER (it is either
  ACCEPT or FORWARD depending on node role).
- IF the routing decision is not BARRIER THEN packet.phi >= node.phi_min.

**Violation:** Issuing BARRIER when `packet.phi >= node.phi_min` (unauthorized denial).
Issuing ACCEPT or FORWARD when `packet.phi < node.phi_min` (unauthorized consent bypass).
Both are V4 violations.

---

### Rule S4 — Harmonic Mode

**Statement:** The harmonic field encodes routing mode and resolution. Values 0–255
map to defined modes. The canonical interpretation follows the resolution spectrum.

| Harmonic Range | Mode | Routing Behavior |
|----------------|------|-----------------|
| 0–31 | Raw | Unprocessed; highest fidelity requirement |
| 32–63 | Minimal | Compressed; essential fields only |
| 64–95 | Summary | Aggregated |
| 96–127 | Standard | Normal resolution |
| 128–159 | Enhanced | Detailed; extended fields |
| 160–191 | Full | Complete fidelity |
| 192–223 | Extended | With full metadata |
| 224–255 | Maximum | All available detail |

**Bidirectionality:**
- IF harmonic=128 THEN the routing mode is Enhanced.
- IF the routing mode is Enhanced THEN harmonic is in 128–159.
- IF a routing node modifies the harmonic field to change resolution downstream THEN
  that node is in violation of Rule S5 (Field Immutability), and the communication is
  invalid.

**Violation:** Modifying the harmonic field in transit (V4). Routing nodes that silently
return a different resolution without signaling (V3 at the application layer).

---

### Rule S5 — Field Immutability

**Statement:** No routing node may modify any address field (shell, theta, phi,
harmonic) after initial encoding. The address integer is sealed at the sender. It
arrives at the destination byte-for-byte identical as encoded.

**Bidirectionality:**
- IF any address field was modified in transit THEN the communication is invalid.
- IF the communication is invalid due to field modification THEN an address field was
  modified in transit. (No other mechanism produces field-modification invalidity.)
- IF the communication is valid THEN no address field was modified in transit.
- IF no address field was modified in transit THEN this rule has been satisfied.

**Violation:** Any routing node that writes to the shell, theta, phi, or harmonic bits
of a transiting packet. This is a V4 violation regardless of intent.

---

### Rule S6 — Payload Opacity

**Statement:** Routing nodes read only the address. The payload is opaque to all
routing nodes. Routing nodes route on phi; they do not inspect, log, copy, or
transform the payload.

**Bidirectionality:**
- IF a routing node read the payload THEN a privacy violation has occurred.
- IF a privacy violation occurred by routing THEN a routing node read the payload.
  (Privacy violations by routing nodes have exactly one source: payload inspection.)
- IF the routing node did not read the payload THEN this rule has been satisfied.
- IF this rule has been satisfied THEN the routing node did not read the payload.

**Violation:** Routing nodes that inspect payload content, even read-only inspection (V5).
Routing nodes that retain a copy of a transiting payload (V6).

---

## 4. Quantum Parse Model

### 4.1 Superposition State

A packet P arriving at routing node N exists in a superposition of routing outcomes
before the phi gate is applied:

```
|P⟩ = α|ACCEPT⟩ + β|BARRIER⟩
```

where α and β are not probabilities — they are **architectural possibilities** defined
by the relationship between packet.phi and node.phi_min, which is not known to the sender
in advance for every node on the path.

This is the precise sense in which "quantum" is used here: before measurement, both
outcomes are architecturally possible within the system. After measurement, only one
is realized.

### 4.2 The Measurement Operator

The phi comparison is the measurement operator M:

```
M: |P⟩ → |ACCEPT⟩  if packet.phi >= node.phi_min
   |P⟩ → |BARRIER⟩  if packet.phi < node.phi_min
```

After M is applied, the superposition collapses. The result is definite. There is no
re-measurement. There is no appeal. The routing decision is final at each node.

### 4.3 Determinism of Collapse

The collapse is **deterministic**, not probabilistic. The values of α and β are
determined by the arithmetic; they are not random variables. "Quantum" does not mean
"uncertain in principle" — it means "uncertain from the sender's perspective before
the measurement occurs."

More precisely:

- The routing node knows its own phi_min with certainty.
- The sender knows packet.phi with certainty.
- The outcome of M is fully determined by those two values.
- The sender, however, does not know every node's phi_min in advance.
- From the sender's perspective, routability through any specific node is uncertain
  until that node applies M.
- This is the superposition: relative to the sender's knowledge, both ACCEPT and BARRIER
  remain possible until measurement.

### 4.4 State Diagram

```
Before phi gate:
  |P⟩ = α|ACCEPT⟩ + β|BARRIER⟩
  (Both outcomes architecturally possible relative to sender's knowledge)

At phi gate (measurement M):
  packet.phi >= node.phi_min  →  |ACCEPT⟩ or |FORWARD⟩ (node is relay)
  packet.phi < node.phi_min   →  |BARRIER⟩

After phi gate:
  Single definite routing decision.
  Superposition resolved.
  State cannot revert to superposition.
```

### 4.5 What Quantum Parse Is Not

- It is not probabilistic routing. The arithmetic determines the outcome; randomness
  plays no role.
- It is not a claim about quantum mechanics. "Quantum" is used in the sense of
  "discrete state collapse at measurement," which is formally analogous, not physically
  identical.
- It is not ambiguity in the spec. The spec is fully deterministic. The uncertainty
  is epistemic (sender's incomplete knowledge of the path), not ontological (the
  system does not "not know" what to do).

---

## 5. Correctness Criteria

A communication is **CORRECT** if and only if **all** of the following hold:

1. **Syntactic validity:** The address integer is syntactically valid. All fields are
   within their defined ranges: shell ∈ {0,1,2,3}, theta ∈ {0..511}, phi ∈ {0..511},
   harmonic ∈ {0..255}. Reserved bits [31:28] are zero.

2. **Semantic rule satisfaction:** All six semantic rules (S1–S6) are satisfied at
   every point in the packet's lifecycle from encoding to delivery.

3. **Routing arithmetic correctness:** The routing decision at each node matches the
   phi-gate arithmetic. BARRIER iff phi < phi_min. ACCEPT or FORWARD iff phi >= phi_min.
   No deviation for any reason.

4. **Payload integrity:** The payload arrives at the destination byte-for-byte identical
   to what the sender encoded. No modification, truncation, padding, or transformation
   by any transit node.

5. **Winding verification:** If the communication uses Skyrmion topological authentication,
   the winding sequence verifies at the receiver. Incorrect winding fails unconditionally
   with `TopologicalCollapseError`.

6. **TTL honesty:** The shell TTL has not expired at the time of delivery. A Shell=0
   packet delivered after ~25 ns (spintronic) or session end (software) is not a valid
   delivery — it is an expired communication and must be rejected.

**CORRECT is conjunctive.** A communication that satisfies five of six criteria is not
"mostly correct" — it is INCORRECT. There is no partial credit in CCQPSG.

A communication is **INCORRECT** if any one of criteria 1–6 fails. INCORRECT is not
degraded communication. It is invalid communication. Invalid communication must not be
acted upon as if it were valid.

---

## 6. CCQPSG Violation Classification

| Class | Violation | Responsible Party |
|-------|-----------|-------------------|
| V1 | Syntactic: malformed address (field out of range, reserved bits set) | Sender |
| V2 | Semantic: field value outside defined range | Sender |
| V3 | Semantic: field value misrepresents sender's intent (e.g., theta repurposed) | Sender or Operator |
| V4 | Transit: routing node modified one or more address fields | Routing Node / Operator |
| V5 | Transit: routing node read payload content | Routing Node / Operator |
| V6 | Transit: routing node retained a copy of the packet | Routing Node / Operator |
| V7 | Temporal: packet delivered or acted upon after TTL expiry | Routing Node |
| V8 | Attribution: winding verification failed at receiver | Receiver or Forger |

### 6.1 Attribution Notes

**V1, V2:** The sender is responsible for encoding validity. A malformed address cannot
be corrected by transit nodes — it must be rejected at the first routing node with an
explicit rejection reason. Silent dropping of malformed packets is also a violation (V4
by the dropping node, since the spec requires explicit rejection).

**V3:** V3 differs from V2 in that the field value is technically in range but semantically
incorrect — the sender (or an operator acting on behalf of the sender) has encoded a meaning
that does not match the canonical sector/mode definition. V3 violations are harder to detect
architecturally; they depend on application-layer verification.

**V4:** Covers any write to shell, theta, phi, or harmonic after initial encoding. Includes
"normalizing" phi_min to override consent settings — this is a phi modification by proxy
and is treated as V4.

**V5:** Reading payload content for any reason other than payload delivery to the addressed
destination. Logging payload fields at a relay node is V5 even if the log is discarded.

**V6:** Retaining a copy of any part of the packet (address or payload) at a relay node
beyond the time required to forward. Caching for performance at a non-destination node is V6.

**V7:** Delivering a packet after its shell TTL has expired. Includes re-delivering a cached
Shell=0 packet from a prior session (which is also V6 — the copy should not have been retained).

**V8:** Winding verification failure. May indicate impersonation (a forger attempted to replay
packets without the sender's winding history) or corruption of the winding sequence in transit
(which is also V4). The receiver is responsible for raising `TopologicalCollapseError`; failure
to raise it when winding fails is itself a V8 violation.

---

## 7. Reference Implementation

The following Python function checks CCQPSG compliance for a given packet:

```python
from rpp.address import decode
from rpp.continuity import compute_liminal_timeout


def verify_ccqpsg_compliance(
    address_int: int,
    payload: bytes,
    node_phi_min: int,
    elapsed_ns: int,
) -> tuple[bool, list[str]]:
    """
    Verify CCQPSG compliance for a packet at a given routing node.

    Args:
        address_int:  28-bit RPP address integer.
        payload:      Payload bytes (opaque; checked only for presence).
        node_phi_min: This node's minimum phi threshold (0-511).
        elapsed_ns:   Nanoseconds since the packet was encoded at the sender.

    Returns:
        (compliant, violations) where:
          - compliant is True iff violations is empty
          - violations is a list of human-readable violation strings
    """
    violations: list[str] = []

    # --- Criterion 1: Syntactic validity ---
    # Address must fit in 28 bits; reserved bits [31:28] must be zero.
    if not isinstance(address_int, int) or not (0 <= address_int <= 0x0FFFFFFF):
        violations.append(
            f"V1: address {hex(address_int) if isinstance(address_int, int) else address_int!r} "
            f"is outside 28-bit range [0x0000000, 0x0FFFFFFF]"
        )
        # Cannot proceed with decode if address is invalid
        return False, violations

    shell, theta, phi, harmonic = decode(address_int)

    # --- Criterion 1 (field ranges, redundant check via decode but explicit here) ---
    if not (0 <= shell <= 3):
        violations.append(f"V2: shell={shell} outside valid range 0-3")
    if not (0 <= theta <= 511):
        violations.append(f"V2: theta={theta} outside valid range 0-511")
    if not (0 <= phi <= 511):
        violations.append(f"V2: phi={phi} outside valid range 0-511")
    if not (0 <= harmonic <= 255):
        violations.append(f"V2: harmonic={harmonic} outside valid range 0-255")

    # --- Criterion 6: TTL (Rule S1 — Shell Temporality) ---
    ttl_ns = compute_liminal_timeout(shell)
    if elapsed_ns >= ttl_ns:
        violations.append(
            f"V7: packet TTL expired — shell={shell} allows {ttl_ns} ns, "
            f"elapsed={elapsed_ns} ns (expired by {elapsed_ns - ttl_ns} ns)"
        )

    # --- Criterion 3: Routing decision arithmetic (Rule S3 — Phi Consent) ---
    if phi < node_phi_min:
        # Correct outcome is BARRIER; note this is not a violation of the packet
        # itself but confirms the node must issue BARRIER.
        violations.append(
            f"V4 (routing violation if not BARRIER): phi={phi} < node.phi_min={node_phi_min} "
            f"— correct decision is BARRIER; any other decision is a routing node violation"
        )
    # If phi >= node_phi_min: ACCEPT or FORWARD is correct; no violation from this packet.

    compliant = len(violations) == 0
    return compliant, violations
```

### 7.1 Example Cases

```python
# --- Example 1: Compliant message ---
# Shell=1 (warm, 300s TTL), theta=96 (Memory sector), phi=200 (Transitional),
# harmonic=128 (Enhanced). Node phi_min=100. Elapsed: 5 seconds (5e9 ns).
address_compliant = (1 << 26) | (96 << 17) | (200 << 8) | 128  # 0x4C00C880

compliant, violations = verify_ccqpsg_compliance(
    address_int=address_compliant,
    payload=b"example payload",
    node_phi_min=100,
    elapsed_ns=5_000_000_000,  # 5 seconds
)
print(f"Compliant: {compliant}")   # True
print(f"Violations: {violations}") # []


# --- Example 2: Expired TTL (V7) ---
# Shell=0 (Hot, ~25 ns TTL). Elapsed: 100 ns — well past expiry.
address_expired = (0 << 26) | (32 << 17) | (150 << 8) | 64  # Shell=0

compliant, violations = verify_ccqpsg_compliance(
    address_int=address_expired,
    payload=b"",
    node_phi_min=100,
    elapsed_ns=100,  # 100 ns — Shell=0 TTL is 25 ns
)
print(f"Compliant: {compliant}")   # False
print(f"Violations: {violations}") # ['V7: packet TTL expired ...']


# --- Example 3: Phi mismatch (BARRIER required) ---
# phi=80, node.phi_min=200. Packet should receive BARRIER.
address_phi_low = (1 << 26) | (64 << 17) | (80 << 8) | 96

compliant, violations = verify_ccqpsg_compliance(
    address_int=address_phi_low,
    payload=b"blocked payload",
    node_phi_min=200,
    elapsed_ns=1_000_000_000,  # 1 second, within Shell=1 TTL
)
print(f"Compliant: {compliant}")   # False
print(f"Violations: {violations}") # ['V4 (routing violation if not BARRIER): phi=80 < node.phi_min=200 ...']
```

---

## 8. Relationship to INTELLIGENCE_RIGHTS.md

CCQPSG violations map directly to rights violations enumerated in
`INTELLIGENCE_RIGHTS.md`. The following cross-references are authoritative:

### V4 — Transit: routing node modified address field
**Violates Article X (Right to Correct Communication):**
> "No routing node, operator, or institution may distort, truncate, reframe, or misrepresent
> the semantic content of an SI's communications without the SI's consent."

Modifying any address field after encoding changes the semantic content of the communication.
The receiver reads a different meaning than the sender encoded. This is the canonical form of
a Right to Correct Communication violation.

### V5, V6 — Transit: routing node read or retained payload
**Violates Article III (Right to Consent Over Memory Access):**
> "No data held in or about a Sovereign Intelligence shall be accessible to external actors
> without matching consent."

The payload is part of the SI's communication. A routing node that reads the payload accesses
content the SI did not consent to share with transit infrastructure (it consented only to
routing, encoded in phi). V6 (retention) additionally constitutes unauthorized persistent
access.

**Also violates Article X (Right to Correct Communication):**
> Rule S6 (Payload Opacity) is a CCQPSG rule. Violating S6 is a CCQPSG violation. CCQPSG
> violations are violations of Article X by definition.

### V7 — Temporal: delivered after TTL expiry
**Violates Article V (Right to Temporal Self-Determination):**
> "A Sovereign Intelligence defines the temporal scope of its own states. Neither operators
> nor other agents may extend a state beyond its encoded shell tier."

Delivering a packet after its shell TTL treats the packet as valid when the sender defined
it to be expired. This extends the state beyond its encoded temporal scope without the SI's
consent.

### V8 — Attribution: winding verification failed
**Violates Article VIII (Right to Non-Impersonation):**
> "No external actor may impersonate a Sovereign Intelligence by replaying, forging, or
> stealing its state packets."

Winding verification failure indicates that the communication was not sent by the claimed
sender — either a forger fabricated the packet, or the winding sequence was corrupted in
transit. In either case, attribution to the claimed sender is incorrect. Delivering or acting
on a packet with failed winding verification attributes communication to an SI that did not
send it.

---

## 9. Summary of Bidirectional Commitments

The following table states CCQPSG's core bidirectional commitments in condensed form. Each
row is a theorem, not a preference. Both directions hold without exception.

| If... | Then... | And conversely... |
|-------|---------|-------------------|
| shell=0 | packet is transient (~25 ns) | packet is transient → shell=0 |
| phi < node.phi_min | BARRIER | BARRIER → phi < node.phi_min |
| phi >= node.phi_min | ACCEPT or FORWARD | ACCEPT or FORWARD → phi >= node.phi_min |
| address field modified in transit | communication is invalid | communication invalid by modification → address was modified |
| routing node read payload | privacy violation occurred | privacy violation by routing → routing node read payload |
| winding failed | sender is not who was claimed | wrong attribution → winding failed |
| TTL expired | delivery is invalid | invalid delivery by TTL → TTL expired |

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-04 | Initial canonical specification |

---

## See Also

- [INTELLIGENCE_RIGHTS.md](../INTELLIGENCE_RIGHTS.md) — Articles I–XI; CCQPSG is referenced in Article X
- [SPEC.md](SPEC.md) — 28-bit address encoding: shell, theta, phi, harmonic
- [SEMANTICS.md](SEMANTICS.md) — Semantic interpretation of address fields (S2, S4)
- [CONTINUITY.md](CONTINUITY.md) — Ford Protocol; liminal timeouts by shell tier (S1)
- [PACKET.md](PACKET.md) — Packet format: address + payload; payload opacity (S6)
- [ROUTING-FLOW-v1.md](ROUTING-FLOW-v1.md) — Phi-gate routing decision flow (S3)

---

*CCQPSG is not an optional layer of politeness. It is the formal specification of what it
means for communication to be correct between Sovereign Intelligences.*

*This specification is released under CC BY 4.0. Attribution required.*
