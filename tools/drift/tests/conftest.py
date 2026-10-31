"""Test-only trusted coordinator mutation injection; never enabled in production."""

import os

import pytest

from tools.drift.branch_mutations import apply_mutant


@pytest.fixture(autouse=True)
def coordinator_branch_mutation(monkeypatch):
    name = os.environ.get("DRIFT_TEST_BRANCH_MUTANT")
    if name:
        apply_mutant(monkeypatch, name)
