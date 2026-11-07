# R-RPP-GATELIST — independent review

Reviewer: Codex (digigami-review), 2026-11-07. Reviewed rpp-spec #48 at
`1bda4691f3a4762f8a17462ba387724a29963d5e`, base/master
`e213efb144275d87523856c728d8da2af9efbfe2`. Read the author report, including
“Remaining source work,” and TR's original AR-21 work order. Review only.

**Verdict: NOT READY at this head.** The unchanged slice gate rejects the
implementation commit. The verified standalone component is useful, but the
existing app's enforce integration and lossless Page consolidation are still
undelivered. No bypass of the implemented verifier was found in this review.

## Findings

**F1 — MEDIUM, `scripts/ci/gate.py:469`: the requested head fails the existing
per-commit size gate.** Commit
`91c8d2460fa20fb115b38b66dbd5c179c88d7d2d` counts **11 files / 1,440 lines**,
exceeding 10 files / 400 lines. Its following report correction is 1 file /
2 lines. The entire PR is 11 files / 1,442 lines and passes the separate
30-file/1,500-line total limit. Checks for pins, permissions, readable text,
tests travelling with source and PR total pass; slice-cap fails with the exact
same first-commit finding as the hosted review job. This is a packaging barrier,
not a request to change the guard.

An ordinary replacement branch from master could retain this exact final
content in five bounded commits: metadata/manifests/lock/readmes **5 files /
345 lines**; library + example **2 / 308**; admission tests **1 / 351**;
mutation runner + receipt **2 / 269**; author report **1 / 169**. These are
measured file groups, not new branches or commits created by this review.
Keep the existing PR branch/history intact; do not relax the gate or rewrite
its commits. The replacement would still need actual-range checks. Current
whole-PR headroom is only 58 lines; further integration work needs recounting.

**F2 — MEDIUM, `docs/codex/OUTBOX/RPP-GATELIST-SIG.md:119`;
`rust/rpp-gatelist/README.md:44`: the requested application enforcement is
not integrated.** The only `GateKeeper::dispatch` consumers in this source are
tests and the new offline example. The real historical log-only app call site,
settings migration and active-mode display are unavailable/unmodified. The
component accepts trusted host time/consent and a restored sequence floor; it
cannot supply the app's durable checkpoint or restart protection itself.
The example's audit callback deliberately returns true without persistence
(`rust/rpp-gatelist/examples/admission.rs:15`) and only permits local printing.
That is an honest demo, not evidence that an installed app now enforces policy.

To complete the app item, identify the real host boundary, preserve existing
authorization/egress/TTL checks, checkpoint the accepted sequence before effects,
restore that floor after restart, and wire explicit enforce/log-only selection
and visible warnings. Test refusal, checkpoint failure and restart replay at
that actual boundary. The spec's access-time consent/TTL duties remain
(`spec/SPEC.md:42`, `:56`). No existing gate-list default mandate was found;
the author's explicit proposed default/migration paragraph correctly satisfies
the instruction to propose that policy instead of silently changing it.

**F3 — MEDIUM, `docs/codex/OUTBOX/RPP-GATELIST-SIG.md:133`: no completed
lossless Page fold or redirect is supplied.** The report contains a future
recipe and proposed redirect wording. Neither original full body, a combined
export nor a block-by-block preservation map is present in the PR. The cited
trellis records identify the two Pages and summarize them; they are not the
original content. Independent accessible-Page searches for both titles did not
retrieve either body; the unrelated returned master-prompt Page has no exact
title matches. This does not establish that the originals do not exist.

Lossless preservation cannot be approved from summaries or short IDs. Obtain
both complete originals, retain them, map every original content block into the
combined artifact and verify the redirect target before claiming consolidation.
This review made no Page edit or redirect/publication.

**F4 — LOW, `rust/rpp-gatelist/Cargo.toml:12`;
`.github/workflows/rust.yml:169`: the security component has no automatic
CI test coverage.** Its independent workspace is outside the existing
`cargo test --workspace` member set. No workflow explicitly runs its locked
fmt/Clippy/tests or removal matrix. The hosted Rust workflow succeeds, but
that result covers the existing workspace, not this new verifier. The author's
proposed locked fetch and explicit host gates at report line 160 are appropriate
follow-up source work. Add those gates through the normal reviewed workflow
change; do not treat this review's one-head execution as ongoing CI coverage.

