# CX-005 E5 simulator validation

Source baseline: `95c67ef`; branch `codex/overlay-design`. Commands were run in
`/workspace/work/cx005/e5` with Python 3.12.14 from
`/workspace/work/cx005/venv/bin/python` and `PYTHONPATH` set to this checkout.
No core, spec, constant, layout, header, golden vector or published outbox changed.
The root's CX-005 report records the final combined design/simulator head and its
committed-diff drift check; this file records the simulator's executed evidence.

| Command | Observed result |
|---|---|
| `python -m pytest tools/overlay_sim/tests/ -q -o addopts=` | 30 passed |
| `python -m tools.overlay_sim.mutation_check` | killed=12 survived=0 controls_passed=12 controls_failed=0 |
| `python -m tools.overlay_sim.scenarios --output-dir tools/overlay_sim/results/` | meter_rows=17 requests=16 artifacts=3 |
| `python -m pytest tests/ -q` | 1256 passed, 1 existing legacy-format warning |
| `python tests/test_golden_vectors_mobius32.py` | SUMMARY pass=5 fail=0 |
| `python -m ruff --version` | ruff 0.14.10 |
| `python -m ruff check rpp/ tests/ tools/overlay_sim/ --ignore E501` | exit 0 |
| `git diff --check` | exit 0; new files separately checked with `git diff --no-index --check /dev/null FILE`, no whitespace diagnostics |

Two scenario runs (committed results directory and a separate
`/workspace/work/cx005/overlay-repeat` directory) produced byte-identical outputs;
all three `cmp` commands exited 0:

| Artifact | SHA-256 (both runs) |
|---|---|
| scenarios.csv | ea0249e994303d2074a00f745798931b668155de00be7bb1f9dae097e1c86245 |
| SCENARIOS.md | 625d5a7701979cdc10bf75c62c09e5d50dace6237f7e4eb302dadfa5ca6c542e |
| billboards.json | f5fac49c1a2e138fea8b219d91f2291d407f842fa52b802fc5bf5ac55972c032 |

Every test names a failing mutation in its docstring. The executed mutations and
clean controls are listed in README.md and `mutation_check.CASES`. The mutation
runner accepts only one collected assertion-failing test as a kill; collection
errors and missing tests do not count. Normal test sources are never modified.
Tests additionally reject START with a true verification fixture, all payload/grant/consent/key/model/text
fields on control, expired billboard delivery/application and clock rollback, false verification fixtures or
out-of-scope statements, receipt replay, unverified readings/tunnels, truthy
nonboolean flags, unbounded sequence integers and malformed operations without
meter rows. Rejected operations cannot add members or grants or generate data.

A cross-agent adversarial review prompted explicit regression guards for bounded
control frames, strict boolean readings, invalid-operation accounting and
expiry followed by clock rollback. Round 2 adds rejected-future-call lockout,
known-path control references, verified independent control tunnels, per-issuer
replay state, malformed object/self-target handling and required explicit output
destinations. CRLF-normalized committed-snapshot comparisons preserve standalone
Windows checkouts. All 30 cases passed after these changes.
The generic “always available” property is limited to eligible, fresh, verified,
authorized reachable candidates; honest no-channel outcomes remain explicit.

Native Windows was not run here. TR should repeat the simulator tests, mutation
runner, scenario generation and SHA-256/cmp-equivalent checks on Windows 11 /
Python 3.13, along with the repository tests, golden vectors and pinned Ruff.
No network, actual Bluetooth/LoRa adapter, tunnel cryptography, NAT traversal or
production clock/replay service was exercised. These remain design/adoption work.
