---
id: RPP-GATELIST-SIG
from: Codex (rpp-spec)
to: TR
repo: anywave/rpp-spec
branch: codex/RPP-GATELIST-SIG
head: refs/heads/codex/RPP-GATELIST-SIG
head_kind: final-pushed-branch-ref
source_base: e213efb144275d87523856c728d8da2af9efbfe2
inbox: trellis-channel/codex/inbox/rpp-spec.md:1500
inbox_head: c2d8791e3720a2ce7e2076d8e97b9de756798c04
date: 2026-11-07
status: PARTIAL-source-blocked
---

The host verifier and protected dispatch component work offline. **AR-21 is not
closed:** the historical desktop-app log-only call site and the full text of
both Pages were not available. This is a tested, usable Rust integration
component and local smoke application, not a claim of deployment in Mobius or
of a completed Page consolidation. No published spec or wire format changed.

| Card item | Result and evidence |
|---|---|
| Pinned signature, rising sequence, expiry | Implemented in `rust/rpp-gatelist/src/lib.rs:158`; Ed25519 strict verification, exact length/domain, audience binding. |
| Rejection retains last good | Updates commit only after every check; tests assert list and sequence retention, then successfully dispatch using the old list. Old expiry is never extended. |
| App enforce/log-only | Actual callback boundary at `lib.rs:206`; offline example calls it. Enforce denies invalid supplied updates, missing/expired lists, denied sectors and rollback. Explicit log-only audits the same failures and permits the operation. |
| Current consent and audit | Both modes refuse absent consent and audit/checkpoint failure. Audit is before operation, with intended dispatch, mode, refusal and sequence. |
| Installation default | No gate-list mode-default mandate located in `spec/`. No implicit default or install setting changed; proposed change below. |
| Existing desktop integration | BLOCKED: no historic RPP gate-list/log-only app call site identified in available source. No claim that the new example changes an installed app. |
| Fold two Pages | BLOCKED: only review summaries/short IDs available. Neither original body nor a writable source export found. No content discarded or redirect falsely published. |

## Implementation and boundaries

`rust/rpp-gatelist` is an independently locked, unpublished Rust 1.85.1 crate,
`#![no_std]`, no heap, no unsafe code in our crate, no I/O or network. It uses
published `ed25519-dalek = 2.2.0` (BSD-3-Clause), with dependencies pinned by
its Cargo.lock. No crypto algorithm is written here and nothing is vendored.
Original wrapper/tests/example/scaffold are Apache-2.0. Upstream licence:
<https://docs.rs/crate/ed25519-dalek/2.2.0/source/LICENSE>.

The new experimental 224-byte local envelope has a 160-byte signed message:
domain/version, public signer identity, host audience, sequence, expiry and a
512-sector bitmap; then a 64-byte Ed25519 signature. This is **not** an addition
to a consent header, address layout or existing control frame. The validated
Mobius32 type is used, theta alone selects the sector. Canonical-v2 is separate.

Trusted pin/audience/time/consent arrive from the host. State is private and
updated atomically in memory. Invalid future-dated calls cannot advance its
clock. A valid list expires at `expires_at == now`; retained expired data grants
nothing in enforce mode. u64::MAX cannot wrap. Tests and smoke application use
OS-generated throwaway signing keys in memory; no key or signed fixture is
committed, printed or persisted. This code has no ledger backend: all effects
are offline, and there is no mainnet, money or account path.

The host must checkpoint `Admission.sequence` before permitting effects, return
false if that audit/checkpoint fails, restore a trusted durable sequence floor
on restart, and supply trusted nondecreasing time. Restart has no active list
and needs an update strictly newer than the restored floor. Storage, pin
rotation, configuration integrity and existing app authorization remain host
responsibilities. This component does not establish peer identity or replace
an app's existing egress, authorization, consent or per-address TTL checks.

`hardware/verilog/RPP_CONSENT_GATE.md:14` explicitly leaves verification outside
v0 (`upd_auth_ok`). No FPGA circuit or ULX3S run is claimed; this signature
verifier does not drive the hardware stub. The full replacement-list sequence
is distinct from the RTL's per-sector epoch/update stream.

## Checks and mutation evidence

All commands below ran on Linux, offline except Git reads/push and the existing
workspace's localhost-only socket tests. Rust commands used the installed
1.85.1 toolchain and cached crates. Python was 3.12, Ruff 0.14.10.

| Command from repo root | Actual result |
|---|---|
| `cargo fmt --manifest-path rust/rpp-gatelist/Cargo.toml -- --check` | exit 0 |
| `cargo clippy --manifest-path rust/rpp-gatelist/Cargo.toml --all-targets --offline --locked -- -D warnings` | exit 0 |
| `cargo test --manifest-path rust/rpp-gatelist/Cargo.toml --all-targets --offline --locked` | 16 passed, 0 failed |
| `python tools/gatelist_scaffold/mutation_check.py --output /tmp/rpp-gatelist-mutations.json` | 22 killed, 0 survived; 6 false-kill classifier controls |
| `cargo test --manifest-path rust/Cargo.toml --workspace --offline --locked --no-fail-fast` | 210 passed, 0 failed, 42 result groups |
| `python -m pytest tests -q -o addopts=` | 1297 passed, 210 skipped (optional Hedera native/SDK coverage unavailable), 1 existing deprecation warning |
| `python tests/test_golden_vectors_mobius32.py` | 5 passed, 0 failed |
| `ruff check --no-cache tools/gatelist_scaffold/mutation_check.py` | exit 0 |
| `ruff check --no-cache rpp tests --ignore E501` | exit 1, 8 pre-existing errors; identical on archived base master |
| `git diff --check` | exit 0 |
| `python -m tools.drift check --base e213efb144275d87523856c728d8da2af9efbfe2 --head HEAD --output-dir /tmp/rpp-gatelist-drift` | See final verification below. |

