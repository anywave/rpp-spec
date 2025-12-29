"""
RPP Mesh Command Line Interface

CLI for RPP Mesh operations - consent-aware overlay network.

Commands:
    rpp-mesh packet --address 0xADDRESS --payload "data" [--consent full]
    rpp-mesh header --decode BYTES
    rpp-mesh demo
    rpp-mesh config [--show | --validate PATH]

Flags:
    --json: Output in JSON format
    --verbose, -v: Show detailed information

Exit codes:
    0: Success
    1: Invalid input
    2: Configuration error
    3: Internal error
"""

import sys
import json
import argparse
import io
import struct
from typing import TextIO

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from rpp_mesh import __version__
from rpp_mesh.transport import (
    ConsentState,
    MeshFlags,
    RPPMeshHeader,
    RPPMeshPacket,
)
from rpp_mesh.config import (
    DEVELOPMENT_CONFIG,
    STAGING_CONFIG,
    PRODUCTION_CONFIG,
    load_config,
)
from rpp_mesh.crypto import (
    derive_key,
    encrypt_payload,
    compress_payload,
)

# Exit codes
EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 1
EXIT_CONFIG_ERROR = 2
EXIT_ERROR = 3


def output(text: str, file: TextIO = sys.stdout) -> None:
    """Write output line."""
    print(text, file=file, flush=True)


def output_json(data: dict, file: TextIO = sys.stdout) -> None:
    """Write JSON output."""
    print(json.dumps(data, indent=2), file=file, flush=True)


def error(text: str) -> None:
    """Write error message to stderr."""
    print(f"error: {text}", file=sys.stderr, flush=True)


def parse_consent(value: str) -> ConsentState:
    """Parse consent state from string."""
    mapping = {
        "full": ConsentState.FULL_CONSENT,
        "diminished": ConsentState.DIMINISHED_CONSENT,
        "suspended": ConsentState.SUSPENDED_CONSENT,
        "emergency": ConsentState.EMERGENCY_OVERRIDE,
    }
    lower = value.lower()
    if lower in mapping:
        return mapping[lower]
    # Try numeric
    try:
        return ConsentState(int(value, 0))
    except (ValueError, KeyError):
        raise ValueError(f"Invalid consent state: {value}")


def format_consent(state: ConsentState) -> str:
    """Format consent state for display."""
    names = {
        ConsentState.FULL_CONSENT: "FULL_CONSENT (0x00)",
        ConsentState.DIMINISHED_CONSENT: "DIMINISHED_CONSENT (0x01)",
        ConsentState.SUSPENDED_CONSENT: "SUSPENDED_CONSENT (0x02)",
        ConsentState.EMERGENCY_OVERRIDE: "EMERGENCY_OVERRIDE (0xFF)",
    }
    return names.get(state, f"UNKNOWN (0x{state:02X})")


def cmd_packet(args: argparse.Namespace) -> int:
    """Create and display a mesh packet."""
    use_json = getattr(args, 'json', False)

    try:
        # Parse address
        address = int(args.address, 0) if isinstance(args.address, str) else args.address

        # Parse consent
        consent = parse_consent(args.consent) if args.consent else ConsentState.FULL_CONSENT

        # Build flags
        flags = 0
        if args.encrypted:
            flags |= MeshFlags.ENCRYPTED
        if args.compressed:
            flags |= MeshFlags.COMPRESSED
        if args.priority:
            flags |= MeshFlags.PRIORITY

        # Create header
        header = RPPMeshHeader(
            version=1,
            flags=flags,
            consent_state=consent,
            soul_id=args.soul_id or 0,
            hop_count=0,
            ttl=args.ttl or 4,
        )

        # Create packet
        payload = args.payload.encode() if isinstance(args.payload, str) else args.payload
        packet = RPPMeshPacket(
            header=header,
            rpp_address=address,
            payload=payload,
        )

        # Pack to bytes
        packed = packet.pack()

        if use_json:
            output_json({
                "header": {
                    "version": header.version,
                    "flags": header.flags,
                    "consent_state": consent.name,
                    "soul_id": header.soul_id,
                    "hop_count": header.hop_count,
                    "ttl": header.ttl,
                },
                "rpp_address": f"0x{address:07X}",
                "payload_size": len(payload),
                "total_size": len(packed),
                "hex": packed.hex(),
            })
        else:
            output("=== RPP Mesh Packet ===")
            output(f"Address:       0x{address:07X}")
            output(f"Consent:       {format_consent(consent)}")
            output(f"Flags:         0x{flags:02X}", )
            if flags & MeshFlags.ENCRYPTED:
                output("               - ENCRYPTED")
            if flags & MeshFlags.COMPRESSED:
                output("               - COMPRESSED")
            if flags & MeshFlags.PRIORITY:
                output("               - PRIORITY")
            output(f"Soul ID:       {header.soul_id}")
            output(f"TTL:           {header.ttl}")
            output(f"Payload:       {len(payload)} bytes")
            output(f"Total size:    {len(packed)} bytes")
            output("")
            output("Wire format (hex):")
            # Show hex in 16-byte rows
            hex_str = packed.hex()
            for i in range(0, len(hex_str), 32):
                row = hex_str[i:i+32]
                # Add spaces every 2 chars
                spaced = " ".join(row[j:j+2] for j in range(0, len(row), 2))
                output(f"  {spaced}")

        return EXIT_SUCCESS

    except ValueError as e:
        error(str(e))
        return EXIT_INVALID_INPUT
    except Exception as e:
        error(f"Internal error: {e}")
        return EXIT_ERROR


