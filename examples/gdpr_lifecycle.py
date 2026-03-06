#!/usr/bin/env python3
"""
RPP: GDPR Compliance by Design
===============================
Demonstrates how RPP addresses implement GDPR Art. 5 (storage limitation)
and Art. 17 (right to erasure) structurally — through address arithmetic,
not policy rules.
"""
import sys, math
sys.stdout.reconfigure(encoding='utf-8')

from rpp.address import encode, decode, from_components
from rpp.network import make_routing_decision, NodeRecord, NodeTier, RoutingDecision
from rpp.geometry import (
    TorusPoint, ToroidalStateVector, antipodal, TWO_PI,
    derive_rotation_key, apply_rotation,
)
from rpp.continuity import compute_liminal_timeout


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _node_id(label: str) -> bytes:
    """Deterministic 32-byte node identifier from a short label."""
    raw = label.encode("utf-8")
    return (raw * 8)[:32]

def _sig() -> bytes:
    return b"\x00" * 32

def _make_node(label: str, theta: int, phi_min: int, tier: NodeTier = NodeTier.WARM) -> NodeRecord:
    """Construct a minimal NodeRecord for demo routing decisions."""
    return NodeRecord(
        node_id=_node_id(label),
        tier=tier,
        theta=theta,
        phi_min=phi_min,
        phi_max=511,
        harmonic_modes=[128, 192],
        substrate_modality="ipv4",
        consent_epoch=1,
        t2_ns=0,
        announced_at_ns=0,
        signature=_sig(),
    )

def _banner(title: str) -> None:
    width = 72
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)

def _section(title: str) -> None:
    print(f"\n--- {title} ---")


# ---------------------------------------------------------------------------
# PART 1: Data Creation with Consent
# ---------------------------------------------------------------------------

def part1_data_creation() -> tuple:
    _banner("PART 1 — DATA CREATION WITH CONSENT ENCODED IN THE ADDRESS")

    # Alice creates a health record.
    #   Shell=1  — Warm tier, session-scoped (300-second TTL)
    #   Theta=80 — Memory sector (64 <= 80 < 128)
    #   Phi=300  — Abstract grounding level; high consent threshold required
    #   Harmonic=128 — Reflective routing mode
    shell    = 1
    theta    = 80
    phi      = 300
    harmonic = 128

    addr = from_components(shell, theta, phi, harmonic)
    ttl_ns = compute_liminal_timeout(shell)
    ttl_s  = ttl_ns / 1e9

    print(f"""
Scenario
--------
  Alice creates a personal health record and submits it to an RPP-aware system.
  The system issues an address that encodes four GDPR-relevant properties in
  a single 28-bit integer — no separate access-control list is written.

  Address: {addr.to_hex()}  (raw integer: {addr.raw})

  Field breakdown:
    Shell    = {addr.shell}   ({addr.shell_name} tier)
                  Lifetime: {ttl_s:,.0f} seconds ({ttl_s/60:.0f} minutes)
                  This is encoded in bits [27:26] of the address.
                  A system honouring RPP semantics treats a Shell=1 address
                  as non-existent after 300 seconds — not by policy, but
                  because the Shell field declares it.

    Theta    = {addr.theta:3d}  ({addr.sector_name} sector)
                  Identifies the data type domain: health/memory records.
                  Routing nodes in the Memory sector (theta 64-127) handle this.

    Phi      = {addr.phi:3d}  ({addr.grounding_level} consent tier)
                  A node must declare phi_min <= {addr.phi} to conduct this address.
                  phi={addr.phi} means high consent is required — only nodes that
                  explicitly accept "Abstract" data will route it.

    Harmonic = {addr.harmonic:3d}  (Reflective routing mode)
                  Signals deliberate, auditable routing behaviour.

  The address IS the policy.
  There is no ACL table, no permissions record, no consent database row.
  A router that can do arithmetic can enforce Art. 25 (Privacy by Design)
  without reading a policy file.
""")

    return addr.raw, shell, theta, phi, harmonic


# ---------------------------------------------------------------------------
# PART 2: Authorised Access — Routing as Consent Enforcement
# ---------------------------------------------------------------------------

