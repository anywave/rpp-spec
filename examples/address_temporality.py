#!/usr/bin/env python3
"""
RPP Address Temporality Demo
=============================

Demonstrates the core RPP property: addresses are not permanent identifiers
— they are temporal routing states that expire by design.

The shell field encodes retention scope directly into the 28-bit address
integer. Temporality is not a property OF the address. It IS the address.

Usage:
    python examples/address_temporality.py
"""

import sys
import time
import math

sys.stdout.reconfigure(encoding='utf-8')

from rpp.address import encode, decode
from rpp.continuity import SHELL_LIMINAL_TIMEOUT_NS, SHELL_T2_NS, compute_liminal_timeout


# ---------------------------------------------------------------------------
# Part 1: The Same Data, Four Lifetimes
# ---------------------------------------------------------------------------

def part1_four_lifetimes():
    print()
    print("=" * 70)
    print("PART 1 — THE SAME DATA, FOUR LIFETIMES")
    print("=" * 70)
    print()
    print("Encoding theta=96, phi=300, harmonic=128 at each shell tier.")
    print("Same logical data. Four different addresses. Four different lifetimes.")
    print()

    theta    = 96
    phi      = 300
    harmonic = 128

    shell_labels = {
        0: ("25 ns",     "spintronic T2 decoherence"),
        1: ("5 min",     "session scope"),
        2: ("24 hours",  "daily archive"),
        3: ("30 days",   "long-term archive"),
    }

    for shell in range(4):
        addr = encode(shell=shell, theta=theta, phi=phi, harmonic=harmonic)
        label, description = shell_labels[shell]
        print(f"  shell={shell}: 0x{addr:07X}  ->  expires in {label:<10}  ({description})")

    print()
    print("In IPv4, a memory address is permanent until explicitly deleted.")
    print("In RPP, the address carries its own expiry. You cannot store a shell=0 address")
    print("and use it an hour later — it is gone, by design.")


# ---------------------------------------------------------------------------
# Part 2: Simulate Address Expiry
# ---------------------------------------------------------------------------

def part2_simulate_expiry():
    print()
    print("=" * 70)
    print("PART 2 — SIMULATE ADDRESS EXPIRY")
    print("=" * 70)
    print()

    shell = 1
    theta    = 96
    phi      = 300
    harmonic = 128

    addr = encode(shell=shell, theta=theta, phi=phi, harmonic=harmonic)
    timeout_ns = compute_liminal_timeout(shell=1)
    timeout_s  = timeout_ns // 1_000_000_000

    # Simulated base time — we do not actually sleep
    issued_at_ns = 1_000_000_000_000  # arbitrary epoch in ns

    print(f"Shell=1 (Warm) address: 0x{addr:07X}")
    print(f"Liminal timeout: compute_liminal_timeout(shell=1) = {timeout_ns:,} ns  ({timeout_s} seconds)")
    print()

    events = [
        (0,   "Address issued",              "LIVE"),
        (30,  "Packet routes successfully",  f"LIVE - {timeout_s - 30}s remaining"),
        (120, "Packet routes successfully",  f"LIVE - {timeout_s - 120}s remaining"),
        (300, "TTL expires",                 "DEAD"),
        (301, "Routing attempt",             "REJECTED - address expired"),
    ]

    print(f"  {'t':>6}   {'Event':<32}  {'Status'}")
    print(f"  {'-'*6}   {'-'*32}  {'-'*32}")

    for t_s, event, status in events:
        now_simulated_ns = issued_at_ns + (t_s * 1_000_000_000)
        print(f"  t={t_s:<4}s  {event:<32}  [{status}]")

    print()
    print("Expiry check at t=301s:")
    now_301_ns = issued_at_ns + (301 * 1_000_000_000)
    expired    = issued_at_ns + timeout_ns < now_301_ns
    print(f"  issued_at + timeout_ns  = {issued_at_ns:,} + {timeout_ns:,}")
    print(f"                         = {issued_at_ns + timeout_ns:,}")
    print(f"  now_simulated (t=301s)  = {now_301_ns:,}")
    print(f"  issued_at + timeout < now_simulated  ->  {expired}  (address expired)")
    print()
    print("Stolen address property:")
    print(f"  An adversary who captures address 0x{addr:07X} at t=0 and tries to use")
    print( "  it at t=301s gets nothing. The address is not just unauthorized — it")
    print( "  does not exist anymore.")


# ---------------------------------------------------------------------------
# Part 3: Compare to Alternatives
# ---------------------------------------------------------------------------

def part3_comparison_table():
    print()
    print("=" * 70)
    print("PART 3 — COMPARE TO ALTERNATIVES")
    print("=" * 70)
    print()

    col1 = 16
    col2 = 28
    col3 = 38

    header = f"{'System':<{col1}}  {'Address lifetime':<{col2}}  {'How it expires'}"
    print(header)
    print("-" * (col1 + col2 + col3 + 4))

    rows = [
        ("IPv4 address",  "Permanent (until release)", "Manual deallocation or DHCP lease"),
        ("DNS record",    "TTL (separate header)",     "TTL field in DNS record"),
        ("HTTP resource", "Cache-Control: max-age",    "Separate header, not in URL"),
        ("OAuth token",   "exp claim in JWT payload",  "Separate field, token still exists"),
        ("RPP address",   "Shell field IN the address","The address IS the TTL. Inseparable."),
    ]

    for system, lifetime, expiry in rows:
        print(f"{system:<{col1}}  {lifetime:<{col2}}  {expiry}")

    print()
    print("RPP is the only addressing scheme where temporality is not a property OF the address —")
    print("it IS the address. You cannot strip the expiry from an RPP address without changing its bits.")
    print("They are the same integer.")


# ---------------------------------------------------------------------------
# Part 4: Address Recycling
# ---------------------------------------------------------------------------

def part4_address_recycling():
    print()
    print("=" * 70)
    print("PART 4 — ADDRESS RECYCLING")
    print("=" * 70)
    print()

    total = 2 ** 28

    print("After a shell=1 address expires, that bit pattern can be reissued with new consent.")
    print()
    print("Unlike an OAuth token (which must be revoked and a new one issued), RPP just lets")
    print("the address expire. No DELETE call. No revocation broadcast. No registry update.")
    print("The TTL runs out and the address self-clears.")
    print()
    print("Two different data items can occupy the same address at different times — like a")
    print("telephone number being reassigned after the previous subscriber disconnects.")
    print()
    print("This means the address space represents CONCURRENT ROUTING CAPACITY, not a permanent")
    print("namespace. Addresses encode 'what is routable right now', not 'what has ever existed'.")
    print()
    print(f"  {total:,} RPP addresses represent {total:,} simultaneous routing states,")
    print(f"  not {total:,} permanent object identifiers.")
    print( "  The namespace is temporal, not spatial.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("#" * 70)
    print("#" + "  RPP: Addresses as Temporal Routing States  ".center(68) + "#")
    print("#" * 70)

    part1_four_lifetimes()
    part2_simulate_expiry()
    part3_comparison_table()
    part4_address_recycling()

    print()
    print("=" * 70)
    print("Demo complete.")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
