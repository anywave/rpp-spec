# CX-005 foreign-binding reference probes

The source-reference probes characterize hand-written Python transcriptions of
reviewed formulas. Their tests are not independent validation of the foreign
implementation. A separate native Rust harness executes the actual public
`ra_core` gate functions and agrees with the Rust transcription at all 6,042
grid/boundary points. Clash remains **source transcription, not native execution**.
These checks establish no physical or biological claim. The foreign quantities
consume different inputs from RPP progress and cannot be silently substituted
into it.

The read-only source is `anywave/ra-system` at
`e685d3abacca3105a7c377e9db80df33ce7c2985`. The generator verifies five
SHA-256 hashes over canonical LF bytes before producing evidence; the hashes and revision appear in
`foreign_reference.py` and the generated summary. No foreign source is changed.
The four toolchains were initially absent from PATH. A task-local authenticated
Debian Rust/Cargo 1.85.1 extraction subsequently enabled the native gate run;
GHC/Clash compilation, tests and synthesis remain unexecuted. Native Clash
reproducibility remains a separate condition for a cross-binding claim.
`evidence_bytes` normalizes only CRLF to LF before source/evidence comparisons
or file-content hashing. It preserves lone CR, other bytes and final-newline
presence. This supports existing Windows checkouts converted by `core.autocrlf`
without accepting a changed passage. The source-guard test checks LF and CRLF
against the same digest and then rejects changed content.

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

## Mutation execution and its limits

After the review changes, the foreign-reference pytest file has **15 passing
cases**. Nine selected in-memory mutations were executed against their named
tests and produced assertion failures: **killed=9, survived=0**. Every mutation
below changes only the Python transcription, harness guard or a read's in-memory
artifact bytes. No Rust/Clash source mutation is executed or claimed.

| Executed mutation | Target test suffix after `test_` | Exact exercised change |
|---|---|---|
| `foreign_rust_alpha_reverse` | `rust_transcription_grid_bounded_and_monotone_for_all_six_rac_levels` | Reverse the computed partial-alpha sign |
| `foreign_rust_floor_strict` | `rust_transcription_floor_and_threshold_branches_use_greater_or_equal` | Make only the floor comparison strict |
| `foreign_clash_shift` | `clash_transcription_all_65536_avatar_products_are_bounded_and_axis_monotone` | Shift the product by seven instead of eight |
| `foreign_clash_wrap` | `clash_transcription_fixed_three_aligned_group_is_bounded_and_axis_monotone` | Replace saturating additions with byte wrapping |
| `foreign_clash_strict179` | `clash_transcription_stability_is_strictly_above_179_without_inversion` | Treat score 179 as stable |
| `foreign_clash_inversion_denominator` | `clash_transcription_inverted_active_members_affect_denominator_and_cluster_bonus` | Exclude inverted avatars from the averaging denominator |
| `foreign_clash_unconditional_bonus` | `clash_transcription_empty_and_separate_clusters_have_no_alignment_bonus` | Add the group bonus without an aligned cluster |
| `foreign_source_hash_guard` | `source_hash_verification_refuses_changed_reviewed_file` | Skip comparison with the reviewed source digest |
| `foreign_native_artifact_row` | `committed_native_rust_evidence_matches_all_6042_reference_rows` | Flip one stored native row's result on read |

The docstrings also describe **eight unexecuted mutation examples**; none is
included in the killed count:

| Target test | Unexecuted example |
|---|---|
| Rust transcription boundary test | Make the full-access threshold comparison strict; the executed mutant changes only the floor |
| Rust transcription nonfinite test | Add a finite-input guard |
| Reference invalid-RAC test | Remove the index guard, across its four fixed inputs 0, 7, True and 1.5 |
| Clash transcription inverted-member test | Exclude inverted avatars from cluster membership; the executed mutant changes only the denominator |
| Clash transcription empty/separate-cluster test | Merge the four L clusters |
| Reference output integrity test | Drop a probe row |
| Reference output integrity test | Add a clock-dependent output value |
| Native artifact integrity test | Alter the recorded digest; the executed mutant changes a CSV row |

The native Rust comparison is independent execution on 6,042 inputs. The
65,536 Clash product rows and 65,536 fixed-composition group cases remain
transcription coverage only, with **zero independently executed Clash inputs**.
They cannot satisfy the native-Clash agreement condition by increasing their
row or assertion count.

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
65,536 equal-input three-avatar cases characterize the Python transcription's
bounded, monotonic formula. These are not an independent check of native Clash
arithmetic or compilation. Composition has this transcription counterexample:

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