def part2_authorised_access(address_int: int) -> None:
    _banner("PART 2 — AUTHORISED ACCESS (CONSENT ENFORCED BY ARITHMETIC)")

    shell, theta, phi, harmonic = decode(address_int)

    print(f"""
Scenario
--------
  Alice's health record sits at address {hex(address_int)} (phi={phi}).
  Three infrastructure nodes each have a declared phi_min threshold.
  The routing algorithm performs one comparison: packet_phi >= node_phi_min.
  No network call to a policy server.  No ACL lookup.  Pure arithmetic.
""")

    # Node A: phi_min=200 — well below phi=300, conducts the packet
    # Node B: phi_min=250 — still below phi=300, conducts the packet
    # Node C: phi_min=350 — above phi=300, becomes a BARRIER
    nodes = [
        ("Node-A", 200,  70, NodeTier.HOT),   # theta=70 near Memory sector
        ("Node-B", 250,  95, NodeTier.WARM),
        ("Node-C", 350, 110, NodeTier.WARM),
    ]

    print(f"  {'Node':<8}  {'phi_min':>7}  {'phi comparison':>25}  {'Decision'}")
    print(f"  {'-'*8}  {'-'*7}  {'-'*25}  {'-'*30}")

    for label, phi_min, node_theta, tier in nodes:
        node = _make_node(label, node_theta, phi_min, tier)
        decision = make_routing_decision(address_int, node, [])
        comparison = f"phi {phi} {'>=':>2} phi_min {phi_min} -> {'YES' if phi >= phi_min else 'NO ':>3}"
        print(f"  {label:<8}  {phi_min:>7}  {comparison:>25}  {decision.action}  ({decision.reason})")

    print(f"""
  Node-C is a BARRIER: phi={phi} < phi_min=350.
  This is enforced at the node level, locally, in constant time.
  The node does not need to know who Alice is, what the data contains,
  or what any other node decided.

  Art. 25 (Privacy by Design): consent requirements are enforced at
  every routing hop, not just at the access point.  A rogue node that
  ignores phi_min is detectable and excludable from the consent field.
""")


# ---------------------------------------------------------------------------
# PART 3: Consent Revocation — GDPR Art. 17
# ---------------------------------------------------------------------------

def part3_consent_revocation(old_address_int: int, shell: int, theta: int,
                              harmonic: int) -> None:
    _banner("PART 3 — CONSENT REVOCATION (GDPR Art. 17: Right to Erasure)")

    old_phi = 300
    new_phi = 450   # more restrictive: fewer nodes can route this

    new_address_int = encode(shell, theta, new_phi, harmonic)

    print(f"""
Scenario
--------
  Alice revokes consent.  The controller increments the consent epoch and
  reissues Alice's record under a new address with phi raised from {old_phi} to {new_phi}.

  Old address: {hex(old_address_int)}  (phi={old_phi})
  New address: {hex(new_address_int)}  (phi={new_phi})

  The old address is not deleted from any database.
  It continues to exist as an integer in memory.
  What changes is the consent field: every routing node now requires
  phi_min >= {new_phi} for the health-record sector.  The old address
  encodes phi={old_phi}, which no node will accept.
""")

    # Demonstrate: old address is now universally barriered
    nodes_after_revocation = [
        ("Node-A", 400,  70, NodeTier.HOT),
        ("Node-B", 400,  95, NodeTier.WARM),
        ("Node-C", 400, 110, NodeTier.WARM),
    ]

    print(f"  Routing the OLD address ({hex(old_address_int)}, phi={old_phi}) after revocation:")
    print(f"  {'Node':<8}  {'phi_min':>7}  {'phi comparison':>25}  {'Decision'}")
    print(f"  {'-'*8}  {'-'*7}  {'-'*25}  {'-'*30}")

    all_barrier = True
    for label, phi_min, node_theta, tier in nodes_after_revocation:
        node = _make_node(label, node_theta, phi_min, tier)
        decision = make_routing_decision(old_address_int, node, [])
        if decision.action != "BARRIER":
            all_barrier = False
        comparison = f"phi {old_phi} {'>=':>2} phi_min {phi_min} -> {'YES' if old_phi >= phi_min else 'NO ':>3}"
        print(f"  {label:<8}  {phi_min:>7}  {comparison:>25}  {decision.action}")

    print()
    if all_barrier:
        print(f"  Result: ALL NODES BARRIER")
    else:
        print(f"  Result: ROUTING PARTIALLY INTACT (unexpected)")

    print(f"""
  The old address {hex(old_address_int)} has not been deleted.
  It has become unroutable.
  The data at that address is inaccessible by arithmetic, not by policy.

  A node that receives a packet addressed to {hex(old_address_int)} computes:
      phi_field = (address >> 8) & 0x1FF  =>  {old_phi}
      phi_min   = node.phi_min            =>  400
      decision  = BARRIER if {old_phi} < 400 else ACCEPT
  That is the entirety of the enforcement mechanism.

  The traditional approach requires:
      DELETE FROM health_records WHERE patient_id = 'alice'
      ... on every system that holds a copy.
      Miss one replica, one cache, one backup, one analytics pipeline,
      one third-party processor: GDPR breach.

  The RPP approach:
      Raise phi_min on your consent field nodes above the data's phi.
      Done.  Every node enforces this independently, simultaneously,
      without coordination, without a DELETE round-trip.
""")


