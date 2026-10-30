"""Command line interface: python -m tools.drift check --base SHA --head SHA."""

import argparse
from pathlib import Path
import sys

from .checker import ToolError, check, write_reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("check")
    command.add_argument("--base", required=True)
    command.add_argument("--head", required=True)
    command.add_argument("--output-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        # These two files belong to this command. Never leave stale success reports
        # behind when the new range cannot be evaluated.
        for name in ("drift-report.json", "drift-report.md"):
            (args.output_dir / name).unlink(missing_ok=True)
        report = check(Path.cwd(), args.base, args.head)
        write_reports(report, args.output_dir)
    except (ToolError, OSError, UnicodeError, ValueError) as exc:
        # Do not echo Git stderr or arbitrary target content (may contain secrets).
        print(f"drift: tool error: {exc}", file=sys.stderr)
        return 2
    counts = report["summary"]
    print("drift: high={high} medium={medium} low={low}".format(**counts))
    return int(bool(counts["high"] or counts["medium"]))


if __name__ == "__main__":
    sys.exit(main())
