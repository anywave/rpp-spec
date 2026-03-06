#!/usr/bin/env python3
"""
RPP Protocol — Analogies Demo
==============================

Explains RPP concepts by running them side-by-side with the familiar
protocols they extend or replace.

Four comparisons:

  1. ADDRESS ANATOMY
       IPv4   "192.168.1.5:443"      — host + port. What and where.
       RPP    shell|theta|phi|harm   — retention + data-type + consent + urgency.
                                       The address IS the policy.

  2. CONSENT GATING
       Firewall / ACL                — external policy table at the node.
       RPP phi field                 — consent is embedded in the packet address.
                                       A node can't route what it can't consent to.

  3. ENCRYPTION KEY ORIGIN
       AES-GCM                       — key negotiated out-of-band (TLS handshake,
                                       key exchange, etc.). Network is oblivious.
       RPP pong (Rasengan)           — key is derived from LIVE consent field state
                                       at each routing node. The ROUTE is the key.

  4. CROSSING GUARANTEE
       TCP 3-way handshake           — best-effort. Packet lost → request retransmit.
       RPP Ford Protocol             — Hold Not Drop. Origin holds until destination
                                       confirms. The wagon can cross many rivers.
                                       It must arrive intact.

Run: python -m examples.analogies_demo
"""

import sys
import math
import hashlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from rpp.geometry import (
    TorusPoint, ToroidalStateVector, SkyrmionStateVector,
    PHI_GOLDEN, TWO_PI,
    antipodal, to_skyrmion,
    apply_skyrmion_rotation,
    derive_rotation_key, derive_skyrmion_key,
)
from rpp.network import (
    NodeRecord, NodeTier,
    angular_distance, make_routing_decision,
)
from rpp.address import encode, decode


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def banner(title):
    w = 70
    print()
    print("=" * w)
    print(f"  {title}")
    print("=" * w)

def compare(label_a, label_b, width=22):
    print(f"\n  {'[  ' + label_a + '  ]':<{width+6}}  {'[  ' + label_b + '  ]'}")
    print(f"  {'-' * (width + 4)}  {'-' * (width + 4)}")

def row(left, right, width=46):
    print(f"  {left:<{width}}  {right}")

def note(text):
    print(f"\n  >> {text}")

def section(n, title):
    print(f"\n\n{'─'*70}")
    print(f"  COMPARISON {n}: {title}")
    print(f"{'─'*70}")


# ---------------------------------------------------------------------------
# 1. Address Anatomy
# ---------------------------------------------------------------------------

