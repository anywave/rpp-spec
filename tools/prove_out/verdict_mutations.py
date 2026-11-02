"""Reproduce bounded Python counterfactuals in disposable source copies.

Selectors require an explicit runner marker; this prevents ambient test leakage,
not malicious callers. Receipts contain current observations, relative selectors
and canonical-LF source hashes. Logs and tool paths stay outside the checkout.
"""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from tools.prove_out.verdict_mutation_cases import guard_cases

MARKER = "CX017_MUTATION_RUNNER"
SELECTOR = "CX017_MUTATION"
MT = "tools/prove_out/tests/test_verdict.py::"
RA = MT + "test_python_ra_formula_and_driver_use_actual_function"
PYTHON_CASES = (
    ("python-score-zero", RA, MT + "test_reserved_bits_do_not_change_actual_coordinate_affinity"),
    ("reserved-influence", MT + "test_reserved_bits_do_not_change_actual_coordinate_affinity", RA),
    ("unknown-affinity-row", MT + "test_affinity_parser_rejects_unknown_rows", MT + "test_terminal_affinity_row_preserves_each_binding_contract_and_exact_disagreement"),
    ("python-no-wrap", "tools/prove_out/tests/test_coherence_cases.py::test_all_ordinary_theta_pairs_match_declared_circular_formula", "tools/prove_out/tests/test_coherence_cases.py::test_fractional_counterexamples_record_actual_nonfinite_and_clamping_results"),
)
KNOWN_SELECTORS = frozenset(case[0] for case in PYTHON_CASES)


def selected_mutation(environ=None):
    """Return only explicitly enabled, whitelisted test-only counterfactuals."""
    environ = os.environ if environ is None else environ
    value = environ.get(SELECTOR)
    return value if environ.get(MARKER) == "1" and value in KNOWN_SELECTORS else None


def classify(result, selector):
    """Only one selected pytest assertion failure is an eligible kill."""
    text = result.stdout + result.stderr
    def summary(label):
        return re.search(rf"^{label}(?:, \d+ warnings?)? in [\d.]+s$", text, re.M)
    if result.returncode == 0 and summary("1 passed"):
        return "passed"
    selected = re.search(rf"^FAILED {re.escape(selector)}(?: - (.*))?$", text, re.M)
    if result.returncode != 1 or not summary("1 failed") or not selected:
        return "tool_error"
    reason = selected[1] or ""
    if reason and not re.match(r"(?:assert\b|AssertionError\b|Failed: DID NOT RAISE\b)", reason):
        return "key_error" if re.match(r"(?:[\w]+\.)*KeyError\b", reason) else "non_assertion_failure"
    terminal = "non_assertion_failure"
    for diagnostic in re.findall(r"^E\s+(.+)$", text, re.M):
        if re.match(r"(?:assert\b|AssertionError\b|Failed: DID NOT RAISE\b)", diagnostic):
            terminal = "assertion_failure"
        elif exception := re.match(r"([\w.]+)(?::(?:\s|$)|$)", diagnostic):
            terminal = "key_error" if exception[1].rsplit(".", 1)[-1] == "KeyError" else "non_assertion_failure"
    if re.search(r"^ERROR\b|ImportError|ModuleNotFoundError|SyntaxError", text, re.M):
        return "tool_error"
    return terminal


def alter(source, case):
    """Apply exactly one reviewed operation inside exactly one named function."""
    nodes = [node for node in ast.walk(ast.parse(source))
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == case["function"]]
    if len(nodes) != 1:
        raise RuntimeError("missing or ambiguous function: " + case["name"])
    node = nodes[0]
    old = "".join(source.splitlines(keepends=True)[node.lineno - 1:node.end_lineno])
    count = old.count(case["before"])
    expected = case.get("operation_count", 1)
    if count != expected or source.count(old) != 1 or case["before"] == case["after"]:
        raise RuntimeError("missing, unchanged or ambiguous operation: " + case["name"])
    new = old.replace(case["before"], case["after"], count)
    return source.replace(old, new, 1)


def _snapshot(repo):
    files = set((repo / "rpp").rglob("*.py")) | set((repo / "tools/prove_out").glob("*.py"))
    files |= set((repo / "tools/prove_out/tests").glob("*.py"))
    files.add(repo / "hardware/verilog/spintronic_sim.py")
    return {path.relative_to(repo).as_posix(): path.read_bytes().replace(b"\r\n", b"\n") for path in sorted(files)}


