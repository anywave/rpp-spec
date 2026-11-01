"""CX-005 finite policy coverage and actual additional RTL comparison evidence."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from rpp.address_canonical import RPPAddress, compute_fallback
from rpp.coherence import compute_coherence, compute_complecount, is_binding_valid, compute_binding_coefficient
from rpp.consent_header import ConsentState, derive_consent_state
from rpp.sector_router import RoutableSector, can_access_sector
from rpp.transitions import FallbackGate
from tools.prove_out.experiments import sector_rows, write_csv


THRESHOLDS = (0, 136, 137, 138, 299, 300, 499, 500, 673, 674, 675, 1023)


def policy_rows():
    return [dict(score=score, binding=int(is_binding_valid(compute_binding_coefficient(score))),
                 stage=compute_complecount(score)) for score in range(675)]


def access_rows():
    return [dict(state=state.name, sector=sector.name, at_zero=int(can_access_sector(state, sector, 0)),
                 at_674=int(can_access_sector(state, sector, 674)))
            for state in ConsentState for sector in RoutableSector]


def sector_table():
    rows = sector_rows()
    lines = ["# All 512 legacy theta projections", "",
             "Informational theta projection only: v2=floor(27*v1/512)+1. Radius is unresolved.",
             "Every v1 theta equivalence class appears once; other v1 address fields do not choose its sector.",
             "Names are compared as labels, without claiming content equivalence or an invertible migration.", "",
             "| v1 theta | v1 label | projected v2 theta | v2 label | same label |",
             "|---:|---|---:|---|---:|"]
    for row in rows:
        lines.append(f"| {row['theta_v1']} | {row['v1_name']} | {row['projected_theta_v2']} | {row['v2_name']} | {row['same_name']} |")
    return "\n".join(lines) + "\n"


def read_log(path):
    """Validate every expected input exactly once before producing counts."""
    scores, derives, fallbacks, triggers = {}, {}, {}, {}
    buckets = {"SCORE": (scores, 3, 10), "DERIVE": (derives, 2, 3),
               "FALLBACK": (fallbacks, 4, 8), "TRIGGER": (triggers, 1, 4)}
    for line in path.read_text(encoding="utf-8").splitlines():
        name, _, values = line.partition(",")
        if name not in buckets:
            continue
        bucket, width, expected_length = buckets[name]
        fields = tuple(map(int, values.split(",")))
        if len(fields) != expected_length or fields[:width] in bucket:
            raise ValueError("Malformed or duplicate RTL evidence row")
        bucket[fields[:width]] = fields[width:]
    expected = (
        (scores, {(e, c, t) for e in range(32) for c in range(8) for t in THRESHOLDS}),
        (derives, {(s, v) for s in range(16) for v in range(2)}),
        (fallbacks, {(t, p, o, v) for t in range(1, 28) for p in range(6) for o in range(5) for v in range(256)}),
        (triggers, {(n,) for n in range(34)}),
    )
    if any(set(bucket) != domain for bucket, domain in expected):
        raise ValueError("RTL evidence grid incomplete or outside declared domain")
    return scores, derives, fallbacks, triggers


def analyze(path):
    scores, derives, fallbacks, triggers = read_log(path)
    result = dict(score_points=len(scores), derivation_points=len(derives),
                  fallback_points=len(fallbacks), trigger_points=len(triggers),
                  log_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    score_bad, valid_bad, decreases = Counter(), Counter(), Counter()
    for (e, c, threshold), fields in scores.items():
        reference = compute_coherence(e / 31, c / 7)
        for index, name in enumerate(("exact", "approximate", "lut")):
            score_bad[name] += fields[index] != reference.score
            valid_bad[name] += bool(fields[index + 3]) != (reference.score >= threshold)
            if threshold == 137:
                for axis in (0, 1):
                    adjacent = (e + (axis == 0), c + (axis == 1), threshold)
                    if adjacent in scores:
                        decreases[f"{name}_{'entropy' if axis == 0 else 'completion'}"] += scores[adjacent][index] < fields[index]
    result.update(score_mismatches=dict(score_bad), threshold_mismatches=dict(valid_bad), decreases=dict(decreases))
    old_names = {0: "FULL_CONSENT", 1: "DIMINISHED_CONSENT", 2: "SUSPENDED_CONSENT"}
    derivation_rows = []
    for (somatic, verbal), (state,) in sorted(derives.items()):
        # Explicit comparison wiring: boolean override -> supplied strength3 or0.
        python = derive_consent_state(somatic, 3 * verbal).name
        derivation_rows.append(dict(somatic=somatic, override=verbal, python=python,
                                    rtl=old_names[state], equal=int(python == old_names[state])))
    result["named_derivation_mismatches"] = sum(not r["equal"] for r in derivation_rows)
    fallback_bad = Counter()
    samples = []
    for (theta, phi_zero, omega, vector), (ft, fp, fo, fr) in sorted(fallbacks.items()):
        # Port uses phi0..5. Python ordinary domain uses phi1..6. This is an explicit
        # experimental adapter, not an adopted wire-format conversion.
        ref = compute_fallback(RPPAddress(theta, phi_zero + 1, omega, 128 / 255), vector)
        values = (ref.theta, ref.phi - 1, ref.omega, 128)
        actual = (ft, fp, fo, fr)
        for index, name in enumerate(("theta", "phi_zero", "omega", "radius")):
            fallback_bad[name] += actual[index] != values[index]
        fallback_bad["any"] += actual != values
        if actual != values and len(samples) < 16:
            samples.append(dict(theta=theta, phi_zero=phi_zero, omega=omega, vector=vector,
                                python_theta=ref.theta, rtl_theta=ft,
                                python_phi_zero=ref.phi - 1, rtl_phi_zero=fp,
                                python_omega=ref.omega, rtl_omega=fo))
    result["fallback_component_mismatches"] = dict(fallback_bad)
    gate = FallbackGate()
    trigger_bad = 0
    for (n,), (score, active, counter) in sorted(triggers.items()):
        # Only the consecutive-cycle gate is compared: invert the condition because
        # the RTL detects high input while Python FallbackGate detects low input.
        expected = gate.update(136 if score >= 137 else 137)
        trigger_bad += bool(active) != expected
        if counter != min(gate.cycles_below, 15):
            raise ValueError("Unexpected trigger counter behavior")
    result["condition_inverted_trigger_mismatches"] = trigger_bad
    result["trigger_first_true_indices"] = [n for (n,), (_, active, _) in sorted(triggers.items())
                                             if active and (n == 0 or not triggers[n - 1,][1])]
    return result, derivation_rows, samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl-log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("tools/prove_out/results/completion"))
    args = parser.parse_args()
    summary, derives, samples = analyze(args.rtl_log)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "policy.csv", policy_rows())
    write_csv(args.output_dir / "sector-access.csv", access_rows())
    write_csv(args.output_dir / "consent-derivation.csv", derives)
    write_csv(args.output_dir / "fallback-counterexamples.csv", samples)
    (args.output_dir / "sector-projection.md").write_text(sector_table(), encoding="utf-8", newline="\n")
    (args.output_dir / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
