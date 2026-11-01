"""Run actual reviewed Rust gates and compare canonical CSV with the reference.

The temporary manifest points at the explicit read-only source checkout. Cargo
writes its lock/target only under a temporary directory and its configured cache;
the foreign source and this checkout are never edited by this runner.
"""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile

from tools.prove_out.foreign_reference import render_csv, rust_rows, verify_sources
from tools.prove_out.evidence import evidence_bytes


def run(source_root, output_dir, cargo):
    source_root = Path(source_root).resolve()
    verify_sources(source_root)
    here = Path(__file__).resolve().parent
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cx005-native-rust-") as scratch:
        project = Path(scratch)
        manifest = evidence_bytes(here / "Cargo.toml").decode("utf-8")
        start = manifest.index("ra_core = ")
        manifest = manifest[:start] + "ra_core = { path = " + json.dumps(str(source_root / "rust")) + " }\n"
        (project / "Cargo.toml").write_text(manifest, encoding="utf-8", newline="\n")
        (project / "src").mkdir()
        (project / "src/main.rs").write_bytes(evidence_bytes(here / "src/main.rs"))
        raw = project / "native-raw.csv"
        subprocess.run([str(cargo), "run", "--release", "--manifest-path", str(project / "Cargo.toml"),
                        "--target-dir", str(project / "target"), "--", str(raw)], check=True)
        rows = list(csv.DictReader(io.StringIO(evidence_bytes(raw).decode("utf-8"))))
        if len(rows) != 6042:
            raise ValueError("native Rust probe rows missing or duplicated")
        for row in rows:
            row["rac"] = int(row["rac"])
            for key in ("input", "threshold", "alpha"):
                row[key] = format(float(row[key]), ".17g")
        data = render_csv(rows).encode("utf-8")
        expected = render_csv(rust_rows()).encode("utf-8")
        if data != expected:
            raise ValueError("native Rust and Python reference CSV differ")
        (output_dir / "rust-native.csv").write_bytes(data)
        summary = {"native_grid_rows": 6006, "native_boundary_rows": 36, "mismatches": 0,
                   "csv_sha256": hashlib.sha256(data).hexdigest(),
                   "evidence_kind": "actual ra_core public Rust gates, canonicalized numeric CSV"}
        (output_dir / "rust-native-summary.json").write_bytes(
            (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print("native_rust_rows=6042 reference_mismatches=0")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cargo", type=Path, default=Path("cargo"))
    args = parser.parse_args()
    run(args.source_root, args.output_dir, args.cargo)


if __name__ == "__main__":
    main()
