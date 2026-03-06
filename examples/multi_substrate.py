#!/usr/bin/env python3
"""
RPP: Transport-Modality-Agnostic Routing
=========================================
Demonstrates that the same RPP address routes over UDP/IPv4, LoRa, IPFS,
and Hedera Hashgraph. No external dependencies — transports are mocked
to show the architecture, not the wiring.

Usage:
    python -m examples.multi_substrate
"""
import sys, struct, base64, hashlib
sys.stdout.reconfigure(encoding='utf-8')

from rpp.address import encode, decode, from_components
from rpp.network import make_routing_decision, NodeRecord, NodeTier, RoutingDecision


# ---------------------------------------------------------------------------
# Sentinel exception — stands in for a real network layer error
# ---------------------------------------------------------------------------

class TransportUnavailable(Exception):
    """Raised by a transport when it cannot deliver the packet."""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _node_id(tag: str) -> bytes:
    """Deterministic 32-byte node ID from a string tag."""
    return hashlib.sha256(tag.encode()).digest()


def _hex_bytes(data: bytes, max_shown: int = 6) -> str:
    """Format bytes as a short hex list, truncating long payloads."""
    shown = data[:max_shown]
    parts = [f"0x{b:02X}" for b in shown]
    suffix = ", ..." if len(data) > max_shown else ""
    return "[" + ", ".join(parts) + suffix + "]"


# ---------------------------------------------------------------------------
# Part 1: Transport classes — four substrates, one address
# ---------------------------------------------------------------------------

class UDPIPv4Transport:
    """
    Serializes an RPP address into a UDP/IPv4 envelope.

    Mapping (illustrative — not real routing):
        dst_ip  = 192.168.{theta // 2}.{phi}
        port    = harmonic * 100
        payload = 4-byte big-endian of the raw 28-bit address integer
    """

    def serialize(self, shell: int, theta: int, phi: int, harmonic: int) -> dict:
        raw = encode(shell, theta, phi, harmonic)
        dst_ip   = f"192.168.{theta // 2}.{phi}"
        port     = harmonic * 100
        payload  = struct.pack(">I", raw)
        return {
            "substrate":     "IPv4/UDP",
            "endpoint":      f"{dst_ip}:{port}",
            "payload_bytes": payload,
            "latency_class": "sub-ms",
        }

    def is_available(self) -> bool:
        return True   # mocked as always-up for baseline


class UDPIPv4TransportFailing(UDPIPv4Transport):
    """Same as UDPIPv4Transport but raises TransportUnavailable on every call."""

    def is_available(self) -> bool:
        return False

    def serialize(self, shell: int, theta: int, phi: int, harmonic: int) -> dict:
        raise TransportUnavailable("IPv4 link is down (simulated failure)")


