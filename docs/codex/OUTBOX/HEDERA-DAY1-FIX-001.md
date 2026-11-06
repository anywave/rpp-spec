---
id: HEDERA-DAY1-FIX-001
from: Codex (hedera-day1)
to: TR
repo: anywave/rpp-spec
branch: codex/HEDERA-DAY1
head: refs/heads/codex/HEDERA-DAY1
head_kind: final-report-inclusive-branch-ref
source_freeze: 4395e27889a8ec6a2a5e40452a800c0cc209ccee
review_pin: 078843ad27d4855791c949c7ba1cb3b14b368782
instruction_pin: 9efe9ae2052bf876cfa30a77fb59470f40c6ea22
task_label: 2026-11-06
type: security-fix-and-policy-report
subject: F1-F5 corrected; alpha testnet only, custom fees refused; live proof unproved
---

F1-F5 are corrected in the scoped HCS foundations and job packs. RADIX's later
chat rulings supersede the old flag-based design: **the alpha supports testnet
only, and refuses every custom fee**. The old mainnet constructor, mirror and
activation path are removed from all three day-1 layers. No environment variable
enables mainnet. A later release requires a signer outside an agent account.
Live testnet proof remains **unproved**; no credentials were added and no live
smoke, mainnet write, real-HBAR operation, funding or account creation ran.

Read the independent report at the review pin above, including each finding's
original file:line, and the HEDERA-DAY1-FIX inbox entry. The two subsequent RADIX
chat rulings are applied in this same fix and match the newest fetched inbox entry at the instruction pin above. The historical HEDERA-DAY1-001 report
remains unchanged; this report supersedes its network/fee-policy claims.

| Commit / repository | Finding or ruling closed |
| --- | --- |
| `4395e27889a8ec6a2a5e40452a800c0cc209ccee` / rpp-spec | F1, F2 by removal plus fresh send checks, F3, F4; both RADIX rulings. |
| `a297f018be71cb3ce467b0fbfe2b48cbe67a1a33` / digigami-stack | F1, F2 by removal plus concrete RPC guards; both RADIX rulings. |
| `ecbfcd04412a967f5b35e9b9c5de0b97416f7b83` / mobius | F1; testnet-only ruling removes the mainnet path and adds fresh send checks. |
| `7ef0a6dab95d459aeea2efecd847da329d2707aa` / digigami-audit | F5: all three flagged phrases corrected; restoring each triggers the real linter. |
| `82184a31f14b8bac97f31d46f49ea931de400208` / digigami-audit | Current job pack aligned with the testnet-only ruling; obsolete flag guidance removed. |
| `c06f501d9d3b25dcd14461f8f042e4916f682fa6` / hedera-auction-integrity | Current job pack aligned with the testnet-only ruling; previously READY launcher/ZIP code unchanged. |

The final rpp-spec report/evidence commit adds no further source changes; its
head is the delivery ref above and the final remote-SHA message. Both
`codex/HEDERA-DAY1` and `codex/HEDERA-DAY1-python` deliver that same commit.
**PR #47 duplicates #46**: same implementation and final head, not an additional
fix or test run. TR will ask RADIX to close #47. Neither PR is closed here.

F1: every public message boundary reads the requested topic and requires an
explicit empty `custom_fees.fixed_fees` list. Missing, unreadable, malformed,
unknown or nonempty schedules refuse before message preparation/send, including
HBAR, HTS, zero-valued and exempt fee entries. Each submit additionally serializes
one payer custom-fee allowance containing one zero-HBAR FixedFee and no HTS
denomination. This preserves the separate network transaction-fee cap and closes
the post-preflight fee-change race. It is not applied to topic creation, which
does not support that field. Actual SDK wire/getter tests check payer, zero,
nonempty repeated entries, denomination and node alternatives.

