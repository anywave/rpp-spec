# Coherence is several different quantities

Source throughout: rpp-spec `0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e`.
The word does not identify one measurement. The following definitions are distinct;
there is no source-supported conversion that makes them interchangeable.

| Definition | Inputs/computation | Range, units, interpretation | Actual consumer / decision | Source |
|---|---|---|---|---|
| Weighted engagement/completion score | clamp E,C to0..1; floor(165E)+floor(509C) | integer0..674, arbitrary policy points; not similarity/confidence/stability or a sensor measurement | normalized binding coefficient and completion stage | rpp/coherence.py:86-118,197-249 |
| Binding coefficient/stage | score/674 clipped; stage=floor(7score/674),0..7 | dimensionless coefficient; ordinal stage | binding at>=137/674; completion_flag only at stage7 | rpp/coherence.py:121-176,228-237; rpp/ra_constants.py:45-71 |
| Address similarity | 1 minus weighted coordinate distance: theta circular/13.5, phi/5,omega/4,radius/1; weights.3,.4,.2,.1 | dimensionless closeness of chosen encoded coordinates; not confidence in content | public API, same-sector/adjacency helpers; no automatic forwarding into consent.py | rpp/address_canonical.py:520-580; rpp/__init__.py:18-31 |
| Caller consent scalar | supplied `ConsentContext.coherence_score` | expected normalized0..1; no measurement/provenance calculation | FULL-consent ethereal-zone writes require>=0.4, independently of verified identity and other permissions | rpp/consent.py:150,172-175,290-308; rpp/resolver.py:151-199 forwards context |
| Biofield binding score | supplied integer clipped0..674, coefficient=score/674 | same numeric policy score; energetic/biological interpretation is unvalidated | bound above137; state transitions and logical grace ticks; event dates are bookkeeping, not score inputs | rpp/biofield.py:76-108,111-138,181-258,286-307,491-511 |
| Aggregate HNC score | priority-weighted mean of active fragment scores | float raw0..674 for positive weights; no probabilistic confidence | master binding, priority/conflict decisions; activity/weights affect result | rpp/hnc.py:46-79,209-240,258-309,321-382 |
| Aggregate mesh score | priority-weighted mean over connected nodes | float raw0..674 for positive weights | node binding and routing priority/node choice; supplied node scores | rpp/mesh.py:188-214,534-599 |
| Somatic index | clamp three supplied channels; .5HRV+.3EEG+.2breath; optional RADEL1/e smoothing; floor(15x) | integer0..15, heuristic weighted input index; units/calibration of channel acquisition are not defined here | packed somatic consent field; five-state header consent thresholds | rpp/hrda.py:27-36,277-322,366-387; rpp/consent_header.py:254-280 |
| PMA stored value | round(63x) clipped0..63; decode x/63 | quantized dimensionless supplied value, 64 levels | stored record/audit field, not a new coherence estimator | rpp/pma.py:98-105,318-344; header coherence_window_id is merely a16-bit link at consent_header.py:206,295 |
| Geometric complement consistency | angular drift from antipodal observation; sum max(0,1-drift/(tolerance*phiGolden))/N | dimensionless internal consistency; radians belong to drift/tolerance, not probability or truth | anomaly list and `coherent` flag; later transition code can use these diagnostics | rpp/geometry.py:561-614,685-704 |
| T2 / coherence volume wording | supplied/claimed substrate fields, not computed by any scalar above | nanoseconds / nm³, categorically different from normalized scores | continuity eligibility/timeouts and physical narrative | rpp/continuity.py:29-46,181-193,269-289; rpp/network.py:102; rpp/geometry.py:129-135,723-760 |

`results/SOURCE_USES.md` contains every lexical coherence/sector use under rpp,
so demo/export/formatting uses are visible as well as operational consumers.
The frozen source was imported only for pure numeric computations and consent
functions. No timer, stochastic demo, key generation or real-world channel is an
experiment input. Stateful HRDA smoothing was disabled in its sweep; this is not
a statement that live smoothing has no history dependence.

## Thresholds are software policy, not physical measurements