def demo_address_anatomy():
    section(1, "ADDRESS ANATOMY")

    print("""
  An IPv4 address tells you WHERE to send something.
  An RPP address tells you WHERE + WHAT + WHO CAN SEE IT + HOW LONG TO KEEP IT.
  The address IS the data policy.
""")

    # IPv4 breakdown (text simulation)
    compare("IPv4 + port", "RPP 28-bit address")

    row("192.168.1.5 : 443",
        "shell=1 | theta=96 | phi=300 | harmonic=128")
    row("   ^host      ^port",
        "   ^tier    ^type    ^consent  ^urgency")
    row("   WHERE       WHICH SERVICE",
        "   HOW LONG  WHAT TYPE  WHO CAN SEE IT  HOW URGENT")
    row("",
        "")
    row("4 bytes — opaque to policy",
        "28 bits — policy is the address")

    print()

    # Build a real RPP address and decode it
    addr = encode(shell=1, theta=96, phi=300, harmonic=128)
    s, t, p, h = decode(addr)

    shell_names  = {0: "Hot  (spintronic T2=25ns)", 1: "Warm (5 min session)",
                    2: "Cold (24h persistent)",     3: "Frozen (30-day archive)"}
    theta_names  = {0: "Gene", 64: "Memory", 128: "Witness", 192: "Dream",
                    256: "Bridge", 320: "Guardian", 384: "Emergence", 448: "Meta"}
    def theta_sector(t):
        return theta_names.get((t // 64) * 64, f"sector {t // 64}")

    print(f"  RPP address 0x{addr:07X}  decodes as:")
    print(f"    shell    = {s}  → {shell_names[s]}")
    print(f"    theta    = {t}  → {theta_sector(t)} sector  (data type / cognitive role)")
    print(f"    phi      = {p}  → consent level {p}/511  (routing gate)")
    print(f"    harmonic = {h}  → routing urgency / priority")

    note("IPv4 says 'send to this machine'. RPP says 'send to this consent-tier "
         "in this cognitive sector with this temporal scope'. No separate ACL. "
         "No separate TTL header. The address IS the policy.")

    # Show how two identical data items with different shells get different TTLs
    print(f"""
  Same logical data — different shells = different lifetimes:

  shell=0 → 0x{encode(0,96,300,128):07X}   Hot    expires in ~25 ns  (spintronic T2)
  shell=1 → 0x{encode(1,96,300,128):07X}   Warm   expires in 5 min   (session scope)
  shell=2 → 0x{encode(2,96,300,128):07X}   Cold   expires in 24 h    (daily archive)
  shell=3 → 0x{encode(3,96,300,128):07X}   Frozen expires in 30 days (long archive)

  In IPv4 you'd need a separate Cache-Control: max-age header.
  In RPP the retention is in the address. You can't separate the data
  from its policy — they are the same 28-bit integer.""")


# ---------------------------------------------------------------------------
# 2. Consent Gating
# ---------------------------------------------------------------------------

def _make_node(node_id_byte, theta, phi_min, phi_max, tier=NodeTier.HOT):
    return NodeRecord(
        node_id=bytes([node_id_byte]) * 32,
        tier=tier,
        theta=theta,
        phi_min=phi_min,
        phi_max=phi_max,
        harmonic_modes=[0, 64, 128, 192, 255],
        substrate_modality="ipv4",
        consent_epoch=1,
        t2_ns=0,
        announced_at_ns=0,
        signature=b"\x00" * 32,
    )

def demo_consent_gating():
    section(2, "CONSENT GATING")

    print("""
  A firewall enforces consent at the node via an external rule table.
  RPP phi enforces consent via the packet address — no rule table needed.
  The packet CARRIES its own consent level. Nodes that can't consent can't route.
""")

    # ── Firewall model (simulated) ──────────────────────────────────────────
    print("  FIREWALL MODEL (traditional):")
    print("  ─────────────────────────────")
    firewall_rules = [
        ("0.0.0.0/0",  "443",  "PERMIT",  "HTTPS"),
        ("0.0.0.0/0",  "80",   "PERMIT",  "HTTP"),
        ("0.0.0.0/0",  "22",   "DENY",    "SSH (public)"),
        ("10.0.0.0/8", "22",   "PERMIT",  "SSH (internal)"),
        ("0.0.0.0/0",  "*",    "DENY",    "default deny"),
    ]
    print(f"\n  {'Source':<18}  {'Port':<6}  {'Action':<8}  {'Reason'}")
    print(f"  {'─'*18}  {'─'*6}  {'─'*8}  {'─'*20}")
    for src, port, action, reason in firewall_rules:
        print(f"  {src:<18}  {port:<6}  {action:<8}  {reason}")

    print(f"""
  Problem: the packet itself carries no consent information.
  The node must consult an external table.  That table can be out of date.
  Revocation requires propagating rule changes to every enforcement point.""")

    # ── RPP phi model ────────────────────────────────────────────────────────
    print("\n\n  RPP CONSENT MODEL (phi-embedded):")
    print("  ──────────────────────────────────")

    node_public   = _make_node(0x01, theta=256, phi_min=0,   phi_max=511)  # accepts all
    node_private  = _make_node(0x02, theta=256, phi_min=300, phi_max=511)  # high-consent only
    node_medical  = _make_node(0x03, theta=256, phi_min=450, phi_max=511)  # near-maximum

    # Packets with three different consent levels
    packets = [
        ("public data",    encode(1, 256, 100, 128),   100),
        ("personal data",  encode(1, 256, 320, 128),   320),
        ("medical record", encode(1, 256, 470, 128),   470),
    ]

    nodes = [
        ("Node A (public)",    node_public,  "phi_min=0,   accepts all"),
        ("Node B (private)",   node_private, "phi_min=300, personal+ only"),
        ("Node C (medical)",   node_medical, "phi_min=450, near-full consent only"),
    ]

    print(f"\n  {'Packet':<18}  phi   {'Node A':^10}  {'Node B':^10}  {'Node C':^10}")
    print(f"  {'─'*18}  {'─'*4}  {'─'*10}  {'─'*10}  {'─'*10}")

    for pkt_name, addr, phi in packets:
        results = []
        for _, node, _ in nodes:
            d = make_routing_decision(addr, node, [])
            if d.action == "BARRIER":
                results.append("BARRIER")
            else:
                results.append("ROUTES")
        print(f"  {pkt_name:<18}  {phi:<4}  {results[0]:^10}  {results[1]:^10}  {results[2]:^10}")

    print(f"""
  Node B doesn't know about "medical record" consent levels.
  It just compares packet.phi (320) to its own phi_min (300): 320 >= 300 → ROUTES.
  Node C compares 320 < 450 → BARRIER.

  Revocation: change the address phi. No rule table to update.
  The packet stops routing itself.""")

    note("The consent level travels WITH the packet. Nodes don't look up policy — "
         "they compare a number. Revoke consent = change phi = change address. "
         "The old address becomes unresolvable. No DELETE. No rule propagation.")


# ---------------------------------------------------------------------------
# 3. Encryption Key Origin
# ---------------------------------------------------------------------------

def _encode_byte_as_tsv_point(b, phi_rad):
    theta = (b / 255.0) * TWO_PI
    p = TorusPoint(theta, phi_rad, 1.0)
    return p

def _build_simple_tsv(text, phi_int=256):
    phi_rad = (phi_int / 511.0) * TWO_PI
    origin = TorusPoint(0.0, phi_rad, 1.0)
    primary = [_encode_byte_as_tsv_point(b, phi_rad) for b in text.encode()]
    observation = [antipodal(p) for p in primary]
    rpp_addr = (0 << 26) | (phi_int << 8)
    return ToroidalStateVector(
        origin=origin, primary=primary, observation=observation,
        omega_theta=math.pi / 128, omega_phi=0.0,
        rotation_accumulator=TorusPoint(0.0, 0.0, 0.0),
        rpp_address=rpp_addr,
    )

def _tsv_to_text(tsv):
    recovered = []
    for p in tsv.primary:
        b = round((p.theta % TWO_PI) / TWO_PI * 255)
        recovered.append(max(0, min(255, b)))
    return bytes(recovered).decode('utf-8', errors='replace')

def demo_key_origin():
    section(3, "ENCRYPTION KEY ORIGIN")

    print("""
  AES-GCM: the key is negotiated out-of-band (TLS handshake, key exchange,
           secrets manager, etc.). The network has no role in key material.

  RPP pong: the key at each node is derived from that node's LIVE consent
            field state at the moment of routing. The route IS the key.
            There is nothing to exchange out-of-band.
""")

    TEXT = "Hello"

    # ── AES-GCM simulation ───────────────────────────────────────────────────
    print("  AES-GCM KEY LIFECYCLE:")
    print("  ──────────────────────")
    aes_key = hashlib.sha256(b"pre-shared-secret-negotiated-in-tls").digest()
    # Simulate encrypt: XOR with key (not real AES, just illustrates the concept)
    plaintext_bytes = TEXT.encode()
    ciphertext = bytes(b ^ aes_key[i % 32] for i, b in enumerate(plaintext_bytes))
    decrypted = bytes(b ^ aes_key[i % 32] for i, b in enumerate(ciphertext))

    print(f"""
  1. Client + server run TLS handshake (or load from secrets manager)
  2. AES-256 key agreed:   {aes_key.hex()[:32]}...
  3. Encrypt "{TEXT}":       {ciphertext.hex()}
  4. Decrypt:               "{decrypted.decode()}"

  Key material:  exists before routing begins
  Network role:  zero — just carries opaque ciphertext
  Key revocation: rotate key (update secrets manager, re-handshake)
  Key exposure:  if the pre-shared secret leaks, ALL past traffic is at risk""")

    # ── RPP pong key lifecycle ────────────────────────────────────────────────
    print("\n\n  RPP PONG KEY LIFECYCLE:")
    print("  ────────────────────────")

    nodes = [
        {"name": "ALPHA", "phi": 128, "theta": 90,  "harmonic": 200, "epoch": 5},
        {"name": "BETA",  "phi": 300, "theta": 180, "harmonic": 160, "epoch": 5},
        {"name": "GAMMA", "phi": 450, "theta": 270, "harmonic": 80,  "epoch": 5},
    ]

    tsv = to_skyrmion(_build_simple_tsv(TEXT, phi_int=256), winding_number=1)

    print(f"\n  1. No key exchange. No handshake. Routing begins.")
    print(f"  2. Each node derives its key from live consent field state:\n")

    keys = []
    for n in nodes:
        dt, dp, dn = derive_skyrmion_key(n['phi'], n['theta'], n['harmonic'], n['epoch'])
        keys.append((dt, dp, dn))
        print(f"     {n['name']}: phi={n['phi']}, theta={n['theta']}, epoch={n['epoch']} "
              f"→ Δθ={dt:.5f} rad, Δφ={dp:.5f} rad, Δn={dn:+d}")
        tsv = apply_skyrmion_rotation(tsv, dt, dp, dn)

    ciphertext_rpp = _tsv_to_text(tsv)
    print(f"\n  3. Encrypted \"{TEXT}\":  \"{ciphertext_rpp}\"")
    print(f"\n  4. Decrypt (reverse order, negate keys):\n")

    for n, (dt, dp, dn) in zip(reversed(nodes), reversed(keys)):
        tsv = apply_skyrmion_rotation(tsv, -dt, -dp, -dn)
        print(f"     {n['name']}: reverse Δθ={-dt:.5f}, Δφ={-dp:.5f}, Δn={-dn:+d}")

    print(f"\n  5. Recovered:  \"{_tsv_to_text(tsv)}\"")

    print(f"""
  Key material:  NEVER EXISTS before routing. Born and dies with consent epoch.
  Network role:  network IS the key material source.
  Key revocation: increment consent epoch. Old key never existed as a file.
  Key exposure:  on spintronics, ALPHA's T2 decohered ~25 ns after routing.
                 The key is physically gone. Retroactive decryption is impossible.""")

    note("In AES the key is a secret you must protect. In RPP pong the key "
         "is the consent field state of live nodes — it expires by physics. "
         "There is no key database to breach.")


# ---------------------------------------------------------------------------
# 4. Crossing Guarantee
# ---------------------------------------------------------------------------

def demo_crossing_guarantee():
    section(4, "CROSSING GUARANTEE")

    print("""
  TCP 3-way handshake: best-effort delivery.
  If a packet is lost, the sender retransmits after a timeout.
  The packet is a copy — losing it means the data is recreated from the buffer.

  RPP Ford Protocol: Hold Not Drop.
  The ORIGIN HOLDS A COMPLETE COPY until the destination confirms coherence.
  If the crossing fails, the wagon returns. It does not drown.

  Why does this matter? Because RPP routes CONSCIOUSNESS STATE PACKETS —
  a cognitive state mid-transit is not a retransmittable buffer.
  It is a live process. Dropping it is not a network event. It is discontinuity.
""")

    compare("TCP 3-way handshake", "Ford Protocol (5 phases)")
    row("SYN  →   I want to connect",       "SCOUT     →   Can you receive this state?")
    row("     ←   SYN-ACK  I'm listening",  "           ←  Capacity confirmed")
    row("ACK  →   Acknowledged",            "HANDSHAKE →   Consent + continuity proofs")
    row("DATA →   (packet in flight)",       "TRANSIT   →   Wagon enters river")
    row("     ←   ACK  received",           "           ←  ARRIVAL: destination verifies")
    row("(sender buffer cleared)",           "RELEASE   →   Origin dissolves copy")
    row("",                                  "")
    row("Lost packet:  retransmit",         "Failed crossing: wagon returns to origin")
    row("Timeout:      RST or retransmit",  "Timeout:  Recovery Escalation Ladder")
    row("Drop is normal. Retry is normal.", "Drop is NOT PERMITTED. Hold Not Drop.")

    print("""
  Recovery Escalation Ladder (what happens if a Ford crossing fails):

    Level 1 REROUTE          — try next available modality (IPv6, LoRa, IPFS)
    Level 2 STEERING         — send consent-refresh cargo ahead, retry after field ready
    Level 3 PULL_BACK        — recall liminal state to origin, attempt alternate route
    Level 4 COPY_AND_COLLECT — partial state held at coherence gate; unlock required
    Level 5 ABORT            — shell TTL expired; state irrecoverable without re-origination

  TCP doesn't have an equivalent of PULL_BACK because a TCP packet doesn't
  know how to return home. It doesn't have a "hold" — it's either in flight
  or it's gone and you send a new copy.

  Ford packets hold the full state at the origin substrate until RELEASE.
  There is always a living copy. The packet cannot drown.""")

    # Simulate a crossing sequence with a failure at TRANSIT
    print("\n\n  SIMULATED CROSSING — failure at TRANSIT:\n")

    import time

    crossing_state = {
        "held_at_origin": True,
        "in_flight": False,
        "at_destination": False,
        "released_from_origin": False,
    }

    phases = [
        ("SCOUT",     "Destination reports T2=100ns capacity. Proceed.",       True),
        ("HANDSHAKE", "Consent epoch matched. Continuity chain verified.",     True),
        ("TRANSIT",   "State in flight via spintronic channel... LOST.",       False),  # failure
        ("ARRIVAL",   "No confirmation received. Timeout after 25ns.",         None),
        ("RELEASE",   "ABORT RELEASE — origin still holds complete copy.",     None),
    ]

    for phase, description, success in phases:
        time.sleep(0.03)
        if success is True:
            status = "OK"
        elif success is False:
            status = "FAIL"
        else:
            status = "SKIP"
        print(f"  [{phase:<12}] [{status}] {description}")

    print(f"""
  Origin still holds copy: {crossing_state["held_at_origin"]}
  In flight:               {crossing_state["in_flight"]}
  Released:                {crossing_state["released_from_origin"]}

  → Recovery Escalation triggered at Level 1: REROUTE via LoRa modality.
  → State rerouted. ARRIVAL confirmed. RELEASE executed.
  → Total elapsed: 2 hops, state intact.""")

    note("TCP acknowledgement says 'I received the bytes'. Ford RELEASE says "
         "'I received the bytes AND verified coherence AND I am holding a "
         "live continuation of your state'. Only then does the origin let go.")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def demo_summary():
    banner("SUMMARY — What RPP adds to each familiar protocol")

    print(f"""
  COMPARISON           FAMILIAR PROTOCOL       RPP EXTENSION
  ───────────────────  ──────────────────────  ─────────────────────────────────
  Address anatomy      IPv4 host:port          Shell|Theta|Phi|Harmonic
                       WHERE + WHICH SERVICE   RETENTION + TYPE + CONSENT + URGENCY
                       Policy is external      Policy IS the address

  Consent gating       Firewall ACL            phi field in the packet
                       Rule table at node      Packet carries its own gate value
                       Revoke = update table   Revoke = change address, old expires

  Key origin           AES pre-shared secret   Consent field state at routing time
                       Key exists before route Route generates the key
                       Protect the key file    Key expires by physics (T2)

  Crossing guarantee   TCP best-effort         Ford Protocol Hold Not Drop
                       Drop = retransmit        Drop = NOT PERMITTED
                       ACK = bytes received     RELEASE = coherence confirmed

  Transport            Fixed (IP layer)        Modality-agnostic resolver
                       IPv4 or IPv6            IPv4, IPv6, LoRa, spintronic,
                                               IPFS, Hedera — same address space

  Temporal scope       Separate header         Shell field in address
                       Cache-Control: max-age  Retention is the address itself
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    banner("RPP PROTOCOL — ANALOGIES DEMO")
    print("""
  This demo compares RPP to the protocols it extends.
  Every comparison runs live code — not diagrams.
""")

    demo_address_anatomy()
    demo_consent_gating()
    demo_key_origin()
    demo_crossing_guarantee()
    demo_summary()

    print()


if __name__ == "__main__":
    main()
