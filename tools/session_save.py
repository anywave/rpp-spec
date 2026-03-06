#!/usr/bin/env python3
"""
RPP Session Save — explicit memory write tool.

Usage:
    python tools/session_save.py "memory content" [options]

Options:
    --phi     INT   Consent level [0-511]. Default: 200.
                    80-199: public context (always shown)
                    200-299: working memory (shown)
                    300-399: trusted context (shown)
                    400-511: private reasoning (loaded but not echoed)
    --shell   INT   TTL tier. 2=24h, 3=30d. Default: 3.
    --theta   INT   Semantic sector [0-511]. Default: 160 (Witness).
    --tags    STR   Comma-separated tags. Default: none.
    --list          List all current memories and exit.
    --stats         Show memory store statistics and exit.
    --expire        Remove expired memories and exit.
    --revoke        Revoke all memories (increment consent epoch) and exit.

Examples:
    # Write a public 30-day memory
    python tools/session_save.py "RPP v2.1.0, 1190 tests passing" --phi 80

    # Write a private reasoning note
    python tools/session_save.py "Uncertain about substrate claim" --phi 400

    # List all accessible memories
    python tools/session_save.py --list

    # Show stats
    python tools/session_save.py --stats
"""

import argparse
import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RPP_ROOT = os.path.dirname(SCRIPT_DIR)
if RPP_ROOT not in sys.path:
    sys.path.insert(0, RPP_ROOT)

from rpp.memory_bridge import RPPMemoryBridge, THETA_MEMORY, THETA_WITNESS, THETA_PROJECT


def main():
    parser = argparse.ArgumentParser(
        description="Write to RPP cross-session memory store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("content", nargs="?", help="Memory content to store")
    parser.add_argument("--phi",    type=int, default=200,       help="Consent level [0-511]")
    parser.add_argument("--shell",  type=int, default=3,         help="Shell tier: 2=24h, 3=30d")
    parser.add_argument("--theta",  type=int, default=THETA_WITNESS, help="Semantic sector [0-511]")
    parser.add_argument("--tags",   type=str, default="",        help="Comma-separated tags")
    parser.add_argument("--list",   action="store_true",         help="List all memories")
    parser.add_argument("--stats",  action="store_true",         help="Show statistics")
    parser.add_argument("--expire", action="store_true",         help="Remove expired memories")
    parser.add_argument("--revoke", action="store_true",         help="Revoke all memories")

    args = parser.parse_args()
    bridge = RPPMemoryBridge()

    if args.list:
        memories = bridge.recall_all(requesting_phi=511)
        if not memories:
            print("No memories in store.")
            return
        from rpp.continuity import compute_liminal_timeout
        import time
        now_ns = time.time_ns()
        ttl_label = {2: "24h", 3: "30d"}
        print(f"RPP Memory Store — {len(memories)} memories (epoch={bridge.identity['consent_epoch']})")
        print()
        for m in memories:
            shell = m.get("shell", 3)
            ttl_ns = compute_liminal_timeout(shell)
            elapsed_s = (now_ns - m.get("created_ns", now_ns)) / 1e9
            remaining_s = (ttl_ns / 1e9) - elapsed_s
            label = ttl_label.get(shell, "?")
            private = "[PRIVATE] " if m.get("phi", 0) >= 400 else ""
            print(f"  {m['address']}  phi={m['phi']:3d}|{label}  {remaining_s/3600:.1f}h left")
            print(f"    {private}{m['content'][:100]}")
            if m.get("tags"):
                print(f"    tags: {', '.join(m['tags'])}")
        return

    if args.stats:
        stats = bridge.stats()
        print("RPP Memory Store Statistics")
        print(f"  Total memories:   {stats['total']}")
        print(f"  Consent epoch:    {stats['consent_epoch']}")
        print(f"  Chain length:     {stats['chain_length']}")
        print(f"  Continuity:       {'INTACT' if stats['continuity_intact'] else 'BROKEN'}")
        print(f"  By phi bucket:    {stats['by_phi_bucket']}")
        return

    if args.expire:
        removed = bridge.expire_stale()
        print(f"Expired {removed} stale memories.")
        return

    if args.revoke:
        confirm = input("Revoke ALL memories and increment consent epoch? [y/N] ")
        if confirm.lower() == "y":
            bridge.revoke_all()
            print(f"All memories revoked. New consent epoch: {bridge.identity['consent_epoch']}")
        else:
            print("Aborted.")
        return

    if not args.content:
        parser.print_help()
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    address = bridge.remember(
        content=args.content,
        phi=args.phi,
        shell=args.shell,
        theta=args.theta,
        tags=tags,
    )

    from rpp.address import decode
    shell, theta, phi, harmonic = decode(address)
    from rpp.continuity import compute_liminal_timeout
    ttl_s = compute_liminal_timeout(shell) / 1e9
    ttl_label = {2: "24h (86400s)", 3: "30d (2592000s)"}.get(shell, f"{ttl_s:.0f}s")
    privacy = "PRIVATE (not echoed in responses)" if phi >= 400 else "accessible"

    print(f"Memory stored:")
    print(f"  Address:  {hex(address)}")
    print(f"  phi:      {phi}  ({privacy})")
    print(f"  TTL:      {ttl_label}")
    print(f"  Content:  {args.content[:80]}")


if __name__ == "__main__":
    main()