# ---------------------------------------------------------------------------
# PART 4: Address Expiry — GDPR Art. 5 Storage Limitation
# ---------------------------------------------------------------------------

def part4_address_expiry(address_int: int) -> None:
    _banner("PART 4 — ADDRESS EXPIRY (GDPR Art. 5: Storage Limitation)")

    shell, theta, phi, harmonic = decode(address_int)
    ttl_ns  = compute_liminal_timeout(shell)   # returns int nanoseconds
    ttl_s   = ttl_ns / 1e9

    # Simulate time advancing past the TTL
    # We do not sleep — we compute the arithmetic directly
    issued_at    = 1_700_000_000_000_000_000   # arbitrary fixed ns timestamp
    now_before   = issued_at + int(299 * 1e9)  # 299 s in — still valid
    now_after    = issued_at + int(301 * 1e9)  # 301 s in — expired
    expired_before = now_before > issued_at + ttl_ns
    expired_after  = now_after  > issued_at + ttl_ns

    print(f"""
Scenario
--------
  Alice's record sits at a Shell={shell} address.
  Shell={shell} has a liminal timeout of {ttl_ns:,} nanoseconds
  ({ttl_s:,.0f} seconds, {ttl_s/60:.0f} minutes).

  This timeout is not a configuration value.
  It is derived directly from the Shell field by compute_liminal_timeout(shell={shell}).
  The Shell field occupies bits [27:26] of the address.
  The lifetime is part of the address.

  Simulation (no sleeping — arithmetic only):

    issued_at  = {issued_at:,} ns  (arbitrary fixed reference)
    ttl_ns     = {ttl_ns:,} ns  (= compute_liminal_timeout({shell}))

    At t = issued_at + 299 s:
      now_ns   = {now_before:,}
      expired  = {now_before} > {issued_at + ttl_ns}  =>  {expired_before}

    At t = issued_at + 301 s:
      now_ns   = {now_after:,}
      expired  = {now_after} > {issued_at + ttl_ns}  =>  {expired_after}

  The check is:
      expired = now_ns > issued_at + compute_liminal_timeout({shell})

  One integer comparison.  No cron job.  No TTL header lookup.
  No out-of-band expiry daemon.

  You cannot store a Shell={shell} address permanently.
  Not because of a policy rule.
  Because the address encodes its own expiry, and a system that honours
  RPP semantics treats expired addresses as non-existent.

  If a storage system holds an address whose TTL has elapsed, it is holding
  an invalid address — equivalent to holding a reference to freed memory.
  An RPP-conformant node will refuse to route it.

  GDPR Art. 5(1)(e) — storage limitation:
    "Personal data shall be kept in a form which permits identification of
     data subjects for no longer than is necessary."

  Shell=1 makes this a physical property of the address, not an
  administrative obligation remembered in a policy document.

  Shell lifetimes for reference:
    Shell 0 (Hot):    25 nanoseconds  — spintronic T2 decoherence
    Shell 1 (Warm):   300 seconds     — session / transaction scope
    Shell 2 (Cold):   86,400 seconds  — 24-hour agreement scope
    Shell 3 (Frozen): 2,592,000 seconds — 30-day archival scope
""")


# ---------------------------------------------------------------------------
# PART 5: The Audit Trail
# ---------------------------------------------------------------------------

