# Pin Ruff 0.14.10 and restore the lint gate

Pin CI's Ruff version, manually clear its 19 existing F401/F841 findings, and remove
the advisory bypass now that lint exits 0. Keep memory-write calls and strengthen
the existing continuity assertion instead of dropping its unused computation.
No layout, constants, spec, vectors, or drift tooling changes are included.

Validation at implementation `b385eca3fb85e270aad41f0d9da3e18c23a182ce`:

- `ruff --version`: 0.14.10.
- `ruff check rpp/ tests/ --ignore E501`: exit 0, no findings.
- `PYTHONPATH=/workspace/cx004-ci-lint python -m pytest tests/ -q`: 1256 passed.
- `PYTHONPATH=/workspace/cx004-ci-lint python tests/test_golden_vectors_mobius32.py`: pass=5 fail=0.
- `git diff --check`: exit 0.
- Re-add the unused struct import in a disposable full-scope copy: exactly 1 F401,
  Ruff exit 1. The CI job now propagates that failure.

Hosted CI is pending this draft PR. This is independent of CX-001/PR #4; TR owns
all merges. Merge this lint repair first, then recheck PR #4 against the new base.
