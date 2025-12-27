"""
RPP Command Line Interface

Emulator-proof CLI for RPP operations.
Works via stdin/stdout with no ANSI codes or cursor control.
Compatible with: SSH, PuTTY, serial terminals, air-gapped systems.

Commands:
    rpp encode --theta T --phi P --shell S --harmonic H
    rpp decode --address 0xADDRESS
    rpp resolve --address 0xADDRESS [--operation read|write]

Exit codes:
    0: Success
    1: Invalid input
    2: Resolution denied
    3: Internal error
"""

import sys
import json
import argparse
from typing import List, Optional, TextIO

from rpp.address import (
    from_raw,
    from_components,
    parse_address,
    MAX_SHELL,
    MAX_THETA,
    MAX_PHI,
    MAX_HARMONIC,
)
from rpp.resolver import resolve


# Exit codes
EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 1
EXIT_DENIED = 2
EXIT_ERROR = 3


def output(text: str, file: TextIO = sys.stdout) -> None:
    """Write output line. No ANSI, no color, just plain text."""
    print(text, file=file, flush=True)


def output_json(data: dict, file: TextIO = sys.stdout) -> None:
    """Write JSON output. Compact, single-line for simple parsing."""
    print(json.dumps(data, separators=(",", ":")), file=file, flush=True)


def error(text: str) -> None:
    """Write error message to stderr."""
    print(f"error: {text}", file=sys.stderr, flush=True)


def cmd_encode(args: argparse.Namespace) -> int:
    """Handle encode command."""
    try:
        # Validate ranges
        if not (0 <= args.shell <= MAX_SHELL):
            error(f"shell must be 0-{MAX_SHELL}")
            return EXIT_INVALID_INPUT
        if not (0 <= args.theta <= MAX_THETA):
            error(f"theta must be 0-{MAX_THETA}")
            return EXIT_INVALID_INPUT
        if not (0 <= args.phi <= MAX_PHI):
            error(f"phi must be 0-{MAX_PHI}")
            return EXIT_INVALID_INPUT
        if not (0 <= args.harmonic <= MAX_HARMONIC):
            error(f"harmonic must be 0-{MAX_HARMONIC}")
            return EXIT_INVALID_INPUT

        # Encode
        addr = from_components(args.shell, args.theta, args.phi, args.harmonic)

        if args.json:
            output_json(addr.to_dict())
        else:
            output(f"address: {addr.to_hex()}")
            output(f"shell: {addr.shell} ({addr.shell_name})")
            output(f"theta: {addr.theta} ({addr.sector_name})")
            output(f"phi: {addr.phi} ({addr.grounding_level})")
            output(f"harmonic: {addr.harmonic}")

        return EXIT_SUCCESS

    except ValueError as e:
        error(str(e))
        return EXIT_INVALID_INPUT
    except Exception as e:
        error(f"internal error: {e}")
        return EXIT_ERROR


def cmd_decode(args: argparse.Namespace) -> int:
    """Handle decode command."""
    try:
        # Parse address (handles hex or decimal)
        raw = parse_address(args.address)
        addr = from_raw(raw)

        if args.json:
            output_json(addr.to_dict())
        else:
            output(f"address: {addr.to_hex()}")
            output(f"shell: {addr.shell} ({addr.shell_name})")
            output(f"theta: {addr.theta} ({addr.sector_name})")
            output(f"phi: {addr.phi} ({addr.grounding_level})")
            output(f"harmonic: {addr.harmonic}")

        return EXIT_SUCCESS

    except ValueError as e:
        error(str(e))
        return EXIT_INVALID_INPUT
    except Exception as e:
        error(f"internal error: {e}")
        return EXIT_ERROR


def cmd_resolve(args: argparse.Namespace) -> int:
    """Handle resolve command."""
    try:
        # Parse address
        raw = parse_address(args.address)

        # Build context
        context = {}
        if args.consent:
            context["consent"] = args.consent
        if args.emergency:
            context["emergency_override"] = True

        # Resolve
        result = resolve(raw, operation=args.operation, context=context)

        if args.json:
            output_json(result.to_dict())
        else:
            output(f"allowed: {str(result.allowed).lower()}")
            output(f"route: {result.route if result.route else 'null'}")
            output(f"reason: {result.reason}")

        # Exit code based on result
        if result.allowed:
            return EXIT_SUCCESS
        else:
            return EXIT_DENIED

    except ValueError as e:
        error(str(e))
        return EXIT_INVALID_INPUT
    except Exception as e:
        error(f"internal error: {e}")
        return EXIT_ERROR