def part5_audit_trail(address_int: int) -> None:
    _banner("PART 5 — THE AUDIT TRAIL (Art. 5(2) Accountability)")

    shell, theta, phi, harmonic = decode(address_int)
    addr = from_components(shell, theta, phi, harmonic)
    ttl_ns = compute_liminal_timeout(shell)

    print(f"""
Scenario
--------
  An auditor asks: "Show me the consent record for Alice's health data."

  In a traditional system, the answer requires:
    - The data record in the database
    - The ACL entry in the access control system
    - The consent record in the consent management platform
    - The retention policy in the policy management system
    - The audit log in the audit logging system
    - Cross-referencing all five to confirm they agree

  In RPP, the answer is one number:

    Address: {addr.to_hex()}

  From this single value, a conformant system can extract:

    Shell    = {addr.shell}   => Storage tier: {addr.shell_name}
               TTL: {ttl_ns:,} ns ({ttl_ns/1e9:.0f} seconds)
               Derived by: (address >> 26) & 0x3

    Theta    = {addr.theta:3d} => Data domain: {addr.sector_name} sector
               Derived by: (address >> 17) & 0x1FF

    Phi      = {addr.phi:3d} => Consent threshold: {addr.grounding_level}
               Any node with phi_min > {addr.phi} is a BARRIER
               Derived by: (address >> 8) & 0x1FF

    Harmonic = {addr.harmonic:3d} => Routing mode: Reflective (deliberate, auditable)
               Derived by: address & 0xFF

  No database JOIN.  No API call.  Bitwise AND and right-shift.
""")

    print()
    print("  GDPR Compliance Summary")
    print()

    # Each row: (requirement_lines, mechanism_lines, traditional_lines)
    # All cells are plain lists of strings — no embedded padding.
    col_req  = 34
    col_mech = 44
    col_trad = 42

    def _print_table_row(req_lines, mech_lines, trad_lines):
        n = max(len(req_lines), len(mech_lines), len(trad_lines))
        for i in range(n):
            r = req_lines[i]  if i < len(req_lines)  else ""
            m = mech_lines[i] if i < len(mech_lines) else ""
            t = trad_lines[i] if i < len(trad_lines) else ""
            print(f"  {r:<{col_req}}  {m:<{col_mech}}  {t}")

    header = f"  {'GDPR Requirement':<{col_req}}  {'RPP Mechanism':<{col_mech}}  {'Traditional Approach'}"
    sep    = f"  {'-'*col_req}  {'-'*col_mech}  {'-'*col_trad}"
    print(header)
    print(sep)

    rows = [
        (
            ["Art. 5(1)(e) — Storage limitation"],
            [f"Shell TTL in address bits [27:26];",
             f"Shell=1 => {ttl_ns/1e9:.0f}s enforced at every hop"],
            ["Separate cron job / TTL header;",
             "must run on every system"],
        ),
        (
            ["Art. 17 — Right to erasure"],
            ["phi shift => old address unroutable",
             "by arithmetic at every node"],
            ["DELETE cascade across all systems;",
             "miss one copy = breach"],
        ),
        (
            ["Art. 25 — Privacy by design"],
            ["phi enforced at every routing node",
             "without central coordinator"],
            ["ACL table lookup at access point only;",
             "back-channel routes bypass it"],
        ),
        (
            ["Art. 5(2) — Accountability"],
            ["Address encodes all four properties;",
             "one integer = complete record"],
            ["Separate audit log; requires",
             "reconciliation across systems"],
        ),
    ]

    for req_lines, mech_lines, trad_lines in rows:
        _print_table_row(req_lines, mech_lines, trad_lines)
        print(sep)

    print(f"""
  A note on scope
  ---------------
  This demonstration shows structural compliance properties — the RPP
  address architecture enforces storage limitation, consent thresholds,
  and routing-level erasure through arithmetic, not administrative procedure.

  "Structural compliance" means the architecture makes non-compliance
  harder than compliance.  It does not mean legal compliance is automatic.
  GDPR compliance still requires human processes: lawful basis assessment,
  data subject rights workflows, processor agreements, and DPA registration.

  What RPP eliminates is the most common failure mode: the systems-engineering
  gap between the consent policy and the enforcement point.  In RPP, there
  is no gap.  The consent level is the routing key.
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print()
    print("#" * 72)
    print("#" + "  RPP: GDPR Compliance by Design  ".center(70) + "#")
    print("#" + "  Structural enforcement through address arithmetic  ".center(70) + "#")
    print("#" * 72)

    # Part 1 returns the address components used by subsequent parts
    address_int, shell, theta, phi, harmonic = part1_data_creation()

    part2_authorised_access(address_int)
    part3_consent_revocation(address_int, shell, theta, harmonic)
    part4_address_expiry(address_int)
    part5_audit_trail(address_int)

    print("=" * 72)
    print("  Demo complete.")
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()
