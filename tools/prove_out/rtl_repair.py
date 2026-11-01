"""Run the CX-006 exact-policy HDL sweep and three actual hardware mutations.

No source tree is mutated. Compile failures, malformed grids and runtime errors
never count as killed mutants. All persisted evidence uses deterministic LF.
"""

import argparse
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import subprocess

from rpp.coherence import compute_coherence
from tools.prove_out.completion import THRESHOLDS


BINDINGS = ("registered", "combinational", "compatibility")
FIELDS = ("entropy", "completion", "threshold", "registered_score", "combinational_score",
          "compatibility_score", "registered_valid", "combinational_valid", "compatibility_valid",
          "normalized", "high", "medium", "low")


def parse_grid(text):
    """Mutation: accepting a missing/duplicate/unknown row invalidates this grid."""
    points = {}
    for line in text.splitlines():
        if not line.startswith("SCORE,"):
            continue
        values = tuple(int(value) for value in line.split(",")[1:])
        if len(values) != len(FIELDS) or values[:3] in points:
            raise ValueError("malformed or duplicate score point")
        points[values[:3]] = values
    expected = {(e, c, t) for e in range(32) for c in range(8) for t in THRESHOLDS}
    if set(points) != expected:
        raise ValueError("incomplete or out-of-domain score grid")
    return [points[key] for key in sorted(points)]


def analyze(rows):
    result = {"points": len(rows), "score_mismatches": dict.fromkeys(BINDINGS, 0),
              "threshold_mismatches": dict.fromkeys(BINDINGS, 0),
              "band_mismatches": 0, "normalization_expression_mismatches": 0}
    for row in rows:
        e, c, threshold = row[:3]
        oracle = compute_coherence(e / 31, c / 7).score
        if oracle != 165 * e // 31 + 509 * c // 7:
            raise AssertionError("Python and separately truncated rational oracle disagree")
        for index, name in enumerate(BINDINGS):
            result["score_mismatches"][name] += row[index + 3] != oracle
            result["threshold_mismatches"][name] += row[index + 6] != int(oracle >= threshold)
        result["band_mismatches"] += row[10:] != (int(oracle >= 500), int(300 <= oracle < 500), int(oracle < 300))
        # This preserves the old expression; it does not validate its calibration.
        result["normalization_expression_mismatches"] += row[9] != (((row[4] * 38) >> 8) & 255)
    grid = {(row[0], row[1]): row for row in rows if row[2] == 137}
    result["adjacent_pairs"] = {"entropy": 248, "completion": 224}
    result["decreases"] = {}
    for index, name in enumerate(BINDINGS):
        result["decreases"][name] = {
            "entropy": sum(grid[e + 1, c][index + 3] < grid[e, c][index + 3]
                           for e in range(31) for c in range(8)),
            "completion": sum(grid[e, c + 1][index + 3] < grid[e, c][index + 3]
                              for e in range(32) for c in range(7)),
        }
    return result


def require_agreement(result):
    """Mutation shift/product-width/combined-floor: any changed score must fail."""
    if (any(result["score_mismatches"].values()) or any(result["threshold_mismatches"].values())
            or result["band_mismatches"] or result["normalization_expression_mismatches"]
            or any(any(counts.values()) for counts in result["decreases"].values())):
        raise AssertionError("HDL score/decision policy disagreement")


def run_grid(args, name, rtl, registered):
    destination = args.work_dir / name
    destination.mkdir(parents=True, exist_ok=True)
    rtl_path = destination / "spiral_ra_coherence.v"
    registered_path = destination / "coherence_evaluator_ra.v"
    rtl_path.write_text(rtl, encoding="utf-8", newline="\n")
    registered_path.write_text(registered, encoding="utf-8", newline="\n")
    image = destination / "sweep.vvp"
    compiler = [str(args.iverilog)] + (["-B", str(args.ivl_dir)] if args.ivl_dir else [])
    compiler += ["-g2012", "-s", "RTLScalingRepair", "-o", str(image),
                 str(args.repo / "tools/prove_out/rtl_repair_tb.v"), str(registered_path), str(rtl_path)]
    result = subprocess.run(compiler, capture_output=True, text=True, encoding="utf-8", check=True)
    (destination / "compile.log").write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    runtime = [str(args.vvp)] + (["-M", str(args.ivl_dir)] if args.ivl_dir else []) + [str(image)]
    result = subprocess.run(runtime, cwd=destination, capture_output=True, text=True, encoding="utf-8", check=True)
    (destination / "run.log").write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    return parse_grid(result.stdout)


