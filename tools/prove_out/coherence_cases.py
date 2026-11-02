"""Finite Python-only coherence evidence; no core changes or physical claims.

The coordinate sweep varies both ordinary theta inputs with other fields fixed.
Fractional counterexamples record behavior outside the stated finite [0,1]
input contract. Observing a returned result does not extend that contract.
"""
import csv
import io

from rpp import address_canonical as canonical
from rpp.coherence import compute_coherence, compute_coherence_score


def _theta_checks():
    rows = []
    for source in range(1, 28):
        for target in range(1, 28):
            a = canonical.RPPAddress(source, 1, 0, 0.0, 0)
            b = canonical.RPPAddress(target, 1, 0, 0.0, 0)
            # Modulo directions independently declare the circular distance;
            # the actual core helper uses abs/min. Comparison is exact.
            steps = min((target - source) % 27, (source - target) % 27)
            expected = 1.0 - 0.30 * (steps / 13.5)
            rows.append({"source_theta": source, "target_theta": target,
                         "circular_steps": steps, "actual": canonical.coherence(a, b),
                         "declared": expected})
    scores = {(row["source_theta"], row["target_theta"]): row["actual"] for row in rows}
    if len(scores) != 729:
        raise AssertionError("incomplete ordinary theta-pair domain")
    for row in rows:
        row["reverse"] = scores[row["target_theta"], row["source_theta"]]
    formula = sum(row["actual"] != row["declared"] for row in rows)
    symmetry = sum(row["actual"] != row["reverse"] for row in rows)
    bounds = sum(not 0 <= row["actual"] <= 1 for row in rows)
    if formula or symmetry or bounds:
        raise AssertionError("ordinary circular coherence contract failed")
    summary = {"ordinary_pairs": len(rows), "actual_coherence_calls": len(rows),
               "symmetry_checks": len(rows), "formula_mismatches": formula,
               "symmetry_mismatches": symmetry, "range_failures": bounds,
               "wrap_pairs": sum(abs(row["source_theta"] - row["target_theta"]) > 13.5 for row in rows),
               "minimum": min(scores.values()), "maximum": max(scores.values()),
               "fixed_fields": {"phi": 1, "omega": 0, "radius": 0.0, "reserved": 0},
               "declared_formula": "1 - 0.30 * min((target-source)%27, (source-target)%27) / 13.5",
               "comparison": "exact float equality; no tolerance",
               "scope": "ordinary theta 1..27 only; separate from native RTL orientation probes"}
    return summary, rows


def _fractional_counterexamples():
    edges = (("negative", -0.25, "-0.25"), ("above-one", 1.25, "1.25"),
             ("nan", float("nan"), "NaN"),
             ("positive-infinity", float("inf"), "+Infinity"),
             ("negative-infinity", float("-inf"), "-Infinity"))
    rows = []
    for driver in ("engagement", "completion"):
        for kind, value, tag in edges:
            engagement, completion = (value, 0.0) if driver == "engagement" else (0.0, value)
            score = compute_coherence_score(engagement, completion)
            result = compute_coherence(engagement, completion)
            if score != result.score:
                raise AssertionError("fractional score APIs disagree")
            rows.append({"case": driver + "-" + kind, "driver": driver, "input_class": kind,
                         "engagement": tag if driver == "engagement" else "0.0",
                         "completion": tag if driver == "completion" else "0.0",
                         "score_api": score, "score": result.score,
                         "binding_coefficient": result.binding_coefficient,
                         "stage": result.complecount, "state": result.state.name,
                         "binding_valid": result.is_binding_valid,
                         "completion_flag": result.completion_flag,
                         "engagement_weight": result.engagement_weight,
                         "completion_weight": result.completion_weight})
    return rows


def run_checks():
    """Return deterministic, strict-JSON-safe evidence without paths, times or I/O."""
    summary, pairs = _theta_checks()
    counterexamples = _fractional_counterexamples()
    return {"summary": {"ordinary_theta": summary,
                        "fractional_inputs": {"input_cases": len(counterexamples),
                            "score_api_calls": len(counterexamples),
                            "full_result_api_calls": len(counterexamples),
                            "input_encoding": "all input values are strings, including NaN/+Infinity/-Infinity",
                            "scope": "observed behavior outside finite [0,1]; no new accepted domain or core fix"}},
            "counterexamples": counterexamples, "theta_rows": pairs}


def csv_artifacts(result):
    """Render all ordered pairs and tagged counterexamples with explicit LF bytes."""
    outputs = {}
    for name, rows in (("python-theta-pairs.csv", result["theta_rows"]),
                       ("fractional-input-counterexamples.csv", result["counterexamples"])):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        outputs[name] = stream.getvalue().encode("utf-8")
    return outputs
