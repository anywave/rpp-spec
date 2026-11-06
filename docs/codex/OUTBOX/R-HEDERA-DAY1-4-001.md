# R-HEDERA-DAY1-4-001

Independent reviewer-only re-read requested by TR on 2026-11-06. Latest inbox
blob: `b0001d4788b186d7e2010601a631f9efe3006d14`. Baseline:
[R-HEDERA-DAY1-3-001](R-HEDERA-DAY1-3-001.md) at
`4b9a4efe0560c48fea7609a04dba646f51c0242e`. Another thread wrote both changes.

**The native orphan-reference N2 repair is verified. rpp-spec #46 is READY WITH
FIXES for a separate LOW direct-initializer diagnostic edge (N3). mobius #291
is READY: the merge preserves the complete reviewed crate and both Hedera
documents byte for byte, and all 50 mutation controls pass.**

No merge, force push, PR-branch changes, ledger writes, live smoke, funding or
real credential access occurred. Only rpp-spec, mobius and trellis-channel were
used. Native tests used harmless receivers or actual SDK synthetic keys generated
only in memory. Key-bearing representations stayed in memory; saved outputs
contain booleans/counts/fixed labels. Core dumps were disabled. Temporary controls
ran in detached worktrees/copies and were restored. This report is the only
delivery file added to `codex/R-HEDERA-DAY1`.

## PR decisions

| PR | Exact reviewed head | Verdict | Result |
| --- | --- | --- | --- |
| rpp-spec #46 | `2e0020c0eef4349480658add57f47bfa2427a70e` | **READY WITH FIXES** | N2 native ownership closed; N3 LOW interrupted direct-initializer traceback retains key inputs. |
| mobius #291 | `82557ce835cc49f056098b6a7d8976de5f051c57` | **READY** | F4-R/N1 unchanged; merge resolutions match the incoming base; tests and 50 mutants pass. |

The Python implementation is frozen at source commit
`28f0335aab6626fe3d3a73f937449642fd6a4a12`; its report-inclusive head adds
documentation/evidence only. READY covers the reviewed HCS foundation and merge
preservation, rather than complete Mobi/application or production readiness.

## N3 — LOW — SIGINT before the direct signer's cleanup assignment leaves key-bearing traceback locals

**rpp-spec #46: `rpp/adapters/hedera_safe.py:132`.**

The direct _Signer initializer retains its raw key argument and bound signing
operation until the finally assignment `key = operation = None`. A single
SIGINT delivered just before that assignment interrupts cleanup itself. The
escaped KeyboardInterrupt traceback still owns those locals. Standard
`traceback.TracebackException.from_exception(error, capture_locals=True)`
captures raw private-key bytes from this product frame.

An unchanged-source line trace delivers actual SIGINT at line132 after otherwise
successful native creation/publication. Both Ed25519 and ECDSA probes find the
generated key in the library frame's captured diagnostic locals. Comparisons
are restricted to hedera_safe.py frames, so caller-held fixture keys are not
misattributed. The no-key diagnostic regression exits1 on an intended assertion.
No key-bearing diagnostic text was printed or saved.

This is a bounded direct-helper issue: reproduction calls _Signer directly with
a generated key. The normal ExperimentalHieroBackend constructor replaces that
inner exception, and both equivalent backend-factory probes remain key-safe.
No recovery of an opaque client's owner key, default-log disclosure, unauthorized
send or orphan C reference was demonstrated. Those limits account for LOW
severity. This is separate from the corrected native reference-count defect.

**Correction:** ensure the normal raw-input lifetime ends inside the protected
path so one interrupt at its final cleanup hand-off cannot leave those inputs in
an escaped direct-initializer traceback. Retain native ownership, safe control
exception types and the factory's exception-graph replacement. Add direct and
factory regressions with the actual error/traceback retained, covering the
cleanup-assignment boundary as well as native return/publication/release.