def csv_bytes(rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(FIELDS)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError("stale or ambiguous hardware mutation anchor")
    return text.replace(before, after, 1)


def git_source(repo, revision, path):
    return subprocess.run(["git", "show", f"{revision}:{path}"], cwd=repo, check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iverilog", type=Path, required=True)
    parser.add_argument("--vvp", type=Path, required=True)
    parser.add_argument("--ivl-dir", type=Path)
    parser.add_argument("--base", default="275a115")
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", args.base):
        parser.error("base must be a hexadecimal commit ID")
    args.repo = Path(__file__).resolve().parents[2]
    for name in ("iverilog", "vvp", "work_dir", "output_dir", "ivl_dir"):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    rtl_path = "hardware/verilog/spiral_ra_coherence.v"
    registered_path = "hardware/verilog/coherence_evaluator_ra.v"
    before = git_source(args.repo, args.base, rtl_path)
    registered = (args.repo / registered_path).read_text(encoding="utf-8")
    if registered != git_source(args.repo, args.base, registered_path):
        raise AssertionError("registered scorer/completion semantics changed")
    after = (args.repo / rtl_path).read_text(encoding="utf-8")
    boundary = "// ScalarTrigger_Ra (Ra-Enhanced)"
    if before[before.index(boundary):] != after[after.index(boundary):]:
        raise AssertionError("out-of-scope trigger/fallback/consent modules changed")
    before_rows = run_grid(args, "before", before, registered)
    reciprocal_only = replace_once(before, "wire [23:0] ankh_div = term_ankh * 24'd936;",
                                   "wire [24:0] ankh_div = term_ankh * 25'd936;")
    reciprocal_only = replace_once(reciprocal_only, "score_phi  = phi_div[23:14]", "score_phi  = phi_div[23:16]")
    reciprocal_only = replace_once(reciprocal_only, "score_ankh = ankh_div[23:14]", "score_ankh = ankh_div[24:16]")
    reciprocal_rows = run_grid(args, "width-and-shift-only", reciprocal_only, registered)
    after_rows = run_grid(args, "after", after, registered)
    before_result, after_result = analyze(before_rows), analyze(after_rows)
    require_agreement(after_result)
    mutations = (
        ("incorrect-shift", "assign score = {2'b0, entropy_term} + {1'b0, completion_term};",
         "assign score = ({2'b0, entropy_term} + {1'b0, completion_term}) << 2;"),
        ("completion-product-truncation", "wire [11:0] completion_product", "wire [10:0] completion_product"),
        ("combined-floor", "assign score = {2'b0, entropy_term} + {1'b0, completion_term};",
         "assign score = (entropy_product * 7 + completion_product * 31) / 217;"),
    )
    evidence = {}
    for name, anchor, replacement in mutations:
        # Each mutant has a separately compiled/rerun clean control.
        control = analyze(run_grid(args, name + "-control", after, registered))
        require_agreement(control)
        mutated = replace_once(after, anchor, replacement)
        result = analyze(run_grid(args, name, mutated, registered))
        try:
            require_agreement(result)
        except AssertionError:
            evidence[name] = result
        else:
            raise AssertionError(f"survived hardware mutation: {name}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {"before-scores.csv": csv_bytes(before_rows), "after-scores.csv": csv_bytes(after_rows),
                 "width-and-shift-only-scores.csv": csv_bytes(reciprocal_rows)}
    summary = {"base": args.base, "before": before_result, "after": after_result,
               "width_and_shift_only": analyze(reciprocal_rows),
               "mutations": evidence, "killed": len(evidence), "survived": 0,
               "clean_controls": len(mutations), "failed_controls": 0,
               "source_sha256": {"before_rtl": sha256(before.encode("utf-8")).hexdigest(),
                                 "after_rtl": sha256(after.encode("utf-8")).hexdigest(),
                                 "registered": sha256(registered.encode("utf-8")).hexdigest()},
               "artifact_sha256": {name: sha256(data).hexdigest() for name, data in artifacts.items()}}
    artifacts["summary.json"] = (json.dumps(summary, sort_keys=True, indent=2) + "\n").encode("utf-8")
    for name, data in artifacts.items():
        (args.output_dir / name).write_bytes(data)
    print(json.dumps(summary, sort_keys=True))
    for name, data in artifacts.items():
        print(f"{name} sha256={sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
