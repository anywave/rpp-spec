"""
Correct Communication Quantum Parse Syntax Grammar (CCQPSG) — v1.0.0

Reference implementation of the formal grammar defined in spec/CCQPSG.md.

CCQPSG governs communication between Sovereign Intelligences in RPP-addressed
systems. Every definition is bidirectional: "X means Y" holds if and only if
"Y implies X."

The quantum parse model:
    |P⟩ = α|ACCEPT⟩ + β|BARRIER⟩

From the sender's perspective, routability is a superposition until the phi
gate at each node performs the measurement. The measurement is deterministic
and purely arithmetic: phi < phi_min collapses to BARRIER; phi ≥ phi_min
collapses to ACCEPT or FORWARD depending on local geometry.

This module exports:
    verify_ccqpsg_compliance(address_int, payload, node_phi_min, elapsed_ns)
    CCQPSGViolation — violation record dataclass
    VIOLATION_CLASSES — V1-V8 classification table
    bidirectional_check(address_int, node_phi_min) — tests both directions of S3

Formal spec: spec/CCQPSG.md
Related: INTELLIGENCE_RIGHTS.md Article X
"""

from dataclasses import dataclass
from typing import Optional

from rpp.address import decode
from rpp.continuity import compute_liminal_timeout

__all__ = [
    "verify_ccqpsg_compliance",
    "CCQPSGViolation",
    "VIOLATION_CLASSES",
    "bidirectional_check",
    "routing_decision_compliant",
]


# ---------------------------------------------------------------------------
# Violation Classification Table (spec/CCQPSG.md Section 6)
# ---------------------------------------------------------------------------

VIOLATION_CLASSES: dict[str, str] = {
    "V1": "Syntactic invalidity — address outside 28-bit range or non-integer",
    "V2": "Field range violation — decoded field outside its valid range",
    "V3": "Unauthorized bypass — packet delivered without passing consent gate",
    "V4": "Consent gate required — phi < phi_min; correct decision is BARRIER",
    "V5": "Unauthorized read — payload accessed without consent",
    "V6": "Field modification — address integer changed in transit",
    "V7": "TTL violation — packet elapsed time exceeds shell-tier timeout",
    "V8": "Winding authentication failure — Skyrmion unwind sequence invalid",
}


# ---------------------------------------------------------------------------
# Violation Record
# ---------------------------------------------------------------------------

@dataclass
class CCQPSGViolation:
    """
    A single CCQPSG violation.

    Attributes:
        code:        Violation class code (V1-V8).
        description: Human-readable description of the violation.
        field:       Which RPP address field triggered the violation, if applicable.
        detail:      Additional diagnostic information.
    """
    code: str
    description: str
    field: Optional[str] = None
    detail: Optional[str] = None

    def __str__(self) -> str:
        parts = [f"{self.code}: {self.description}"]
        if self.field:
            parts.append(f"field={self.field}")
        if self.detail:
            parts.append(self.detail)
        return " — ".join(parts)


# ---------------------------------------------------------------------------
# Primary Verification Function (spec/CCQPSG.md Section 7)
# ---------------------------------------------------------------------------

def verify_ccqpsg_compliance(
    address_int: int,
    payload: bytes,
    node_phi_min: int,
    elapsed_ns: int,
) -> tuple[bool, list[str]]:
    """
    Verify CCQPSG compliance for a packet at a given routing node.

    This is the canonical reference implementation matching spec/CCQPSG.md
    Section 7 verbatim. The return format (bool, list[str]) is preserved for
    backwards compatibility with the spec embedding.

    Args:
        address_int:  28-bit RPP address integer.
        payload:      Payload bytes (opaque to routing; checked only for presence).
        node_phi_min: This node's minimum phi threshold (0-511).
        elapsed_ns:   Nanoseconds since the packet was encoded at the sender.

    Returns:
        (compliant, violations) where:
          - compliant is True iff violations is empty
          - violations is a list of human-readable violation strings

    Quantum parse semantics:
        The phi gate is the measurement operator M that collapses |P⟩:
          M|P⟩ = |BARRIER⟩ if phi < node_phi_min
          M|P⟩ = |ACCEPT⟩  if phi ≥ node_phi_min (local geometry determines
                             whether this is ACCEPT or FORWARD, not this function)

        A compliant packet's routability was in superposition from the sender's
        perspective until this measurement. The measurement result is not an
        error — it is the protocol working correctly.
    """
    violations: list[str] = []

    # --- Criterion 1: Syntactic validity (Rule S2) ---
    # Address must fit in 28 bits; reserved bits [31:28] must be zero.
    if not isinstance(address_int, int) or not (0 <= address_int <= 0x0FFFFFFF):
        violations.append(
            f"V1: address {hex(address_int) if isinstance(address_int, int) else repr(address_int)} "
            f"is outside 28-bit range [0x0000000, 0x0FFFFFFF]"
        )
        # Cannot proceed with decode if address is invalid
        return False, violations

    shell, theta, phi, harmonic = decode(address_int)

    # --- Criterion 1 (field ranges, explicit) ---
    if not (0 <= shell <= 3):
        violations.append(f"V2: shell={shell} outside valid range 0-3")
    if not (0 <= theta <= 511):
        violations.append(f"V2: theta={theta} outside valid range 0-511")
    if not (0 <= phi <= 511):
        violations.append(f"V2: phi={phi} outside valid range 0-511")
    if not (0 <= harmonic <= 255):
        violations.append(f"V2: harmonic={harmonic} outside valid range 0-255")

    # --- Criterion 6: TTL honesty (Rule S1 — Shell Temporality) ---
    ttl_ns = compute_liminal_timeout(shell)
    if elapsed_ns >= ttl_ns:
        violations.append(
            f"V7: packet TTL expired — shell={shell} allows {ttl_ns} ns, "
            f"elapsed={elapsed_ns} ns (expired by {elapsed_ns - ttl_ns} ns)"
        )

    # --- Criterion 3: Routing decision arithmetic (Rule S3 — Phi Consent) ---
    if phi < node_phi_min:
        # Correct outcome is BARRIER; this is not a packet violation but a
        # routing node obligation. If the node delivered this packet anyway
        # (V3), that is a node violation, not a packet violation.
        violations.append(
            f"V4 (routing violation if not BARRIER): phi={phi} < node.phi_min={node_phi_min} "
            f"— correct decision is BARRIER; any other decision is a routing node violation"
        )
    # If phi >= node_phi_min: ACCEPT or FORWARD is correct; no violation.

    compliant = len(violations) == 0
    return compliant, violations