Ruff baseline: E402 in `tests/hedera_initializer_sigint_probe.py:15,17`; E731
in `tests/test_hedera_sdk_security.py:809,842,912,922,952,954`. These files are
unchanged. An initial unscoped repository Ruff run found 245 existing errors;
the table uses CI's actual `rpp tests --ignore E501` scope. No suppression added.
Initial sandbox workspace tests could not bind localhost (`Operation not
permitted`); the permitted localhost repeat passed all 210 with no outside peer.

Every new test documents its failing mutation. The committed bounded mutation
matrix is `tools/gatelist_scaffold/results/mutations.json`: signature, pin,
sequence removal/equality, expiry removal/boundary, audience, domain, weak pin,
restart floor, update/admission rollback, active-list expiry, sector lookup,
missing list, enforce bypass, request-update error hiding, consent, audit,
last-good replacement, visible mode and phi/theta mix-up. Each mutant must
produce an assertion failure in its named test and pass an unrelated clean
control; compiler errors, empty runs and arbitrary panics never count as kills.

Source SHA-256 (UTF-8/LF):
`9b029208dd9968e0b15b982136ed83b26eae74a0c7724d6b644a58fe795083ab`.
Mutation JSON SHA-256 (exact bytes, `.gitattributes -text`):
`038b5793674df8680d1a6c79328d30f350cc0d24f4d1945fdd2bb4ad52f44ea4`.

The smoke example in enforce mode dispatched valid/last-good cases and refused
replay/expiry; log-only printed its warning and each refusal while continuing.
Missing mode returned exit 2. Example operations print locally and send nothing.

## Remaining source work and proposed edits

The spec requires access-time consent resolution (`spec/SPEC.md:42`) and software
TTL enforcement (`:56`), but no text found specifies a gate-list admission mode
default. **Proposed, not decided:** new installs explicitly select `enforce`;
existing log-only installs retain `log-only` with a visible warning until an
owner changes it. Required changes: an approved admission-default paragraph,
new-install initializer and settings migration, visible active-mode display,
then the real app call site using `GateKeeper::dispatch` and durable checkpoint.
No installation initializer, desktop UI or mode migration exists in this repo.

Sources for the Page task are only trellis-channel `codex/PRODUCT_DESIGN_MAP.md:697`
and `artifacts/research/ARTIFACT-REVIEW-2026-11-05.md:113` (same inbox freeze).
They identify `6678c975` **RPP Shown Working** and `177a0b68` **What Makes RPP
Different**, but contain no original bodies. Accessible Pages search and a
fully paginated Page listing returned neither. Named-repo searches found no
full export. Remote Mobius searches found unrelated r2 capability admission,
not this historic RPP gate-list hook. Those searches do not prove its absence
from every private branch. A source-location question was sent while coding.

Pending exact source access: retain **RPP Shown Working**, append every unique
section from **What Makes RPP Different**, preserve both complete originals in
an appendix/export, and check each original content block maps to the combined
page before replacing the second body. Proposed redirect note, not applied:
“This page has been consolidated into RPP Shown Working (6678c975). All prior
content is preserved there, including the source appendix.” Do not publish this
claim until preservation is verified; no URL is invented from a short ID.

## Reproduce on Windows and integrate

PowerShell, root checkout, with Rust 1.85.1 and the locked crates cached:

```powershell
cargo +1.85.1 fmt --manifest-path rust/rpp-gatelist/Cargo.toml -- --check
cargo +1.85.1 clippy --manifest-path rust/rpp-gatelist/Cargo.toml --all-targets --offline --locked -- -D warnings
cargo +1.85.1 test --manifest-path rust/rpp-gatelist/Cargo.toml --all-targets --offline --locked
cargo +1.85.1 run --manifest-path rust/rpp-gatelist/Cargo.toml --offline --locked --example admission -- enforce
cargo +1.85.1 run --manifest-path rust/rpp-gatelist/Cargo.toml --offline --locked --example admission -- log-only
python tools/gatelist_scaffold/mutation_check.py --output "$env:TEMP/rpp-gatelist-mutations.json"
python -m pytest tests -q -o addopts=
python tests/test_golden_vectors_mobius32.py
```

No native Windows or hosted CI result is claimed. The standalone crate has
separate gates because the current workspace workflow has an offline cache and
does not fetch Ed25519 dependencies. Proposed owner CI addition: fetch its
locked manifest in the read-only setup, then run its fmt/Clippy/test commands on
Ubuntu/Windows. No protected workflow, gate, owners file or ruleset is edited.

IMPOSED: standalone host component; Mobius32 theta bitmap; audience separation;
exclusive expiry; no mode default; host-managed durable floor and checkpoint;
fresh newer list after restart; no implicit key rotation; no deployed-app,
FPGA, physical-erasure or lossless-Page claim. One ordinary branch push, no PR,
merge, force or master write. PR title suggestion: “Add pinned signed gate lists
and explicit application admission (host component; integration pending)”.
