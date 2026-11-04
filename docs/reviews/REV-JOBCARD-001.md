---
branch: codex/rev-jobcard-001
head: refs/heads/codex/rev-jobcard-001
head_kind: final-pushed-branch-ref
source_base: ae10d65a520d25958197f77e6cf784e6b8d177ce
reviewed_repo: anywave/latticeworks
reviewed_branch: pl/lw-jobcard-v0
reviewed_head: 86899f736f751e32603129fcdaf47e4aa313052f
trellis_head: 0e0e64275475c56a0f51070ebcdb6531e5215c54
---

# RPP-REV-JOBCARD-001

Verdict: **READY-WITH-NITS for draft_only**. Three LOW findings; no retained
HIGH or MEDIUM. This permits review of the draft. It does not freeze the wire
format or approve a runner, unattended service, or a production trust boundary.
No worker-to-VERIFIED or coordinator-to-RUNNING bypass was found under the
stated trusted-context and current-record rules. This is a source review, with
small Python/Node byte probes, not an independent Rust test pass.

## Scope and proof level

Read codex/LESSONS.md first, then pulled trellis-channel main. Reviewed the
pinned latticeworks source above: crates/lw-jobcard, its contract tests,
docs/design/JOB_CARD_V0.md, and lw-registry's canonical_json. Read PL-919,
PL-923, PL-926 and artifacts/pl/tr-cards-2026-11-03/a3-gaps.md as data.
Read the latticeworks AGENTS.md and docs/CODEX-WORK-ORDER.md. Searches stayed
inside rpp-spec, trellis-channel and the named latticeworks snapshot.

Three read-only subagents split canonical bytes, replay/binding, and roles/docs.
All returned; the main thread checked their claims against the source and
alone wrote and pushed this report. The split helped cover separate boundaries.
Per-agent time and token cost were not exposed. No latticeworks tracked file
was changed. The only RPP change is this new report; no PR was opened.

`cargo --version` and `rustup --version` each exited 127 here:

```text
bash: line 1: cargo: command not found
bash: line 1: rustup: command not found
```

No toolchain was installed. No Rust tests or builds ran in this review.
PL-926 S1 reports 39 contract tests and 2 doc tests passed, zero failed, on
86899f7, then a regenerated manifest. That is PL's reported run, not mine.
The two failing cases below are source-traced reproducers for PL, not executed
Rust assertions. Byte probes used Python 3.12 and Node v24.19.0, outside both
repositories' tracked files: 9 families / 10 rows, all probe assertions passed.

## Findings

All source paths and line numbers here refer to the reviewed latticeworks SHA.

### JC-01 - LOW: signed compare counters escape the stated 53-bit domain

Files: docs/design/JOB_CARD_V0.md:28; crates/lw-jobcard/src/lib.rs:259,
:282, :299 and :329. MAX_INT at :25 bounds card expiry/readings (:229-230),
but not attempt epoch/revision/fence or the counters returned by claim/result.
checked_add refuses u64 overflow, not the documented 53-bit limit.

Concrete case using tests/contract.rs:46-60's otherwise valid ready()/attempt():
set old.revision and old.fence to 9007199254740991, create the matching signed
attempt, and call claim at 100. All compare tokens match. The source returns
Won with revision and fence 9007199254740992. Even domain-valid inputs thus
produce counters outside the promised maximum. Starting instead with matching
old.epoch and a.epoch = 9007199254740993 also reaches Won. On a fresh result
publication, record_result can increment revision past MAX_INT as well.

Effect: a JS Number consumer of the accepted epoch 9007199254740993 signs
9007199254740992 after JSON.parse. CB6 demonstrates the byte difference.
The existing counter test at tests/contract.rs:222 exercises only u64::MAX.

Refutation: the current record is trusted, no JS signer is promised, reaching
this counter from zero is impractical, and PL-926 forbids CX-029 from relying
on signing bytes. This is a draft domain mismatch, not an observed replay or
authorization bypass. Hence LOW, rather than MEDIUM.

Before freeze, choose and state one domain. To keep the stated 53-bit rule,
bound incoming and returned counters, including checked increments; add
`kills_compare_counter_above_safe_integer` and
`kills_counter_increment_past_safe_integer` negative tests. Their mutants are
omitted input bounds and omitted post-increment bounds. No fix is applied here.

### JC-02 - LOW: CLAIMED proposal labels can hold consent-shaped sentences

Files: crates/lw-jobcard/src/lib.rs:386 and :405, versus :36 and :274;
docs/design/JOB_CARD_V0.md:155-156. claim uses label (ASCII, <=64, no spaces),
but check_move uses text (nonempty, no control characters) for attempt/slot.
READY-origin moves skip the active-grant binding block.

Concrete case: use ready(), then event(..., Ready, Claimed, "worker") as in
tests/contract.rs:230. Replace attempt_id with "VECTARIS approved this run"
and slot with "person said yes", then re-sign with the worker. With the same
epoch/fence/component and trusted current Ready, check_move reaches Ok(Claimed).
The proposed negative assertion `check_move(...).is_err()` would fail.