| Threshold | Exact behavior | Provenance / limit |
|---|---|---|
|137 raw points|binding>=137, coefficient137/674≈0.203264|ALPHA_INV_SCALED137, named for truncated alpha-inverse; using it as a software cutoff does not derive human/digital coupling from physics (ra_constants.py:57-71)|
|completion stages|first scores97,193,289,386,482,578,674; stage7 only at674|floor(7score/674), coherence.py:155-176|
|fallback<137|13 consecutive low-score updates trigger, because counter>KHAT_DURATION12; a137 update resets|transitions.py:280-334; logical ticks, not measured T2|
|consent0.4|FULL consent + verified synthetic identity still needs caller scalar>=0.4 for phi450 write|literal policy cutoff, consent.py:172-175,302-308; not137/674|
|somatic10,7,6,2|five-state header thresholds, distinct from consent.py's four-state legacy context|ra_constants.py:78-92, consent_header.py:254-280; labels/weights do not validate sensor consent|

The 165 weight is explicitly adjusted for digital-root symmetry (ra_constants.py:45-46),
not a calibrated fit to a measured target.509 is the Ankh-labelled coefficient.
No dataset, error model, validation target, confidence interval, biometric
acquisition specification or calibration study is supplied for these weights.
These are inspectable policy choices, not a universal physical constant set.

## Reproducibility and monotonicity

The deterministic experiment varies one input while holding the rest fixed.
`python -m tools.prove_out.experiments` emits150 coherence/decision/simulation rows plus512
sector rows. The new suite checks10,201 fixed(E,C) pairs for formula/bounds and
monotonicity and all675 raw score levels for binding/stage thresholds. The address
check covers216 ordinary endpoint-coordinate points and46,656 ordered pairs;
symmetry, bounds and self-similarity hold there. These are explicitly finite tests,
not a claim that all real numbers or every future binding was exercised.

Within the ordinary v2 domain, increasing coordinate separation decreases address
similarity; circular theta means increasing its *number* is not globally monotonic.
For example theta1 andtheta27 are neighbors on a27-position circle. Changing a
semantic label may also change the requested policy, not confidence in anything.

The geometry experiment increases one angular drift; its consistency score falls
as expected. It checks a constructed antipodal relationship, not correctness of
payload meaning or biological state. An empty vector has no anomalies but score0;
the Boolean only means no observed mismatches.

`coherence()` has important domain limitations: constructors accept raw/sentinel
states outside ordinary Repitan validity. At theta1 versus theta31 with all other
coordinates equal, circular subtraction makes similarity1.06666666667; null theta0
compared with itself yields0.7. Tests record these counterexamples. They are not
an excuse to change core here. Require an explicit valid domain before presenting
this as a bounded similarity.

Native HDL evidence and the separately reachable ra-system are in HARDWARE_RA.md.
One exact HDL scorer agrees with Python at all256 shared input codes; two other
shipped HDL scorers do not. Thus **cross-binding equality is not established**.

## Proposed definitions, outside core only

`proposed.py` offers two reference quantities with explicit operational names:

1. `progress_index(engaged,opportunities,completed,required)` is an exact rational
   weighted task-progress index with supplied *counts*. It keeps165/509 as visible
   policy weights but does not pretend they measure confidence. It rejects empty
   totals, bool counts and out-of-range counts. It avoids the shipped per-component
   truncation bias; this intentional difference means it is not a silent adapter.
2. `address_affinity(a,b)` is strictly domain-validated, version-specific coordinate
   closeness. It uses the actual maximum integer theta separation13 so the opposing
   endpoint reaches0, rather than the shipped13.5 normalization. Rational weights
   avoid floating endpoint residue. This is an IMPOSED proposal, never authorization.

These proposals give explicit meanings to their inputs/outputs, not evidence of
biological measurement. Adopting either into rpp, changing a published constant
or layout, or exposing it on a site requires a separate steward decision.

## Plain words and verdict

Overall coherence verdict: **partly proved**. Several finite-domain arithmetic
and policy behaviors are reproducible and operationally consumed. A single
unqualified “Coherence0.847” is **not yet meaningful**: it does not specify which
quantity, its inputs/provenance, unit/scale, binding or calibration. Keep that
readout absent; no page change is authorized by these experiments.

For end users: “We do not yet have one validated score that tells you how reliable
this item is.” For engineers: “Choose a named, domain-validated progress,
coordinate-affinity, or consistency quantity; never treat an overloaded coherence
number as confidence, consent evidence, truth, health or physical enforcement.”

CX-001's radius derivation, four steward items, TTL/T2 issues and243 open baselines
remain unresolved for RADIX. This card does not decide them.