Evidence: `work/hedera-review4-evidence/diagnostic_boundary.py`,
`diagnostic-boundary-results.json`, `diagnostic_regression.py`/log and the narrower
`probe_cleanup_interrupt.py`. Direct initialization leaks in two algorithm cases;
the two normal backend cases pass.

## N2: owning capsule and every surrounding ownership hand-off

The original manually pinned callback could be stranded before Python had a
capsule to own it. The new helper closes that native window:

- `rpp/adapters/_hedera_signer_native.c:135`: new increments at line147 and creates
  the owning capsule/destructor at line148 in one C call. Allocation failure
  decrements at line150 before returning.
- `.../_hedera_signer_native.c:102`: release tombstones at line116 before its one
  decrement at line119. Repeated release observes the tombstone and returns.
- `.../_hedera_signer_native.c:124`: the native destructor releases an abandoned
  returned capsule, while preserving an already active exception.
- `.../_hedera_signer_native.c:184`: invocation takes an additional strong reference
  at line199, calls the operation and drops that reference at line201. Concurrent
  close cannot free an in-flight callback.
- `rpp/adapters/hedera_safe.py:126` receives an already owning object. Destruction
  at line161 releases before removing its registry entry at line162, so an
  interrupted unpublication leaves discoverable cleanup state. Shutdown and
  explicit repeated cleanup use the same idempotent native release.

The native entry points retain the GIL, refuse non-main-interpreter calls, and
reject unsupported free-threaded compilation. No operation/key accessor or GC
referent is exposed. Native callback failures replace their SDK error graphs
before returning fixed errors or fresh supported control exceptions.

Independent unchanged-source interrupt probes cover **280 normal-path actual
SIGINT line/opcode points**: initialization71, callable entry27, invocation42,
release26, destructor60, shutdown54. Each delivered interrupt is verified;
receiver references release exactly once, registry cleanup is repeatable and
saved handles close. Python error frames are explicitly cleared before this
native-balance check; N3 separately tests whether retained diagnostic frames
are key-safe. No native crash or double release occurred.

An additional **232 allocation/store-failure plus interrupt observations** are
recorded separately. All132 store cases released; five of100 synthetic allocation-
refusal cases retained Python references during interrupted exception unwinding.
In those five the replacement allocator refused before calling native.new, so
there was no C allocation or native pin to orphan. They are not counted as
passing native ownership cases. This distinction avoids treating Python
exception-frame retention as evidence for or against the repaired C owner.

Another **2,004 checks** pass: 1,000 create/repeated-close/GC cycles, automatic
capsule destruction, concurrent invocation/close, and the real C allocation-
failure rollback branch. The latter compiles an isolated copy forcing
PyCapsule_New failure and confirms receiver release; product sources remain
unchanged. The compiler's unused-destructor warning for that forced branch is
expected. The supplied destructor-removal control also recompiles the helper
and fails its actual SIGINT regression by assertion.

The helper builds explicitly for the active GIL-enabled CPython. Missing native
support refuses local signing; defaults remain pure Python with experimental
signing opt-in. The new build scripts read compiler/interpreter configuration,
not Hedera keys. Windows, other runtimes and full distribution packaging were
not independently exercised in this re-read. Python remains the explicitly
experimental community SDK boundary.

## Rust merge audit: conflicts and their resolutions

Reviewed merge parents:

- First parent, previously reviewed Hedera head:
  `2d8d036792aa97548b51d04491ee9b2afe337d83`.
- Incoming fp/v081-usable:
  `3c08a537416f576afb5912cf9e00099970aea219`.

Read-only merge-resolution diffs confirm five conflict paths. Each resulting
file is byte-identical to the incoming parent, including its deletion decision:

