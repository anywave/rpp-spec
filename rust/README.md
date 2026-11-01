# Provisional RPP Rust library

`rpp-core` is one dependency-free library crate for Mobi/LatticeWorks callers.
The name is provisional and publishing is disabled; PL/FP may rename it. The
workspace pins Rust **1.85.1** and commits its lockfile.

CX-008 adds the unpublished `rpp-control` fixed-frame codec and `rpp-link`
adapter interface crates to this workspace. [ESP32 adapter guidance](ESP32.md)
describes their features, host simulation, provisional frame and board gaps.
The module and Python-parity details below describe `rpp-core`.

CX-010 adds the unpublished `rpp-fleet` crate: explicit proposed address
bindings, endpoint records and live selection through the existing overlay
policy. [Fleet guidance](FLEET.md) describes assignment and adapter boundaries.

`rpp-link` simulation helpers require the explicit, non-default `sim` feature.
Default features and `std` alone do not expose `rpp_link::simulated`, including
`verified_fixture` and its assumed-verification fixture. Enable host simulation
with `--features rpp-link/sim`; this also enables `std`. Actual downstream
compile probes check that default and no-default-feature consumers cannot name
the helper. The fixture is development support, not a production verifier.

The ESP32 readiness check builds the library for
`riscv32imc-unknown-none-elf`, a bare-metal RISC-V target used for ESP32-C3
integration. This is a library cross-compile check, not a board run or a firmware
image. No board, radio, transport, linker script, HAL, flashing or boot behavior
is implemented or validated here. Xtensa targets are outside this CI check.

The library operates entirely on caller-provided values. It performs no I/O,
networking, discovery probes, threading, randomness, inference or cryptography.
`#![forbid(unsafe_code)]` applies to every module. Collections use deterministic
ordering. Hosts supply transport outcomes, current membership/consent, measured
links and abstract verification results; a boolean fixture does not establish
real authenticity or implement a tunnel.

## Modules

| Module | Contract |
|---|---|
| `canonical` | Current canonical v2 field layout, big-endian words/bytes, half-to-even radius byte, URI parsing/formatting and explicit migration policies. |
| `mobius32` | Separate Mobius32 profile and the original five golden-check families. Its layout must not be passed to the canonical v2 decoder as the same profile. |
| `resolver` | Pure selection from host-supplied discovery, preferences/default order, access gate and attempt outcomes. Unavailable/not-found falls back; denial terminates; `tried_modalities` preserves attempts. |
| `overlay` | Scripted route eligibility/ranking, relay, token-boundary retries, breakers, complete meter rows, verified independent control and scoped expiring billboards. |
| `scenarios` | In-memory CSV, Markdown and JSON artifacts for the same scripted Python scenarios. It opens no transport and writes no files. |

Migration requires a `MigrationPolicy::{NeutralRadius, ShellProjection}` argument.
There is no `Default` policy. This adds no Python migration API or wire field.
Resolver discovery is input: the crate does not probe devices, authenticate
identities, persist data or implement the legacy Python storage backends.

## Embedded feature profiles

| Cargo selection | Library profile | Allocation and integration boundary |
|---|---|---|
| `--no-default-features` | `no_std` canonical and Mobius32 codecs | Word/byte encoding and decoding require no heap. Allocating convenience APIs and policy models are excluded. |
| `--no-default-features --features alloc` | `no_std` with `alloc` | Adds allocating helpers and resolver/overlay/scenario policy models. A firmware application using these allocations must supply its own allocator and memory budget. |
| Default features (`std`) | Host library with `std` and `alloc` | Preserves host APIs, parity tests and in-memory scenario artifacts; still performs no I/O or transport operations. |

The allocation-free codec profile does not require an allocator. A successful
`alloc` library cross-build checks that the policy models compile without `std`;
it does not provide an allocator or establish that their dynamic collections fit
a particular device. Hosts remain responsible for input sizes, heap limits,
timing, transport outcomes, identity and consent. These feature boundaries add no
protocol profile, wire field or crypto implementation.

Without `alloc`, canonical URI support uses `from_uri_ascii`: numeric fields
accept ASCII digits, with the documented Greek field keys. The full Unicode Nd
parser remains available with `alloc`. Heap-free `write_uri` and `write_hex`
write through a caller-supplied `core::fmt::Write`; callers choose their buffer
and handle its capacity errors. The owned `String`-returning `to_uri`/`to_hex`
helpers require `alloc`. No allocator implementation is supplied by the crate.

## Fidelity and input domain

The default/alloc canonical binding is checked against **9497 actual Python-reference rows**:
4110 constructor cases, 2119 raw words and 3268 URI cases. Coverage includes all
2048 accepted discrete field combinations, decoded radius codes, all quantizer
ties with adjacent floats, fixed-seed sweeps, reserved/null/wildcard states and
Unicode decimal URI digits.

