# Hostile-input development checks

This detached workspace adds no dependency or lock entry to the shipping Rust
workspace. Proptest1.6.0 and optional libfuzzer-sys0.4.9 are pinned; Cargo.lock
pins their transitive graph. Owned helpers are safe Rust; libFuzzer is an
external development runtime. No keys, signing, network or radio experiments run.

From checkout, with Rust1.85.1 selected:

```
cargo fetch --manifest-path tools/fuzz_scaffold/Cargo.toml --locked
cargo test --manifest-path tools/fuzz_scaffold/Cargo.toml --offline --locked
cargo clippy --manifest-path tools/fuzz_scaffold/Cargo.toml --all-targets --offline --locked -- -D warnings
python -m unittest tools.fuzz_scaffold.test_smoke tools.esp32_scaffold.test_billboard_errors
python tools/fuzz_scaffold/smoke.py --output-dir <outside-new-directory>
```

Four properties each run256 fixed-seed cases; shrinking is bounded1024 and
persistence disabled. Inputs cap4096bytes, reassembly pushes64, MTUs20/51.
A fifth test exercises the committed HEX seeds. A structural accept callback
allows deep parser coverage, not authenticity; roundtrip/refusal properties use
exact prefix/signature fixtures. Reassembly uses exact verified control fixtures
and an independent coverage bitmap; generated sessions stay at tick0. Targeted
crate tests cover time, expiry, rollback and cache eviction separately.

CI fetches this locked graph read-only, then always runs properties offline on
Linux/Windows. Actual fuzzing requires preinstalled Linux nightly and cargo-fuzz
0.12.0; missing prerequisites produce an explicit SKIP, never an invented pass.
No auto-install or RUSTC_BOOTSTRAP. Two targets get30seconds each, max_len4096,
per-input timeout2seconds/RSS512MiB; outer process-group timeouts are bounded.
Builds, binary seed materialization and crash artifacts stay in an outside copy.
Tool-present build/run errors fail. Stable fuzz-bin checks prove compilation,
not instrumented coverage. Reassemble mode byte chooses raw or structured input;
remaining bytes control order, duplicates and overlaps independently.

Recent verified completions retain only two peer/tag keys until the original
fragment deadline. This is bounded duplicate suppression, not host replay policy.
ExpiredKey reports the old key before consuming new bytes; handle that event,
then retry the identical fragment locally once. Empty slots take priority, so
this needs no expiry queue or unbounded retry. BLE preserves the typed error;
no automatic retry, transport receipt or consent grant is implied.
