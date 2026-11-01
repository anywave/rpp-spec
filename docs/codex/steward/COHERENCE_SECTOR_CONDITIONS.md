# CX-005: exact conditions for proved

Source under study: `95c67ef`. The earlier CX-003 report remains an immutable
record. This extension changes only `tools/prove_out/`. The generic coherence
and sector readouts remain absent. The verdicts below concern engineering
quantities and deterministic partitions; no physical claim is added.

## Coherence

**Updated verdict: partly proved.** Named progress, affinity, complement and
group quantities can have their own verified properties. A single interchangeable
scalar called coherence is still not established.

The term becomes **proved for a named protocol profile** exactly when every A
condition and every applicable B condition below holds. A claim about calibrated
confidence or real-world measurement additionally needs declared observations,
reference labels, calibration/error bounds and repeatable external validation.
Numerical consistency alone does not satisfy that extra claim.

| ID | Checkable condition | Work possible now and result |
|---|---|---|
| A-C1 | Inputs, domains, units, formulas and real consumers are separately traced for every advertised quantity. | Prior COHERENCE_TRACE/HARDWARE_RA maps retained; FOREIGN_BINDINGS adds pinned Rust/Clash formulas and scope. No aliasing of unlike quantities. |
| A-C2 | Supplied-input monotonicity and all decision boundaries are tested rather than inferred from sample readouts. | All 675 raw scores retain binding137 and seven stage transitions; 10,201 Python fraction pairs from CX-003; actual RTL grid now 256 inputs × 12 thresholds. Both input axes are checked; alternate RTL scores still decrease. |
| A-C3 | Every runnable same-quantity binding is compared on the shared finite domain, with missing/duplicate/unknown rows rejected. | Actual three-scorer RTL 3,072-point comparison; additional derivation32, fallback207,360 and consecutive-counter34-point probes. Source transcriptions cover Rust supplied-scalar and Clash group policies without claiming these are the same quantity. Native execution is recorded separately in FOREIGN_BINDINGS. |
| A-C4 | Downstream consequences and counterexamples stay visible, including threshold inclusivity and hold/reset semantics. | Twelve thresholds include137,300,500,674 and adjacent values; consent derivation13/32 named mismatches; fallback134,400/207,360 theta mismatches; cycle trigger activates on the13th true sample. The declaration of each test wiring is explicit. |
| A-C5 | Evidence reruns produce byte-identical tables and tests detect named failures. | Deterministic generators; actual RTL log digest; malformed/duplicate/incomplete grid controls; mutation runner includes four additional executed witnesses. Exact rerun commands and counts in CX005_VALIDATION. |

| ID | Steward/core condition still required | Exact acceptance test after authorized adoption |
|---|---|---|
| B-C1 | Decide which quantity is exposed by each API/UI. Adopt the explicit count-defined progress and strict ordinary-v2 affinity APIs, or retain them as proposals. | A public call names its profile/domain/provenance; counts produce exact endpoints; affinity rejects reserved/nonfinite states and reaches both endpoints. CX005_PROPOSALS gives an additive patch that leaves the existing APIs intact. |
| B-C2 | Decide whether the three HDL scorers are required to implement one weighted policy, or are explicitly separate legacy profiles. | Equality profile: all256 scores, all declared thresholds and both monotonic axes agree; completion flags also agree. Current evidence fails this. Separate-profile option: no adapter silently treats outputs as interchangeable. |
| B-C3 | Resolve the 2-bit RTL versus 5-state Python consent policy and the input override meaning. | A reviewed adapter preserves named states and does not turn a supplied signal into an unrequested permission. A declaration of 3-bit state codes and thresholds must precede adoption. Current named comparison has13 differences. |
| B-C4 | Decide whether canonical fallback uses Python's zero-based XOR or the RTL's one-based XOR. | Under the adopted explicit phi adapter, all207,360 component cases agree; current theta mismatch count is134,400. Proposed Python-aligned theta patch is included but not applied. |
| B-C5 | Resolve any proposed physical or lifecycle claim through the existing four steward items and grouped baselines. | Shell-0/T2/radius/claim dispositions are approved and implemented in a separately authorized change. This work does not mark any entry accepted. |

## Sector

**Updated verdict: partly proved.** The legacy theta partition and the ordinary-v2
partition are individually proved as finite deterministic partitions within their
declared domains. A profile-independent semantic number and stable category
migration are still not established.

The term becomes **proved for a named protocol profile** exactly when A-S1..A-S4
and B-S1..B-S3 hold. It may then describe an application-assigned routing category;
it cannot imply that an address partition inferred the meaning of arbitrary text.

| ID | Checkable condition | Work possible now and result |
|---|---|---|
| A-S1 | Every valid address belongs to exactly one sector, with dependence on other fields checked. | All512 v1 theta classes partition the2^28 valid addresses into8 disjoint64-code bins;18,432 other-field combinations are already checked. All27 ordinary v2 theta codes partition into8 declared ranges. Reserved codes are not silently admitted to this claim. |
| A-S2 | The documented v1→v2 theta projection is tabulated for every input and its information loss is counted. | results/completion/sector-projection.md is a512-row Markdown table, supplementing the existing CSV. Names agree36/512 and differ476/512. The projection is not invertible; radius is deliberately outside it. |
| A-S3 | Actual authorization is exhaustively checked against the shipped matrix, including exceptions. | All45 state/sector pairs checked at zero and674; VOID is zero-only, GUARDIAN always allowed, BRIDGE blocked in emergency despite the universal helper label. The zero/nonzero cases cover all675 score values because the function tests only equality with zero. |
| A-S4 | Determinism and named failing mutations are present. | Table byte repeatability and mutation of theta0's projection are tested; full finite matrix mutation is killed by the new runner. |

| ID | Steward/core condition still required | Exact acceptance test after authorized adoption |
|---|---|---|
| B-S1 | Adopt explicit profile/namespace tags at API and UI boundaries; decide whether sector means a v1 theta bin, canonical Repitan category, or routable-sector enum. | A profile-tagged label round-trips without passing an ordinal through another namespace. No profileless Sector4 readout remains. |
| B-S2 | Approve the migration contract and unresolved radius derivation. Either explicitly permit the existing lossy mapping, or define another mapping without implying label preservation. | Every512-row theta projection agrees with the adopted table; radius vectors follow the approved fixed.5 or shell/3 rule. A category-name stability claim must either pass all512 cases or be removed from the proposed contract. |
| B-S3 | Reconcile semantic/universal helper descriptions with actual runtime admission and cross-binding fallback policy. | The approved state/sector matrix agrees across advertised implementations; emergency access never relies on the helper's BRIDGE label. Any content semantics have a declared assignment procedure and validated evidence rather than integer labels alone. |

All owner-independent checks above are completed and reproducible. Failed
cross-binding equality is evidence, not a reason to reinterpret or silently fix
the protected protocol. Native Clash/GHC execution and physical-device tests
remain unrun; neither is claimed by the source-transcription slice. A future
cross-language Clash agreement claim requires a native harness and its declared
clock/state domain before B-C2 can be satisfied for that binding.