def cmd_header(args: argparse.Namespace) -> int:
    """Decode and display a mesh header."""
    use_json = getattr(args, 'json', False)

    try:
        # Parse hex input
        hex_data = args.data.replace(" ", "").replace("0x", "")
        data = bytes.fromhex(hex_data)

        if len(data) < 16:
            error(f"Header requires 16 bytes, got {len(data)}")
            return EXIT_INVALID_INPUT

        header = RPPMeshHeader.unpack(data)

        if use_json:
            output_json({
                "version": header.version,
                "flags": header.flags,
                "consent_state": header.consent_state.name,
                "consent_value": header.consent_state.value,
                "soul_id": header.soul_id,
                "hop_count": header.hop_count,
                "ttl": header.ttl,
                "coherence_hash": f"0x{header.coherence_hash:04X}",
            })
        else:
            output("=== RPP Mesh Header ===")
            output(f"Version:       {header.version}")
            output(f"Flags:         0x{header.flags:02X}")
            output(f"Consent:       {format_consent(header.consent_state)}")
            output(f"Soul ID:       {header.soul_id}")
            output(f"Hop Count:     {header.hop_count}")
            output(f"TTL:           {header.ttl}")
            output(f"Coherence:     0x{header.coherence_hash:04X}")

        return EXIT_SUCCESS

    except ValueError as e:
        error(f"Invalid hex data: {e}")
        return EXIT_INVALID_INPUT
    except Exception as e:
        error(f"Internal error: {e}")
        return EXIT_ERROR


def cmd_demo(args: argparse.Namespace) -> int:
    """Run interactive demo of mesh packet creation."""
    import rpp

    output("=== RPP Mesh Demo ===")
    output("")
    output("RPP Mesh adds consent-aware routing to RPP addresses.")
    output("Each packet carries consent state for enforcement at relay nodes.")
    output("")

    # Create sample addresses
    examples = [
        {"shell": 0, "theta": 44, "phi": 160, "harmonic": 7, "desc": "Root zone"},
        {"shell": 2, "theta": 128, "phi": 64, "harmonic": 15, "desc": "Shell 2 sector"},
        {"shell": 1, "theta": 200, "phi": 200, "harmonic": 31, "desc": "High harmonic"},
    ]

    for i, ex in enumerate(examples, 1):
        addr = rpp.encode(
            shell=ex["shell"],
            theta=ex["theta"],
            phi=ex["phi"],
            harmonic=ex["harmonic"]
        )

        output(f"Example {i}: {ex['desc']}")
        output(f"  RPP Address: 0x{addr:07X}")
        output(f"  Components:  shell={ex['shell']}, theta={ex['theta']}, phi={ex['phi']}, h={ex['harmonic']}")

        # Create packet with FULL_CONSENT
        header = RPPMeshHeader(
            consent_state=ConsentState.FULL_CONSENT,
            soul_id=42,
            ttl=4,
        )
        packet = RPPMeshPacket(
            header=header,
            rpp_address=addr,
            payload=b'{"action":"query"}'
        )
        packed = packet.pack()

        output(f"  Packet size: {len(packed)} bytes")
        output(f"  Consent:     FULL_CONSENT (packet will pass consent gates)")
        output("")

    output("Consent States:")
    output("  FULL_CONSENT      - Packet passes through immediately")
    output("  DIMINISHED_CONSENT - Packet delayed, consent re-checked")
    output("  SUSPENDED_CONSENT  - Packet dropped, logged to SCL")
    output("  EMERGENCY_OVERRIDE - Packet dropped, HNC alerted")
    output("")

    return EXIT_SUCCESS


