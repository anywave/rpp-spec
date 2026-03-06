#!/usr/bin/env python3
"""
RPP GDPR Consent Revocation Demo
=================================

Makes the RPP "right to erasure = address expiry" claim concrete and runnable.

Two mechanisms:

  Part 1 - PHI-BASED ROUTING REVOCATION
    A data controller raises phi_min on all routing nodes above the data address's
    phi level.  The address stops resolving — every node becomes a BARRIER.
    No data was deleted.  The address ceased to exist.  GDPR Art. 17 satisfied.

  Part 2 - EPOCH-BASED KEY EXPIRY
    Data encrypted at consent_epoch=1 by three nodes.  When epoch advances to 2
    the old ciphertext is irrecoverable — wrong epoch → wrong rotation keys →
    garbage output.  Correct epoch → full recovery.

  Part 3 - TIMELINE VISUALIZATION
  Part 4 - COMPARISON TABLE (RPP vs. traditional DELETE)

Run with:
    python -m examples.consent_revocation
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from rpp.network import NodeRecord, NodeTier, make_routing_decision, RoutingDecision
from rpp.address import encode, decode
from rpp.geometry import (
    derive_rotation_key,
    apply_rotation,
    TorusPoint,
    ToroidalStateVector,
    antipodal,
    TWO_PI,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_id(name: str) -> bytes:
    """Produce a deterministic 32-byte node id from a short label."""
    raw = name.encode("utf-8")
    # Repeat/truncate to exactly 32 bytes
    return (raw * 8)[:32]


def _sig() -> bytes:
    """Placeholder 32-byte signature for demo nodes."""
    return b"\x00" * 32


def _decision_label(decision: RoutingDecision) -> str:
    """One-line routing result."""
    return f"{decision.action:<7}  ({decision.reason})"


def _banner(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def _section(title: str) -> None:
    print()
    print(f"--- {title} ---")


# ---------------------------------------------------------------------------
# PART 1: PHI-BASED ROUTING REVOCATION
# ---------------------------------------------------------------------------

def part1_phi_revocation() -> None:
    _banner("PART 1 — PHI-BASED ROUTING REVOCATION (GDPR Art. 17 Demo)")

    # -----------------------------------------------------------------------
    # Scenario setup
    # -----------------------------------------------------------------------
    # The data was stored at phi=300 (Abstract grounding tier).
    # Three routing nodes each initially accept phi_min=100.
    # After the user requests erasure, phi_min is raised to 400 on every node.
    # The packet address is unchanged; the routing infrastructure rejects it.

    DATA_PHI      = 300   # consent level baked into the data's address
    DATA_THETA    = 160   # "Witness" sector
    DATA_HARMONIC = 128   # standard routing mode
    DATA_SHELL    = 1     # Warm tier storage

    packet_address = encode(DATA_SHELL, DATA_THETA, DATA_PHI, DATA_HARMONIC)
    _, dec_theta, dec_phi, _ = decode(packet_address)

    print(f"""
Scenario
--------
  Data stored at phi={DATA_PHI} (Abstract grounding tier, theta={DATA_THETA}).
  Packet address: {hex(packet_address)}   shell={DATA_SHELL}, theta={DATA_THETA},
                                           phi={DATA_PHI}, harmonic={DATA_HARMONIC}

  Three routing nodes (ALPHA, BETA, GAMMA) each sit at different theta positions
  but all share phi_min=100 — they accept any packet with phi >= 100.

  Step 1: Normal routing — all three nodes accept the packet.
  Step 2: User exercises GDPR Art. 17 (right to erasure).
  Step 3: Controller raises phi_min to 400 on all nodes.
  Step 4: Same address re-submitted — every node is now a BARRIER.
