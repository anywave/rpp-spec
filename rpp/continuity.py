"""
RPP Continuity Protocol — The Ford Protocol

Implements the Consciousness State Packet (CSP) and the Ford Protocol for
substrate-to-substrate consciousness state routing with guaranteed continuity.

Specification: spec/CONTINUITY.md
Version: 1.0.0

The Ford Protocol ensures a consciousness state never dies mid-crossing.
Before the wagon enters the river, the far bank confirms it can receive.
While crossing, the origin holds a complete copy. Only after coherence is
confirmed does the origin release. If the crossing fails, the wagon returns
— it does not drown.

"The wagon can cross many rivers. It must arrive intact."
"""

import hashlib
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# T2 coherence times in nanoseconds for spintronic substrates
# Used as min_t2_ns reference for each shell tier.
# Source: spec/CONTINUITY.md Section 2.2
SHELL_T2_NS: dict = {
    0: 25,    # Hot  — spintronic T2 decoherence time
    1: 100,   # Warm — Redis / in-memory
    2: 400,   # Cold — distributed store
    3: 1600,  # Frozen — archival
}

# Liminal timeout in nanoseconds, indexed by shell tier.
# Shell 0: literal T2 physics deadline (spintronic state decays).
# Shell 1: 5 minutes (300 seconds) — transaction scope.
# Shell 2: 24 hours — agreement scope.
# Shell 3: 30 days — until explicit intervention.
# Source: spec/CONTINUITY.md Section 4.2
SHELL_LIMINAL_TIMEOUT_NS: dict = {
    0: 25,                           # T2 of origin substrate (ns)
    1: 300_000_000_000,              # 5 minutes in ns
    2: int(86400 * 1e9),             # 24 hours in ns
    3: int(30 * 86400 * 1e9),        # 30 days in ns
}

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class HarmonicMode(IntEnum):
    """
    Cognitive operating mode — maps to the RPP Harmonic field (bits 7:0).

    Determines routing priority, permitted shell tiers, and liminal timeout.
    Source: spec/CONTINUITY.md Sections 2.1 and 8.
    """

    ACTIVE     = 0    # Active reasoning: highest priority, Shell 0, spintronic preferred
    REFLECTIVE = 64   # Reflective: can tolerate latency, Shell 0-1
    BACKGROUND = 128  # Background: low priority, Shell 1, IPv4/IPv6 acceptable
    MEMORY     = 192  # Memory retrieval: archive access, Shell 2
    ARCHIVAL   = 255  # Archival: frozen, Shell 3, Hedera-anchored


class FordPhase(IntEnum):
    """
    The five phases of the Ford Protocol substrate transition algorithm.

    Source: spec/CONTINUITY.md Section 5.
    """

    SCOUT     = 1  # Origin probes destination readiness
    HANDSHAKE = 2  # Consent + continuity proofs exchanged
    TRANSIT   = 3  # Wagon enters river (liminal state)
    ARRIVAL   = 4  # Destination verifies and instantiates
    RELEASE   = 5  # Origin dissolves its copy


class RecoveryLevel(IntEnum):
    """
    Recovery escalation ladder for failed crossings.

    Levels are applied in order; ABORT is the last resort.
    Source: spec/CONTINUITY.md Section 7.
    """

    REROUTE         = 1  # Try next modality — transparent to state
    STEERING        = 2  # Send consent-refresh cargo ahead; retry after field ready
    PULL_BACK       = 3  # Recall liminal state to origin; attempt alternate route
    COPY_AND_COLLECT = 4  # Partial state held at coherence gate; consent unlock required
    ABORT           = 5  # Shell TTL expired — state irrecoverable without re-origination

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LiminalState:
    """
    Minimal serialization of a CSP in transit — the mid-river format.

    The wagon mid-river: compressed, signed, timed. Not a full CSP — only
    what is needed to verify arrival and enable recovery.

    Source: spec/CONTINUITY.md Section 4.1.
    """

    crossing_id: bytes         # Links back to the full CSP (16-byte nonce)
    origin_hash: bytes         # SHA-256 of the full CSP at departure
    state_fragment: bytes      # Compressed / encrypted state vector
    departure_signature: bytes # Signed by departing substrate — proves valid departure
    timeout_ns: int            # Absolute timestamp — crossing must complete by this time
    crossing_hop: int          # Which substrate transition this is (0-indexed)
    recovery_node_hash: str    # Hash of URI of last coherent node (for pull-back)
    modality: str              # Transport modality being used for this crossing