def cmd_config(args: argparse.Namespace) -> int:
    """Show or validate configuration."""
    use_json = getattr(args, 'json', False)

    if args.validate:
        # Validate config file
        try:
            config = load_config(args.validate)
            output(f"Configuration valid: {args.validate}")
            return EXIT_SUCCESS
        except Exception as e:
            error(f"Invalid configuration: {e}")
            return EXIT_CONFIG_ERROR

    # Show default configurations
    configs = {
        "development": DEVELOPMENT_CONFIG,
        "staging": STAGING_CONFIG,
        "production": PRODUCTION_CONFIG,
    }

    target = args.show if args.show else "development"

    if target not in configs:
        error(f"Unknown config: {target}. Use: development, staging, production")
        return EXIT_INVALID_INPUT

    deployment_config = configs[target]
    mesh_config = deployment_config.rpp_mesh

    if use_json:
        output_json({
            "name": target,
            "mode": deployment_config.mode.value,
            "rpp_mesh": {
                "ingress_nodes": mesh_config.ingress_nodes,
                "encrypt_payload": mesh_config.encrypt_payload,
                "compress_payload": mesh_config.compress_payload,
                "sector_ttl": mesh_config.sector_ttl,
                "fallback_mode": mesh_config.fallback_mode,
            },
        })
    else:
        output(f"=== {target.upper()} Configuration ===")
        output(f"Mode:             {deployment_config.mode.value}")
        output(f"Ingress nodes:    {mesh_config.ingress_nodes}")
        output(f"Encryption:       {'enabled' if mesh_config.encrypt_payload else 'disabled'}")
        output(f"Compression:      {'enabled' if mesh_config.compress_payload else 'disabled'}")
        output(f"Sector TTL:       {mesh_config.sector_ttl}")
        output(f"Fallback mode:    {mesh_config.fallback_mode}")

    return EXIT_SUCCESS


def cmd_version(args: argparse.Namespace) -> int:
    """Show version."""
    use_json = getattr(args, 'json', False)

    if use_json:
        output_json({"version": __version__})
    else:
        output(f"rpp-mesh {__version__}")

    return EXIT_SUCCESS


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="rpp-mesh",
        description="RPP Mesh - Consent-Aware Overlay Network",
    )
    parser.add_argument("--version", "-V", action="store_true", help="Show version")
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # packet command
    packet_parser = subparsers.add_parser("packet", help="Create mesh packet")
    packet_parser.add_argument("--address", "-a", required=True, help="RPP address (hex)")
    packet_parser.add_argument("--payload", "-p", default="", help="Payload data")
    packet_parser.add_argument("--consent", "-c", default="full",
                               help="Consent state (full/diminished/suspended/emergency)")
    packet_parser.add_argument("--soul-id", "-s", type=int, default=0, help="Soul ID")
    packet_parser.add_argument("--ttl", "-t", type=int, default=4, help="Sector TTL")
    packet_parser.add_argument("--encrypted", "-e", action="store_true", help="Encrypt payload")
    packet_parser.add_argument("--compressed", "-z", action="store_true", help="Compress payload")
    packet_parser.add_argument("--priority", action="store_true", help="Priority flag")
    packet_parser.set_defaults(func=cmd_packet)

    # header command
    header_parser = subparsers.add_parser("header", help="Decode mesh header")
    header_parser.add_argument("data", help="Header bytes (hex)")
    header_parser.set_defaults(func=cmd_header)

    # demo command
    demo_parser = subparsers.add_parser("demo", help="Run demo")
    demo_parser.set_defaults(func=cmd_demo)

    # config command
    config_parser = subparsers.add_parser("config", help="Show/validate configuration")
    config_parser.add_argument("--show", "-s",
                               help="Show config (development/staging/production)")
    config_parser.add_argument("--validate", "-V", help="Validate config file")
    config_parser.set_defaults(func=cmd_config)

    return parser


def main(argv: list = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.version:
        return cmd_version(args)

    if not args.command:
        parser.print_help()
        return EXIT_SUCCESS

    if hasattr(args, 'func'):
        return args.func(args)

    parser.print_help()
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
