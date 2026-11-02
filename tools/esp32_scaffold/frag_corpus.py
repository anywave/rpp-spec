"""Independent stdlib vectors for the local five-byte small-MTU derivative."""

import argparse
import hashlib
import json
from pathlib import Path

from tools.esp32_scaffold.control_corpus import frame


def artifacts():
    rows = ["mtu\tkind\ttag\tindex\tfragment"]
    for mtu in (20, 51):
        for kind in range(1, 7):
            data = frame(kind)
            for index, offset in enumerate(range(0, len(data), mtu - 5)):
                header = bytes((0xE0, len(data), 0x12, 0x34, offset))
                rows.append(f"{mtu}\t{kind}\t4660\t{index}\t{(header + data[offset:offset + mtu - 5]).hex()}")
    table = ("\n".join(rows) + "\n").encode("ascii")
    manifest = {"schema": 1, "fragments": len(rows) - 1, "frames": 12,
                "mtus": [20, 51], "sha256": hashlib.sha256(table).hexdigest()}
    return {"frag-corpus.tsv": table,
            "frag-manifest.json": (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("ascii")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts().items():
        (args.output_dir / name).write_bytes(content)


if __name__ == "__main__":
    main()