def _materialize(root, snapshot):
    for name, content in snapshot.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _invoke(root, selector, log, python, mutation=None):
    environment = dict(os.environ)
    for name in (MARKER, SELECTOR, "PROVE_OUT_MUTATION", "PYTEST_ADDOPTS", "PYTEST_CURRENT_TEST"):
        environment.pop(name, None)
    environment.update(PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0",
                       PYTHONIOENCODING="utf-8", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    if mutation is not None:
        if mutation not in KNOWN_SELECTORS:
            raise RuntimeError("unknown fixture mutation")
        environment.update({MARKER: "1", SELECTOR: mutation})
    command = [str(python), "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
               "--tb=short", "--color=no", selector]
    result = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True,
                            encoding="utf-8", timeout=120)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    return {"selector": selector, "exit": result.returncode, "status": classify(result, selector)}


def _require_pass(results, label):
    if any(result["status"] != "passed" for result in results):
        raise RuntimeError(label + " failed; inspect external logs")


def _fixture_case(case, snapshot, work, python):
    name, target, unaffected = case
    root = work / name
    _materialize(root, snapshot)
    baseline = _invoke(root, target, root / "baseline.log", python)
    _require_pass([baseline], name + " baseline")
    changed = _invoke(root, target, root / "mutant.log", python, name)
    control = _invoke(root, unaffected, root / "unaffected.log", python, name)
    clean = _invoke(root, target, root / "clean.log", python)
    _require_pass([control, clean], name + " controls")
    if changed["status"] != "assertion_failure":
        raise RuntimeError(name + " survived or failed without its selected assertion")
    return dict(name=name, classification="killed", baseline=baseline, positive=changed,
                clean=clean, unaffected=control)


def _source_case(case, snapshot, baselines, work, python):
    root = work / case["name"]
    _materialize(root, snapshot)
    source = snapshot[case["source"]].decode("utf-8")
    changed = alter(source, case)
    path = root / case["source"]
    path.write_text(changed, encoding="utf-8", newline="\n")
    positives = [_invoke(root, test, root / f"mutant-{index}.log", python)
                 for index, test in enumerate(case["targets"])]
    unaffected = _invoke(root, RA, root / "unaffected.log", python)
    path.write_text(source, encoding="utf-8", newline="\n")
    clean = [_invoke(root, test, root / f"clean-{index}.log", python)
             for index, test in enumerate(case["targets"])]
    baseline = [baselines[test] for test in case["targets"]]
    _require_pass([*baseline, *clean, unaffected], case["name"] + " controls")
    states = [result["status"] for result in positives]
    classification = "killed" if all(state == "assertion_failure" for state in states) else "survived"
    if case["expected"] == "equivalent_excluded" and all(state == "passed" for state in states):
        classification = "equivalent_excluded"
    if case["expected"] == "non_assertion_excluded" and states == ["key_error"]:
        classification = "non_assertion_excluded"
    if classification != case["expected"]:
        raise RuntimeError(case["name"] + " unexpected classification: " + str(states))
    return dict(name=case["name"], source=case["source"], function=case["function"],
                source_sha256=sha256(source.encode()).hexdigest(), mutated_source_sha256=sha256(changed.encode()).hexdigest(),
                classification=classification, baselines=baseline, positives=positives, clean=clean, unaffected=unaffected)


def _group(cases):
    return dict(cases=cases, variants=len(cases), killed=sum(case["classification"] == "killed" for case in cases),
                equivalent_exclusions=sum(case["classification"] == "equivalent_excluded" for case in cases),
                fail_closed_non_assertion_exclusions=sum(case["classification"] == "non_assertion_excluded" for case in cases),
                eligible_non_equivalent_survivors=sum(case["classification"] == "survived" for case in cases))