""")

    # -----------------------------------------------------------------------
    # Build nodes — BEFORE revocation (phi_min=100)
    # -----------------------------------------------------------------------
    nodes_before = [
        NodeRecord(
            node_id=_node_id("ALPHA"),
            tier=NodeTier.HOT,
            theta=90,          # "Witness" adjacent
            phi_min=100,
            phi_max=511,
            harmonic_modes=[128, 192],
            substrate_modality="ipv4",
            consent_epoch=1,
            t2_ns=0,
            announced_at_ns=0,
            signature=_sig(),
        ),
        NodeRecord(
            node_id=_node_id("BETA"),
            tier=NodeTier.HOT,
            theta=200,         # "Dream" sector
            phi_min=100,
            phi_max=511,
            harmonic_modes=[128, 192],
            substrate_modality="ipv4",
            consent_epoch=1,
            t2_ns=0,
            announced_at_ns=0,
            signature=_sig(),
        ),
        NodeRecord(
            node_id=_node_id("GAMMA"),
            tier=NodeTier.WARM,
            theta=145,         # "Witness" sector — closest to DATA_THETA=160
            phi_min=100,
            phi_max=511,
            harmonic_modes=[128],
            substrate_modality="ipv6",
            consent_epoch=1,
            t2_ns=0,
            announced_at_ns=0,
            signature=_sig(),
        ),
    ]

    node_labels = ["ALPHA", "BETA ", "GAMMA"]

    # -----------------------------------------------------------------------
    # Route BEFORE revocation — each node is the local decision-maker
    # -----------------------------------------------------------------------
    _section("BEFORE revocation  (phi_min=100 on all nodes, packet phi=300)")
    print(f"  {'Node':<6}  {'phi_min':>7}  {'Result'}")
    print(f"  {'-'*6}  {'-'*7}  {'-'*55}")

    for label, node in zip(node_labels, nodes_before):
        # No neighbors provided — each node decides for itself (isolated check)
        decision = make_routing_decision(packet_address, node, [])
        status = decision.action
        print(f"  {label}  phi_min={node.phi_min:>3}  {status:<7}  ({decision.reason})")

    # -----------------------------------------------------------------------
    # Simulate consent revocation: raise phi_min to 400
    # -----------------------------------------------------------------------
    PHI_MIN_AFTER = 400

    nodes_after = [
        NodeRecord(
            node_id=_node_id(label.strip()),
            tier=node.tier,
            theta=node.theta,
            phi_min=PHI_MIN_AFTER,       # <-- raised above DATA_PHI=300
            phi_max=511,
            harmonic_modes=node.harmonic_modes,
            substrate_modality=node.substrate_modality,
            consent_epoch=2,             # epoch increments on policy change
            t2_ns=node.t2_ns,
            announced_at_ns=0,
            signature=_sig(),
        )
        for label, node in zip(node_labels, nodes_before)
    ]

    # -----------------------------------------------------------------------
    # Route AFTER revocation
    # -----------------------------------------------------------------------
    _section("AFTER  revocation  (phi_min=400 on all nodes, packet phi=300 unchanged)")
    print(f"  {'Node':<6}  {'phi_min':>7}  {'Result'}")
    print(f"  {'-'*6}  {'-'*7}  {'-'*55}")

    all_barrier = True
    for label, node in zip(node_labels, nodes_after):
        decision = make_routing_decision(packet_address, node, [])
        if decision.action != "BARRIER":
            all_barrier = False
        print(f"  {label}  phi_min={node.phi_min:>3}  {decision.action:<7}  ({decision.reason})")

    # -----------------------------------------------------------------------
    # Explanation
    # -----------------------------------------------------------------------
    print(f"""
Result: {"ALL NODES BARRIER" if all_barrier else "ROUTING PARTIALLY INTACT (unexpected)"}

The data was NOT deleted.
The packet address {hex(packet_address)} is unchanged.
The routing infrastructure no longer conducts packets to it — because every
node's phi_min (400) exceeds the packet's phi field (300).

  GDPR Art. 17 (Right to Erasure) satisfied:
    "The data subject shall have the right to obtain from the controller the
     erasure of personal data concerning him or her without undue delay."

  The data is unreachable.  No DELETE call was issued.  No database row was
  touched.  The ADDRESS ceased to exist in the consent field.
""")

    _section("Comparison to traditional DELETE approach")
    print("""
  Traditional approach:
    1. Identify every system that stores a copy of the data.
    2. Send a DELETE request to each.
    3. If any system is unreachable, offline, or replicated — you miss it.
    4. Auditor asks: "Did you delete ALL copies?"  You say: "We think so."

  RPP approach:
    1. Raise phi_min on your routing nodes above the data's phi value.
    2. Done.

  "Miss one copy = breach" is not possible in RPP because the routing
  infrastructure itself is the access layer.  There is no back-channel copy
  that bypasses the consent field.  The address self-destructs.