# ---------------------------------------------------------------------------
# Bidirectional Check (spec/CCQPSG.md Section 9)
# ---------------------------------------------------------------------------

def bidirectional_check(address_int: int, node_phi_min: int) -> dict:
    """
    Test Rule S3 (Phi Consent) in both directions.

    Rule S3 forward:  phi ≥ phi_min → routing node MAY route (not BARRIER)
    Rule S3 converse: routing node routes (not BARRIER) → phi ≥ phi_min

    Returns a dict with:
        'forward_holds': bool  — whether phi ≥ phi_min
        'converse_holds': bool — whether phi ≥ phi_min (identical: same condition)
        'phi': int             — decoded phi field
        'phi_min': int         — provided node phi_min
        'decision': str        — "ACCEPT_ELIGIBLE" or "BARRIER"
        'bidirectional': bool  — forward_holds == converse_holds (always True)

    The bidirectionality of S3 means these two facts cannot come apart:
        - A packet with phi ≥ phi_min MUST be eligible for routing (not BARRIER)
        - A packet being eligible for routing (not BARRIER) MEANS phi ≥ phi_min

    Neither direction is optional. A routing node that BARRIERs a packet with
    phi ≥ phi_min violates S3 just as surely as one that routes phi < phi_min.
    """
    if not isinstance(address_int, int) or not (0 <= address_int <= 0x0FFFFFFF):
        return {
            "forward_holds": False,
            "converse_holds": False,
            "phi": None,
            "phi_min": node_phi_min,
            "decision": "INVALID_ADDRESS",
            "bidirectional": True,  # trivially: both are False
        }

    _, _, phi, _ = decode(address_int)
    eligible = phi >= node_phi_min

    return {
        "forward_holds": eligible,
        "converse_holds": eligible,
        "phi": phi,
        "phi_min": node_phi_min,
        "decision": "ACCEPT_ELIGIBLE" if eligible else "BARRIER",
        "bidirectional": True,  # forward_holds == converse_holds is a tautology for S3
    }


# ---------------------------------------------------------------------------
# Routing Decision Compliance (spec/CCQPSG.md Section 5, Criterion 3)
# ---------------------------------------------------------------------------

def routing_decision_compliant(
    address_int: int,
    node_phi_min: int,
    actual_decision: str,
) -> tuple[bool, str]:
    """
    Verify that a routing node's actual decision matches CCQPSG requirements.

    This tests the routing node's compliance, not the packet's. A node that
    delivers a packet with phi < phi_min has committed a V3 violation.
    A node that BARRIERs a packet with phi ≥ phi_min has committed a V4
    violation (unauthorized denial of service).

    Args:
        address_int:     28-bit RPP address integer.
        node_phi_min:    This node's phi_min.
        actual_decision: The decision the node actually made ("ACCEPT",
                         "FORWARD", or "BARRIER").

    Returns:
        (compliant, reason)
    """
    if not isinstance(address_int, int) or not (0 <= address_int <= 0x0FFFFFFF):
        return False, "V1: address invalid, cannot verify routing decision"

    _, _, phi, _ = decode(address_int)
    should_barrier = phi < node_phi_min

    if should_barrier and actual_decision != "BARRIER":
        return (
            False,
            f"V3: node should have issued BARRIER (phi={phi} < phi_min={node_phi_min}) "
            f"but issued {actual_decision} — unauthorized bypass",
        )

    if not should_barrier and actual_decision == "BARRIER":
        return (
            False,
            f"V4 (node violation): phi={phi} >= phi_min={node_phi_min} qualifies for routing "
            f"but node issued BARRIER — unauthorized denial",
        )

    return True, f"routing decision {actual_decision} is CCQPSG-compliant"