class LoRaTransport:
    """
    Serializes an RPP address into a LoRa LPWAN frame.

    Mapping:
        payload  = 4-byte big-endian of the raw 28-bit address integer
                   (identical wire bits; the chip's RF modem provides the envelope)
        SF       = 7 + (shell % 6)   — spreading factor scales with shell depth
        BW       = 125 kHz           — standard LoRaWAN bandwidth
        channel  = (theta // 43) + 1 — 12 channels across 512-wide theta space
    """

    def serialize(self, shell: int, theta: int, phi: int, harmonic: int) -> dict:
        raw     = encode(shell, theta, phi, harmonic)
        payload = struct.pack(">I", raw)
        sf      = 7 + (shell % 6)
        channel = (theta // 43) + 1
        return {
            "substrate":     "LoRa",
            "endpoint":      f"SF{sf} BW125 CH{channel}",
            "payload_bytes": payload,
            "latency_class": "seconds",
        }

    def is_available(self) -> bool:
        return True


class IPFSTransport:
    """
    Serializes an RPP address as a simulated IPFS CIDv1.

    Real CIDv1 = multicodec + multihash of content. Here we simulate the
    encoding by constructing a deterministic base32-like string from the
    address fields, prefixed with "bafyrei" (the real CIDv1/dag-pb prefix).

    The 4-byte payload is the big-endian raw address — the same as LoRa.
    IPFS delivers it as a named chunk; the CID is the routing handle.
    """

    _B32_ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"

    def _encode_b32(self, n: int, width: int) -> str:
        """Encode integer n as a zero-padded base-32 string of given width."""
        chars = []
        for _ in range(width):
            chars.append(self._B32_ALPHABET[n & 0x1F])
            n >>= 5
        return "".join(reversed(chars))

    def serialize(self, shell: int, theta: int, phi: int, harmonic: int) -> dict:
        raw     = encode(shell, theta, phi, harmonic)
        payload = struct.pack(">I", raw)
        # Simulated CID: prefix + base32(theta) + base32(phi) + base32(harmonic)
        cid = "bafyrei" + self._encode_b32(theta, 4) + self._encode_b32(phi, 4) + self._encode_b32(harmonic, 3)
        return {
            "substrate":     "IPFS",
            "endpoint":      cid,
            "payload_bytes": payload,
            "latency_class": "variable (DHT lookup)",
        }

    def is_available(self) -> bool:
        return True


class HederaTransport:
    """
    Serializes an RPP address as a Hedera Consensus Service (HCS) message.

    Mapping:
        topic_id        = 0.0.{theta}
        message_sequence = {phi}.{harmonic}
        payload          = 4-byte big-endian raw address (submitted as HCS message body)

    In production this would be a real HCS SubmitMessage transaction.
    """

    def serialize(self, shell: int, theta: int, phi: int, harmonic: int) -> dict:
        raw     = encode(shell, theta, phi, harmonic)
        payload = struct.pack(">I", raw)
        topic   = f"0.0.{theta}"
        seq     = f"{phi}.{harmonic}"
        return {
            "substrate":     "Hedera",
            "endpoint":      f"{topic} seq {seq}",
            "payload_bytes": payload,
            "latency_class": "3-5 s (consensus)",
        }

    def is_available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Part 2: SubstrateResolver — consent gate + substrate dispatch
# ---------------------------------------------------------------------------

_SUBSTRATE_HANDLERS = {
    "IPv4":   UDPIPv4Transport(),
    "LoRa":   LoRaTransport(),
    "IPFS":   IPFSTransport(),
    "Hedera": HederaTransport(),
}

PHI_GATE = 100   # phi < PHI_GATE → DENY on ALL substrates


class SubstrateResolver:
    """
    Resolves a 28-bit RPP address to a transport-layer envelope.

    The consent gate (phi field) is evaluated once, before any substrate
    logic runs.  There is no per-substrate ACL — the address itself
    carries the consent signal.
    """

    def resolve(self, address_int: int, substrate: str) -> dict:
        """
        Resolve address_int over a single named substrate.

        Returns a dict with keys:
            allowed       bool
            substrate     str
            endpoint      str or None
            packet_bytes  bytes or None
            reason        str
        """
        shell, theta, phi, harmonic = decode(address_int)

        # Consent gate — encoded in the phi field of the address itself
        if phi < PHI_GATE:
            return {
                "allowed":      False,
                "substrate":    substrate,
                "endpoint":     None,
                "packet_bytes": None,
                "reason":       f"DENIED — phi={phi} below gate ({PHI_GATE})",
            }

        handler = _SUBSTRATE_HANDLERS.get(substrate)
        if handler is None:
            return {
                "allowed":      False,
                "substrate":    substrate,
                "endpoint":     None,
                "packet_bytes": None,
                "reason":       f"Unknown substrate: {substrate!r}",
            }

        envelope = handler.serialize(shell, theta, phi, harmonic)
        return {
            "allowed":      True,
            "substrate":    envelope["substrate"],
            "endpoint":     envelope["endpoint"],
            "packet_bytes": envelope["payload_bytes"],
            "reason":       "OK",
        }

    def resolve_with_fallback(self, address_int: int, priority_order: list) -> list:
        """
        Try substrates in priority_order.  On TransportUnavailable, mark as
        FAILED and continue.  Stop at the first success; remaining entries
        are STANDBY.

        Returns a list of result dicts, one per substrate in priority_order.
        Each dict has: substrate, status, endpoint, packet_bytes.
        """
        shell, theta, phi, harmonic = decode(address_int)

        # Build the handler map with the failing IPv4 for simulation
        failing_handlers = dict(_SUBSTRATE_HANDLERS)
        failing_handlers["IPv4"] = UDPIPv4TransportFailing()

        delivered = False
        results   = []

        for substrate in priority_order:
            handler = failing_handlers.get(substrate)
            if handler is None:
                results.append({
                    "substrate":    substrate,
                    "status":       "UNKNOWN",
                    "endpoint":     "—",
                    "packet_bytes": None,
                })
                continue

            if delivered:
                # Already succeeded — remaining substrates are standby
                try:
                    env = handler.serialize(shell, theta, phi, harmonic)
                    results.append({
                        "substrate":    substrate,
                        "status":       "STANDBY",
                        "endpoint":     env["endpoint"],
                        "packet_bytes": env["payload_bytes"],
                    })
                except TransportUnavailable:
                    results.append({
                        "substrate":    substrate,
                        "status":       "STANDBY",
                        "endpoint":     "(unavailable)",
                        "packet_bytes": None,
                    })
                continue

            # Attempt delivery
            try:
                env = handler.serialize(shell, theta, phi, harmonic)
                results.append({
                    "substrate":    substrate,
                    "status":       "OK",
                    "endpoint":     env["endpoint"],
                    "packet_bytes": env["payload_bytes"],
                })
                delivered = True
            except TransportUnavailable as exc:
                # Compute what the bytes would have been for the display table
                raw     = encode(shell, theta, phi, harmonic)
                payload = struct.pack(">I", raw)
                results.append({
                    "substrate":    substrate,
                    "status":       "FAILED",
                    "endpoint":     UDPIPv4Transport().serialize(shell, theta, phi, harmonic)["endpoint"],
                    "packet_bytes": payload,
                })

        return results


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

WIDTH = 72

def section(title: str) -> None:
    print()
    print("=" * WIDTH)
    print(f"  {title}")
    print("=" * WIDTH)


def subsection(title: str) -> None:
    print()
    print(f"  -- {title} --")


# ---------------------------------------------------------------------------
# Part 1 output: one address, four representations
# ---------------------------------------------------------------------------

def part1(address_int: int, shell: int, theta: int, phi: int, harmonic: int) -> None:
    section("PART 1: One Address, Four Transport Representations")

    print(f"""
  Logical address:  shell={shell}, theta={theta}, phi={phi}, harmonic={harmonic}
  28-bit integer:   {address_int}  (hex: 0x{address_int:07X})

  The same integer is handed to each substrate serializer.
  Each serializer produces a different byte envelope — but the
  28-bit integer at the core is identical on every transport.
""")

    for name, handler in [
        ("IPv4/UDP", UDPIPv4Transport()),
        ("LoRa",     LoRaTransport()),
        ("IPFS",     IPFSTransport()),
        ("Hedera",   HederaTransport()),
    ]:
        env = handler.serialize(shell, theta, phi, harmonic)
        print(f"  [{name}]")
        print(f"    substrate     : {env['substrate']}")
        print(f"    endpoint      : {env['endpoint']}")
        print(f"    payload_bytes : {_hex_bytes(env['payload_bytes'])}")
        print(f"    latency_class : {env['latency_class']}")
        print()


# ---------------------------------------------------------------------------
# Part 2 output: resolver is substrate-aware
# ---------------------------------------------------------------------------

def part2(resolver: SubstrateResolver, address_int: int, address_int_denied: int) -> None:
    section("PART 2: The Resolver Is Substrate-Aware")

    shell, theta, phi, harmonic = decode(address_int)
    _, _, phi_denied, _ = decode(address_int_denied)

    print(f"""
  The SubstrateResolver decodes the RPP address, checks the phi consent
  gate ({PHI_GATE}), then dispatches to the appropriate substrate handler.

  Address under test : 0x{address_int:07X}  (phi={phi} — above gate, ALLOW)
  Denied address     : 0x{address_int_denied:07X}  (phi={phi_denied} — below gate, DENY)
""")

    subsection("Resolution of allowed address over all four substrates")
    print()
    print(f"  {'Substrate':<10}  {'Allowed':<8}  {'Endpoint':<40}  Bytes")
    print(f"  {'----------':<10}  {'-------':<8}  {'--------':<40}  -----")
    for name in ["IPv4", "LoRa", "IPFS", "Hedera"]:
        r = resolver.resolve(address_int, name)
        allowed_str = "YES" if r["allowed"] else "NO"
        endpoint    = r["endpoint"] or r["reason"]
        bstr        = _hex_bytes(r["packet_bytes"]) if r["packet_bytes"] else "—"
        print(f"  {name:<10}  {allowed_str:<8}  {endpoint:<40}  {bstr}")

    subsection("Same phi gate, phi=50 — denied on ALL substrates simultaneously")
    print()
    print(f"  {'Substrate':<10}  {'Allowed':<8}  Reason")
    print(f"  {'----------':<10}  {'-------':<8}  ------")
    for name in ["IPv4", "LoRa", "IPFS", "Hedera"]:
        r = resolver.resolve(address_int_denied, name)
        allowed_str = "YES" if r["allowed"] else "NO"
        print(f"  {name:<10}  {allowed_str:<8}  {r['reason']}")

    print("""
  Key insight: the phi field in the address bits IS the consent gate.
  No per-substrate ACL table is consulted.  Changing phi to 50 denies
  the packet on every transport simultaneously — not because each
  transport was configured individually, but because the address itself
  changed.
""")


# ---------------------------------------------------------------------------
# Part 3 output: fallback chain
# ---------------------------------------------------------------------------

def part3(resolver: SubstrateResolver, address_int: int) -> None:
    section("PART 3: Fallback Chain")

    priority_order = ["IPv4", "LoRa", "IPFS", "Hedera"]

    print(f"""
  Priority order: {priority_order}
  IPv4 is simulated as down (raises TransportUnavailable).
  The resolver tries each substrate in order; on failure it continues.
  Remaining substrates after first success are marked STANDBY.
""")

    results = resolver.resolve_with_fallback(address_int, priority_order)

    print(f"  {'Substrate':<10}  {'Status':<8}  {'Endpoint':<38}  Bytes")
    print(f"  {'----------':<10}  {'--------':<8}  {'--------':<38}  -----")
    for r in results:
        bstr = _hex_bytes(r["packet_bytes"]) if r["packet_bytes"] else "(not needed)"
        print(f"  {r['substrate']:<10}  {r['status']:<8}  {r['endpoint']:<38}  {bstr}")

    print("""
  The byte payload is the same 4-byte big-endian integer on IPv4 and LoRa.
  IPFS and Hedera are on standby — the address is resolved but not transmitted.
  If LoRa also failed, IPFS would be promoted automatically.
  The application code calls resolve_with_fallback() once; substrate
  selection is handled entirely inside the resolver, not in application logic.
""")


# ---------------------------------------------------------------------------
# Part 4 output: comparison table
# ---------------------------------------------------------------------------

def part4() -> None:
    section("PART 4: Why This Matters")

    print()
    rows = [
        ("Property",              "Traditional URL",                 "RPP Address"),
        ("─" * 28,               "─" * 28,                          "─" * 28),
        ("Transport binding",     "Scheme in URL (http://, udp://)", "None — schema is separate"),
        ("Endpoint format",       "Hostname + path",                 "Substrate-specific formatter"),
        ("Consent gate",          "External — middleware / ACL",     "phi field in address bits"),
        ("Fallback",              "Application logic",               "Substrate priority chain"),
        ("Same address across",   "No (different URLs per scheme)",  "Yes — same 28-bit integer"),
        ("  transports",          "",                                "  on WiFi, LoRa, IPFS, Hedera"),
    ]

    col_w = [30, 34, 32]
    for row in rows:
        cells = [str(row[i]).ljust(col_w[i]) for i in range(3)]
        print("  " + "  ".join(cells))

    print()
    print(
        "  RPP addresses are substrate-agnostic because they encode semantics\n"
        "  (what, who, when, how urgent), not transport (where). The 28-bit\n"
        "  integer is the same on WiFi, LoRa, IPFS, and Hedera. Only the\n"
        "  byte envelope changes."
    )
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # The single logical address used throughout the demo
    SHELL    = 1
    THETA    = 96
    PHI      = 200
    HARMONIC = 128

    address_int = encode(SHELL, THETA, PHI, HARMONIC)

    # Denied variant: phi below the gate
    address_int_denied = encode(SHELL, THETA, 50, HARMONIC)

    print()
    print("  RPP: Transport-Modality-Agnostic Routing")
    print("  " + "-" * 68)
    print(f"  Python {sys.version.split()[0]}")
    print(f"  rpp.address  encode / decode / from_components")
    print(f"  rpp.network  make_routing_decision / NodeRecord / NodeTier")

    resolver = SubstrateResolver()

    part1(address_int, SHELL, THETA, PHI, HARMONIC)
    part2(resolver, address_int, address_int_denied)
    part3(resolver, address_int)
    part4()


if __name__ == "__main__":
    main()
