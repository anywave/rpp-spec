# DOVU-LW-TIER1 — FP, PL review

Status: **offline inventory/fake checks only; live handoff HELD**. Source T is
trellis-channel `17ec5e41798035f887807236af6b4f6e2da40e41`.
Authority: TR DOVU-OS-INTEGRATE; FP-1874; TR-1057. This pack does not enable DOVU.

1. Pull the lane's current repository and record its head. Inventory existing
   `hcs_anchor`, daily wiring, public-reference constructor, release valves and
   DovuSink reuse before proposing code. October's no-caller report is history;
   T `codex/PRODUCT_DESIGN_MAP.md:119` says merged, valve shut, never run, first
   write requires RADIX approval, W8 and a new build. Report what source proves.
2. Keep six-stage rows, auditor/settlement contents, counts, openings and pins
   local. Preserve engine-native/missing labels: missing never becomes zero.
   Source: T `artifacts/pl/tr-cards-2026-11-03/ship-lanes/lend-stage-rows.md:25-61`.
3. Evaluate the closed fake crate at digigami-audit
   `617beedb5cb008621a784e02a4d2ac4d515eb5ff`, `04_dovu_fake/`, against existing
   production-boundary code. Do not import its memory journal into a sender.
   Tier 1 has exactly `{topic_id, sequence_number, consensus_timestamp, root}`;
   owner sees precisely those fields before opt-in. Source: T
   `artifacts/fp/dovu-access-boundary/BOUNDARY-v1.md:38-76,87-95`.
4. Produce a source-cited gap plan. Any subsequent Rust implementation needs
   verified pinned-topic mirror input, single chunk/exact reference, confirmed
   lend-only daily publication, opt-in lower bound and a durable atomic attempted
   claim before the call. Missing/corrupt state refuses; lost acknowledgement
   consumes the attempt, never automatic retry. Sources: FP-1895, FP-1896;
   PL-519/PL-520 record later fixes, so establish the current gap before coding.
5. Do no live transaction. Remaining dependencies: actual root-only DOVU schema,
   customer actor/vault path, release/terms/network clearance, and HCS W8/new
   build. Never change a release valve to satisfy a test. Sources: FP-1874,
   TR-1057, T `artifacts/fp/dovu-access-boundary/BOUNDARY-v1.md:3-7,62-76`.

Acceptance: inventory with file:line and current pin; bounded fake tests refuse
default/off, unpublished, old opt-in, wrong host/network/topic/root/chunk,
non-lend and every never-list key; write-failure/corrupt/restart/concurrent claim
tests for any durable component; unknown result never resends; reply never
changes authority or auditor verdict. Remove each rule and show its named test
fails. Source: FP-1895/FP-1896; the prototype is a starting comparison, not that
durability acceptance result. Work is Rust-only for anything shipped.

No accounts, emails, money, mainnet, keys, provider calls, product release,
network writes or contact with DOVU in this pack. Use ordinary lane consent and
review procedures; this is a plan, not a bypass. No raw logs or person's clock
values exported; offsets and counts only, apart from the permitted public root
reference's consensus field (TR-1761i; BOUNDARY-v1).
