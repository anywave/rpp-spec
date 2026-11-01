# CX-007 Part B validation

Base `5677ea2`; branch `codex/rust-rpp-crate`. Rust **1.85.1**, Python **3.12.14**,
Ruff **0.14.10**. This adds one dependency-free library crate and development
scaffolds. Published specification, Python runtime, original tests, constants,
layouts, consent header, vectors and earlier outboxes are unchanged.

## Executed commands

Commands below run from the repository root unless noted. The local extracted
toolchain was selected through command-scoped PATH/LD_LIBRARY_PATH and a task
Cargo cache; rustup installations can use `cargo +1.85.1` instead.

| Command | Observed result |
|---|---|
| `cargo fmt --manifest-path rust/Cargo.toml --all -- --check` | exit 0 |
| `cargo clippy --manifest-path rust/Cargo.toml --workspace --all-targets --offline --locked -- -D warnings` | exit 0 |
| `cargo test --manifest-path rust/Cargo.toml --workspace --offline --locked` | **37 passed**: 7 Mobius32, 1 heap-free canonical unit, 5 canonical corpus, 18 overlay, 6 resolver; 0 failures; 0 doctests |
| `cargo package --manifest-path rust/rpp-core/Cargo.toml --list --allow-dirty --offline` | library package lists **20 files**, no Python scaffold or binary targets |
| `PYTHONPATH=. python -m pytest tests/ -q` | **1256 passed**, 1 existing legacy-format warning |
| `python tests/test_golden_vectors_mobius32.py` | **SUMMARY pass=5 fail=0** |
| `ruff --version` | **ruff 0.14.10** |
| `ruff check rpp/ tests/ tools/rust_scaffold/ --ignore E501` | exit 0 |
| `git diff --cached --check`; `git diff --check 5677ea2 HEAD` | exit 0 |
| `python -m tools.drift check --base 5677ea2 --head <resolved SHA> --output-dir <scratch>` | exit 0; **0 HIGH / 0 MEDIUM / 0 LOW** |

ESP32-readiness addendum executed on the final feature split:

| Command | Observed result |
|---|---|
| `cargo test --workspace --no-default-features --offline --locked` | **8 passed**, including the same heap-free canonical golden and seven Mobius32 tests |
| `cargo test --workspace --no-default-features --features alloc --offline --locked` | **37 passed** |
| `cargo clippy --workspace --all-targets --no-default-features --features alloc --offline --locked -- -D warnings` | exit 0 |
| `cargo build --workspace --no-default-features --target riscv32imc-unknown-none-elf --offline --locked` | exit 0, actual target library build |
| Same build with `--features alloc` | exit 0, actual no_std resolver/overlay build |

The cross-build used official Rust 1.85.1 `(4eb161250)` and the matching target
component, both verified against the official SHA-256 manifest before extraction.
The Debian host compiler has distinct metadata and was not mixed with the target.
Manifest SHA-256: `1e7dae690cd12e27405a97e64704917489a27c650201bf47780a936055d67909`.
Rustc archive SHA-256: `92a5c532b9e87912190128704e0d65825912e3b08a6ee9203c4068d6d1df62c4`.
Target archive SHA-256: `30bbd341a134bb10395c8c6904053c6239e49ac37acfc4c33b06b8b6b064071c`.
The shared quantizer's rounding-mode mutation was updated to half-away-from-zero
and re-executed: **4 killed / 0 survived**, **4 baseline + 4 clean controls**.
Final mutation summary SHA-256:
`c33201b3270ff9eda56f82b7af244a1b92e0c5bca9e5fd5926dcb7f74cd9c29c`.

The pre-existing pytest-asyncio configuration notice is also visible. Rust tests
have fixed titles and each names its failing mutation. The same heap-free canonical byte/ASCII-URI golden test runs with default
features and with no features. The original five golden
check families are implemented in the separate Mobius32 module; two additional
unit cases test all field values and raw-word rejection. Canonical v2 is a
different profile, checked independently against Python.

## Python oracle corpus

`PYTHONPATH=. python tools/rust_scaffold/address_corpus.py --output-dir <scratch>`
executes the unchanged Python reference. It generates **9497 rows**:
constructor **4110**, raw-word **2119**, URI **3268**. The three TSVs total
**1074054 bytes**. Coverage includes all 2048 discrete accepted field
combinations, all decoded radius codes, all 255 half-step boundaries and their
neighboring floats, fixed seeds **0/1**, null/reserved/wildcard states, signed
raw masking, 68 Unicode decimal digit sets, suffix parsing and negative zero.

| File | Bytes | SHA-256 |
|---|---:|---|
| address-construct.tsv | 386536 | `7f68bc4bbfdc6e0f0e5dff92b02bbae08633d325bb23dc408653b8fec519893a` |
| address-raw.tsv | 217295 | `2236f7fea51beacc32c6e3f807ca873a500b667d18cc00d46abf6a4c44e3711e` |
| address-uri.tsv | 470223 | `48886c20fda49012fb715dedb5b443045cc5dcc89a1d6dbc252b6bfe58b118c7` |