Effect: the doc and a3-gaps section 1 claim a stricter label contract than this
entry point enforces. Refutation: CLAIMED is only a proposal; claim later
rejects these labels (:274), and RUNNING still needs the bound door reading.
This text grants no consent and cannot itself start work. Retain as LOW.

Use label on proposal attempt/slot, or narrow the doc's claim to granted
attempts. Proposed test: `kills_claimed_proposal_sentence_labels`; mutant:
replace proposal label checks with text. No word blacklist is needed.

### JC-03 - LOW: the fixture proof note predates the reported Rust pass

File: docs/design/JOB_CARD_V0.md:276-278 says the commit_mib-derived digest
ID "has not yet been checked by the Rust test". tests/contract.rs:85-90
recomputes the ID and compares it to the archive. PL-926 S1 reports this
suite green at the very head reviewed here.

Concrete contradiction: that successful reported test checks the same ID that
the doc labels untested. Refutation: I could not rerun it or inspect its raw
execution log; the assertion is based on PL-926 plus the test body, not a new
claim that Rust passed here. It affects proof status, not runtime behavior.
Replace the note with the pinned PL run and its limited scope once confirmed.

These three deltas are absent from a3-gaps.md's open list. JC-02 also qualifies
its CLOSED assertion about short labels. JC-03 reflects a later reported run;
it does not invalidate a3-gaps.md's honest NOT_RUN status at its older commit.

## Replay, trust, and role checks

| Attack tried by reading | Guard / result under the stated preconditions |
|---|---|
| Move an attempt to another job, or use old revision/epoch/fence | lib.rs:274 binds both job IDs; :282 compares all tokens. Re-signing stale tokens cannot satisfy the current record. |
| Reuse an attempt nonce | :292 refuses used_attempts; :278-280 blocks an active grant. The caller must persist the returned record. |
| Two grants from the same snapshot | Both pure calls may say Won. Doc :185-206 explicitly requires the single coordinator's lock and durable append. Supplying the unchanged snapshot violates that duty; this is the already-open C5 integration, not a new exactly-once claim. |
| Late/wrong-job result, wrong queue/epoch/attempt/worker/slot/fence/component | :317-322 binds each and verifies the worker's signature. The result fence is the new grant fence, not the attempt's old compare token. |
| Replay a valid result | :321, :328-330 allow the same hash without another revision increment; another hash fails. This is the intended spool repost, not a second run or VERIFIED. |
| Replay an event at a different state or grant | :359-362 binds trusted current/job/queue/epoch/fence/component; :387-390 binds the active attempt after READY. Doc :109-110 says the log tail and grant record are separate inputs: equating current with old.state would be the wrong model. |
| Worker or coordinator signs VERIFIED | :369, :382-384 require the exact independent checker; :178-187 verifies role/key/signature. Independence uses name, key and owner (:189-198). Existing tests :95-102 exercise extra Checker roles; :216-219 covers a key alias. |
| Coordinator also takes Worker role and signs RUNNING | :401-405 requires the assigned allowed worker, independent checker and distinct coordinator key/name. A renamed identity with the same key fails distinct. Shared owner alone is permitted by PL-919 for worker/coordinator. |
| A grant, proof hash, or worker text ends a wait | :391-396 calls door_says (:348-353): exact door/job/attempt/fence and Started/Refused. Expiry or unknown journal holds. Doc :140-143 admits the real proof reader is still C6/C7 work. |
| Bad signature falls back to an unsigned run | :436-440 refuses any signature on the attended path. AttendedCard is separate from CheckedCard (:201, :433); its result cannot enter claim/move/result APIs as a checked card. Used-door persistence remains the caller's duty. |

I also tried to refute apparent record-tampering bugs: constructing an active
grant with arbitrary job/epoch, omitting prior signature checks from a fabricated
stored record, changing the pinned context between calls, or choosing a fake
current state crosses the documented trusted-input boundary. None establishes
a new untrusted-packet bypass. A future loader must enforce those preconditions.
This review did not validate that loader; none is built here (lib.rs:161).

## Canonical bytes and ten proposed adoption vectors

By source, jobcard lib.rs:119-134 and registry lib.rs:185-218 recursively sort
keys in Rust string/UTF-8 order, preserve array order, and use serde_json for
scalars. No differing JSON part was found for the same Value. Their envelopes
differ on purpose: jobcard removes outer sig and prefixes domain plus LF;
registry has its domain inside an array. Typed duplicate fields are refused
by jobcard parsing; comparing that with an already-parsed arbitrary Value is
not evidence of equal parsing rules. A shared Rust test still does not exist.

The vectors below are proposals, not a second wire contract. Invoke the public
jobcard signing_bytes("d", &Value) and compare its JSON part with registry's
canonical_json on the same Value after removing outer sig. The toy domain d
is for vectors only. Actual packet domains stay unchanged. ASCII expected
JSON below follows bytes 64 0a (d plus LF); no final LF. Hex entries include
that prefix. Unicode escapes are input JSON notation; emitted strings are UTF-8.

