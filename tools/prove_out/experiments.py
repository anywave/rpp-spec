"""Deterministic one-input sweeps of shipped scalar computations and decisions."""

import argparse
import csv
from pathlib import Path

from rpp.address_canonical import RPPAddress, coherence
from rpp.coherence import compute_coherence, compute_binding_coefficient, is_binding_valid, compute_complecount
from rpp.consent import ConsentContext, ConsentState, check_consent
from rpp.geometry import TorusPoint, ToroidalStateVector, antipodal, verify_self_coherence
from rpp.hrda import HRDAProcessor
from rpp.consent import Sector
from rpp.address import from_components
from rpp.address_canonical import ThetaSector
from hardware.verilog.spintronic_sim import SpinSite


def number(x):
    return format(x, ".12g") if isinstance(x, float) else str(x)


def sweeps():
    rows = []
    def add(family, changed, value, result, units, decision=""):
        rows.append(dict(family=family, changed_input=changed, input_value=number(value),
                         result=number(result), units=units, decision=decision))
    for changed in ("engagement", "completion"):
        for tick in range(11):
            value = tick / 10
            result = compute_coherence(value, 0.5) if changed == "engagement" else compute_coherence(0.5, value)
            add("weighted_progress", changed + " (other=0.5)", value, result.score, "policy points /674",
                f"binding={int(result.is_binding_valid)};stage={result.complecount}")
    for score in (0, 96, 97, 136, 137, 138, 192, 193, 288, 289, 385, 386, 481, 482, 577, 578, 673, 674):
        coefficient = compute_binding_coefficient(score)
        add("binding_stage", "raw score", score, coefficient, "dimensionless score/674",
            f"binding={int(is_binding_valid(coefficient))};stage={compute_complecount(score)}")
    fixed = RPPAddress(theta=1, phi=1, omega=0, radius=0.0)
    for name, values in [("theta", range(1, 28)), ("phi", range(1, 7)),
                         ("omega", range(5)), ("radius", [i / 10 for i in range(11)])]:
        for value in values:
            fields = dict(theta=1, phi=1, omega=0, radius=0.0)
            fields[name] = value
            add("address_similarity", name + " (others fixed)", value, coherence(fixed, RPPAddress(**fields)),
                "dimensionless 1-distance", "no direct consent decision")
    processor = HRDAProcessor()
    for name in ("hrv", "eeg", "breath"):
        for tick in range(11):
            fields = dict(hrv=0.5, eeg=0.5, breath=0.5)
            fields[name] = tick / 10
            add("somatic_index", name + " (others=0.5; smoothing off)", tick / 10,
                processor.compute_somatic_coherence(**fields, apply_smoothing=False), "integer /15",
                "input channels supplied; no sensor validation")
    primary = TorusPoint(0.5, 0.7, 1.0)
    expected = antipodal(primary)
    for tick in range(11):
        drift = tick / 500
        observed = TorusPoint(expected.theta + drift, expected.phi, expected.amplitude)
        tsv = ToroidalStateVector(primary, [primary], [observed], 0.0, 0.0, TorusPoint(0.0, 0.0, 0.0))
        result = verify_self_coherence(tsv)
        add("complement_consistency", "theta drift radians", drift, result["coherence_score"], "dimensionless",
            f"coherent={int(result['coherent'])};anomalies={result['anomaly_count']}")
    for value in (0.0, 0.399999, 0.4, 0.400001, 0.847, 1.0):
        context = ConsentContext(ConsentState.FULL_CONSENT, soul_id="synthetic-local-id", coherence_score=value)
        result = check_consent(theta=96, phi=450, operation="write", context=context)
        add("consent_input", "caller coherence (other permissions fixed)", value, int(result.allowed), "allow=1/deny=0",
            "ethereal write threshold 0.4; not Ra 137/674")
    for tick in range(11):
        site = SpinSite(repitan=1, rac=1, shell=0)
        site.excite(0.8)
        site.step(dt_ns=tick * 10, omega=0.01)
        add("spin_site_simulation", "simulated duration ns (same initial state)", tick * 10, site.coherence,
            "simulated transverse magnitude", f"active={int(site.active)};not measured hardware")
    return rows


def sector_rows():
    rows = []
    for theta in range(512):
        address = from_components(0, theta, 0, 0)
        projected = max(1, min(27, (theta * 27) // 512 + 1))
        rows.append(dict(theta_v1=theta, v1_name=address.sector_name,
                         consent_name=Sector.from_theta(theta).value,
                         projected_theta_v2=projected, v2_name=ThetaSector.from_theta(projected).name,
                         same_name=int(address.sector_name.upper() == ThetaSector.from_theta(projected).name)))
    return rows


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render(rows):
    lines = ["# Deterministic one-input sweeps", "",
             "All inputs are synthetic supplied values. These computations are policy/similarity/consistency",
             "quantities, not validated measures of a person, truth, or physical coherence. No clock, random",
             "source, model, network request, key generation or public-network operation is used.", "",
             "| Family | Changed input | Value | Result | Units | Decision |",
             "|---|---|---:|---:|---|---|"]
    for row in rows:
        lines.append("| " + " | ".join(str(v) for v in row.values()) + " |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("tools/prove_out/results"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = sweeps()
    sectors = sector_rows()
    write_csv(args.output_dir / "coherence-sweeps.csv", rows)
    write_csv(args.output_dir / "sector-map.csv", sectors)
    (args.output_dir / "SWEEPS.md").write_text(render(rows), encoding="utf-8", newline="\n")
    print(f"SUMMARY coherence_rows={len(rows)} sector_rows={len(sectors)} same_name={sum(r['same_name'] for r in sectors)} different_name={sum(not r['same_name'] for r in sectors)}")


if __name__ == "__main__":
    main()