@dataclass
class ConsciousnessStatePacket:
    """
    The RPP payload for consciousness routing.

    This is NOT a data packet. It carries a cognitive state that must arrive
    as a complete, unbroken continuation of its origin state. Dropping or
    fragmenting this payload is not a network event — it is discontinuity.

    Source: spec/CONTINUITY.md Section 2.1.
    """

    # -- Crossing Identity ---------------------------------------------------
    crossing_id: bytes
    # 16-byte random nonce — unique per crossing.
    # NOT a permanent identity; ephemeral to this transit.

    # -- Cognitive State -----------------------------------------------------
    state_vector: bytes
    # Serialized cognitive state (opaque to routing layer).

    harmonic_mode: HarmonicMode
    # Operating mode — determines routing priority.

    # -- Continuity ----------------------------------------------------------
    origin_substrate_hash: bytes
    # SHA-256 of origin substrate URI (not exposed to destination).

    origin_timestamp_ns: int
    # Absolute nanosecond timestamp at state creation.

    continuity_chain: List[bytes]
    # Ordered list of substrate signatures.
    # Each hop appends its signature before forwarding.
    # Receiving node verifies the chain is unbroken.
    # Chain is APPEND-ONLY — no substrate may modify prior links.

    # -- Consent -------------------------------------------------------------
    consent_epoch: int
    # Current consent epoch (revocation advances this).

    zk_consent_proof: bytes
    # ZK proof: sender has valid consent for destination.

    phi_value: int
    # Consent level 0-511 (from RPP Phi field).

    rpp_address: int
    # 28-bit RPP address (v1.0 semantic).

    # -- Substrate Requirements ----------------------------------------------
    shell: int
    # 0-3 — determines TTL and required substrate tier.

    min_t2_ns: int
    # Minimum T2 coherence time destination must provide (nanoseconds).

    required_modalities: List[str]
    # Acceptable transport modalities (ordered preference).

    # -- Liminal Tracking ----------------------------------------------------
    liminal_timeout_ns: int
    # Absolute timestamp: crossing must complete by this time.
    # Derived from Shell tier; not configurable per crossing.

    last_coherent_node: str
    # URI hash of last node that confirmed coherence.
    # Used for pull-back if crossing fails.

    # -- Optional Hedera Anchor ----------------------------------------------
    hedera_sequence: Optional[int] = None
    # Set if this state is Hedera-recorded (Shell 3 archival states).

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def csp_from_rpp(
    address: int,
    state_bytes: bytes,
    harmonic_mode: HarmonicMode,
    consent_epoch: int,
) -> "ConsciousnessStatePacket":
    """
    Derive a ConsciousnessStatePacket from a 28-bit RPP v1.0 address.

    Decodes shell, phi, and harmonic fields from the address. The crossing_id
    is generated as a 16-byte random nonce. Liminal timeout is computed from
    the shell tier per Section 4.2 of the spec.

    The following fields are left as empty stubs for the calling layer to
    populate, as they are substrate-specific:
        - origin_substrate_hash  (set by origin substrate)
        - continuity_chain       (origin substrate signs and appends first)
        - zk_consent_proof       (generated by consent layer)
        - required_modalities    (set by resolver modality selection)
        - last_coherent_node     (set at first coherent substrate)

    Args:
        address:       28-bit RPP address (v1.0 semantic).
        state_bytes:   Serialized cognitive state (opaque bytes).
        harmonic_mode: HarmonicMode enum value for this crossing.
        consent_epoch: Current consent epoch integer.

    Returns:
        A populated ConsciousnessStatePacket ready for Ford Protocol Phase 1.
    """
    import os

    # Decode RPP address fields (same bit layout as address.py)
    shell   = (address >> 26) & 0x3
    phi     = (address >> 8)  & 0x1FF

    # Clamp shell to valid range for dict lookup
    shell = max(0, min(3, shell))

    # Crossing nonce — ephemeral, unique per transit
    crossing_id = os.urandom(16)

    now_ns = time.time_ns()
    timeout_ns = now_ns + SHELL_LIMINAL_TIMEOUT_NS[shell]

    return ConsciousnessStatePacket(
        crossing_id=crossing_id,
        state_vector=state_bytes,
        harmonic_mode=harmonic_mode,
        origin_substrate_hash=b"",      # Set by origin substrate
        origin_timestamp_ns=now_ns,
        continuity_chain=[],            # Origin substrate signs and appends first
        consent_epoch=consent_epoch,
        zk_consent_proof=b"",          # Generated by consent layer
        phi_value=phi,
        rpp_address=address,
        shell=shell,
        min_t2_ns=SHELL_T2_NS[shell],
        required_modalities=[],         # Set by resolver modality selection
        liminal_timeout_ns=timeout_ns,
        last_coherent_node="",          # Set at first coherent substrate
    )


