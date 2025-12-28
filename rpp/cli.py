"""
RPP Command Line Interface

Emulator-proof CLI for RPP operations.
Works via stdin/stdout with no ANSI codes or cursor control.
Compatible with: SSH, PuTTY, serial terminals, air-gapped systems.

Commands:
    rpp encode --theta T --phi P --shell S --harmonic H
    rpp decode --address 0xADDRESS
    rpp resolve --address 0xADDRESS [--operation read|write]

Flags:
    --fancy, -f: Enable ANSI colors for modern terminals
    --visual, -V: Show ASCII diagrams and visual feedback

Exit codes:
    0: Success
    1: Invalid input
    2: Resolution denied
    3: Internal error
"""

import sys
import json
import argparse
import io
from typing import List, Optional, TextIO

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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
from rpp import visual
from rpp.i18n import t, get_supported_languages, DEFAULT_LANG


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
    fancy = getattr(args, 'fancy', False)
    show_visual = getattr(args, 'visual', False)
    lang = getattr(args, 'lang', DEFAULT_LANG)

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
            # Get translated names
            shell_name = t(f"shell_{addr.shell_name.lower()}", lang)
            sector_name = t(f"sector_{addr.sector_name.lower()}", lang)
            grounding = t(f"grounding_{addr.grounding_level.lower()}", lang)

            # Show operation status
            output(visual.operation_status(t("encode", lang), True, fancy))
            output("")

            if show_visual:
                # Show full bit layout diagram
                output(visual.bit_layout_diagram(
                    addr.shell, addr.theta, addr.phi, addr.harmonic,
                    addr.raw, fancy
                ))
                output("")
                # Show consent meter
                output(visual.consent_meter(addr.phi, fancy))
                output("")
                # Show shell tier
                output(f"{t('shell', lang).title()}:")
                output(visual.shell_tier_visual(addr.shell, fancy))
            else:
                # Compact output with mini visual
                output(visual.address_mini(
                    addr.to_hex(), shell_name,
                    sector_name, grounding, fancy
                ))
                output("")
                output(f"  {t('shell', lang)}: {addr.shell} ({shell_name})")
                output(f"  {t('theta', lang)}: {addr.theta} ({sector_name})")
                output(f"  {t('phi', lang)}: {addr.phi} ({grounding})")
                output(f"  {t('harmonic', lang)}: {addr.harmonic}")

        return EXIT_SUCCESS

    except ValueError as e:
        error(str(e))
        return EXIT_INVALID_INPUT
    except Exception as e:
        error(f"internal error: {e}")
        return EXIT_ERROR


def cmd_decode(args: argparse.Namespace) -> int:
    """Handle decode command."""
    fancy = getattr(args, 'fancy', False)
    show_visual = getattr(args, 'visual', False)
    lang = getattr(args, 'lang', DEFAULT_LANG)

    try:
        # Parse address (handles hex or decimal)
        raw = parse_address(args.address)
        addr = from_raw(raw)

        if args.json:
            output_json(addr.to_dict())
        else:
            # Get translated names
            shell_name = t(f"shell_{addr.shell_name.lower()}", lang)
            sector_name = t(f"sector_{addr.sector_name.lower()}", lang)
            grounding = t(f"grounding_{addr.grounding_level.lower()}", lang)

            # Show operation status
            output(visual.operation_status(t("decode", lang), True, fancy))
            output("")

            if show_visual:
                # Show full bit layout diagram
                output(visual.bit_layout_diagram(
                    addr.shell, addr.theta, addr.phi, addr.harmonic,
                    addr.raw, fancy
                ))
                output("")
                # Show consent meter
                output(visual.consent_meter(addr.phi, fancy))
                output("")
                # Show theta wheel
                output(visual.theta_wheel(addr.theta, fancy))
            else:
                # Compact output with mini visual
                output(visual.address_mini(
                    addr.to_hex(), shell_name,
                    sector_name, grounding, fancy
                ))
                output("")
                output(f"  {t('shell', lang)}: {addr.shell} ({shell_name})")
                output(f"  {t('theta', lang)}: {addr.theta} ({sector_name})")
                output(f"  {t('phi', lang)}: {addr.phi} ({grounding})")
                output(f"  {t('harmonic', lang)}: {addr.harmonic}")

        return EXIT_SUCCESS

    except ValueError as e:
        error(str(e))
        return EXIT_INVALID_INPUT
    except Exception as e:
        error(f"internal error: {e}")
        return EXIT_ERROR