## Does the remaining source work block merge?

**For #48's current app-enforcement-and-Page-fold scope, yes.** F2/F3 block
acceptance of the advertised AR-21 delivery; the original work order explicitly
requests the app change and Page consolidation. They are scope gaps, with no
evidence of a new bypass in the standalone library. F1 independently blocks
this exact head under repository policy.

The tested host component can be delivered separately in an explicitly scoped
component-only replacement after its size barrier is resolved, with the
uncompleted app/Page work kept open. The proposed installation-default policy
does not itself require changing an existing default before such a component
landing. A Rust component landing must not be reported as AR-21 closed or as
an installed-app, durable-store, FPGA or Page-preservation acceptance.

F1 and F4 can be addressed together when preparing bounded component delivery
and its CI gates; recount after adding workflow changes. F2 needs the real app
source/host state path. F3 needs the original Page bodies. They are separate
source dependencies, not fixes a test scaffold can substitute for.

## Verified behavior of the implemented component

- `src/lib.rs:159–181`: exact 224-byte envelope and domain/version, independent
  pinned key identity, audience binding and Ed25519 strict verification precede
  acceptance. All 160 message bytes are signed, including sequence, expiry and
  sector grants. A payload-selected key is never used as the trust root.
- Sequence must be strictly greater than the in-memory/restored floor; equal,
  lower and zero-at-zero are rejected. No counter arithmetic can wrap;
  `u64::MAX` refuses all subsequent non-rising values. Restart is safe only when
  the host restores its durable trusted floor, as documented/tested.
- Expiry is exclusive: `expires_at <= now` refuses the update. Signature,
  unknown-key, malformed, audience, sequence, expiry and rollback refusals leave
  the last good list/sequence intact. Refusal never extends its old deadline.
- Enforce checks the supplied update and active list at the operation boundary.
  An invalid supplied update refuses that request even when the old list could
  otherwise admit it. Missing/expired lists, denied theta sectors and clock
  rollback cannot dispatch. A later request can use the retained good list.
- `src/lib.rs:220–239`: log-only is an explicit constructor argument with a
  distinct label, audit mode/refusal/sequence and visible smoke output. It
  permits observed policy refusals by design. Both modes refuse absent consent
  and a failed audit callback; audit happens before the operation. The dispatch
  bit describes intended permission, not proof that a host operation completed.
- Validated Mobius32 theta alone indexes the 512-bit map, including 0 and 511.
  Phi/shell/harmonic changes cannot redirect the grant lookup. No published
  address format, control frame, consent header or spec default is modified.

“Future-dated call” protection is against invalid calls poisoning state; the
API relies on trusted host time. It does not obtain a wall clock or authenticate
an arbitrary caller's timestamp. A future timestamp alone grants no new
sequence; a valid pinned signature, rising sequence and unexpired list remain
mandatory. Untrusted timestamps must not be passed as trusted host time in the
eventual app integration.

## Executed tests and removal evidence

Independent tools: official workspace-local Rust **1.85.1** with rustfmt/Clippy;
Python **3.12.14**, pytest **8.4.2**, pytest-asyncio **1.2.0**, Ruff **0.14.10**.
The review gates use the repository's hash-pinned PyYAML **6.0.2**. Tool/package
downloads preceded testing; Cargo test/mutation commands use `--offline --locked`.

| Check at `1bda4691` | Independent result |
| --- | --- |
| New crate fmt / all-target Clippy | PASS / PASS |
| New crate all-target tests | **16 PASS**, 0 failures |
| Committed bounded removal matrix | **22 killed / 0 survived**, 6 false-kill classifier controls |
| Two additional future-clock probes | **2 PASS**, both targeted removals caught with assertion failures and an unrelated passing control; restored **2 PASS** |
| Offline example `enforce` / `log-only` | PASS; expected refusal/dispatch and visible mode output |
| Example without mode | Correctly exits **2** |
| Existing Rust workspace | **210 PASS**, 0 failures, 42 result groups |
| Python `pytest tests -q -o addopts=` | **1,297 PASS / 210 SKIP**, 1 existing deprecation warning |
| Mobius32 golden script | **5 PASS** |
| New scaffold Ruff | PASS |
| Existing `rpp tests --ignore E501` Ruff | FAIL: **8 pre-existing** errors in unchanged Hedera test files |
| Review gates | pins / permissions / readable / tests-travel / PR-total PASS; slice-cap FAIL, F1 |
| Drift check | **0 HIGH / 0 MEDIUM / 0 LOW** new findings; 239 open baselines remain |
| Rust lift boundary guard | PASS; 11 manifests / 67 Rust sources / 40 references, 0 findings |