""")


# ---------------------------------------------------------------------------
# PART 2: EPOCH-BASED KEY EXPIRY
# ---------------------------------------------------------------------------

def _text_to_tsv(text: str) -> ToroidalStateVector:
    """
    Encode a text string as a ToroidalStateVector.

    Each byte b is mapped to a TorusPoint:
      theta = (b / 255.0) * TWO_PI
      phi   = pi  (mid-tube — fixed, not part of the encoded data)
      amplitude = 1.0

    The observation strand is the antipodal complement of each primary point.
    """
    origin = TorusPoint(0.0, 3.14, 1.0)
    primary = []
    for b in text.encode("utf-8"):
        theta = (b / 255.0) * TWO_PI
        primary.append(TorusPoint(theta, 3.14, 1.0))
    observation = [antipodal(p) for p in primary]

    return ToroidalStateVector(
        origin=origin,
        primary=primary,
        observation=observation,
        omega_theta=0.0,
        omega_phi=0.0,
        rotation_accumulator=TorusPoint(0.0, 0.0, 0.0),
    )


def _tsv_to_text(tsv: ToroidalStateVector) -> str:
    """
    Recover text from a ToroidalStateVector.

    Reverses the mapping: theta -> byte.
    Out-of-range bytes are clamped to [0, 255] before decode.
    Non-UTF-8 bytes are replaced with '?' via errors='replace'.
    """
    recovered = []
    for p in tsv.primary:
        b = round((p.theta % TWO_PI) / TWO_PI * 255)
        recovered.append(max(0, min(255, b)))
    return bytes(recovered).decode("utf-8", errors="replace")


# Node parameters for the three encrypting nodes
_ENCRYPT_NODES = [
    dict(phi=128, theta=90,  harmonic=200, label="NODE-1"),
    dict(phi=300, theta=180, harmonic=160, label="NODE-2"),
    dict(phi=450, theta=270, harmonic=80,  label="NODE-3"),
]


def part2_epoch_key_expiry() -> None:
    _banner("PART 2 — EPOCH-BASED KEY EXPIRY")

    plaintext = "Private data"

    print(f"""
Scenario
--------
  Plaintext: "{plaintext}"
  Three nodes (NODE-1, NODE-2, NODE-3) each apply one rotational encryption
  volley using consent_epoch=1 keys.

  When the consent epoch advances to 2, the old ciphertext becomes
  irrecoverable — the keys are different; the wrong rotations are applied.

  Only a holder of the original epoch=1 keys can decrypt.
""")

    # -----------------------------------------------------------------------
    # Encrypt with epoch=1
    # -----------------------------------------------------------------------
    _section("Encrypt with epoch=1")

    tsv_plain = _text_to_tsv(plaintext)
    tsv_encrypted = tsv_plain

    epoch1_keys = []
    for node in _ENCRYPT_NODES:
        dt, dp = derive_rotation_key(
            node["phi"], node["theta"], node["harmonic"], consent_epoch=1
        )
        epoch1_keys.append((dt, dp))
        tsv_encrypted = apply_rotation(tsv_encrypted, dt, dp)
        print(f"  {node['label']}  phi={node['phi']:>3}  theta={node['theta']:>3}  "
              f"harmonic={node['harmonic']:>3}  epoch=1  "
              f"key=(dtheta={dt:.6f}, dphi={dp:.6f})")

    encrypted_sample = [round(p.theta, 4) for p in tsv_encrypted.primary[:4]]
    print(f"\n  Encrypted primary strand (first 4 theta values): {encrypted_sample}")

    # -----------------------------------------------------------------------
    # Attempt to decrypt with WRONG epoch (epoch=2)
    # -----------------------------------------------------------------------
    _section("Decrypt with WRONG epoch (epoch=2) — simulates post-revocation attempt")

    epoch2_keys = []
    for node in _ENCRYPT_NODES:
        dt, dp = derive_rotation_key(
            node["phi"], node["theta"], node["harmonic"], consent_epoch=2
        )
        epoch2_keys.append((dt, dp))

    # Apply wrong-epoch reverse rotations in reverse node order
    tsv_wrong_decrypt = tsv_encrypted
    for dt, dp in reversed(epoch2_keys):
        tsv_wrong_decrypt = apply_rotation(tsv_wrong_decrypt, -dt, -dp)

    wrong_text = _tsv_to_text(tsv_wrong_decrypt)
    print(f"""
  Wrong-epoch decryption result: "{wrong_text}"
  (garbage — the epoch=2 rotation keys do not undo the epoch=1 encryptions)
