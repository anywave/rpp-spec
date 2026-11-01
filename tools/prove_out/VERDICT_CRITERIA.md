# CX-017 verdict criteria, fixed before experiments

Source: master 94c372be9d12d30d94e69afc39569aadedea1d69.
These criteria concern informational quantities and executable models. They make
no claim about a physical device, health, truth, confidence or payload meaning.
Existing source and published definitions stay unchanged.

## What is being claimed

**Coherence:** a named profile computes a reproducible informational score from
declared inputs; its range, unit and direction of change belong to that profile.
The bare historical example "Coherence 0.847" has no identified producer or input
record in this repository. No experiment will retrospectively assign it one.

**Sector:** a named address profile assigns an informational routing label from
the address's decoded theta coordinate, independently of its other fields.
The label is neither a physical observable nor an inferred description of text.
Sector names have no ordering of quality, reliability or permission.

The reference profiles are kept separate:

| Profile | Exact quantity and declared domain | Driver |
|---|---|---|
| ra-policy-674 | S = floor(165 E) + floor(509 C) after clamping finite supplied fractions E and C to [0,1]; integer policy points [0,674]; Python coefficient is S/674 | Increasing either supplied fraction cannot decrease S; truncation plateaus are expected |
| canonical-v2-affinity | Existing Python 1 - address_distance(a,b) on ordinary canonical-v2 coordinates: theta 1..27, phi 1..6, omega 0..4, radius [0,1]; dimensionless | Increasing circular theta separation or an absolute other-coordinate separation cannot increase affinity |
| semantic-v1-theta8 | Decoded theta 0..511 selects one of eight 64-code bins in a valid legacy 28-bit address | Bin index is nondecreasing in theta; other fields do not choose the label |
| canonical-v2-theta27 | Ordinary theta 1..27 selects the existing eight named ranges | Range index is nondecreasing in theta; other fields do not choose the label |

The eight v1 labels, eight v2 labels, RoutableSector enum and 512-entry Mobius32
consent table are different namespaces. No ordinal adapter makes them identical.
Constructor-accepted sentinel states and inconsistent manually supplied raw/field
records do not silently enlarge the ordinary-address claim.

## Mandatory tests and falsifiers

1. Determinism: repeat the same inputs and complete native runs. Every generated
   artifact must be byte-identical across two runs, excluding local execution
   logs. A changed byte, missing row, duplicate row or unknown input fails.
2. Formula and range: compare the actual functions with independently stated
   formulas on declared finite grids. Check endpoints and out-of-domain
   counterexamples separately. Any in-domain disagreement fails that claim;
   an out-of-domain failure is not hidden or called an ordinary-address result.
3. Driver: test both positive Ra inputs; test affinity against circular distance
   0..13, not raw theta number around the wrap. Sector monotonicity means its
   categorical range index only. A decrease/increase in the wrong direction
   fails the corresponding claim.
4. Irrelevance: changing a configured threshold must not change a Ra score.
   Changing reserved bits must not change coordinate affinity or sector.
   Changing shell, phi, harmonic/radius or reserved bits must not change a
   sector when theta is fixed. State/reset/enable are not irrelevant RTL inputs.
5. Native Ra agreement: all three current RTL scorers must equal the actual
   Python integer score on all 32 by 8 input codes and the twelve existing
   thresholds. Inclusive threshold decisions must agree exactly. No tolerance.
6. Coordinate-affinity agreement: compare actual Python with the actual
   spiral_consolidated.v evaluator. Its byte is displayed diagnostically as
   byte/255. No adopted float-to-byte adapter is specified, so do not call this
   byte an interchangeable Python result or select a tolerance after measuring.
   Record exact differences and endpoint examples. A claim of exact equality
   fails on any difference. Binding-specific arithmetic can still be verified.
7. Sector agreement: native ThetaToSector must match Python on all 27 ordinary
   theta codes; native same_sector must match on all 729 ordinary theta pairs.
   Characterize all 32 raw codes separately. An ordinary mismatch fails the
   partition claim. A sentinel mismatch does not disappear into the ordinary
   domain. Compare all 64 adjacency pairs as a separate graph claim: graph
   disagreement must not be presented as partition equality or hidden by it.
8. D1 migration: require an explicit neutral-radius or shell-projection policy
   wherever an actual migration API is tested. Never introduce a default.
   All four shells must yield byte 128 for neutral, or 0/85/170/255 for shell
   projection. Both policies must have identical projected theta, phi, harmonic
   and sector. Check all 512 theta and phi inputs and document lossy examples.
   Missing/unknown policies must reject in an actual API; a tools-only Python
   projection is not described as a shipped Python migration API.
