# Why FP / PL

- DOVU-OS-INTEGRATE asks for a downstream public-root use without delegating
  agent authority (TR card; FP-1901 section 4).
- The boundary already chooses push-only Tier 1 and customer actor; inventing
  a per-call/settlement export would cross it (BOUNDARY-v1 sections 2.1-2.4).
- The HCS plan assigns session wiring to FP with PL's review; the lender's own
  account/topic is authoritative, borrower submits nothing (T
  `artifacts/fp/hcs-anchor-wiring/PLAN-v0.md:17-27,37-44`). Current merged state
  still requires the lane inventory, not assumptions from the old plan.
- DOVU cannot establish engine truth, energy truth or authorize a machine
  merely by recording a reference (TR-1057; FP-1901 section 4).
