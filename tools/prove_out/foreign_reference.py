"""Source-grounded reference probes, deliberately not native foreign execution.

These transcribe the reviewed ra-system formulas; they do not compare unlike
quantities with RPP progress, infer input calibration or alter package constants.
"""

import argparse
import csv
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path


SOURCE_REVISION = "e685d3abacca3105a7c377e9db80df33ce7c2985"
SOURCE_HASHES = {
    "rust/src/gates.rs": "ef7cff9c6d1a55eeefc5d665d899de68220e8428566aef00c4b7c9b663b54131",
    "rust/src/lib.rs": "fa5193fa9a3a7bea0b62c93ebe2dfd47143a3926045b8114220a4d11d9c2a450",
    "rust/src/rac.rs": "c0d3698b72c3465ccc44997df0024c726a49c589a8104dfab27114b5409035aa",
    "rust/src/constants.rs": "24b566b48511e39f18adc6e5d05e2f173694b4a3d5c8d19ec8a31b4329dee832",
    "haskell/clash/RaGroupCoherence.hs": "79abd59e0d7fa03ec5c049d0559a50212dd9f2fcae2d63424eeb626b1003201e",
}


def verify_sources(source_root):
    """Reject unreviewed input before generating evidence from its transcription."""
    hashes = {}
    for name, expected in SOURCE_HASHES.items():
        actual = hashlib.sha256((Path(source_root) / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"unreviewed source: {name}")
        hashes[name] = actual
    return hashes


def rust_floor():
    """gates.rs:30 and constants.rs:35,56; author policy ratio, no measurement."""
    return 1.62 / (3.0 * 84823.0 / 50000.0)


def rust_threshold(level):
    """rac.rs:76-85,111-113; level argument is the finite ordinary range 1..6."""
    values = (0.6361725, 0.628318519, 0.57255525, 0.523598765, 0.4580442, 0.3998594565)
    if type(level) is not int or not 1 <= level <= 6:
        raise ValueError("RAC level must be an integer from 1 to 6")
    return values[level - 1] / values[0]


def rust_access(coherence, level):
    """Transcribe gates.rs:79-89; at floor, PartialAccess(0) is not Blocked."""
    threshold = rust_threshold(level)
    if coherence >= threshold:
        return "full", 1.0
    if coherence >= rust_floor():
        alpha = (coherence - rust_floor()) / (threshold - rust_floor())
        return "partial", min(1.0, max(0.0, alpha))
    return "blocked", 0.0


def clash_avatar_weight(coherence, depth):
    """RaGroupCoherence.hs:346-355, ordinary two unsigned 8-bit inputs."""
    if any(type(x) is not int or not 0 <= x <= 255 for x in (coherence, depth)):
        raise ValueError("unsigned 8-bit inputs required")
    return (coherence * depth) >> 8


@dataclass(frozen=True)
class Avatar:
    coherence: int
    depth: int
    active: bool = True
    inverted: bool = False
    harmonic_l: int = 0


def clash_group(avatars):
    """Transcribe only cluster-size and score/stability slice, hs:265-291,358-405.

    This intentionally excludes clocks, tie-selected signature, windows, feedback
    and synthesis. It is not a translation of the entire Clash module.
    """
    if len(avatars) != 8:
        raise ValueError("the reviewed module has exactly eight avatar slots")
    for avatar in avatars:
        clash_avatar_weight(avatar.coherence, avatar.depth)
        if type(avatar.harmonic_l) is not int or not 0 <= avatar.harmonic_l <= 7:
            raise ValueError("harmonic L must be an integer from 0 to 7")
    active = [avatar for avatar in avatars if avatar.active]
    sizes = [0] * 4
    for avatar in active:
        cluster = 0 if avatar.harmonic_l <= 1 else min(avatar.harmonic_l - 1, 3)
        sizes[cluster] += 1
    dominant_size = max(sizes)
    total = sum(clash_avatar_weight(a.coherence, a.depth) for a in active if not a.inverted)
    base = total // len(active) if active else 0
    group = min(255, base + (38 if dominant_size >= 3 else 0))
    field = min(255, group + (77 if dominant_size >= 3 else 0))
    inverted = sum(a.inverted for a in active)
    status = ("stable" if inverted == 0 and group > 179 else "collapsed" if inverted > 2
              else "unstable" if inverted > 0 else "transitioning")
    return {"active": len(active), "inverted": inverted, "dominant_size": dominant_size,
            "coherence": group, "field_strength": field, "status": status}


def avatar_slots(*active):
    """Pad ordinary active examples to the reviewed module's eight input slots."""
    if len(active) > 8:
        raise ValueError("at most eight active avatars")
    return tuple(active) + (Avatar(0, 0, active=False),) * (8 - len(active))


def rust_rows():
    rows = []
    for level in range(1, 7):
        for tick in range(1001):
            value = tick / 1000
            kind, alpha = rust_access(value, level)
            rows.append({"rac": level, "probe": f"grid-{tick}", "input": format(value, ".17g"),
                         "threshold": format(rust_threshold(level), ".17g"),
                         "kind": kind, "alpha": format(alpha, ".17g")})
        for label, value in (
            ("below-floor", math.nextafter(rust_floor(), -math.inf)),
            ("at-floor", rust_floor()),
            ("above-floor", math.nextafter(rust_floor(), math.inf)),
            ("below-threshold", math.nextafter(rust_threshold(level), -math.inf)),
            ("at-threshold", rust_threshold(level)),
            ("above-threshold", math.nextafter(rust_threshold(level), math.inf)),
        ):
            kind, alpha = rust_access(value, level)
            rows.append({"rac": level, "probe": label, "input": format(value, ".17g"),
                         "threshold": format(rust_threshold(level), ".17g"),
                         "kind": kind, "alpha": format(alpha, ".17g")})
    return rows


def clash_rows():
    return [{"coherence": coherence, "depth": depth,
             "avatar_weight": clash_avatar_weight(coherence, depth),
             "three_aligned_group": min(255, clash_avatar_weight(coherence, depth) + 38),
             "three_aligned_field": min(255, clash_avatar_weight(coherence, depth) + 38 + 77)}
            for coherence in range(256) for depth in range(256)]


def render_csv(rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def write_results(source_root, output_dir):
    hashes = verify_sources(source_root)
    rust = rust_rows()
    clash = clash_rows()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    summary = {"evidence_kind": "source transcription, not native execution",
               "source_revision": SOURCE_REVISION, "source_hashes": hashes,
               "rust_grid_rows": 6006, "rust_boundary_rows": 36, "clash_product_rows": len(clash),
               "rust_floor": rust_floor(), "rust_thresholds": [rust_threshold(i) for i in range(1, 7)],
               "clash_max_avatar_weight": 254,
               "three_inverted": clash_group(avatar_slots(*(Avatar(255, 255, inverted=True),) * 3))}
    for name, rows in (("rust-reference.csv", rust), ("clash-reference.csv", clash)):
        data = render_csv(rows).encode("utf-8")
        (output / name).write_bytes(data)
        summary[name + "_sha256"] = hashlib.sha256(data).hexdigest()
    (output / "summary.json").write_bytes((json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = write_results(args.source_root, args.output_dir)
    print("source_files=5 rust_grid_rows=6006 rust_boundary_rows=36 clash_product_rows=65536 native_runs=0")
    return summary


if __name__ == "__main__":
    main()
