"""CX-017 fixed-bar experiments; native simulation is not a device measurement."""
import argparse
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess

import rpp
from rpp.address_canonical import RPPAddress, coherence
from rpp.coherence import compute_coherence, compute_coherence_score
from tools.prove_out.evidence import evidence_bytes
from tools.prove_out import rtl_repair

AFF_DOMAIN = {(t, p, w, r) for t in range(14) for p in range(6) for w in range(5) for r in range(256)}
ROOT = Path(__file__).resolve().parents[2]
BASE = "94c372be9d12d30d94e69afc39569aadedea1d69"


def csv_data(header, rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return output.getvalue().encode()


def native(args, name, bench, top, sources):
    directory = args.work_dir / name
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, text in sources.items():
        path = directory / filename
        path.write_text(text, encoding="utf-8", newline="\n")
        paths.append(str(path))
    command = [str(args.iverilog)] + (["-B", str(args.ivl_dir)] if args.ivl_dir else [])
    bench_copy = directory / Path(bench).name
    bench_copy.write_text((args.repo / bench).read_text(encoding="utf-8").replace("$finish;", "$finish(0);"), encoding="utf-8", newline="\n")
    command += ["-g2012", "-s", top, "-o", str(directory / "image.vvp"), str(bench_copy), *paths]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=True, timeout=120)
    (directory / "compile.log").write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    command = [str(args.vvp)] + (["-M", str(args.ivl_dir)] if args.ivl_dir else []) + [str(directory / "image.vvp")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=True, timeout=120)
    (directory / "run.log").write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    return result.stdout


def affinity_rows(text):
    rows = {}
    for line in text.splitlines():
        if not line.startswith("AFF,"):
            raise ValueError("unknown affinity output row")
        row = tuple(map(int, line.split(",")[1:]))
        if len(row) != 12 or row[:4] in rows:
            raise ValueError("duplicate or malformed affinity row")
        rows[row[:4]] = row
    if set(rows) != AFF_DOMAIN:
        raise ValueError("missing or unknown affinity input")
    return [rows[key] for key in sorted(rows)]


