# Why inventory before another adapter

- PL built DovuSink and later Tier-1 revisions; review/fix history already
  exists (T3 report; FP-1895/FP-1896; PL-519/PL-520).
- The four-field public reference replaced the earlier per-call sink; the
  never list and owner gate survive (BOUNDARY-v1; FP-1874).
- DOVU OS is a credits/RWA workflow, not agent authority. Existing direct
  Guardian verification must not be replaced (FP-1901 section 4).
- The cloud card has no authority to release the adapter, contact DOVU or
  accept a different schema. Unknown terms and network backing remain held
  (TR-1057; BOUNDARY-v1 header and section 2.4).
