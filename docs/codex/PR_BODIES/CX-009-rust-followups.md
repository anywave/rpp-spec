# Keep simulation fixtures opt-in and detect stale Rust oracle data in CI

Default `rpp-link` consumers could previously call assumed-verification helpers.
The complete simulation module now requires the non-default `sim` feature;
default and no-default downstream compile probes check that its helper is absent,
and explicit `rpp-link/sim` tests preserve the scenario coverage. Decode docs
state that sequence freshness/replay remains host policy, and `CanonicalError`
implements `Eq`.

Rust CI regenerates all nine address, control and overlay oracle files in scratch
and rejects any byte difference, including manifests. Python is exactly pinned
per OS to available Unicode 15.0 engines (Ubuntu 3.12.14, Windows 3.12.10).
Host checks cover default, explicit simulation, no-default and alloc-only
profiles; Clippy covers default and all features. Existing pinned toolchain,
read-only permissions and bare-metal RISC-V builds remain ordinary failing gates.

The drift ruling guard checks now use explicit errors under Python optimization;
the baseline note distinguishes passage start from finding line without changing
its hash or status. Exact commands, counts, mutations and remote head are in
`docs/codex/OUTBOX/CX-009-001.md`. Hosted execution and board runs are not claimed.

Branch `codex/cx-009-review-follow-ups` → `master`, base `990905c` after CX-008.
No specification, Python runtime behavior, address layout, consent header,
published vector or constant changes. TR creates the PR and performs any merge.