def rtl_affinity(key, binding="consolidated"):
    t, p, w, r = key
    if binding == "canonical":
        return max(0, 255 - (20 * t * 77 // 256 + 51 * p * 102 // 256 + 64 * w * 51 // 256 + r * 26 // 256))
    weighted = 77 * min(255, 20 * t) + 102 * (51 * p) + 51 * min(255, 64 * w) + 26 * r
    return 255 - (weighted >> 8)


def python_affinity(key, reserved=0):
    t, p, w, r = key
    return coherence(RPPAddress(1, 1, 0, 0.0), RPPAddress(1 + t, 1 + p, w, r / 255, reserved))


def analyze_affinity(rows):
    summary = dict(points=len(rows), python_formula_mismatches=0,
                   python_bounds_failures=0, symmetry_mismatches=0)
    names = ("consolidated", "canonical")
    summary["bindings"] = {name: dict(rtl_formula_mismatches=0, threshold_mismatches=0,
        threshold_score_dependence=0, rtl_bounds_failures=0, exact_scaled_disagreements=0,
        maximum_diagnostic_byte255_error=0.0) for name in names}
    values = {}
    for row in rows:
        key = t, p, w, r = row[:4]
        actual = python_affinity(key)
        expected = 1 - (0.30 * (t / 13.5) + 0.40 * (p / 5) + 0.20 * (w / 4) + 0.10 * (r / 255))
        summary["python_formula_mismatches"] += actual != expected
        summary["python_bounds_failures"] += not 0 <= actual <= 1
        for index, name in enumerate(names):
            score, repeat, zero_valid, full_valid = row[4 + index * 4:8 + index * 4]
            binding = summary["bindings"][name]
            binding["rtl_formula_mismatches"] += score != rtl_affinity(key, name)
            binding["rtl_bounds_failures"] += not 0 <= score <= 255
            binding["threshold_score_dependence"] += score != repeat
            binding["threshold_mismatches"] += (zero_valid, full_valid) != (1, int(score == 255))
            binding["exact_scaled_disagreements"] += actual != score / 255
            binding["maximum_diagnostic_byte255_error"] = max(binding["maximum_diagnostic_byte255_error"], abs(actual - score / 255))
        reverse = coherence(RPPAddress(1 + t, 1 + p, w, r / 255), RPPAddress(1, 1, 0, 0.0))
        summary["symmetry_mismatches"] += actual != reverse
        values[key] = actual, row[4], row[8]
    summary["minimum_python"] = min(value[0] for value in values.values())
    summary["minimum_rtl_byte"] = {name: min(value[index + 1] for value in values.values()) for index, name in enumerate(names)}
    summary["wrong_direction"] = dict.fromkeys(("python", *names), 0)
    pairs = 0
    for key, value in values.items():
        for axis, maximum in enumerate((13, 5, 4, 255)):
            if key[axis] == maximum:
                continue
            neighbor = list(key)
            neighbor[axis] += 1
            later = values[tuple(neighbor)]
            summary["wrong_direction"]["python"] += later[0] > value[0]
            for index, name in enumerate(names):
                summary["wrong_direction"][name] += later[index + 1] > value[index + 1]
            pairs += 1
    summary["adjacent_driver_pairs"] = pairs
    return summary


def require_affinity(summary):
    """Reject changed weights, threshold dependence, wrong drivers and bounds."""
    fields = ("rtl_formula_mismatches", "threshold_mismatches", "threshold_score_dependence", "rtl_bounds_failures")
    if (any(summary[key] for key in ("python_formula_mismatches", "python_bounds_failures", "symmetry_mismatches"))
            or any(binding[key] for binding in summary["bindings"].values() for key in fields)
            or any(summary["wrong_direction"].values()) or summary["points"] != len(AFF_DOMAIN)):
        raise AssertionError("affinity profile contract failed")



def orientation(text):
    rows = {}
    for line in text.splitlines():
        if not line.startswith("ORI,"):
            raise ValueError("unknown orientation row")
        row = tuple(map(int, line.split(",")[1:]))
        if len(row) != 5 or row[:3] in rows:
            raise ValueError("duplicate or malformed orientation row")
        rows[row[:3]] = row[3:]
    domain = {(a, b, m) for a in range(1, 28) for b in range(1, 28) for m in range(8)}
    if set(rows) != domain:
        raise ValueError("incomplete orientation grid")
    wrong = 0
    for (a, b, m), scores in rows.items():
        distance = min(abs(a - b), 27 - abs(a - b))
        expected = tuple(rtl_affinity((distance, 5, 4, 255), name) for name in ("consolidated", "canonical"))
        wrong += scores != expected or scores != rows[b, a, m ^ 7]
    if wrong:
        raise AssertionError("native wrap/reverse contract failed")
    return [(*key, *rows[key]) for key in sorted(rows)]


def python_checks():
    wrong = points = 0
    for e in range(101):
        for c in range(101):
            points += 1
            value = compute_coherence_score(e / 100, c / 100)
            wrong += value != int(165 * (e / 100)) + int(509 * (c / 100)) or not 0 <= value <= 674
            if e:
                wrong += value < compute_coherence_score((e - 1) / 100, c / 100)
            if c:
                wrong += value < compute_coherence_score(e / 100, (c - 1) / 100)
    base = python_affinity((13, 5, 4, 255))
    reserved_values = [python_affinity((13, 5, 4, 255), reserved) for reserved in range(8192)]
    irrelevant = sum(value != base for value in reserved_values)
    if wrong or irrelevant or points != 10201 or len(reserved_values) != 8192:
        raise AssertionError("Python formula/driver/irrelevance contract failed")
    return {"ra_fraction_points": points, "ra_formula_driver_failures": wrong,
            "affinity_reserved_probes": len(reserved_values), "affinity_irrelevance_failures": irrelevant,
            "reserved_theta31_similarity": coherence(RPPAddress(1, 1, 0, 0.0), RPPAddress(31, 1, 0, 0.0)),
            "null_self_similarity": coherence(RPPAddress(0, 1, 0, 0.0), RPPAddress(0, 1, 0, 0.0))}


def ra_evidence(args):
    spiral = (args.repo / "hardware/verilog/spiral_ra_coherence.v").read_text(encoding="utf-8")
    registered = (args.repo / "hardware/verilog/coherence_evaluator_ra.v").read_text(encoding="utf-8")
    rows = rtl_repair.run_grid(args, "ra-current", spiral, registered)
    summary = rtl_repair.analyze(rows)
    rtl_repair.require_agreement(summary)
    mutations = {}
    for name, which, before, after in (
        ("registered-score-shift", 1, "coherence_score <= total_score;", "coherence_score <= total_score << 1;"),
        ("completion-product-width", 0, "wire [11:0] completion_product", "wire [10:0] completion_product"),
    ):
        rtl_repair.require_agreement(rtl_repair.analyze(rtl_repair.run_grid(args, name + "-clean", spiral, registered)))
        sources = [spiral, registered]
        sources[which] = rtl_repair.replace_once(sources[which], before, after)
        changed = rtl_repair.analyze(rtl_repair.run_grid(args, name, *sources))
        try:
            rtl_repair.require_agreement(changed)
        except AssertionError:
            mutations[name] = {"killed": True, "clean_control_passed": True}
        else:
            raise AssertionError("survived native Ra mutation")
    summary["native_mutations"] = mutations
    # Compare every repeated threshold without interpreting normalized byte as a coefficient.
    scores = {}
    for row in rows:
        key, score = row[:2], row[3:6]
        if key in scores and scores[key] != score:
            raise AssertionError("threshold changed a score")
        scores[key] = score
    log = native(args, "ra-completion", "tools/prove_out/compare_coherence_tb.v", "CompareCoherence",
                 {"spiral_ra_coherence.v": spiral, "coherence_evaluator_ra.v": registered})
    flags = {}
    for line in log.splitlines():
        if not line.startswith("POINT,"):
            raise ValueError("unknown completion row")
        row = tuple(map(int, line.split(",")[1:]))
        if len(row) != 9 or row[:2] in flags:
            raise ValueError("duplicate or malformed completion row")
        if row[-1] not in (0, 1) or row[-1] != int(row[1] == 7):
            raise AssertionError("registered completion expression changed")
        flags[row[:2]] = row[-1]
    if set(flags) != {(e, c) for e in range(32) for c in range(8)}:
        raise ValueError("incomplete completion grid")
    summary["completion_flag_disagreements"] = sum(flag != compute_coherence(e / 31, c / 7).completion_flag
                                                 for (e, c), flag in flags.items())
    summary["normalized_byte_formula"] = "(score * 38) >> 8; separate from coefficient"
    summary["threshold_irrelevance_points"] = len(rows)
    return summary, rtl_repair.csv_bytes(rows)


def other_models(args, source):
    from hardware.verilog.hdl_simulation import CoherenceEvaluator as Legacy
    from hardware.verilog.hdl_simulation_canonical import CoherenceEvaluator as Canonical
    from hardware.verilog.hdl_simulation_ra import CoherenceEvaluator_Ra as Floating, GREEN_PHI, ANKH
    from tools.prove_out.experiments import sweeps
    def check(text):
        rows = {}
        model = Legacy()
        for line in text.splitlines():
            values = tuple(map(int, line.removeprefix("LEG,").split(",")))
            if not line.startswith("LEG,") or len(values) != 4 or values[:2] in rows:
                raise ValueError("invalid legacy row")
            e, c, score, valid = values
            if valid not in (0, 1) or not 0 <= score <= 127:
                raise AssertionError("invalid legacy signal range")
            model.evaluate(e, c, 64)
            if (score, bool(valid)) != (model.coherence_score, model.coherence_valid):
                raise AssertionError("legacy Python/RTL disagreement")
            rows[e, c] = values
        if set(rows) != {(e, c) for e in range(64) for c in range(32)}:
            raise ValueError("incomplete legacy grid")
        return rows
    def invoke(name, text):
        return native(args, name, "tools/prove_out/verdict_tb.v", "CX017Legacy", {"spiral_consolidated.v": text})
    legacy = check(invoke("legacy-current", source))
    check(invoke("legacy-clean", source))
    altered = rtl_repair.replace_once(source, "wire [6:0] coherence_score;", "wire [7:0] coherence_score;")
    try:
        check(invoke("legacy-width", altered))
    except AssertionError:
        killed = True
    else:
        raise AssertionError("survived legacy width mutation")
    canonical, floating = Canonical(), Floating()
    bad, float_bad, scaled_different = 0, 0, 0
    for e in range(32):
        for c in range(8):
            canonical.evaluate(e, c, 137)
            floating.evaluate(e, c)
            bad += canonical.coherence_score != compute_coherence_score(e / 31, c / 7)
            float_bad += floating.coherence_score != GREEN_PHI * (e / 31) + ANKH * (c / 7)
            scaled_different += floating.coherence_score_x100 != canonical.coherence_score
    if bad or float_bad:
        raise AssertionError("separate Python model formula changed")
    reference = sweeps()
    fields = tuple(reference[0])
    return {"legacy_points": len(legacy), "legacy_python_rtl_mismatches": 0,
            "legacy_entropy_decreases": sum(legacy[e + 1, c][2] < legacy[e, c][2] for e in range(63) for c in range(32)),
            "legacy_width_mutation": {"killed": killed, "clean_control_passed": True},
            "python_canonical_points": 256, "python_canonical_mismatches": bad,
            "python_floating_points": 256, "python_floating_formula_mismatches": float_bad,
            "python_floating_maximum": GREEN_PHI + ANKH, "floating_x100_vs_674_disagreements": scaled_different,
            "reference_sweep_rows": len(reference), "reference_families": sorted({row["family"] for row in reference})}, {
                "legacy.csv": csv_data(("entropy", "completion", "score", "valid"), [legacy[key] for key in sorted(legacy)]),
                "reference-sweeps.csv": csv_data(fields, ([row[field] for field in fields] for row in reference))}


def run(args):
    from tools.prove_out.sector_verdict import run_sector
    if not Path(rpp.__file__).resolve().is_relative_to(args.repo):
        raise ValueError("imported rpp is outside the selected checkout")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    python = python_checks()
    ra, ra_bytes = ra_evidence(args)
    source = (args.repo / "hardware/verilog/spiral_consolidated.v").read_text(encoding="utf-8")
    models, model_artifacts = other_models(args, source)
    canonical = (args.repo / "hardware/verilog/rpp_canonical.v").read_text(encoding="utf-8")
    sources = {"spiral_consolidated.v": source, "rpp_canonical.v": canonical}
    rows = affinity_rows(native(args, "affinity-current", "tools/prove_out/verdict_tb.v", "CX017Affinity",
                                sources))
    affinity = analyze_affinity(rows)
    require_affinity(affinity)
    mutants = (
        ("affinity-weight", "spiral_consolidated.v", "W_PHI    = 8'd102", "W_PHI    = 8'd103"),
        ("threshold-enters-score", "spiral_consolidated.v", "assign coherence_score = 8'd255 - weighted_dist;",
         "assign coherence_score = 8'd255 - weighted_dist + threshold[0];"),
        ("canonical-weight", "rpp_canonical.v", "W_PHI    = 8'd102", "W_PHI    = 8'd103"),
    )
    mutation_results = {}
    for name, filename, before, after in mutants:
        control = analyze_affinity(affinity_rows(native(args, name + "-clean", "tools/prove_out/verdict_tb.v",
                                                      "CX017Affinity", sources)))
        require_affinity(control)
        changed = dict(sources)
        changed[filename] = rtl_repair.replace_once(changed[filename], before, after)
        result = analyze_affinity(affinity_rows(native(args, name, "tools/prove_out/verdict_tb.v",
                                                     "CX017Affinity", changed)))
        try:
            require_affinity(result)
        except AssertionError:
            mutation_results[name] = {"killed": True, "clean_control_passed": True}
        else:
            raise AssertionError("survived native affinity mutation")
    oriented = orientation(native(args, "orientation-current", "tools/prove_out/verdict_tb.v", "CX017Orientation", sources))
    for name, filename, before, after in (
        ("consolidated-wrap", "spiral_consolidated.v", "(t_diff_a < t_diff_b) ? t_diff_a : t_diff_b", "t_diff_a"),
        ("canonical-wrap", "rpp_canonical.v", "(theta_diff > 5'd13) ? (5'd27 - theta_diff) : theta_diff", "theta_diff"),
    ):
        orientation(native(args, name + "-clean", "tools/prove_out/verdict_tb.v", "CX017Orientation", sources))
        changed = dict(sources)
        changed[filename] = rtl_repair.replace_once(changed[filename], before, after)
        try:
            orientation(native(args, name, "tools/prove_out/verdict_tb.v", "CX017Orientation", changed))
        except AssertionError:
            mutation_results[name] = {"killed": True, "clean_control_passed": True}
        else:
            raise AssertionError("survived native orientation mutation")
    affinity["native_orientation_points"] = len(oriented)
    sector = run_sector(args)
    by_key = {row[:4]: row for row in rows}
    examples = list(sector["counterexamples"])
    for key in ((13, 5, 4, 255), (13, 0, 0, 0), (0, 5, 0, 0)):
        examples.append({"claim": "Python affinity equals RTL byte/255", "input": str(key),
                         "python": format(python_affinity(key), ".17g"),
                         "rtl": f'consolidated={by_key[key][4]}/255; canonical={by_key[key][8]}/255'})
    examples.append({"claim": "registered completion equals derived Python completion",
                     "input": "entropy=0 completion=7", "python": "False", "rtl": "True"})
    artifacts = dict(sector["artifacts"])
    artifacts.update(model_artifacts)
    artifacts["orientation.csv"] = csv_data(("src_theta", "dst_theta", "endpoint_reversals", "consolidated", "canonical"), oriented)
    artifacts.update({"ra.csv": ra_bytes, "affinity.csv": csv_data(
        ("theta_distance", "phi_distance", "omega_distance", "radius_byte_distance",
         "consolidated_score0", "consolidated_score255", "consolidated_valid0", "consolidated_valid255",
         "canonical_score0", "canonical_score255", "canonical_valid0", "canonical_valid255"), rows)})
    artifacts["counterexamples.csv"] = csv_data(("claim", "input", "python", "rtl"),
                                               ([row[key] for key in ("claim", "input", "python", "rtl")] for row in examples[:24]))
    summary = {"base": BASE, "criteria_sha256": sha256(evidence_bytes(args.repo / "tools/prove_out/VERDICT_CRITERIA.md")).hexdigest(),
               "python": python, "ra": ra, "affinity": affinity, "sector": sector["summary"], "other_models": models,
               "native_affinity_mutations": mutation_results,
               "source_sha256": {name: sha256(evidence_bytes(args.repo / name)).hexdigest() for name in (
                   "rpp/coherence.py", "rpp/address.py", "rpp/address_canonical.py", "rpp/sector_router.py",
                   "hardware/verilog/spiral_ra_coherence.v", "hardware/verilog/coherence_evaluator_ra.v",
                   "hardware/verilog/spiral_consolidated.v", "hardware/verilog/rpp_canonical.v",
                   "hardware/verilog/spintronic_sim.py", "hardware/verilog/hdl_simulation.py",
                   "hardware/verilog/hdl_simulation_canonical.py", "hardware/verilog/hdl_simulation_ra.py",
                   "tools/prove_out/experiments.py", "rpp/geometry.py", "rpp/hrda.py", "rpp/consent.py",
                   "rust/rpp-core/src/canonical.rs", "DECISIONS.md")},
               "readouts": {"coherence": {"verdict": "NOT PROVABLE", "generic_public_display": False,
                                            "reason": "Unidentified producer; unlike profile outputs are not one metric."},
                            "sector": {"verdict": "PROVED", "generic_public_display": False,
                                       "scope": "Named ordinary address partitions only; no content or permission inference."}},
               "artifacts_sha256": {name: sha256(data).hexdigest() for name, data in sorted(artifacts.items())}}
    artifacts["summary.json"] = (json.dumps(summary, sort_keys=True, indent=2) + "\n").encode()
    for name, data in artifacts.items():
        (args.output_dir / name).write_bytes(data)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iverilog", type=Path, required=True)
    parser.add_argument("--vvp", type=Path, required=True)
    parser.add_argument("--cargo", type=Path)
    parser.add_argument("--ivl-dir", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.repo = ROOT
    for name in ("work_dir", "output_dir"):
        value = getattr(args, name).resolve()
        if value.is_relative_to(ROOT):
            parser.error("write experiment artifacts outside the checkout")
        setattr(args, name, value)
    summary = run(args)
    print(json.dumps({"readouts": summary["readouts"], "affinity_points": summary["affinity"]["points"],
                      "ra_points": summary["ra"]["points"]}, sort_keys=True))


if __name__ == "__main__":
    main()