SHA-256 of these three byte strings concatenated in table order:
`e20b0741dce89ab85a4ef2f11eef10c84ec6041f44caccab6893bd517c840996`.
Two independent scaffold runs compare **4/4 files byte-identically**, including
the manifest under the same Python/Unicode version. Unused error-row cells use `-` sentinels to avoid trailing tabs. Rust tests compare actual
word/byte/URI/field outputs with every committed oracle row and assert exact
row counts. Reference source canonical-LF SHA-256 is recorded in the manifest.

## Actual overlay byte identity

The current `tools.overlay_sim.scenarios.artifacts()` was executed twice.
Its outputs equal the Rust test fixtures below; Rust's in-memory scenario
renderer passes direct byte equality against those same fixtures and reruns.
There are **17 meter rows / 16 requests**, no generated timestamp or random input.

| Rust fixture | Bytes | SHA-256 |
|---|---:|---|
| overlay-scenarios.csv | 708 | `ea0249e994303d2074a00f745798931b668155de00be7bb1f9dae097e1c86245` |
| overlay-scenarios.md | 1350 | `625d5a7701979cdc10bf75c62c09e5d50dace6237f7e4eb302dadfa5ca6c542e` |
| overlay-billboards.json | 779 | `f5fac49c1a2e138fea8b219d91f2291d407f842fa52b802fc5bf5ac55972c032` |

`.gitattributes` marks `rust/rpp-core/tests/data/** -text`. A real temporary Git
repository with `core.autocrlf=true` committed and checked out all **7** data
files. Every protected file equalled its Git blob and original raw bytes; an
ordinary control became CRLF, proving conversion was active.

## Executed mutations

```sh
python tools/rust_scaffold/mutation_check.py --cargo <cargo-1.85.1> --rustc <rustc-1.85.1> --work-dir <scratch> --output-dir <results>
```

Observed **killed=4 survived=0**, baseline controls **4 passed**, mutated clean
controls **4 passed**, failed controls **0**. Six synthetic classifier controls
reject non-assertion outcomes. Source copies and logs remain in scratch.

| Mutation | Positive test | Mutated clean control |
|---|---|---|
| `address_field_shift` | `constructor_corpus_matches_python_words_and_bytes` | separate Mobius32 golden encode |
| `rounding_mode` | `constructor_corpus_matches_python_words_and_bytes` | separate Mobius32 golden encode |
| `retry_after_first_token` | `retry_stops_after_first_token` | `retry_before_token_preserves_meter_rows` |
| `expired_billboard_applied` | `billboard_expiry_and_clock_rollback` | `billboard_unexpired_delivery` |

The runner requires Cargo exit 101 from one selected assertion panic with the
expected failed test and summary. Compilation failure, arbitrary panic, signal,
wrong/missing test and failed clean controls cannot count as killed mutants.
Other test docstring mutations name failure modes; they are not claimed as extra
executed mutants.

## Scope, choices and repeats

Independent review found no prohibited library I/O, networking, threads, unsafe
blocks/FFI, random collections/clock access or cryptography. The lockfile has
only `rpp-core 0.1.0`. Production code uses deterministic ordered collections.
The resolver invalid-first-URI shadowing case was fixed and covered before the
full Cargo run. CSV tests cover comma, quote, LF and CR; JSON tests cover UTF-8
and control-character escaping. Typed-domain limits and preserved Python quirks
are documented in README and the corpus manifest.

IMPOSED: zero dependencies; provisional non-published crate; separate address
profiles; host-supplied discovery and outcomes; first eligible URI per modality;
one recorded attempt per repeated modality; terminal consent/trust/adapter
denial; no implicit migration policy; preserve existing URI quirks. The library
does not reproduce arbitrary Python dynamic types, unlimited integers or a
host's configurable huge-URI integer-conversion limit.

Features are `default = ["std"]`, `std = ["alloc"]`, and optional `alloc`.
The crate uses `no_std` without `std`. Word/byte codecs, named migration, ASCII
numeric URI parsing and caller-buffer URI/hex writers use `core` without a heap.
The full Unicode-digit parser and String helpers require `alloc`; resolver,
overlay and renderers also require `alloc` and compile without `std`. The shared
quantizer uses bounded binary64 multiplication and explicit half-even arithmetic
with no math-library dependency. All 9497 corpus rows still match.

CI is **non-advisory** on Ubuntu and Windows: read-only contents permission,
SHA-pinned checkout, exact Rust 1.85.1 with rustfmt/Clippy, fmt, Clippy `-D
warnings`, locked offline tests, no-default host tests, and both no-default
and alloc-only RISC-V library builds. Xtensa needs Espressif's toolchain and was
not added to CI; no board/firmware/radio or physical result is claimed. Repository required-check settings are
unchanged. No hosted outcome is claimed before observing the new run.

TR's Windows 11 / Python 3.13 repeat: run README's Cargo commands and the common
Python gates, then the mutation scaffold with native Cargo/Rustc paths. Expect
37 Rust tests, 1256 Python tests, golden 5/0 and 4 killed mutants. Compare corpus
TSV and overlay hashes. A different Python Unicode version may change generator
manifest environment metadata; native Windows was not executed here. Python
scaffolds are outside the library package; final Cargo builds need no Python.
