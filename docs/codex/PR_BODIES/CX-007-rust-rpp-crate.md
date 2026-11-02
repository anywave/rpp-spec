# Add a dependency-free Rust RPP library with parity and embedded compile checks

Mobi/LatticeWorks can use canonical addresses and resolver/overlay policy without
Python in final builds. Add one provisional `rpp-core` library, pinned Rust
1.85.1, explicit migration policies, a separate Mobius32 profile, pure modality
selection and an in-memory port of the overlay simulator. No I/O, networking,
threads, unsafe code, randomness or cryptography is implemented by the library.

The allocation-free codec profile supports `no_std` without a heap. Resolver,
overlay and scenario models use the optional `alloc` profile; default `std`
preserves host behavior. Pinned Rust 1.85.1 CI runs host tests without default
features and cross-compiles both codec-only and alloc-enabled library profiles
for `riscv32imc-unknown-none-elf`. This checks ESP32-C3 integration readiness at
the library boundary; no board, firmware, radio, transport or Xtensa target is
run or implemented.

Validation commands, feature-specific test/build results, the 9497-row Python
oracle corpus, scenario byte comparisons and named mutation evidence are recorded
in `rust/VALIDATION.md`. CI adds Ubuntu/Windows formatting, Clippy `-D warnings`,
host tests and both cross-builds as ordinary failing checks; none is advisory.
Required-check settings remain unchanged. The library cross-build does not
validate device memory capacity or supply a firmware allocator.

Branch `codex/rust-rpp-crate` → `master`. Merge the catalog-rulings branch first,
then this branch and the CX-007 report. No spec, Python behavior, header, vectors,
layouts or constants change. TR creates the PR and performs any merge.