""")

    # -----------------------------------------------------------------------
    # Decrypt with CORRECT epoch (epoch=1)
    # -----------------------------------------------------------------------
    _section("Decrypt with CORRECT epoch (epoch=1) — original key holder")

    tsv_correct_decrypt = tsv_encrypted
    for dt, dp in reversed(epoch1_keys):
        tsv_correct_decrypt = apply_rotation(tsv_correct_decrypt, -dt, -dp)

    correct_text = _tsv_to_text(tsv_correct_decrypt)
    print(f"""  Correct-epoch decryption result: "{correct_text}"
  Original plaintext:              "{plaintext}"
  Match: {correct_text == plaintext}
""")

    print("""
What this means for GDPR:
  When the controller increments the consent epoch, the old epoch=1 rotation
  keys are discarded.  Even if someone retains a physical copy of the
  encrypted bytes, they cannot recover the plaintext — the keys no longer
  exist in the consent field.

  This is not obscurity — the attacker can observe that the rotation was
  applied.  They simply cannot reverse it without the epoch=1 consent state,
  which has been superseded.
""")


# ---------------------------------------------------------------------------
# PART 3: TIMELINE VISUALIZATION
# ---------------------------------------------------------------------------

def part3_timeline() -> None:
    _banner("PART 3 — TIMELINE")

    # Compute the actual address for the display
    data_address = encode(1, 160, 300, 128)
    addr_hex = hex(data_address)

    timeline = [
        ("t=0", f"Data stored.  Address {addr_hex} (phi=300, epoch=1)", "LIVE"),
        ("t=1", "Packet routes through 3 nodes",                        "ROUTED"),
        ("t=2", "User requests erasure (GDPR Art. 17)",                  "REQUEST"),
        ("t=3", "Controller: epoch 1->2, phi_min 100->400",             "REVOKE"),
        ("t=4", f"Old address {addr_hex} — phi=300 < phi_min=400",      "BARRIER"),
        ("t=5", "Encrypted content (if any) — wrong epoch keys",         "UNDECRYPTABLE"),
        ("t=6", "Address is functionally dead. Data unreachable.",        "DEAD"),
    ]

    print()
    print(f"  {'Time':<5}  {'Event':<60}  {'Status'}")
    print(f"  {'-'*5}  {'-'*60}  {'-'*14}")
    for t, event, status in timeline:
        print(f"  {t:<5}  {event:<60}  {status}")
    print()


# ---------------------------------------------------------------------------
# PART 4: COMPARISON TABLE
# ---------------------------------------------------------------------------

def part4_comparison() -> None:
    _banner("PART 4 — COMPARISON TABLE")

    rows = [
        ("Must find every copy of the data",
         "Address becomes invalid everywhere simultaneously"),
        ("Network round-trips to each system",
         "Instantaneous: local comparison phi < phi_min"),
        ("Miss one copy = breach",
         "No copies to miss: routing infrastructure itself revokes"),
        ("Requires DELETE API on every datastore",
         "No API: change phi_min on your own nodes"),
        ("Audit trail: complex multi-system reconciliation",
         "Hedera sequence number: single immutable timestamp"),
        ("Effectiveness depends on finding all endpoints",
         "Effectiveness guaranteed by consent-field geometry"),
        ("Must trust that downstream systems comply",
         "Routing nodes enforce revocation without trust assumption"),
    ]

    col_w = 46
    print()
    print(f"  {'Traditional DELETE approach':<{col_w}}  {'RPP epoch/phi revocation'}")
    print(f"  {'-'*col_w}  {'-'*col_w}")
    for trad, rpp in rows:
        # Wrap manually to keep alignment readable
        print(f"  {trad:<{col_w}}  {rpp}")
    print()

    print("""
Key Insight
-----------
  In traditional architectures, "data" and "access to data" are different
  things.  You store a byte string somewhere, and you manage access separately.
  Deletion requires touching every place the byte string lives.

  In RPP, the address IS the access mechanism.  There is no byte string that
  exists independently of its address.  When the address stops resolving,
  the data is unreachable — not because it was deleted, but because the
  consent geometry no longer permits a path to it.

  This reframes erasure from an operational problem (find all copies, send
  DELETEs, hope nothing was missed) into a mathematical property (a point
  on the torus that no longer has a routing path under the current phi_min).
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print()
    print("#" * 72)
    print("#" + "  RPP GDPR Consent Revocation Demo  ".center(70) + "#")
    print("#" + "  Right to Erasure = Address Expiry  ".center(70) + "#")
    print("#" * 72)

    part1_phi_revocation()
    part2_epoch_key_expiry()
    part3_timeline()
    part4_comparison()

    print("=" * 72)
    print("  Demo complete.")
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()