def cmd_resolve(args: argparse.Namespace) -> int:
    """Handle resolve command."""
    fancy = getattr(args, 'fancy', False)
    show_visual = getattr(args, 'visual', False)
    lang = getattr(args, 'lang', DEFAULT_LANG)

    try:
        # Parse address
        raw = parse_address(args.address)
        addr = from_raw(raw)

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
            # Show operation status
            output(visual.operation_status(t("resolve", lang), result.allowed, fancy))
            output("")

            if show_visual:
                # Show routing diagram
                output(visual.routing_diagram(
                    addr.shell, result.allowed, result.route,
                    result.reason, fancy
                ))
                output("")
                # Show consent meter for context
                output(visual.consent_meter(addr.phi, fancy))
            else:
                # Compact output (ASCII-safe for Windows)
                output(f"  {t('allowed', lang)}: {str(result.allowed).lower()}")
                output(f"    {t('route', lang)}: {result.route if result.route else 'null'}")
                output(f"    {t('reason', lang)}: {result.reason}")

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
    fancy = getattr(args, 'fancy', False)
    lang = getattr(args, 'lang', DEFAULT_LANG)

    # Show banner
    output(visual.demo_banner(fancy))
    output("")

    # Scenario 1: Allowed read (low phi)
    output("=" * 60)
    output(f"  {t('scenario_1_title', lang)}")
    output("=" * 60)
    output("")
    addr1 = from_components(shell=0, theta=12, phi=40, harmonic=1)
    output(visual.bit_layout_diagram(
        addr1.shell, addr1.theta, addr1.phi, addr1.harmonic,
        addr1.raw, fancy
    ))
    output("")
    result1 = resolve(addr1.raw, operation="read")
    output(visual.routing_diagram(
        addr1.shell, result1.allowed, result1.route,
        result1.reason, fancy
    ))
    output("")
    output(visual.consent_meter(addr1.phi, fancy))
    output("")

    # Scenario 2: Denied write (high phi)
    output("=" * 60)
    output(f"  {t('scenario_2_title', lang)}")
    output("=" * 60)
    output("")
    addr2 = from_components(shell=0, theta=100, phi=450, harmonic=64)
    output(visual.bit_layout_diagram(
        addr2.shell, addr2.theta, addr2.phi, addr2.harmonic,
        addr2.raw, fancy
    ))
    output("")
    result2 = resolve(addr2.raw, operation="write")
    output(visual.routing_diagram(
        addr2.shell, result2.allowed, result2.route,
        result2.reason, fancy
    ))
    output("")
    output(visual.consent_meter(addr2.phi, fancy))
    output("")

    # Scenario 3: Routed to archive (cold shell)
    output("=" * 60)
    output(f"  {t('scenario_3_title', lang)}")
    output("=" * 60)
    output("")
    addr3 = from_components(shell=2, theta=200, phi=128, harmonic=32)
    output(visual.bit_layout_diagram(
        addr3.shell, addr3.theta, addr3.phi, addr3.harmonic,
        addr3.raw, fancy
    ))
    output("")
    result3 = resolve(addr3.raw, operation="read")
    output(visual.routing_diagram(
        addr3.shell, result3.allowed, result3.route,
        result3.reason, fancy
    ))
    output("")
    output("Shell Tiers:")
    output(visual.shell_tier_visual(addr3.shell, fancy))
    output("")

    # Summary
    output("=" * 60)
    output(visual.success_box(t("demonstration_complete", lang), fancy))
    output("")
    output("Key takeaways:")
    output(f"  * {t('takeaway_grounded', lang)}")
    output(f"  * {t('takeaway_ethereal', lang)}")
    output(f"  * {t('takeaway_cold', lang)}")
    output("")

    return EXIT_SUCCESS


def cmd_version(args: argparse.Namespace) -> int:
    """Show version."""
    from rpp import __version__
    output(f"rpp {__version__}")
    return EXIT_SUCCESS