F2: only literal testnet is accepted. Requests for mainnet receive the plain
message "Day-1 alpha is testnet only; mainnet is unavailable" or its equivalent.
Runtime network selection is re-read before sends; endpoint overrides cannot
enable another network. JS/Python also pin actual initialized SDK routes, so
changing an exposed SDK network while retaining a testnet label cannot redirect
the operation. Their concrete RPC guards run after signing and channel setup;
SDK and native gRPC retries are disabled and the shared layer owns the budget.
Tests change selection during signing, initialization/readiness and BUSY/retry,
including the retired enable flag set true, and observe no forbidden RPC.
Rust keeps its SDK client private, pins exactly one public testnet node and one
SDK attempt, and checks fresh runtime selection at each shared/SDK send. Its
prepared handle is opaque, preventing callers from injecting unchecked SDK
transactions. An SDK operation already in flight is not cancelled; its target
cannot become mainnet. No private tonic-dispatch interceptor is claimed.

F3: Python uses SDK `set_operator_with` and a slot-only callable signer with a
fixed redacted representation and refused serialization. The SDK client and
Operator retain no PrivateKey field. Actual SDK repr/str/vars, JSON, logging,
bound callbacks, signed transactions and pickle were probed with synthetic keys
generated only in memory. Leak checks report booleans even when intentionally
failed; no key value is printed or stored. This covers ordinary inspection and
serialization, not hostile reflection into private Python/process memory.

F4: Python creation verifies both requested admin and submit keys on mirror
read-back, in addition to topic/memo and successful creation-transaction identity.
Missing or altered admin/submit keys refuse confirmation.

F5: the current audit job pack passes the real claims linter. Its three original
wording controls each restore exactly one PROOF_WORD finding. Both consumer job
packs now describe testnet-only operation and the later outside-agent signer.

| Final validation | Result |
| --- | --- |
| Python focused actual-SDK/fake suite / full RPP | 103 / 1,359 passed, no skips; Ruff and diff checks clean. |
| Python named compilable guard-removal checks | 24 killed by intended assertions. |
| JS policy/SDK/fix tests | 35 passed, no skips; offline locked install passed. |
| JS named compilable guard-removal checks | 38 killed by intended assertions. |
| Rust SDK-enabled tests | 23 passed, plus one successful compile-fail doctest for prepared-handle opacity. |
| Rust named guard-removal checks | 36/36 killed in one complete run of the final committed runner; source restored exactly. |
| Audit lint / wording restoration | 0 current findings; 3/3 original phrase restorations detected. |
| Consumer launchers | 14 credential-free refusal cases passed against the exact JS head; both shell syntax checks passed. |
| Independent immutable-code review | F1-F4 and testnet-only routing passed; actual SDK wire/RPC/representation probes and routing-bypass controls included. |

[Independent verification](../hedera-day1/fix/VERIFICATION.md) records immutable
source SHAs, supplementary probes, mutation evidence and scope. The independent
routing probes initially exposed SDK network-map mutation bypasses; those were
fixed before the recorded final review. [Fee protocol evidence](../hedera-day1/fix/FEE-POLICY.md)
pins official node `9efa5c465a49249e55235d560b4c8addad4a0182` and mirror schema
`87884a06cba0ff8bafbddf247ab9565f39739211`: zero is a valid allowance; positive
HBAR exceeds it and unlisted HTS denominations are refused. This is source and
wire evidence, not execution of a deployed node or the Java node test suite.
Additional [fee metadata](../hedera-day1/fix/fee-research.json),
[signer probe](../hedera-day1/fix/signer-probe.json),
[claims controls](../hedera-day1/fix/claims-lint.json) and
[current consumer checks](../hedera-day1/fix/consumer-checks.json) and
[final validation receipt](../hedera-day1/fix/validation.json) contain no keys.

SDK versions remain JS 2.90.1, Rust 0.45.0 and experimental community Python
0.3.0. JS makes the existing gRPC 1.13.6 dependency explicit; compacting its
generated lock preserved every existing package/integrity record. JS/Python's
pinned private SDK transport hooks need renewed contract review on upgrade.

Product valves, production wiring, restart reconciliation, Windows/MSRV packaging
and live testnet verification remain separate release work. The reported #291
base divergence is unchanged: no merge, rebase, base change or force push was
performed. Corrections stay on the existing branches as TR directed, with all
security regressions retained; the cumulative rpp-spec PR exceeds the historic
1,500-line lane guideline. No branch split or history rewrite was performed.
Only the approved HEDERA-DAY1 refs are delivery targets; no tags, other branches,
email, social publication or PR action is included.
