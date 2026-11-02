"""Rebuild the complete CX-017/CX-018 evidence twice, including every receipt.

No final summary or determinism receipt hashes itself. The determinism receipt
hashes primary payloads and mutation receipts; the final summary hashes that
receipt and is independently constructed and compared for both complete runs.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from tools.prove_out import verdict
from tools.prove_out.evidence import evidence_bytes

ROOT = Path(__file__).resolve().parents[2]
RESERVED = {"summary.json", "primary-payload.json", "mutation-receipts.json", "determinism.json"}
COMMITTED = ("summary.json", "mutation-receipts.json", "determinism.json", "counterexamples.csv",
             "fractional-input-counterexamples.csv")


def serialize(value):
    """Stable strict JSON; never persist NaN, platform line endings or timings."""
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError("evidence payload must be an object with string keys")
    rows = ["  " + json.dumps(key) + ": " + json.dumps(item, sort_keys=True, allow_nan=False,
             ensure_ascii=True, separators=(",", ":")) for key, item in sorted(value.items())]
    return ("{\n" + ",\n".join(rows) + "\n}\n").encode("utf-8")


def digest(data):
    return sha256(data).hexdigest()


def artifact_map(artifacts):
    result, seen = {}, set()
    reserved = {name.casefold() for name in RESERVED}
    for name, data in artifacts.items():
        if (not isinstance(name, str) or not name or name.casefold() in reserved or name.casefold() in seen
                or "/" in name or "\\" in name
                or ":" in name or name in {".", ".."} or not isinstance(data, bytes)):
            raise ValueError("unsafe, reserved or non-byte primary artifact")
        seen.add(name.casefold())
        result[name] = data
    return result


def collect(args, index):
    """Run actual native, Python and mutation checks into a fresh external tree."""
    from tools.prove_out import coherence_cases, verdict_mutations
    run_dir = args.work_dir / f"run-{index}"
    run_dir.mkdir(parents=True, exist_ok=False)
    native_args = SimpleNamespace(**vars(args))
    native_args.work_dir, native_args.output_dir = run_dir / "native", run_dir / "primary"
    payload = verdict.run(native_args)
    artifacts = {p.name: p.read_bytes() for p in native_args.output_dir.iterdir() if p.name != "summary.json"}
    if {name: digest(data) for name, data in artifacts.items()} != payload["artifacts_sha256"]:
        raise AssertionError("native artifact inventory or digest mismatch")
    cases = coherence_cases.run_checks()
    extra = artifact_map(coherence_cases.csv_artifacts(cases))
    if set(extra) & set(artifacts):
        raise ValueError("duplicate evidence artifact name")
    artifacts.update(extra)
    payload["python_cases"] = cases["summary"]
    payload["artifacts_sha256"] = {name: digest(data) for name, data in sorted(artifacts.items())}
    for path in sorted((args.repo / "tools/prove_out").rglob("*.py")):
        payload["source_sha256"][path.relative_to(args.repo).as_posix()] = digest(evidence_bytes(path))
    mutation_args = SimpleNamespace(repo=args.repo, work_dir=run_dir / "mutations", python=args.python)
    receipts = verdict_mutations.run_receipts(mutation_args)
    return {"payload": payload, "artifacts": artifacts, "receipts": receipts}


def primary_files(build):
    files = artifact_map(build["artifacts"])
    files["primary-payload.json"] = serialize(build["payload"])
    files["mutation-receipts.json"] = serialize(build["receipts"])
    return files


def assemble(first, second):
    """Reject any changed metric, receipt or primary byte before finalizing."""
    files = primary_files(first)
    repeated = primary_files(second)
    if files != repeated:
        raise AssertionError("complete evidence runs differ, including payload or receipts")
    determinism = {"schema_version": 2, "complete_runs": 2, "byte_identical": True,
                   "files": {name: {"sha256": digest(data), "bytes": len(data)}
                             for name, data in sorted(files.items())},
                   "hash_scope": "Primary artifacts, payload and mutation receipts; no final-summary or self hash."}
    det_bytes = serialize(determinism)
    candidates = []
    for build in (first, second):
        verification = dict(build["receipts"])
        if verification.pop("schema_version", None) != 2:
            raise ValueError("mutation receipt schema must be version 2")
        generated = {"schema_version": 2, "native_complete_runs": 2, "byte_identical_files": sorted(files),
                     "primary_payload_sha256": digest(files["primary-payload.json"]),
                     "mutation_receipts_sha256": digest(files["mutation-receipts.json"]),
                     "determinism_receipt_sha256": digest(det_bytes), "whole_summary_byte_identical": True,
                     "hash_scope": "Final summary constructed twice from equal complete runs; its own digest is excluded."}
        if set(verification) & set(generated):
            raise ValueError("mutation receipt uses a reserved verification field")
        verification.update(generated)
        summary = dict(build["payload"])
        if "verification" in summary:
            raise ValueError("primary payload already contains verification")
        summary["verification"] = verification
        candidates.append(serialize(summary))
    if candidates[0] != candidates[1]:
        raise AssertionError("complete summary bytes differ")
    return {**files, "determinism.json": det_bytes, "summary.json": candidates[0]}


def run(args):
    args.repo = ROOT
    for field in ("work_dir", "output_dir"):
        path = getattr(args, field).resolve()
        if path.is_relative_to(ROOT):
            raise ValueError("write evidence outside the source checkout")
        path.mkdir(parents=True, exist_ok=False)
        setattr(args, field, path)
    outputs = assemble(collect(args, 1), collect(args, 2))
    for name, data in outputs.items():
        (args.output_dir / name).write_bytes(data)
    if args.check_committed:
        directory = ROOT / "tools/prove_out/results/cx017"
        for name in COMMITTED:
            if (directory / name).read_bytes() != outputs[name]:
                raise AssertionError("committed evidence differs: " + name)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("iverilog", "vvp", "cargo", "ivl-dir", "work-dir", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=name not in {"cargo", "ivl-dir"})
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--check-committed", action="store_true")
    outputs = run(parser.parse_args())
    print(json.dumps({name: digest(outputs[name]) for name in COMMITTED}, sort_keys=True))


if __name__ == "__main__":
    main()