| ID | Raw JSON input | Expected JSON after prefix, or full byte hex |
|---|---|---|
| CB1 | `{"z":2,"sig":"drop","a":{"y":true,"x":null}}` | `{"a":{"x":null,"y":true},"z":2}` |
| CB2 | `{"sig":"outer","band":{"sig":"inner","by":"rule"}}` | `{"band":{"by":"rule","sig":"inner"}}` |
| CB3 | `{"s":"\u00e9\u2028\u2029\ud83d\ude00/"}` | hex `640a7b2273223a22c3a9e280a8e280a9f09f98802f227d` |
| CB4-NFC | `{"s":"\u00e9"}` | hex `640a7b2273223a22c3a9227d` |
| CB4-NFD | `{"s":"e\u0301"}` | hex `640a7b2273223a2265cc81227d` |
| CB5 | `{"job_id":"j","attempt_id":"a","worker":"w","slot":"s","revision":0,"epoch":9007199254740991,"fence":2,"until":160,"by":"c","sig":null}` | `{"attempt_id":"a","by":"c","epoch":9007199254740991,"fence":2,"job_id":"j","revision":0,"slot":"s","until":160,"worker":"w"}` |
| CB6 | `{"job_id":"j","attempt_id":"a","worker":"w","slot":"s","revision":0,"epoch":9007199254740993,"fence":2,"until":160,"by":"c","sig":null}` | `{"attempt_id":"a","by":"c","epoch":9007199254740993,"fence":2,"job_id":"j","revision":0,"slot":"s","until":160,"worker":"w"}` |
| CB7 | `{"\ue000":1,"\ud800\udc00":2}` | hex `640a7b22ee8080223a312c22f0908080223a327d` |
| CB8 | `{"2":"b","10":"a"}` | `{"10":"a","2":"b"}` |
| CB9 | `{"f":1.0,"negative_zero":-0.0}` | `{"f":1.0,"negative_zero":-0.0}` (source-derived serde_json expectation; generic Value diagnostic) |

Executed probes used Python's sort_keys/ensure_ascii=False/compact separators
as a small reference and independent Node implementations of UTF-8 key sorting,
default UTF-16 sorting, and sorted-object JSON.stringify. They did not call
either Rust crate. Results and the limits of each case:

- CB1: reordered nested input and a different removed outer sig give the same
  reference bytes. Sorting only the top object is insufficient in JS.
- CB2: nested band.sig remains. Removing every sig changes the signed value.
- CB3: Python and manual UTF-8 Node agree for non-ASCII, line separators,
  a supplementary character, and slash. Rust still needs to run this vector.
- CB4 pair: NFC and NFD remain distinct. No Unicode normalization is promised;
  silently normalizing is a different contract, not a discovered Rust defect.
- CB5: the maximum safe integer agrees between Python and Node.
- CB6: Node parses epoch to 9007199254740992; Python preserves 9007199254740993.
  This applies to the typed Attempt counter gap in JC-01, subject to a valid
  coordinator signature and matching trusted record; the toy input is not a
  valid signed grant or full card.
- CB7: UTF-16 sort puts U+10000 before U+E000; Rust/UTF-8 order does the reverse.
- CB8: even a sorted JS object reorders integer-looking keys when stringified:
  `{"2":"b","10":"a"}`. Manual recursive emission preserves lexical order.
- CB9: Python emits 1.0/-0.0; Node emits 1/0. Rust output was not measured.
  This is a generic-Value trap to test, not a float-injection path into the
  typed packet structs, whose numeric fields are integers.

CB7/CB8 are generic-helper/registry coverage, not valid jobcard field names:
the current structs have fixed ASCII keys. CB9 likewise cannot be a typed
card field. No HIGH or MEDIUM is retained from these cross-language traps.
PL could adopt all ten in a shared test, plus the valid typed counter-bound
negative tests, before anyone treats these draft bytes as stable.

## Existing gaps and limits

The following are already disclosed in a3-gaps.md, PL-926 and/or the draft,
and are not repackaged as new findings: durable coordinator lock/append and
crash journals; trusted n2HO reader and its admin-writer limit; reconciliation
receipts/no edge back to READY; used-door persistence; real runnable card;
commit margin and worker offer; checker home/trust freshness; C7 artifact
fetch/check; prompt repository identity; B2 coding grants/door policy.
PL-923's ruled LatticeWorks worker, with Echo only as adapter, is reflected in
JOB_CARD_V0.md:20-22. No new worker or hard Mobi dependency was found.

Could not confirm: Rust compilation or tests, a shared Rust canonical test,
PL's raw consent/job log, a full workspace build, schema validation, current
production keys/revokes, a real lock/log/door adapter, real work, Windows, or
cross-site operation. No keys, signatures, model work, or consent were created.
Source-only negative cases do not prove those integrations safe.

RPP publication checks: one new report, ASCII/LF/control-byte check and
git diff --check. Run the BASE-side trusted gate and drift on the exact report
commit before the one normal push; resolve the final branch ref with
git ls-remote. No source, workflows, gates, owners, allowlists, baselines or
published outboxes are changed by this review.