def reproduction_cases():
    """Separate current generator guards; never folded into historical49."""
    target = "tools/prove_out/tests/test_reproduce.py::"
    descriptions = (
        ("verification-block-omitted", "assemble", '        summary["verification"] = verification\n', "", "test_equal_complete_inputs_produce_exact_bytes_and_derived_verification"),
        ("artifact-comparison-omitted", "assemble", '    if files != repeated:\n        raise AssertionError("complete evidence runs differ, including payload or receipts")\n', "", "test_second_run_artifact_inventory_or_byte_change_is_rejected[changed]"),
        ("nonfinite-json-permitted", "serialize", "allow_nan=False", "allow_nan=True", "test_serialization_is_canonical_lf_utf8_and_rejects_nonfinite_json"),
        ("casefold-collision-permitted", "artifact_map", " or name.casefold() in seen", "", "test_casefold_artifact_collisions_and_nonbyte_content_are_rejected"),
    )
    return tuple(dict(name=name, source="tools/prove_out/reproduce.py", function=function, before=before,
                      after=after, targets=(target + selector,), expected="killed")
                 for name, function, before, after, selector in descriptions)


def run_receipts(args):
    """Return schema-v2 current receipts; args provides repo/work_dir/python."""
    repo, work = Path(args.repo).resolve(), Path(args.work_dir).resolve() / "python-mutations"
    if work.is_relative_to(repo):
        raise ValueError("mutation work must be outside the checkout")
    marker = "CX018 disposable Python mutation copies\n"
    if work.exists():
        if not (work / ".owned").is_file() or (work / ".owned").read_text(encoding="utf-8") != marker:
            raise ValueError("refusing to replace unowned mutation work")
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / ".owned").write_text(marker, encoding="utf-8", newline="\n")
    snapshot = _snapshot(repo)
    sources = {path: sha256(content).hexdigest() for path, content in snapshot.items()}
    baseline_root = work / "baseline"
    _materialize(baseline_root, snapshot)
    guards = guard_cases()
    if len(guards) != 49 or len({case["name"] for case in guards}) != 49:
        raise RuntimeError("historical guard inventory must contain 49 unique variants")
    targets = sorted({target for case in guards for target in case["targets"]})
    def baseline(target):
        return target, _invoke(baseline_root, target, work / "baselines" / (sha256(target.encode()).hexdigest() + ".log"), args.python)
    with ThreadPoolExecutor(max_workers=4) as pool:
        baselines = dict(pool.map(baseline, targets))
    _require_pass(baselines.values(), "guard baseline")
    with ThreadPoolExecutor(max_workers=4) as pool:
        guarded = list(pool.map(lambda case: _source_case(case, snapshot, baselines, work, args.python), guards))
        fixtures = list(pool.map(lambda case: _fixture_case(case, snapshot, work, args.python), PYTHON_CASES))
    acp = dict(name="drop-explicit-UTF8", source="tools/prove_out/verdict.py", function="native",
               before=', encoding="utf-8"', after="", operation_count=6,
               targets=(MT + "test_native_helper_preserves_utf8_bench_and_logs_under_simulated_windows_acp",), expected="killed")
    acp_baseline = baseline(acp["targets"][0])
    _require_pass([acp_baseline[1]], "ACP baseline")
    utf8 = _source_case(acp, snapshot, {acp_baseline[0]: acp_baseline[1]}, work, args.python)
    reproductions = reproduction_cases()
    with ThreadPoolExecutor(max_workers=4) as pool:
        reproduction_baselines = dict(pool.map(baseline, [case["targets"][0] for case in reproductions]))
        reproduced = list(pool.map(lambda case: _source_case(case, snapshot, reproduction_baselines, work, args.python), reproductions))
    if _snapshot(repo) != snapshot:
        raise RuntimeError("source changed during mutation runs; freeze and repeat")
    unit = _group(guarded)
    unit.update(unique_baselines=len(baselines), baseline_rechecks=0, clean_control_rechecks=0,
                positive_assertion_failures=sum(result["status"] == "assertion_failure" for case in guarded for result in case["positives"]),
                clean_controls=sum(all(result["status"] == "passed" for result in case["clean"]) for case in guarded),
                unaffected_controls=sum(case["unaffected"]["status"] == "passed" for case in guarded))
    return dict(schema_version=2, source_sha256=sources, python_mutations=_group(fixtures),
                utf8_mutation=_group([utf8]), unit_guard_mutations=unit, reproduction_guards=_group(reproduced))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.repo.resolve()):
        parser.error("write receipts outside the checkout")
    receipt = run_receipts(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: receipt[key]["killed"] for key in ("python_mutations", "utf8_mutation", "unit_guard_mutations")}, sort_keys=True))


if __name__ == "__main__":
    main()