The 210 Python skips are optional SDK/native Hedera coverage absent here, not
gate-list tests. Ruff's E402/E731 inputs and configuration are byte-identical
to master; those eight errors are not introduced by this PR. Counts across
overlapping suites must not be presented as unique product tests.

The committed runner requires a named assertion failure plus an unrelated
passing control. Compiler errors, arbitrary panics and empty runs do not count.
I reran it and reproduced the committed JSON **byte for byte**, SHA-256
`038b5793674df8680d1a6c79328d30f350cc0d24f4d1945fdd2bb4ad52f44ea4`.
Verified source SHA-256:
`9b029208dd9968e0b15b982136ed83b26eae74a0c7724d6b644a58fe795083ab`.

| Rule / boundary | Executed removal coverage |
| --- | --- |
| Strict signature and pinned identity | `signature_removed`, `pin_removed`, `weak_pin_allowed` |
| Strict sequence / replay / restored floor | `sequence_removed`, `equal_sequence_allowed`, `floor_ignored`; full tests include `u64::MAX` then zero |
| Exclusive update expiry | `update_expiry_removed`, `expiry_boundary_inclusive` |
| Envelope domain and audience | `domain_removed`, `audience_removed`; full tests tamper signed regions and lengths |
| Update and admission rollback | `update_rollback_allowed`, `admission_rollback_allowed` |
| Missing/stale/denied active list | `missing_list_allowed`, `admission_expiry_removed`, `sector_guard_removed` |
| Enforce boundary / request update refusal | `enforce_bypassed`, `request_update_failure_hidden` |
| Consent / audit fail closed | `consent_bypassed_in_log_only`, `audit_failure_ignored` |
| Good replacement / visible mode / theta axis | `last_good_not_replaced`, `log_only_mode_hidden`, `phi_as_consent_axis` |

The additional probes were run in disposable copies: an invalid signed update
at `u64::MAX`, and an expired future request in each mode, preserve list/sequence
and permit a subsequent valid update at normal time. Premature update-clock
advancement and advancing the clock on a refused log-only request each fail
their corresponding assertion test. Neither change touched the PR checkout.
These supplement the committed matrix; they are not shipped product tests.

Matching-head hosted Rust, Golden vectors, Consent gate and advisory Drift runs
succeed. `codex-gate` fails at “Review PR range”; CI fails at the existing Ruff
step while its nine Python matrix jobs and package build succeed. No all-green
hosted result or standalone Rust CI coverage is claimed.

## Keys, side effects and review delivery

No fixed signing key, signed fixture, token or actual secret was found in the
new tracked files or added-line secret scan. Tests/example generate throwaway
keys from OS entropy in memory and do not print or persist keys/signatures.
The zero/constant arrays used for invalid public pins, namespace and bitmap
initialization are not committed private credentials. Public signer identity
is part of the signed envelope. `ed25519-dalek = 2.2.0` is the published pinned
dependency, with lockfile checksums and BSD-3-Clause provenance documented.

The library is `no_std`, forbids unsafe code in this crate and has no I/O,
ledger client, transport or mainnet configuration. Example effects only print;
existing workspace socket tests use localhost. No testnet/mainnet transaction,
account, money transfer or external product write was attempted. A host-provided
operation callback still needs the host's own egress/network authorization;
this component is not a Hedera network guard.

No Page, source PR branch, master, workflow, rule or owner setting was changed.
Review tools/build outputs are local; tracked PR source remains byte-identical.
Only this report is written on `codex/R-RPP-GATELIST`, created from pinned master.
No merge or force push.