| Conflicted file | Resolution verified |
| --- | --- |
| `extensions/document-rag/python/whisper_service.py` | Incoming deletion retained; the live Python service stays retired. |
| `src-tauri/src/core/whisper_bridge.rs` | Full incoming blob `ec7bc4dd…`; preserves the incoming native Whisper path and extracted HTTP policy/consent/audit behavior, rather than the old inline duplicates. |
| `web-app/src/components/FirstRunWizard.tsx` | Full incoming blob `ef1de0bc…`; retains incoming provisioning and model filename/id deduplication. |
| `web-app/src/extensions/document-rag/src/library/components/importers/ChatGptImportButton.tsx` | Full incoming blob `f3b50bb6…`; retains typed selected-path extraction and the incoming camelCase invoke argument. |
| `web-app/vitest.config.ts` | Full incoming blob `f0f5fd60…`; retains its superset of test exclusions, including retired paths. |

Two additional **non-conflict** paths, live `loopback_guard.py` and
`test_loopback_guard.py` beside the retired Python service, were removed after
the automatic merge would have resurrected them. Their exact first-parent blobs
remain under `Obsolete/voice-relay-py-2026-10-19/`; this matches the incoming tree.
They are not additional conflict resolutions.

The merged tree differs from `3c08a537` **only by the 11 previously reviewed
Hedera additions**: nine crate files and two Hedera documents. All11 are
byte-identical to `2d8d0367`. The whole crate tree ID remains
`4d23e7ceba9d1b86ddaa1349ca6013f1add09bb3`. Thus F4-R strict admin/submit
parsing/snapshots and N1 retained/shared/direct/send fee ceilings changed no
logic, tests, SDK pins or mutation rules in this merge. GitHub now reports the
PR as automatically mergeable against the updated base.

This verifies conflict resolution and preservation of the reviewed Hedera layer;
the full merged Mobi application/Whisper/wizard release was not rebuilt here.
No merge operation or conflict edit was performed by this reviewer.

## Tests, rulings and limits

| Exact head / scope | Baseline independently run | Supplied removal controls |
| --- | --- | --- |
| rpp-spec `2e0020c0` | Native helper build exit0; **244 focused passed; 1,500 full passed**, zero skipped, exit0. Focused included in full; one existing legacy-address warning. | **49/49 killed**, exit0, including automatic destructor ownership, unpublication order, native error redaction, routing and zero-fee controls. |
| mobius `82557ce8`, standalone HCS crate | **15 core passed; 27 SDK-enabled regular passed total + 1 compile-fail doctest passed**, zero failed/ignored, exit0. Core included in SDK-enabled total. | **50/50 killed** by the intended named assertions, exit0. No compilation/timeout failures count as kills. |

Commands: explicit `python scripts/build_hedera_native.py`; focused/full pytest;
`python scripts/hedera_python_mutations.py`; Rust `cargo test --offline
--manifest-path crates/hedera-day1/Cargo.toml` with/without `--features sdk` and
`python crates/hedera-day1/scripts/mutation_check.py`. Existing pinned SDK and
toolchain installations were reused. Source controls were restored, and both
detached worktrees are tracked-clean. Initial supplemental matrix instrumentation
was corrected before final counts; an unfired opcode and fault-unwind reference
observations were not mislabeled as native product failures or passing cases.

Testnet-only constructors/fixed mirrors, retired-flag refusal, fresh dispatch
checks, bounded retry identity, strict rejection of custom-fee topics and one
actual-payer zero-HBAR custom-fee allowance with no HTS denomination remain in
place and pass their actual-SDK/fake-transport regressions. Successful receipts
and exact mirror bytes/topic/payer/sequence remain required. Rust's private
SdkBackend/Prepared types expose no Debug/Serialize state and errors remain fixed
categories. The native C helper exposes only opaque handles and exact-byte
signatures. N3 is the bounded direct-initializer diagnostic exception above.

No ledger endpoint or live testnet was exercised. These are source, wire and
fake-transport results, not deployed consensus enforcement or product-readiness
certification. Evidence is retained under `rpp-spec/work/hedera-review4-evidence/`
and `mobius/work/hedera-review4-evidence/`, including baseline/mutation logs,
ownership/diagnostic results, merge-resolution.diff and merge-evidence.json.
