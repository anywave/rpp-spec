"""Bounded optional Linux fuzz smoke; dependency/property tests never skip here."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import signal
import subprocess
import time

SCAFFOLD = Path(__file__).resolve().parent
TARGETS = ("decode", "reassemble")
OUTPUT_LIMIT = 1024 * 1024


def seeds(scaffold):
    def bounded(path):
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 16384:
            raise ValueError("seed metadata/text must be regular and at most 16384 bytes")
        return path.read_text(encoding="ascii")
    manifest = json.loads(bounded(scaffold / "seeds/manifest.json"))
    rows = manifest["seeds"]
    if manifest.get("schema") != 1 or not isinstance(rows, list) or not 1 <= len(rows) <= 16:
        raise ValueError("seed schema/count is invalid")
    result, seen = [], set()
    for row in rows:
        target, name, file, digest = (row[key] for key in ("target", "name", "file", "sha256"))
        if (target not in TARGETS or not isinstance(name, str)
                or re.fullmatch(r"[a-z0-9-]{1,64}", name) is None or file != name + ".hex"
                or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or (target, name) in seen):
            raise ValueError("seed target/name/file/hash is invalid or duplicated")
        data = bytes.fromhex(bounded(scaffold / "seeds" / file))
        if len(data) > 4096 or sha256(data).hexdigest() != digest:
            raise ValueError("seed size/hash mismatch")
        result.append((target, name, data))
        seen.add((target, name))
    if {item[0] for item in result} != set(TARGETS):
        raise ValueError("both fuzz targets require seeds")
    return result


def execute(command, timeout, env=None, log=None, cwd=None):
    output = bytearray()
    with selectors.DefaultSelector() as ready, subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0,
            env=env, start_new_session=True, cwd=cwd) as process:
        deadline = time.monotonic() + timeout
        try:
            ready.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not ready.select(remaining):
                    raise subprocess.TimeoutExpired(command, timeout)
                block = os.read(process.stdout.fileno(), min(65536, OUTPUT_LIMIT - len(output)))
                if not block:
                    break
                output.extend(block)
                if len(output) >= OUTPUT_LIMIT:
                    raise RuntimeError("fuzz command reached its output limit")
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except (subprocess.TimeoutExpired, OSError, RuntimeError) as error:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            if isinstance(error, subprocess.TimeoutExpired):
                raise RuntimeError("fuzz command exceeded its outer timeout") from error
            raise
        finally:
            if log:
                log.write_bytes(output)
        if process.returncode:
            raise RuntimeError(f"fuzz command failed; inspect {log or command[0]}")
        return output.decode("utf-8", errors="replace").strip()


def preflight():
    if platform.system() != "Linux":
        return None, "Linux libFuzzer smoke only"
    if not shutil.which("rustup") or not shutil.which("cargo-fuzz"):
        return None, "preinstalled rustup/nightly and cargo-fuzz 0.12.0 are required"
    installed = execute(["rustup", "toolchain", "list"], 10)
    nightly = sorted(line.split()[0] for line in installed.splitlines() if line.startswith("nightly"))
    if not nightly:
        return None, "no preinstalled nightly Rust toolchain"
    compiler = execute(["rustup", "run", nightly[-1], "rustc", "--version"], 10)
    version = execute(["cargo-fuzz", "--version"], 10)
    if re.match(r"^rustc [0-9.]+-nightly\b", compiler) is None or version != "cargo-fuzz 0.12.0":
        raise RuntimeError("present fuzz tools do not match nightly/cargo-fuzz 0.12.0")
    return (nightly[-1], compiler, version), None


def run(output, seconds=30, scaffold=None):
    scaffold = (scaffold or SCAFFOLD).resolve()
    repository, output = scaffold.parents[1], output.resolve()
    if output.is_relative_to(repository) or repository.is_relative_to(output):
        raise ValueError("output must be outside and disjoint from the checkout")
    if not 1 <= seconds <= 30:
        raise ValueError("each of two fuzz targets must run for 1..30 seconds")
    inputs = seeds(scaffold)
    tools, reason = preflight()
    if tools is None:
        return {"status": "SKIP", "reason": reason, "seeds_verified": len(inputs)}
    output.mkdir(parents=True, exist_ok=False)
    project = output / "project"
    ignored = shutil.ignore_patterns("target", "artifacts", "corpus", ".git", "__pycache__")
    shutil.copytree(repository / "rust", project / "rust", ignore=ignored)
    copied = project / "tools/fuzz_scaffold"
    shutil.copytree(scaffold, copied, ignore=ignored)
    for target, name, data in inputs:
        directory = output / "corpus" / target
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_bytes(data)
    lock = copied / "Cargo.lock"
    expected_lock = sha256(lock.read_bytes()).digest()
    env = dict(os.environ, CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(output / "target"))
    env.pop("RUSTC_BOOTSTRAP", None)
    env.pop("RUSTC", None)
    cargo = ["rustup", "run", tools[0], "cargo"]
    common = ["--fuzz-dir", str(copied), "--features", "fuzzing", "--target-dir", str(output / "target")]
    try:
        execute(cargo + ["metadata", "--manifest-path", str(copied / "Cargo.toml"),
                        "--features", "fuzzing", "--locked", "--offline", "--no-deps"],
                30, env, output / "metadata.log", copied)
        execute(cargo + ["fuzz", "build", *common], 180, env, output / "build.log", copied)
        for target in TARGETS:
            execute(cargo + ["fuzz", "run", target, str(output / "corpus" / target), *common,
                            "--", f"-max_total_time={seconds}", "-max_len=4096", "-timeout=2",
                            "-rss_limit_mb=512"], seconds + 15, env, output / f"{target}.log", copied)
    finally:
        if sha256(lock.read_bytes()).digest() != expected_lock:
            raise RuntimeError("fuzz command changed the locked dependency graph")
    return {"status": "PASS", "compiler": tools[1], "cargo_fuzz": tools[2],
            "targets": list(TARGETS), "seconds_per_target": seconds}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=30)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.output_dir, args.seconds), sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(f"fuzz smoke FAILED: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
