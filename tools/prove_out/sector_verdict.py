"""CX-017 informational sector partitions and native RTL; no core edits."""
import argparse
from collections import Counter
import csv
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from rpp.address import from_components, from_raw
from rpp.address_canonical import RPPAddress, ThetaSector, adjacent_sectors
from hardware.verilog.spintronic_sim import v1_to_v2
from tools.prove_out.evidence import evidence_bytes

V1 = ("Gene", "Memory", "Witness", "Dream", "Bridge", "Guardian", "Emergence", "Meta")
RANGES = ((1, 3), (4, 6), (7, 10), (11, 13), (14, 17), (18, 20), (21, 24), (25, 27))
V2 = ("CORE", "GENE", "MEMORY", "WITNESS", "DREAM", "BRIDGE", "GUARDIAN", "SHADOW")
EXTRA_EDGES = {(3, 4), (4, 3), (6, 7), (7, 6)}
PROBES = ((0, 0, 0, 0), (5, 0, 0, 0), (0, 4, 0, 0), (0, 0, 255, 0),
          (0, 0, 0, 8191), (5, 4, 255, 8191), (2, 2, 128, 17), (4, 1, 127, 1))
DOMAINS = {"MAP": {(t,) for t in range(32)}, "SAME": {(s, d) for s in range(1, 28) for d in range(1, 28)},
           "ADJ": {(a, b) for a in range(8) for b in range(8)},
           "IRREL": {(r, f, v) for r in range(2) for f, n in enumerate((6, 5, 256)) for v in range(n)}}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def parse_rows(text):
    result = {kind: {} for kind in DOMAINS}
    for line in text.splitlines():
        kind, *values = line.split(",")
        if kind not in result:
            raise ValueError("unknown sector row kind")
        numbers = tuple(map(int, values))
        width = {"MAP": 1, "SAME": 2, "ADJ": 2, "IRREL": 3}[kind]
        key = numbers[:width]
        if len(numbers) != width + 1 or key in result[kind] or numbers[-1] not in range(8 if kind == "MAP" else 2):
            raise ValueError("malformed, duplicate or unknown sector output")
        result[kind][key] = numbers[-1]
    if any(set(result[kind]) != domain for kind, domain in DOMAINS.items()):
        raise ValueError("missing or out-of-domain sector input")
    return result


def ordinary_index(theta):
    matches = [index for index, (low, high) in enumerate(RANGES) if low <= theta <= high]
    require(len(matches) == 1, "ordinary sector partition gap/overlap")
    return matches[0]


