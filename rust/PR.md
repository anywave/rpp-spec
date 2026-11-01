# Add a dependency-free Rust RPP library with Python parity evidence

Mobi/LatticeWorks can use canonical addresses and resolver/overlay policy without
Python in final builds. Add one provisional `rpp-core` library, pinned Rust
1.85.1, explicit migration policies, a separate Mobius32 profile, pure modality
selection and an in-memory port of the overlay simulator. No I/O, networking,
threads, unsafe code, randomness or cryptography is implemented by the library.

Validation: 36 Rust tests; 9497 Python-oracle rows; CSV/Markdown/JSON scenarios
byte-identical to Python; all 4 named mutants killed with clean controls. Fmt and
Clippy `-D warnings` pass. Python tests 1256, golden 5/0, Ruff 0.14.10, whitespace
and branch-diff drift pass. CI adds non-advisory Ubuntu/Windows Rust checks;
required-check settings remain unchanged. See `rust/VALIDATION.md` for corpus
hashes, commands and explicit typed/runtime limits.

Branch `codex/rust-rpp-crate` → `master`. Merge the catalog-rulings branch first,
then this branch and the CX-007 report. No spec, Python behavior, header, vectors,
layouts or constants change. TR creates the PR and performs any merge.