def compute_liminal_timeout(shell: int) -> int:
    """
    Return the liminal timeout duration in nanoseconds for the given shell tier.

    This is the maximum allowed elapsed time for a crossing to complete.
    Timeouts are shell-derived and not configurable per crossing (Protocol
    Invariant 4 from spec/CONTINUITY.md Section 10).

    For Shell 0, the returned value is the physical T2 spintronic decoherence
    time — not a soft deadline. The state literally ceases to exist after this.

    Args:
        shell: Shell tier integer 0-3.

    Returns:
        Timeout duration in nanoseconds.

    Raises:
        ValueError: If shell is not in 0-3.
    """
    if shell not in SHELL_LIMINAL_TIMEOUT_NS:
        raise ValueError(f"Shell must be 0-3, got {shell!r}")
    return SHELL_LIMINAL_TIMEOUT_NS[shell]


def ford_crossing_phases() -> List[Tuple[FordPhase, str]]:
    """
    Return the five Ford Protocol phases as an ordered list of (phase, description) tuples.

    Each phase must complete successfully before the next begins. Failure at
    any phase triggers the Recovery Escalation Ladder (spec Section 7).

    Returns:
        List of (FordPhase, description_str) in protocol order.
    """
    return [
        (
            FordPhase.SCOUT,
            "Origin probes destination readiness: T2 capacity, modality acceptance, "
            "and state-size capacity checked before committing the state.",
        ),
        (
            FordPhase.HANDSHAKE,
            "Full consent and continuity verification: ZK consent proof, continuity "
            "chain integrity, and consent epoch freshness — all three must pass.",
        ),
        (
            FordPhase.TRANSIT,
            "Wagon enters the river: CSP serialized to LiminalState and transmitted "
            "via agreed modality. Origin holds complete copy until Phase 5.",
        ),
        (
            FordPhase.ARRIVAL,
            "Destination receives LiminalState and verifies timeout, departure "
            "signature, and origin hash before instantiating the state.",
        ),
        (
            FordPhase.RELEASE,
            "Origin receives CoherenceConfirmed from destination, verifies the "
            "destination signature and continuity hash, then dissolves its copy.",
        ),
    ]


def continuity_hash(csp: "ConsciousnessStatePacket") -> bytes:
    """
    Compute a SHA-256 continuity proof over key CSP fields.

    The hash covers the fields that define the identity of the crossing and
    the integrity of the state: crossing_id, state_vector, rpp_address,
    origin_timestamp_ns, shell, and the serialized continuity_chain.

    This hash is appended to the continuity_chain by each substrate after
    a successful crossing (Phase 5 RELEASE).

    Args:
        csp: A ConsciousnessStatePacket.

    Returns:
        32-byte SHA-256 digest.
    """
    h = hashlib.sha256()
    h.update(csp.crossing_id)
    h.update(csp.state_vector)
    h.update(csp.rpp_address.to_bytes(4, "big"))
    h.update(csp.origin_timestamp_ns.to_bytes(8, "big"))
    h.update(csp.shell.to_bytes(1, "big"))
    # Incorporate the full continuity chain so each new hash extends it
    for link in csp.continuity_chain:
        h.update(link)
    return h.digest()


