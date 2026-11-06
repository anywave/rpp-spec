"""Finite witnesses for selector isolation and false-kill prevention."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools.prove_out import verdict_mutations as mutations


def test_fixture_ignores_ambient_selector_and_requires_explicit_runner_marker(tmp_path):
    """Kills ambient-selector leakage or disabling the dedicated fixture hook."""
    repo = Path(__file__).resolve().parents[3]
    command = [sys.executable, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
               "--tb=short", "--color=no", mutations.RA]
    for marker, expected in ((None, "passed"), ("0", "passed"), ("1", "assertion_failure")):
        environment = dict(os.environ, CX017_MUTATION="python-score-zero", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                           PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        environment.pop(mutations.MARKER, None)
        environment.pop("PYTEST_ADDOPTS", None)
        if marker is not None:
            environment[mutations.MARKER] = marker
        result = subprocess.run(command, cwd=repo, env=environment, capture_output=True,
                                text=True, encoding="utf-8", timeout=30)
        (tmp_path / (str(marker) + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        assert mutations.classify(result, mutations.RA) == expected
    assert mutations.selected_mutation({mutations.MARKER: "1", mutations.SELECTOR: "unknown"}) is None


def test_classifier_rejects_nonassertion_failures_missing_tests_and_wrong_selected_test():
    """Kills counting import/runtime errors, empty runs, signals or a different failed test as a mutation kill."""
    selector = "tests/fixture.py::test_fixed_case"
    good = f"E   assert 1 == 2\nFAILED {selector}\n1 failed in 0.01s\n"
    def result(output, code=1):
        return subprocess.CompletedProcess([], code, output, "")
    assert mutations.classify(result(good), selector) == "assertion_failure"
    for output, code in ((good, 0), (good, -6), (good.replace(selector, "tests/other.py::test_other"), 1),
                         (good.replace("E   assert 1 == 2", "E   RuntimeError: failed"), 1),
                         (good.replace("1 failed", "2 failed"), 1), ("ERROR collecting fixture\nImportError\n", 2)):
        assert mutations.classify(result(output, code), selector) != "assertion_failure"


def test_source_operations_require_one_named_function_and_one_reviewed_anchor():
    """Kills ambiguous, unchanged or stale source replacements being called actual counterfactuals."""
    source = "def f():\n    return 1\n\ndef g():\n    return 1\n"
    case = dict(name="fixed-operation", function="f", before="return 1", after="return 2")
    assert mutations.alter(source, case) == source.replace("return 1", "return 2", 1)
    for changed in (dict(case, function="absent"), dict(case, before="return 9"), dict(case, after="return 1")):
        with pytest.raises(RuntimeError):
            mutations.alter(source, changed)
    with pytest.raises(RuntimeError):
        mutations.alter(source + "\ndef f():\n    return 1\n", case)


def test_classifier_refuses_terminal_runtime_chains_and_keeps_rich_assertions(tmp_path):
    """Kills chained-runtime false kills and treating rich assertion context as a terminal exception."""
    source = tmp_path / "test_chain.py"
    source.write_text("def test_chain_message():\n    try:\n        assert False, 'earlier assertion'\n    except AssertionError:\n        raise RuntimeError('terminal runtime failure')\n\ndef test_chain_bare():\n    try:\n        assert False\n    except AssertionError:\n        raise RuntimeError\n\ndef test_rich_assertion():\n    actual = 0\n    assert actual == int(165 * 0.25) + int(509 * 0.5)\n", encoding="utf-8")
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    environment.pop("PYTEST_ADDOPTS", None)
    for name, expected in (("test_chain_message", "non_assertion_failure"), ("test_chain_bare", "non_assertion_failure"), ("test_rich_assertion", "assertion_failure")):
        selector = "test_chain.py::" + name
        command = [sys.executable, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider", "--tb=short", "--color=no", selector]
        result = subprocess.run(command, cwd=tmp_path, env=environment, capture_output=True,
                                text=True, encoding="utf-8", timeout=30)
        assert result.returncode == 1
        assert mutations.classify(result, selector) == expected
