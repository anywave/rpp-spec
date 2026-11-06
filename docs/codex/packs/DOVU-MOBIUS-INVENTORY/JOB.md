# DOVU-MOBIUS-INVENTORY — FP / Mobius, PL review

Status: **review/plan only; no new sender or release enablement**. Source T is
trellis-channel `17ec5e41798035f887807236af6b4f6e2da40e41`.
Authority: TR DOVU-OS-INTEGRATE, FP-1874, FP-1895, TR-1057.

1. Record current canon and the existing DovuSink v2 branch head. Trace the
   actual selection path, exact Tier-1 payload, mirror constructor, atomic
   attempted journal, secret store, host guard and `TIER1_RELEASED`. The old T3
   report describes an earlier per-call design; do not reintroduce it. Source:
   T `artifacts/pl-research/integration-program/trust-wave-1/t3-dovu-built.md:1-18`,
   FP-1895/FP-1896 and PL-519/PL-520. Treat reported fixes as leads; check code.
2. Compare current fake/contract tests with digigami-audit
   `617beedb5cb008621a784e02a4d2ac4d515eb5ff`, `04_dovu_fake/`. That crate is
   offline and memory-only, not a replacement sender. List reuse/gaps; no copy
   of CLI/PHP clients and no product change in this inventory pack. Source:
   `docs/codex/OUTBOX/DOVU-OS-INTEGRATE-001.md` sections 1, 3 and 4.
3. State exactly what is proved: reference match/attempt/acknowledgement, not
   remote computation, counts, settlement authority or agent permission. Keep
   Tier 0; no per-call data, text, IDs, salts, paths, keys, identities or energy
   crosses. Source: T `artifacts/fp/dovu-access-boundary/BOUNDARY-v1.md:38-76`;
   TR-1057; FP-1901 section 4.
4. Return one bounded job plan only if a real owner-independent gap survives.
   It must retain the release gate and demand named mutation failures for each
   boundary. First live send remains held on current owner/schema/terms/network
   approval; this pack authorizes none of them (FP-1874; TR-1057).

Pass: source-cited inventory, current heads, explicit old-versus-current
distinctions, seven boundary checks compared with existing tests (default/off,
exact payload, mirror, publication/opt-in, durable claim, ambiguous retry,
host/secret hygiene), and no proposed duplicated component. Report existing
test evidence separately from anything newly run. Native/consent gates are the
lane's, not satisfied by the cloud prototype. No model call or vendor SDK run.

No account, email, key, money, mainnet, provider call, public post, vendor
contact, live transaction or release change. Never change canon in this pack.
Only Rust may ship; Python may scaffold checks. No person's clock values in
exports; permitted public consensus reference is the boundary's exception
(TR-1761i; BOUNDARY-v1).