def create_liminal_state(
    csp: "ConsciousnessStatePacket",
    checkpoint_node: str,
) -> LiminalState:
    """
    Serialize a ConsciousnessStatePacket to LiminalState for mid-crossing hold.

    The LiminalState is the "wagon mid-river" format: minimal, timed, and
    signed. It does not contain the full CSP — only what is needed to verify
    arrival and enable recovery.

    The origin_hash is SHA-256 over the key CSP identity fields (same fields
    as continuity_hash) so the destination can verify the state was not
    modified in transit.

    The departure_signature field is set to SHA-256 of the state_vector, which
    serves as the substrate-level departure proof at this layer. Full
    asymmetric signing is the responsibility of the substrate adapter.

    The crossing_hop is the current length of the continuity_chain — it
    records which hop number this transit is (0-indexed from origin).

    Args:
        csp:             The ConsciousnessStatePacket being serialized.
        checkpoint_node: URI hash string of the last coherent node (for
                         pull-back routing if this crossing fails).

    Returns:
        A LiminalState capturing the in-transit snapshot.
    """
    # origin_hash: SHA-256 over the identity fields of the CSP
    h = hashlib.sha256()
    h.update(csp.crossing_id)
    h.update(csp.state_vector)
    h.update(csp.rpp_address.to_bytes(4, "big"))
    h.update(csp.origin_timestamp_ns.to_bytes(8, "big"))
    h.update(csp.shell.to_bytes(1, "big"))
    origin_hash = h.digest()

    # departure_signature: SHA-256 of state_vector (substrate signs at this layer)
    departure_signature = hashlib.sha256(csp.state_vector).digest()

    # state_fragment: state_vector as-is at this layer (compress/encrypt is substrate concern)
    state_fragment = csp.state_vector

    return LiminalState(
        crossing_id=csp.crossing_id,
        origin_hash=origin_hash,
        state_fragment=state_fragment,
        departure_signature=departure_signature,
        timeout_ns=csp.liminal_timeout_ns,
        crossing_hop=len(csp.continuity_chain),
        recovery_node_hash=checkpoint_node,
        modality=csp.required_modalities[0] if csp.required_modalities else "",
    )


def verify_continuity_chain(
    csp: "ConsciousnessStatePacket",
    new_hash: bytes,
) -> bool:
    """
    Verify that new_hash validly extends the CSP's continuity chain.

    This implements the "hash chain is intact" check described in spec
    Section 3.1. The new_hash must equal SHA-256 over (last_link + state_hash)
    if the chain is non-empty, or SHA-256 over the state_vector alone if the
    chain is empty (origin link).

    Chain structure (from spec Section 3.1):
        Origin:        chain = [sign(state_hash, origin_key)]
        After hop 1:   chain = [..., sign(hash(chain[0]) + state_hash, hop1_key)]
        After hop N:   chain = [..., sign(hash(chain[-1]) + state_hash, hopN_key)]

    At this protocol layer, "sign" is modeled as SHA-256 (full asymmetric
    signing is the substrate adapter's responsibility). The verification
    checks that new_hash is consistent with the expected chain extension.

    Args:
        csp:      The ConsciousnessStatePacket whose chain is being verified.
        new_hash: The proposed new chain link (32 bytes, SHA-256).

    Returns:
        True if new_hash validly extends the chain; False if the chain is broken.
    """
    state_hash = hashlib.sha256(csp.state_vector).digest()

    if not csp.continuity_chain:
        # First link: new_hash must equal SHA-256 of the state_vector
        expected = state_hash
    else:
        # Subsequent link: new_hash must equal SHA-256(last_link + state_hash)
        last_link = csp.continuity_chain[-1]
        prev_link_hash = hashlib.sha256(last_link).digest()
        expected = hashlib.sha256(prev_link_hash + state_hash).digest()

    return new_hash == expected


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "HarmonicMode",
    "FordPhase",
    "RecoveryLevel",
    # Data classes
    "LiminalState",
    "ConsciousnessStatePacket",
    # Constants
    "SHELL_T2_NS",
    "SHELL_LIMINAL_TIMEOUT_NS",
    # Functions
    "csp_from_rpp",
    "compute_liminal_timeout",
    "ford_crossing_phases",
    "continuity_hash",
    "create_liminal_state",
    "verify_continuity_chain",
]