def cmd_tutorial(args: argparse.Namespace) -> int:
    """Run interactive tutorial explaining RPP concepts."""
    fancy = getattr(args, 'fancy', False)
    lang = getattr(args, 'lang', DEFAULT_LANG)

    output(visual.demo_banner(fancy))
    output("")
    output("=" * 60)
    output(f"  {t('tutorial_welcome', lang)}")
    output("=" * 60)
    output("")

    # Section 1: What is RPP?
    output("-" * 60)
    output(f"  SECTION 1: {t('tutorial_what_is', lang)}")
    output("-" * 60)
    output("")
    output("RPP (Rotational Packet Protocol) encodes MEANING directly")
    output("into addresses. Instead of opaque memory locations, every")
    output("28-bit address carries semantic information:")
    output("")
    output("  * WHERE data lives (Shell: storage tier)")
    output("  * WHAT type it is (Theta: semantic sector)")
    output("  * WHO can access it (Phi: consent/grounding level)")
    output("  * HOW it behaves (Harmonic: frequency/mode)")
    output("")

    # Section 2: The 28-bit Structure
    output("-" * 60)
    output(f"  SECTION 2: {t('tutorial_address', lang)}")
    output("-" * 60)
    output("")
    output("Every RPP address is exactly 28 bits:")
    output("")
    output("  +--------+-------+---------+---------+----------+")
    output("  | Reserved| Shell |  Theta  |   Phi   | Harmonic |")
    output("  |  4 bits | 2 bits|  9 bits |  9 bits |  8 bits  |")
    output("  +--------+-------+---------+---------+----------+")
    output("")

    # Show example
    example_addr = from_components(shell=1, theta=150, phi=200, harmonic=42)
    output("Example: Encoding shell=1, theta=150, phi=200, harmonic=42")
    output("")
    output(visual.bit_layout_diagram(
        example_addr.shell, example_addr.theta, example_addr.phi,
        example_addr.harmonic, example_addr.raw, fancy
    ))
    output("")

    # Section 3: Shell Tiers
    output("-" * 60)
    output("  SECTION 3: Shell Tiers (Storage Routing)")
    output("-" * 60)
    output("")
    output("The SHELL (2 bits) determines storage tier routing:")
    output("")
    output("  Shell 0 (Hot):    In-memory, immediate access")
    output("  Shell 1 (Warm):   Fast storage, quick retrieval")
    output("  Shell 2 (Cold):   Archive storage, slower access")
    output("  Shell 3 (Frozen): Deep archive, explicit consent required")
    output("")
    output(visual.shell_tier_visual(1, fancy))
    output("")

    # Section 4: Theta Sectors
    output("-" * 60)
    output("  SECTION 4: Theta Sectors (Semantic Classification)")
    output("-" * 60)
    output("")
    output("The THETA (9 bits, 0-511) classifies data semantically:")
    output("")
    output("  0-63:     Gene       - Core identity, genetic data")
    output("  64-127:   Memory     - Experiential records")
    output("  128-191:  Witness    - Observational data")
    output("  192-255:  Dream      - Aspirational/creative content")
    output("  256-319:  Bridge     - Connective/relational data")
    output("  320-383:  Guardian   - Protective/security data")
    output("  384-447:  Emergence  - Evolving/transforming content")
    output("  448-511:  Meta       - Self-referential/meta data")
    output("")
    output(visual.theta_wheel(150, fancy))
    output("")

    # Section 5: Phi Grounding
    output("-" * 60)
    output("  SECTION 5: Phi Grounding (Consent Levels)")
    output("-" * 60)
    output("")
    output("The PHI (9 bits, 0-511) determines consent requirements:")
    output("")
    output("  0-127:    Grounded     - Open access, no consent needed")
    output("  128-255:  Transitional - Basic consent for modifications")
    output("  256-383:  Abstract     - Elevated consent required")
    output("  384-511:  Ethereal     - Explicit consent for all ops")
    output("")
    output("Low phi (grounded):")
    output(visual.consent_meter(50, fancy))
    output("")
    output("High phi (ethereal):")
    output(visual.consent_meter(450, fancy))
    output("")

    # Section 6: Resolution
    output("-" * 60)
    output(f"  SECTION 6: {t('tutorial_resolver', lang)}")
    output("-" * 60)
    output("")
    output("When you access an address, the RESOLVER checks:")
    output("")
    output("  1. Is the operation (read/write/delete) allowed?")
    output("  2. Does the phi level require consent?")
    output("  3. Which storage backend should handle it?")
    output("")

    # Show allowed vs denied
    allowed_addr = from_components(shell=0, theta=12, phi=40, harmonic=1)
    result_ok = resolve(allowed_addr.raw, operation="read")
    output("Example: Reading from grounded zone (phi=40)")
    output(visual.routing_diagram(
        allowed_addr.shell, result_ok.allowed, result_ok.route,
        result_ok.reason, fancy
    ))
    output("")

    denied_addr = from_components(shell=0, theta=100, phi=450, harmonic=64)
    result_denied = resolve(denied_addr.raw, operation="write")
    output("Example: Writing to ethereal zone (phi=450)")
    output(visual.routing_diagram(
        denied_addr.shell, result_denied.allowed, result_denied.route,
        result_denied.reason, fancy
    ))
    output("")

    # Summary
    output("=" * 60)
    output(visual.success_box(t("demonstration_complete", lang), fancy))
    output("")
    output(f"{t('tutorial_try_it', lang)}:")
    output("  rpp encode --shell 0 --theta 12 --phi 40 --harmonic 1")
    output("  rpp decode --address 0x0182801")
    output("  rpp resolve --address 0x0182801 --operation read")
    output("  rpp demo")
    output("")
    output("Add --visual for detailed diagrams, --fancy for colors!")
    output("")

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

    parser.add_argument(
        "--fancy", "-f",
        action="store_true",
        help="Enable ANSI colors for modern terminals",
    )

    parser.add_argument(
        "--visual", "-V",
        action="store_true",
        help="Show detailed ASCII diagrams and visual feedback",
    )

    parser.add_argument(
        "--lang", "-l",
        type=str,
        default=DEFAULT_LANG,
        choices=get_supported_languages(),
        help="Output language (en, ar-gulf, ar-hejaz, es, ru)",
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

    # Tutorial command
    tutorial_parser = subparsers.add_parser(
        "tutorial",
        help="Interactive tutorial explaining RPP concepts",
    )
    tutorial_parser.set_defaults(func=cmd_tutorial)

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
