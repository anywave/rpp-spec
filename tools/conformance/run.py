"""Build scaffolding only; the shipped conformance runner is Rust."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PIN = "86899f736f751e32603129fcdaf47e4aa313052f"
CRATES = ("lw-jobcard", "lw-registry", "lw-pool")
ROOT = Path(__file__).resolve().parent


def snapshot(repo):
    def git(*args):
        return subprocess.check_output(["git", "--no-replace-objects", "-C", str(repo), *args], timeout=30)

    if git("rev-parse", f"{PIN}^{{commit}}").decode().strip() != PIN:
        raise ValueError("pinned LatticeWorks commit unavailable")
    prefixes = tuple(f"crates/{name}/src/" for name in CRATES)
    manifests = {"Cargo.toml", *(f"crates/{name}/Cargo.toml" for name in CRATES)}
    entries = git("ls-tree", "-r", "-z", PIN, "--", *manifests, *prefixes)
    blobs = {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t")
        mode, kind, oid = meta.split()
        path = raw_path.decode("ascii")
        if kind != b"blob" or mode not in (b"100644", b"100755") or ".." in path.split("/"):
            raise ValueError("unsupported source entry")
        if path not in manifests and not (path.startswith(prefixes) and path.endswith(".rs")):
            raise ValueError("unexpected source entry")
        blobs[path] = git("cat-file", "blob", oid.decode())
    if not manifests.issubset(blobs):
        raise ValueError("incomplete source manifests")
    target = ROOT.parent / ".conformance-sources" / "latticeworks"
    hashes = {p: hashlib.sha256(b).hexdigest() for p, b in blobs.items()}
    provenance = {"commit": PIN, "sha256": hashes}
    if target.is_symlink() or target.parent.is_symlink():
        raise ValueError("source snapshot link refused")
    if target.exists():
        actual = {str(p.relative_to(target)).replace(os.sep, "/"): p for p in target.rglob("*") if p.is_file()}
        if set(actual) != set(blobs) | {"SOURCE.json"} or any(p.is_symlink() for p in target.rglob("*")):
            raise ValueError("source snapshot changed")
        def bounded(path, size):
            with path.open("rb") as stream:
                return stream.read(size + 1)
        if any(hashlib.sha256(bounded(actual[p], len(blobs[p]))).hexdigest() != h for p, h in hashes.items()):
            raise ValueError("source snapshot changed")
        receipt = (json.dumps(provenance, sort_keys=True, indent=2) + "\n").encode()
        if bounded(actual["SOURCE.json"], len(receipt)) != receipt:
            raise ValueError("source provenance changed")
    else:
        target.parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".snapshot-conformance-", dir=ROOT.parent) as stage:
            stage = Path(stage)
            for path, body in blobs.items():
                p = stage / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(body)
            (stage / "SOURCE.json").write_text(json.dumps(provenance, sort_keys=True, indent=2) + "\n")
            os.rename(stage, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latticeworks", type=Path, required=True)
    parser.add_argument("--cargo", default="cargo")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--test", action="store_true")
    args, rest = parser.parse_known_args()
    if rest[:1] == ["--"]:
        rest = rest[1:]
    snapshot(args.latticeworks.resolve())
    if args.prepare_only:
        return 0
    command = [args.cargo, "test" if args.test else "run", "--locked", "--manifest-path", str(ROOT / "Cargo.toml")]
    if args.test:
        command.append("--no-fail-fast")
    if rest:
        command += ["--", *rest]
    return subprocess.call(command, env=dict(os.environ, RPP_CONFORMANCE_PYTHON=sys.executable))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print("REFUSED: pinned source or build prerequisites unavailable", file=sys.stderr)
        sys.exit(2)