The corpus establishes byte parity on the tested shared domain. Rust integer
arguments cannot represent Python bool/noninteger arguments or arbitrary-size
Python integers. Signed `from_int` is bounded to `i64`; `from_word` covers all
`u32` values. The Unicode Nd table is frozen to the reference's Unicode 15.0.0.
Python's externally configurable `sys.int_max_str_digits` setting for enormous
leading-zero URI groups is not a Rust protocol limit. Hosts must impose their
own input-size budget. These boundaries do not change the Python reference.

The current Python URI quirks are preserved: prefix matches can accept suffixes,
and a negative-zero radius formats as `r:-0.00` that the parser rejects. A2 stays
a separate behavior proposal. Address types preserve accepted reserved values
instead of silently applying a new validation policy.

Overlay types define integer/UTF-8 limits explicitly. Strong enums and typed
booleans make some malformed Python dynamic inputs unrepresentable; absent
verification/billboard options still fail closed. Tick and interval checks,
known data-path provenance, tunnel verification, consent and replay/expiry
guards remain policy requirements. The three reference scenario artifacts are
compared as bytes, including line endings and JSON/CSV escaping.

## Build and verify

From `rust/`, with rustup installed:

```sh
rustup toolchain install 1.85.1 --profile minimal --component rustfmt --component clippy --target riscv32imc-unknown-none-elf
cargo +1.85.1 fmt --all -- --check
cargo +1.85.1 clippy --workspace --all-targets --offline --locked -- -D warnings
cargo +1.85.1 clippy --workspace --all-targets --all-features --offline --locked -- -D warnings
cargo +1.85.1 test --workspace --offline --locked
cargo +1.85.1 test --workspace --features rpp-link/sim --offline --locked
cargo +1.85.1 test --workspace --no-default-features --offline --locked
cargo +1.85.1 test --workspace --no-default-features --features alloc --offline --locked
cargo +1.85.1 build --workspace --no-default-features --target riscv32imc-unknown-none-elf --offline --locked
cargo +1.85.1 build --workspace --no-default-features --features alloc --target riscv32imc-unknown-none-elf --offline --locked
```

The Ubuntu/Windows workflow runs formatting, Clippy with default and all features,
host tests with default features, explicit simulation, no default features and
alloc-only features, and both bare-metal cross-builds as ordinary failing jobs.
None of those checks is advisory. The no-default-feature host run
also exercises the codec golden checks; it does not execute RISC-V code on a
host CPU. CI has read-only contents permission and a SHA-pinned checkout.
Required-check configuration is unchanged; TR controls branch protection.

Python is development scaffolding only. From the repository root, use the
compatible Python 3.12 engine described below for the checker and its tests:

```sh
python tools/rust_scaffold/check_corpora.py
python -m unittest discover -s tools/rust_scaffold/tests -p test_check_corpora.py -v
python tools/rust_scaffold/address_corpus.py --output-dir <scratch-corpus>
python tools/rust_scaffold/mutation_check.py --cargo <cargo-1.85.1> --rustc <rustc-1.85.1> --work-dir <scratch-mutations> --output-dir <scratch-results>
```

Set `PYTHONPATH` to this checkout when invoking the address scaffold directly.
The scaffold executes the unchanged Python address reference with explicit
seeds 0 and 1. It is outside the Rust crate and is not shipped in its package.
Rust final builds/tests consume committed data and require no Python. The
CI checker regenerates all twelve committed oracle files into temporary scratch
directories: the three address TSVs and address manifest, three overlay scenario
artifacts, the control TSV and control manifest, and the fleet scenario TSV,
Markdown and manifest. It compares every byte, including all three manifests, and never rewrites committed evidence. Exit 0 means
fresh; exit 1 means stale/missing/different data; exit 2 means an incomplete
check or incompatible reference engine. No metadata difference is ignored.
CI also runs the freshness guard's regressions for changed rows/manifests,
missing/extra files and incompatible reference engines.

Use a Python 3.12 reference engine with Unicode 15.0.0. CI pins **3.12.14 on
Ubuntu** and **3.12.10 on Windows**, the exact available x64 builds in the
official [actions/python-versions manifest](https://github.com/actions/python-versions/blob/main/versions-manifest.json).
The inspected manifest blob was `b0c84be989675d2d78a4ac17491154d44075a04e`:
3.12.14 supplied Linux builds and 3.12.10 was the latest listed Windows 3.12
build. This is read-only availability evidence, not a hosted CI execution.
The committed manifest records Unicode version rather than Python patch level;
both selected engines must reproduce the same complete files. A Python 3.13
launcher can select a compatible engine using
`check_corpora.py --python <python-3.12>`. Its own newer Unicode tables are not
silently substituted for the reference engine. CI installs no Python package
dependencies for this stdlib-only checker.

All committed test data is covered by `.gitattributes -text`. Test names are
bounded and each test states a failing mutation. The development mutation runner
uses disposable Rust workspace copies; field shift, rounding, post-token retry
and expired-billboard mutants must fail an actual selected assertion test, while
clean controls pass. Compile errors and unrelated panics never count as kills.

This library does not promote the overall coherence/sector verdict, adopt an
informative network proposal as deployed behavior, provision keys or grant
consent. Existing specification, Python runtime, header, vectors and constants
remain unchanged.