def cmd_demo(args: argparse.Namespace) -> int:
    """Run demonstration of the three core scenarios."""
    output("RPP Demonstration")
    output("=================")
    output("")

    # Scenario 1: Allowed read (low phi)
    output("Scenario 1: Allowed read (low phi)")
    output("-" * 40)
    addr1 = from_components(shell=0, theta=12, phi=40, harmonic=1)
    output(f"Address: {addr1.to_hex()}")
    result1 = resolve(addr1.raw, operation="read")
    output(f"allowed: {str(result1.allowed).lower()}")
    output(f"route: {result1.route}")
    output(f"reason: {result1.reason}")
    output("")

    # Scenario 2: Denied write (high phi)
    output("Scenario 2: Denied write (high phi)")
    output("-" * 40)
    addr2 = from_components(shell=0, theta=100, phi=450, harmonic=64)
    output(f"Address: {addr2.to_hex()}")
    result2 = resolve(addr2.raw, operation="write")
    output(f"allowed: {str(result2.allowed).lower()}")
    output(f"route: {result2.route if result2.route else 'null'}")
    output(f"reason: {result2.reason}")
    output("")

    # Scenario 3: Routed to archive (cold shell)
    output("Scenario 3: Routed to archive (cold shell)")
    output("-" * 40)
    addr3 = from_components(shell=2, theta=200, phi=128, harmonic=32)
    output(f"Address: {addr3.to_hex()}")
    result3 = resolve(addr3.raw, operation="read")
    output(f"allowed: {str(result3.allowed).lower()}")
    output(f"route: {result3.route}")
    output(f"reason: {result3.reason}")
    output("")

    output("Demonstration complete.")
    return EXIT_SUCCESS


def cmd_version(args: argparse.Namespace) -> int:
    """Show version."""
    from rpp import __version__
    output(f"rpp {__version__}")
    return EXIT_SUCCESS


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="rpp",
        description="RPP - Rotational Packet Protocol CLI",
        epilog="See https://github.com/anywave/rpp-spec for documentation.",
    )

    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version and exit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Encode command
    encode_parser = subparsers.add_parser(
        "encode",
        help="Encode components into an RPP address",
    )
    encode_parser.add_argument("--shell", "-s", type=int, required=True, help=f"Shell tier (0-{MAX_SHELL})")
    encode_parser.add_argument("--theta", "-t", type=int, required=True, help=f"Theta sector (0-{MAX_THETA})")
    encode_parser.add_argument("--phi", "-p", type=int, required=True, help=f"Phi grounding (0-{MAX_PHI})")
    encode_parser.add_argument("--harmonic", "-H", type=int, required=True, help=f"Harmonic (0-{MAX_HARMONIC})")
    encode_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    encode_parser.set_defaults(func=cmd_encode)

    # Decode command
    decode_parser = subparsers.add_parser(
        "decode",
        help="Decode an RPP address into components",
    )
    decode_parser.add_argument("--address", "-a", type=str, required=True, help="Address (hex or decimal)")
    decode_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    decode_parser.set_defaults(func=cmd_decode)

    # Resolve command
    resolve_parser = subparsers.add_parser(
        "resolve",
        help="Resolve an RPP address to a routing decision",
    )
    resolve_parser.add_argument("--address", "-a", type=str, required=True, help="Address (hex or decimal)")
    resolve_parser.add_argument("--operation", "-o", type=str, default="read", choices=["read", "write", "delete"], help="Operation type")
    resolve_parser.add_argument("--consent", "-c", type=str, choices=["none", "diminished", "full", "explicit"], help="Consent level")
    resolve_parser.add_argument("--emergency", "-e", action="store_true", help="Emergency override")
    resolve_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    resolve_parser.set_defaults(func=cmd_resolve)

    # Demo command
    demo_parser = subparsers.add_parser(
        "demo",
        help="Run demonstration of core scenarios",
    )
    demo_parser.set_defaults(func=cmd_demo)

    # Version command
    version_parser = subparsers.add_parser(
        "version",
        help="Show version",
    )
    version_parser.set_defaults(func=cmd_version)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Handle --version flag at top level
    if args.version:
        return cmd_version(args)

    # No command specified
    if args.command is None:
        parser.print_help()
        return EXIT_SUCCESS

    # Run command
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
