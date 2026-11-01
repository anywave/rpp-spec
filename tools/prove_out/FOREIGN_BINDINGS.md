# CX-005 foreign-binding reference probes

The source-reference probes check finite engineering consequences of reviewed
formulas. A separate native Rust harness now executes the actual public
`ra_core` gate functions and agrees with the Rust transcription at all 6,042
grid/boundary points. Clash remains **source transcription, not native execution**.
These checks establish no physical or biological claim. The foreign quantities
consume different inputs from RPP progress and cannot be silently substituted
into it.

The read-only source is `anywave/ra-system` at
`e685d3abacca3105a7c377e9db80df33ce7c2985`. The generator verifies five exact
SHA-256 hashes before producing evidence; the hashes and revision appear in
`foreign_reference.py` and the generated summary. No foreign source is changed.
The four toolchains were initially absent from PATH. A task-local authenticated
Debian Rust/Cargo 1.85.1 extraction subsequently enabled the native gate run;
GHC/Clash compilation, tests and synthesis remain unexecuted. Native Clash
reproducibility remains a separate condition for a cross-binding claim.

Run from this branch with its source explicitly selected:

```bash
PYTHONPATH=. /workspace/work/cx005/venv/bin/python -m tools.prove_out.foreign_reference --source-root /workspace/ra-system --output-dir tools/prove_out/results/foreign
PYTHONPATH=. /workspace/work/cx005/venv/bin/python -m pytest tools/prove_out/tests/test_foreign_reference.py -q -o addopts=
```

The generator emits 6,006 ordinary Rust-grid rows (six RAC levels times 1,001
input points), 36 adjacent-float boundary rows, and all 65,536 unsigned-byte
coherence/depth product rows. Output uses UTF-8, LF, stable ordering and no
clock, random source, key, model or network operation. `summary.json` records
the CSV digests. Every test's docstring names its failing mutation.

## Actual native Rust comparison

`native_rust/src/main.rs` calls the actual `ra_core::gates` public functions
over the same 6,006 grid points and 36 adjacent-float boundaries. It does not
reimplement the access calculation. The Python runner verifies reviewed source
hashes, builds through a temporary manifest pointing at the explicit source
checkout, then canonicalizes Rust's round-trip numeric CSV representation with
the reference's `.17g` formatting. All 6,042 rows agree byte for byte after this
formatting; this comparison includes input, threshold, result variant and alpha.
The source checkout receives no writes, and Cargo lock/build files are temporary.
No native test suite or `proptest` is run.

```bash
LD_LIBRARY_PATH=/workspace/work/cx005/rust/usr/lib/x86_64-linux-gnu RUSTC=/workspace/work/cx005/rust/usr/bin/rustc CARGO_HOME=/workspace/work/cx005/cargo PYTHONPATH=. /workspace/work/cx005/venv/bin/python -m tools.prove_out.native_rust.run --source-root /workspace/ra-system --output-dir tools/prove_out/results/foreign --cargo /workspace/work/cx005/rust/usr/bin/cargo
```

With normally installed Rust, omit the task-local environment variables and
`--cargo` argument. Dependency downloads are read-only network operations;
the probe itself makes none. A cached repeat can use `CARGO_NET_OFFLINE=true`.
An initial sandbox invocation could not contact the proxy; the authorized
network invocation fetched dependencies and compiled successfully. The final
command emitted `native_rust_grid_rows=6006 native_rust_boundary_rows=36` and
`native_rust_rows=6042 reference_mismatches=0`. Native CSV SHA-256:
`8ad8786406cc1f24625dda28fb2f6eb1432a94c196541389bd93d67304d8f9ff`.
The cached offline second build/run produced the same CSV and summary bytes;
both `cmp` commands exited 0. `git -C /workspace/ra-system status --short`
remained empty. The artifact-integrity pytest case requires all 6,042 native
rows and the recorded zero-mismatch count to match the reference and digest,
without requiring a Rust compiler on the normal pytest path.
The native oracle would fail if an inclusive floor/threshold comparison became
strict or the alpha numerator/sign changed. A modified reviewed source is
rejected by the hash gate before execution. This is equality of the stated
Rust gate formula with its reference on the enumerated points, not equality
with RPP progress or all possible floating-point inputs.

## Rust supplied-scalar access policy

`rust/src/gates.rs:29-33,73-89`, `rac.rs:76-85,111-113` and
`constants.rs:35,56` define floor `1.62/(3*84823/50000)` =
`0.31830989236409934`, and six RAC-normalized full-access thresholds:

| RAC | Full-access threshold |
|---|---:|
| 1 | 1 |
| 2 | 0.9876543217444954 |
| 3 | 0.8999999999999999 |
| 4 | 0.8230452668104956 |
| 5 | 0.72 |
| 6 | 0.628539360786579 |

Access is full at or above the threshold, partial at or above the floor,
otherwise blocked. Partial alpha is `(input-floor)/(threshold-floor)`, clamped
to [0,1]. Consequently **at the floor** the variant is `PartialAccess(0)` and
`can_access` returns true because it tests only whether the variant is blocked
(`gates.rs:92-95`). This differs from testing `alpha>0`. The ordinary-grid
alpha is bounded and nondecreasing. Adjacent floating-point probes pin both
inclusive comparisons. The code supplies no finite-value guard: NaN is blocked
and positive infinity is full. Those are characterization results, not proposed
input-domain rules. The parent packet retains adoption/domain decisions.

## Clash group-score slice

`haskell/clash/RaGroupCoherence.hs:346-355` computes an avatar contribution as
`floor(coherence*depth/256)` for two unsigned bytes. Its exact range is 0..254;
it is nondecreasing along either input axis. The names and boosts are author
policy labels here, not physical constants.

The inspected score slice (`:265-291,358-405`) groups active avatars by L into
four bins: 0..1, 2, 3, 4..7. It sums contributions from active non-inverted
avatars but divides by **all active avatars**, including inverted ones. If the
largest cluster contains at least three avatars, it adds a saturating 38 to
the average and a further saturating 77 for field strength. Stability requires
no inverted avatar and score **greater than 179**; three or more inverted
avatars classify as collapsed. With fixed active/cluster composition, all
65,536 equal-input three-avatar cases satisfy the source formula and remain
bounded and monotonic. Composition itself has a counterexample:

| Active input | Group score | Field strength | Classification |
|---|---:|---:|---|
| Two normal avatars, each coherence=depth=255 | 254 | 254 | stable |
| Same two plus one inverted aligned avatar | 207 | 255 | unstable |
| Three inverted aligned avatars | 38 | 115 | collapsed |
| Four normal avatars in four distinct L bins | 254 | 254 | stable |

The reference deliberately covers only product, cluster size, score and
stability. It does not transcribe clocking, dominant-signature tie resolution,
windows, feedback, signal-level processing or synthesis. Wider claims require
native tests and an explicit meaning for the supplied inputs. No equality with
the RPP 0..674 progress score is claimed.