9. Readout provenance: a public number needs its producer, profile, input
   interpretation and scale. A bare number cannot inherit proof from an
   unrelated function with the same name. Missing provenance fails a generic
   interpretation; it does not justify inventing a physical claim to refute.
10. New checks need named failing mutations, passing baselines and clean
    controls. A compile/import/tool failure is not a successful mutant kill.

The existing RTL normalization (S * 38) >> 8 and registered completion flag
input C == 7 are separately characterized. Neither is silently treated as the
Python coefficient or Python's derived stage-7 flag. Likewise, coordinate
affinity need not be calibrated to confidence, and category assignment does not
establish authorization or content semantics.

## Verdict and public display rules

PROVED means the exact named, domain-limited informational claim passes every
mandatory applicable test. It does not prove a different binding, profile,
physical interpretation or calibration.

NOT PROVABLE means the existing readout does not identify or measure its
claimed quantity. State what the reference functions actually compute and what
provenance/evidence is absent. Lack of a producer is not numerical validation.

MODEL CHANGE means a well-defined desired claim fails the existing model and
a specific smallest proposed change could make that claim true. Such a proposal
is not applied to core, RTL, constants or specification.

Give one closing verdict for each readout, plus explicit per-binding results.
There is no PARTLY PROVED escape. Component proofs and public-display
eligibility are reported separately, so a correct partition or score cannot
silently validate an unattributed generic label.

D1 is already decided as explicit alternatives (DECISIONS.md:19-56), not an
open radius blocker. D5 keeps optional named quantities as experiments and
adopts no generic readout (DECISIONS.md:94-100). No website change, generic
profile adoption or physical claim is authorized by these experiments.

## Additive coverage amendment, before the newly identified bindings run

Independent source review identified a second canonical RTL implementation:
hardware/verilog/rpp_canonical.v contains rpp_coherence_calculator,
rpp_theta_to_sector and rpp_sector_adjacency. It is an additional binding,
not an alias for the consolidated modules above. Apply the same ordinary
domains, exact binding-specific arithmetic checks, diagnostic byte/255
comparison and no-post-hoc-tolerance rule independently to both implementations.
Compare both sector maps and graphs; do not pool their agreement counts.

The separate SpinSite.coherence simulation returns sqrt(mx^2 + my^2) from
model state, with exponential decay under its declared no-drive conditions.
Existing simulation experiments are replayed as model evidence only. They do
not identify the historical 0.847 readout or establish a device measurement.
Its legacy v1_to_v2 helper hardcodes a shell projection; characterize that
helper explicitly rather than call it a named-policy D1 migration API.
This amendment adds coverage without changing any earlier acceptance threshold.

Before the main affinity sweep, its declared output bound is made explicit:
ordinary Python affinity lies within [0,1], with mathematical minimum
1 - (0.30 * 13 / 13.5 + 0.40 + 0.20 + 0.10) = 1/90, not an attainable zero.
Binary64 values are reported without redefining the cross-binding criterion.
The duplicated sector decoder in rpp_canonical.v is a separate label-producing
path: compare decoded full words and their irrelevant fields as well as the
standalone theta helper. Helper agreement cannot stand in for decoder evidence.

## Final inventory addition, before these model bindings run

CoherenceEvaluator_Stub in spiral_consolidated.v and the Python legacy
hdl_simulation.CoherenceEvaluator are distinct legacy arithmetic models:
characterize their shared 64 by 32 input grid, including finite-width wrap.
The Python canonical evaluator is another 674-point policy binding; compare
its 32 by 8 input grid separately. The Python Ra evaluator returns a different
floating scale with different constants; characterize its inputs and outputs
without silently multiplying it into the 674-point profile.
Existing deterministic sweeps also cover HRDA, complement geometry, caller
consent and SpinSite simulation; their names do not turn them into one quantity.
This closes the source inventory without changing an earlier acceptance test.

Before the affinity native runs, the fixed-anchor magnitude grid is supplemented
by all 27 by 27 ordinary theta pairs and all eight reversals of the phi, omega
and radius endpoints (5,832 probes per affinity binding). These explicitly test
circular wrap and both subtraction orientations. The magnitude grid is finite
byte-domain evidence plus the stated separable formula, not an enumeration of
all pairs of arbitrary binary64 radius values.