def python_checks():
    rows = []
    for theta in range(512):
        require(from_components(0, theta, 0, 0).sector_name == V1[theta // 64], "legacy sector boundary")
        for field, limit in (("shell", 4), ("phi", 512), ("harmonic", 256)):
            for value in range(limit):
                values = dict(shell=0, theta=theta, phi=0, harmonic=0)
                values[field] = value
                address = from_components(**values)
                require(from_raw(address.raw).sector_name == V1[theta // 64], "legacy irrelevant field")
        rows.append(("semantic-v1-theta8", theta, theta // 64, V1[theta // 64]))
    for theta in range(1, 28):
        index = ordinary_index(theta)
        require(ThetaSector.from_theta(theta).value == index, "canonical sector boundary")
        for field, values in (("phi", range(1, 7)), ("omega", range(5)),
                              ("radius", (v / 255 for v in range(256))), ("reserved", range(8192))):
            for value in values:
                fields = dict(theta=theta, phi=1, omega=0, radius=0.0, reserved=0)
                fields[field] = value
                require(RPPAddress(**fields).sector.value == index, "canonical irrelevant field")
        rows.append(("canonical-v2-theta27", theta, index, V2[index]))
    require([r[2] for r in rows[:512]] == sorted(r[2] for r in rows[:512]), "legacy bin direction")
    require([r[2] for r in rows[512:]] == sorted(r[2] for r in rows[512:]), "canonical bin direction")
    return dict(v1_theta_inputs=512, v1_bins=dict(Counter(r[3] for r in rows[:512])),
                v2_theta_inputs=27, v2_bins=dict(Counter(r[3] for r in rows[512:])),
                irrelevant_field_probes={"v1": 512 * (4 + 512 + 256), "v2": 27 * (6 + 5 + 256 + 8192)},
                factorization="2^28 valid v1 words factor through the 9-bit theta field; not brute-force enumeration"), rows


def characterize(rows):
    ordinary = sum(rows["MAP"][t,] != ThetaSector.from_theta(t).value for t in range(1, 28))
    same = sum(flag != int(ThetaSector.from_theta(s) == ThetaSector.from_theta(d)) for (s, d), flag in rows["SAME"].items())
    irrelevant = sum(flag != int(relation == 0) for (relation, _, _), flag in rows["IRREL"].items())
    graph = {(a, b): int(adjacent_sectors(RPPAddress(sum(RANGES[a]) // 2, 1, 0, 0.0),
                                                   RPPAddress(sum(RANGES[b]) // 2, 1, 0, 0.0))) for a, b in DOMAINS["ADJ"]}
    examples = [dict(claim="sector-sentinel", input=f"theta={t}", python=ThetaSector.from_theta(t).name, rtl=V2[rows["MAP"][t,]]) for t in (0, 28, 29, 30, 31)]
    examples += [dict(claim="sector-adjacency", input=f"{V2[a]}->{V2[b]}", python=str(graph[a, b]), rtl=str(flag)) for (a, b), flag in sorted(rows["ADJ"].items()) if flag != graph[a, b]]
    return dict(map_inputs=32, ordinary_inputs=27, ordinary_mismatches=ordinary, same_sector_pairs=729,
                same_sector_mismatches=same, irrelevant_field_inputs=534, irrelevant_field_mismatches=irrelevant,
                adjacency_pairs=64, adjacency_mismatches=sum(flag != graph[key] for key, flag in rows["ADJ"].items()),
                sentinel_mismatches=sum(rows["MAP"][t,] != ThetaSector.from_theta(t).value for t in (0, 28, 29, 30, 31))), examples, graph


def require_native(rows, binding="consolidated"):
    result, _, graph = characterize(rows)
    require(not any(result[k] for k in ("ordinary_mismatches", "same_sector_mismatches", "irrelevant_field_mismatches")), "native sector partition disagreement")
    require(all(flag == (graph[key] or binding == "consolidated" and key in EXTRA_EDGES) for key, flag in rows["ADJ"].items()), "characterized RTL graph changed")


def decoder_word(theta, probe):
    phi, omega, radius, reserved = PROBES[probe]
    return (theta << 27) | (phi << 24) | (omega << 21) | (radius << 13) | reserved


def parse_decoder(text):
    rows = {}
    for line in text.splitlines():
        kind, *values = line.split(",")
        row = tuple(map(int, values))
        if kind != "DEC" or len(row) != 10 or row[:2] in rows:
            raise ValueError("malformed or duplicate decoder row")
        rows[row[:2]] = row[2:]
    if set(rows) != {(t, p) for t in range(32) for p in range(8)}:
        raise ValueError("missing or out-of-domain decoder input")
    return rows


def decoder_check(rows):
    ordinary = sentinel = components = validity = 0
    examples = []
    for (theta, probe), (word, label, valid, ot, op, oo, radius, reserved) in sorted(rows.items()):
        expected = decoder_word(theta, probe)
        address = RPPAddress.from_int(expected)
        components += (word, ot, op, oo, radius, reserved) != (expected, address.theta, address.phi - 1, address.omega, (expected >> 13) & 255, address.reserved)
        validity += valid != int(address.is_valid())
        ordinary += 1 <= theta <= 27 and label != address.sector.value
        sentinel += theta not in range(1, 28) and label != address.sector.value
        require(label == (ordinary_index(theta) if 1 <= theta <= 27 else 0 if theta == 0 else 7), "decoder characterized label changed")
        if theta in (0, 28) and probe == 0:
            examples.append(dict(claim="decoder-sector-sentinel", input=f"theta={theta}", python=address.sector.name, rtl=V2[label]))
    require(not (ordinary or components or validity), "decoder ordinary label/component/validity disagreement")
    return dict(encoded_inputs=256, ordinary_inputs=216, ordinary_label_mismatches=ordinary,
                sentinel_inputs=40, sentinel_label_mismatches=sentinel, component_mismatches=components, validity_mismatches=validity), examples


def require_grids(grids):
    for binding in ("consolidated", "canonical"):
        require_native(grids[binding], binding)
    decoder_check(grids["decoder"])


def tools_projection(shell, theta, phi, harmonic, policy):
    """Tools-only D1 transcription; the shipped Python package has no migration API."""
    if policy not in {"neutral-radius", "shell-projection"}:
        raise ValueError("explicit D1 migration policy required")
    if any(type(value) is not int or not 0 <= value <= maximum for value, maximum in zip((shell, theta, phi, harmonic), (3, 511, 511, 255))):
        raise ValueError("invalid legacy field")
    return RPPAddress(theta * 27 // 512 + 1, phi * 6 // 512 + 1, harmonic * 5 // 256,
                      0.5 if policy == "neutral-radius" else shell / 3)


def d1_checks():
    rows = []
    for field in ("theta", "phi"):
        previous = 0
        for value in range(512):
            inputs = dict(shell=0, theta=64, phi=128, harmonic=64)
            inputs[field] = value
            pair = [tools_projection(**inputs, policy=p) for p in ("neutral-radius", "shell-projection")]
            expected = (inputs["theta"] * 27 // 512 + 1, inputs["phi"] * 6 // 512 + 1, inputs["harmonic"] * 5 // 256)
            require(all((a.theta, a.phi, a.omega) == expected for a in pair), "D1 forward projection formula")
            require([(a.theta, a.phi, a.omega, a.sector) for a in pair][0] == [(a.theta, a.phi, a.omega, a.sector) for a in pair][1], "D1 policies changed sector coordinates")
            current = getattr(pair[0], field)
            require(current >= previous and 1 <= current <= (27 if field == "theta" else 6), "D1 projection range/direction")
            previous = current
            rows.extend((field, value, p, a.theta, a.phi, a.omega, round(a.radius * 255), a.sector.name) for p, a in zip(("neutral-radius", "shell-projection"), pair))
    for shell in range(4):
        explicit = tools_projection(shell, 64, 128, 64, "shell-projection")
        require(v1_to_v2(shell, 64, 128, 64) == (explicit.theta, explicit.phi, explicit.omega, explicit.radius), "simulator hardcoded shell projection changed")
        for policy, expected in (("neutral-radius", 128), ("shell-projection", (0, 85, 170, 255)[shell])):
            a = tools_projection(shell, 64, 128, 64, policy)
            require(a.radius == (0.5 if policy == "neutral-radius" else shell / 3) and (a.theta, a.phi, a.omega) == (4, 2, 1), "D1 explicit radius/coordinate policy")
            require(round(a.radius * 255) == expected, "D1 radius policy")
            rows.append(("shell", shell, policy, a.theta, a.phi, a.omega, expected, a.sector.name))
    return rows


def native_grid(args, name, source, canonical):
    work = args.work_dir / name
    work.mkdir(parents=True, exist_ok=True)
    rtl, image = work / "source.v", work / "sector.vvp"
    rtl.write_text(source, encoding="utf-8", newline="\n")
    canonical_path = work / "canonical.v"
    canonical_path.write_text(canonical, encoding="utf-8", newline="\n")
    compiler = [str(args.iverilog)] + (["-B", str(args.ivl_dir)] if args.ivl_dir else [])
    result = subprocess.run(compiler + ["-g2012", "-s", "SectorVerdict", "-o", str(image), str(args.repo / "tools/prove_out/sector_verdict_tb.v"), str(rtl), str(canonical_path)], capture_output=True, text=True, encoding="utf-8", check=True, timeout=120)
    (work / "compile.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    result = subprocess.run([str(args.vvp)] + (["-M", str(args.ivl_dir)] if args.ivl_dir else []) + [str(image)], capture_output=True, text=True, encoding="utf-8", check=True, timeout=120)
    (work / "native.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    grouped = {binding: [] for binding in ("consolidated", "canonical", "decoder")}
    for line in result.stdout.splitlines():
        binding, _, row = line.partition(",")
        if binding not in grouped:
            raise ValueError("unknown native sector binding")
        grouped[binding].append(row)
    return {binding: (parse_decoder if binding == "decoder" else parse_rows)("\n".join(lines)) for binding, lines in grouped.items()}


def csv_bytes(header, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def run_sector(args):
    args.repo, args.work_dir, args.output_dir = (Path(getattr(args, name)).resolve() for name in ("repo", "work_dir", "output_dir"))
    require(not any(p.is_relative_to(args.repo) for p in (args.work_dir, args.output_dir)), "sector evidence must be outside the source checkout")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = evidence_bytes(args.repo / "hardware/verilog/spiral_consolidated.v").decode("utf-8")
    canonical = evidence_bytes(args.repo / "hardware/verilog/rpp_canonical.v").decode("utf-8")
    python, python_rows = python_checks()
    grids = native_grid(args, "sector-baseline", source, canonical)
    require_grids(grids)
    rtl, examples = {}, []
    for binding in ("consolidated", "canonical"):
        rtl[binding], cases, _ = characterize(grids[binding])
        examples += [dict(case, claim=binding + "-" + case["claim"]) for case in cases if case["claim"] == "sector-adjacency" or case["input"] in {"theta=0", "theta=28"}]
    rtl["decoder"], cases = decoder_check(grids["decoder"])
    examples += cases
    mutants = {"memory-boundary": source.replace("5'd7, 5'd8, 5'd9, 5'd10:", "5'd7, 5'd8, 5'd9:").replace("5'd11, 5'd12, 5'd13:", "5'd10, 5'd11, 5'd12, 5'd13:"),
               "all-core": re.sub(r"sector = 3'd[0-7];", "sector = 3'd0;", source),
               "missing-core-gene-edge": source.replace("{3'd0, 3'd1}, {3'd1, 3'd0}: adj_result = 1'b1;", "{3'd0, 3'd1}, {3'd1, 3'd0}: adj_result = 1'b0;")}
    mutants = {name: (mutant, canonical) for name, mutant in mutants.items()}
    mutants.update({"canonical-memory-boundary": (source, canonical.replace("5'd7, 5'd8, 5'd9, 5'd10:", "5'd7, 5'd8, 5'd9:").replace("5'd11, 5'd12, 5'd13:", "5'd10, 5'd11, 5'd12, 5'd13:")),
                    "decoder-memory-boundary": (source, canonical.replace("else if (theta <= 10)", "else if (theta <= 9)", 1))})
    for name, (mutant, canonical_mutant) in mutants.items():
        require((mutant, canonical_mutant) != (source, canonical), "stale sector mutation anchor")
        mutated = native_grid(args, name, mutant, canonical_mutant)
        try:
            require_grids(mutated)
        except AssertionError:
            pass
        else:
            raise AssertionError("survived sector mutation: " + name)
        require_grids(native_grid(args, "clean-" + name, source, canonical))
    d1 = d1_checks()
    cargo = getattr(args, "cargo", None) or shutil.which("cargo")
    rustc = os.environ.get("RUSTC") or shutil.which("rustc")
    require(bool(cargo and rustc), "supply --cargo and configure RUSTC/PATH for Rust 1.85.1")
    for tool, prefix in ((cargo, "cargo 1.85.1 "), (rustc, "rustc 1.85.1 ")):
        version = subprocess.run([str(tool), "--version"], capture_output=True, text=True, encoding="utf-8", check=True, timeout=120)
        require(version.stdout.startswith(prefix), "migration evidence requires Rust 1.85.1")
    env = dict(os.environ, CARGO_HOME=str(args.work_dir / "cargo"), CARGO_TARGET_DIR=str(args.work_dir / "rust-target"))
    command = [str(cargo), "test", "--manifest-path", str(args.repo / "rust/Cargo.toml"), "-p", "rpp-core", "--test", "canonical", "--offline", "--locked", "migration_requires_named_policy_and_retains_lossy_mapping", "--", "--exact"]
    result = subprocess.run(command, env=env, capture_output=True, text=True, encoding="utf-8", check=True, timeout=120)
    (args.work_dir / "rust-migration.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    require("1 passed; 0 failed" in result.stdout, "actual Rust migration test did not execute")
    artifacts = {"sector-python.csv": csv_bytes(("profile", "theta", "index", "label"), python_rows),
                 "d1-tools-projection.csv": csv_bytes(("driver", "value", "policy", "theta", "phi", "omega", "radius_byte", "sector"), d1)}
    for binding in ("consolidated", "canonical"):
        artifacts["sector-" + binding + "-native.csv"] = csv_bytes(("kind", "inputs", "output"), ((kind, ":".join(map(str, key)), value) for kind in DOMAINS for key, value in sorted(grids[binding][kind].items())))
    artifacts["sector-decoder-native.csv"] = csv_bytes(("theta", "probe", "word", "sector", "valid", "decoded_theta", "encoded_phi", "omega", "radius", "reserved"), ((*key, *values) for key, values in sorted(grids["decoder"].items())))
    for name, data in artifacts.items():
        (args.output_dir / name).write_bytes(data)
    summary = dict(python=python, rtl=rtl, mutations=dict(killed=len(mutants), survived=0, clean_controls=len(mutants), failed_controls=0, names=list(mutants)),
                   d1=dict(theta_inputs=512, phi_inputs=512, shell_policy_cases=8, native_rust_tests=1,
                           simulator_cases=4, simulator_policy="actual model v1_to_v2 hardcodes shell/3; it has no explicit-policy API and authorizes no default",
                           scope="512-input grids are a tools-only Python adapter; actual public Rust API separately tested on its existing policy/domain fixtures"),
                   hashes={name: sha256(data).hexdigest() for name, data in artifacts.items()}, source_sha256=dict(consolidated=sha256(source.encode()).hexdigest(), canonical=sha256(canonical.encode()).hexdigest()))
    examples += [dict(claim="lossy-theta", input="v1 theta64", python="Memory", rtl="v2 theta4 GENE; reverse theta56 Gene"),
                 dict(claim="lossy-phi", input="v1 phi128", python="128", rtl="RAC2; informational reverse phi85")]
    return dict(summary=summary, counterexamples=examples, artifacts=artifacts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "work-dir", "output-dir", "iverilog", "vvp", "ivl-dir"):
        parser.add_argument("--" + name, type=Path, required=name != "ivl-dir")
    parser.add_argument("--cargo", type=Path)
    result = run_sector(parser.parse_args())
    print(json.dumps({key: value for key, value in result.items() if key != "artifacts"}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
