# CX-005 v2 steward packet — recommendations awaiting RADIX

Authority: TR's CX-005 v2 card, `anywave/trellis-channel` at `9193abbb`,
`codex/inbox/rpp-spec.md`; RPP base `95c67ef`. This packet changes no specification,
package behavior, constant, address layout, consent header or golden vector.
Every proposal below is **unresolved — steward decision (RADIX)**. A recommendation
is not an acceptance or permission to implement it.

The four catalog items already include radius, Shell-0 TTL and T2 bounds; those
names do not identify seven separate decisions. The frozen catalog additionally
contains **243 unresolved Boundary F passages** and **two LOW advisory groups**.
The exact catalog is `tools/drift/catalog.json` (source revision `0a12c8d`). Its
counts must remain 243 / 4 / 2 until a separately authorized catalog revision.
No PR, issue, lattice post or decision record is created by this task. TR routes
decisions as `[RFC]` under `GOVERNANCE.md:63–71`; the cited source had no
`DECISIONS.md`.

## Decision register

| Decision | Blocks | Recommended next decision; one-line reason |
|---|---|---|
| D1 `STEWARD-RADIUS-DERIVATION` | A single implied v1→v2 migration policy | Require an explicit named migration policy; neither conflicting mapping can silently stand for both. |
| D2 `STEWARD-TTL-1` | A truthful Shell-0 software lifetime contract | Preserve the reference implementation's 25 ns limit as software policy while documenting the mismatch; this does not lengthen retention or claim physical erasure. |
| D3 `STEWARD-T2-1` | Real-device Shell-0 conformance/attestation | Treat device support as experimental until characterized; the repository supplies no device evidence that settles the contradictory bounds. |
| D4 `STEWARD-CLAIM-1` | Honest package documentation of timeout enforcement | Describe the returned value as a software deadline; a function returning an integer proves no physical-erasure claim. |
| D5 CX-003 quantities/profile adoption | A cross-binding or generic “coherence/sector proved” claim | Keep explicit reference quantities optional and profile-tagged; demonstrated reproducibility does not establish confidence, content meaning or calibration. |
| D6 E2 disposition | Closing the two RA testbench failures | Review the isolated expectation corrections; neither failure requires a header, constant or RTL change. |
| D7 E5 resolver/overlay adoption | A normative multi-channel encrypted overlay contract | Review the additive resolver proposal and reuse an established tunnel implementation; the simulator is a policy model. |
| B1–B6 Boundary F classes | Closing any of 243 frozen baseline entries | Approve only a class review/annotation step initially; grouping is not evidence that every claim in a class is valid. |
| A1–A2 LOW radius advisories | Consistent radius wording and strict edge behavior | Approve precise wording separately from behavior; the wording ruling already distinguishes normalized API values from encoded bytes. |

All exact edits are **proposed and unapplied**. Text in diff fences is evidence,
not a request to apply a patch during this task. Approval of one decision does not
approve another. Software-MUST anchors remain protected independently of any
baseline annotation, movement or removal. Other genuine behavioral conflicts are
recorded here instead of being resolved through a wording edit.

## D1 — v1→v2 radius: choose a migration policy explicitly

Evidence: `spec/RPP-CANONICAL-v2.md:347` says `radius_v2 = 0.5`;
`spec/ADDRESSING-LAYERS.md:142` says `radius_v2 = shell / 3.0`. The latter section
calls the mapping informational and lossy. The two formulas disagree for every
integer shell 0–3. Radius API range and byte encoding are not this decision: the
API is a float in 0–1 and the byte is `round(radius * 255) & 0xFF`; the separate
half-to-even tie interpretation is IMPOSED under TR's ruling.

Options and exact follow-up edits:

1. **Neutral default.** Keep the canonical bullet; replace the addressing-layer
   assignment with `radius_v2 = 0.5  # Neutral-radius migration; shell is not preserved`.
   Evidence for this option is the canonical document's explicit default. It
   discards shell information; reverse conversion must say that explicitly.
2. **Shell projection.** Keep the addressing-layer assignment; replace the canonical
   bullet with ``- `radius_v2 = shell_v1 / 3.0` (shell-projection policy)``.
   Evidence is the informational forward/reverse pair, where `round(radius_v2 * 3)`
   recovers shell. This chooses an interpretation connecting distinct fields.
3. **Explicit alternatives (recommended).** Keep both formulas, label them and
   prohibit an implicit universal adapter. This preserves the existing evidence
   without silently choosing which information a caller may lose.

Exact proposed option 3 patch:

```diff
--- a/spec/RPP-CANONICAL-v2.md
+++ b/spec/RPP-CANONICAL-v2.md
@@ -347,1 +347,4 @@
-   - `radius_v2 = 0.5` (default)
+   - `radius_v2 = 0.5` under the explicitly selected `neutral-radius` policy.
+     This does not preserve the v1 shell. The alternative `shell-projection`
+     policy uses `radius_v2 = shell_v1 / 3.0`. A migration API must require the
+     caller to name its policy; neither mapping is a universal default.
--- a/spec/ADDRESSING-LAYERS.md
+++ b/spec/ADDRESSING-LAYERS.md
@@ -133,1 +133,1 @@
-def semantic_to_transport(shell, theta, phi, harmonic):
+def semantic_to_transport_shell_projection(shell, theta, phi, harmonic):
@@ -142,1 +142,1 @@
-    radius_v2 = shell / 3.0                                  # Shell → normalized radius
+    radius_v2 = shell / 3.0  # Explicit shell-projection policy; not neutral-radius
```

After approval: add the chosen policy contract and discriminating shell 0–3
examples in the same RFC; review all named mapping consumers before introducing
an implementation. The patch does not change layouts or encoding.

## D2 — Shell-0 software TTL

Evidence: `spec/SPEC.md:94` says “Session duration” and
`spec/CCQPSG.md:108` says “session-scoped (software)”; `rpp/ccqpsg.py:151–152`
unconditionally compares elapsed time against `compute_liminal_timeout(shell)`,
whose Shell-0 table entry is 25 at `rpp/continuity.py:46`. There is no session
identifier or session-end argument in that check. A session lifetime and 25 ns
are different contracts. Existing tests establish the implementation's policy,
not the precision of a real scheduler.

Options: (1) make the 25 ns reference software policy the documented contract;
(2) implement a session-scoped software policy, requiring a session lifecycle API,
an explicit deployment profile and core/tests review; (3) retain an unresolved
experimental profile and forbid a unified lifetime claim. Recommend option 1
for the reference implementation: it preserves the stricter existing retention
check without claiming a physical guarantee. Choosing it does not settle D3.

Exact proposed option 1 patch:

```diff
--- a/spec/SPEC.md
+++ b/spec/SPEC.md
@@ -94,1 +94,1 @@
-| 0 | Hot | In-memory cache | Session duration | ~25 ns |
+| 0 | Hot | In-memory cache | 25 ns reference software TTL | ~25 ns device-profile target |
--- a/spec/CCQPSG.md
+++ b/spec/CCQPSG.md
@@ -108,1 +108,1 @@
-- IF shell=0 THEN the packet is transient; its TTL is ~25 ns (spintronic) or session-scoped (software).
+- IF shell=0 THEN the reference software rejects elapsed time >= 25 ns. This is a software policy deadline, not a physical-erasure guarantee. A session-scoped profile would require a separate lifecycle contract.
```

Option 2's exact first API proposal is intentionally not invented here: it needs
RADIX to select the lifetime event and failure semantics before a safe function
signature can be specified. The precise action after that answer is a separate
core proposal, keeping the table values unchanged until versioned adoption.
For option 3, add the following exact paragraph after the Shell table instead of
changing runtime behavior: “Shell-0 software lifetime is unresolved: the reference
implementation enforces 25 ns, while earlier prose says session-scoped. Do not
infer a session-scoped implementation from this table.”

## D3 — T2 upper/lower bound and real-device claims

Evidence: `spec/SPINTRONIC.md:288` requires the specific device's T2 ≤ 25 ns;
`:311` requires the destination's available T2 ≥ 25 ns. Taken literally together,
they permit only exactly 25 ns. The same text discusses shorter measured devices
as stronger expiry and rejects destinations below the 25 ns routing window.
Routing availability and post-routing recoverability are distinct questions.
No real-device measurement was supplied by CX-003 or CX-005.

Options: (1) retain both constraints as an exact-25 ns experimental profile and
document that narrow intersection; (2) separate the required routing budget,
measured device lifetime and expiry criterion in a new characterized device
profile; (3) suspend normative real-device conformance claims pending that work.
Recommend option 3 as the interim publication decision: a software simulation
cannot settle a materials or erasure guarantee. Keep the reference admission
values unchanged while the profile is designed.

Exact proposed option 3 replacement paragraphs:

```diff
--- a/spec/SPINTRONIC.md
+++ b/spec/SPINTRONIC.md
@@ -288,1 +288,1 @@
-2. **MUST complete the routing decision within T2** (the measured T2 of the specific device, which must be ≤ 25 ns). If the routing logic cannot complete within T2, it is not a valid Shell=0 implementation.
+2. On spintronic platforms, real-device Shell=0 conformance remains experimental. A device profile must separately specify the routing budget, measured lifetime under routing load and expiry criterion; the reference 25 ns value alone establishes none of these measurements.
@@ -311,1 +311,1 @@
-For Shell=0 packets, `min_t2_ns` is set by `csp_from_rpp()` to `SHELL_T2_NS[0]` = 25. A destination substrate that cannot provide T2 ≥ 25 ns MUST refuse the crossing in the SCOUT phase. This prevents a spintronic origin from crossing to a conventional destination and silently downgrading to software enforcement.
+The reference `csp_from_rpp()` sets Shell=0 `min_t2_ns` to `SHELL_T2_NS[0]` = 25 and applies the existing SCOUT admission check. This software threshold is not device attestation. Real-device support remains experimental until the separate routing and expiry criteria are characterized; no physical-erasure guarantee follows from admission.
```

If option 1 is selected instead, append exactly: “The simultaneous ≤ 25 ns and
≥ 25 ns requirements restrict this experimental profile to T2 = 25 ns; no
uncharacterized device is thereby certified.” Option 2 requires the selected
measurement, operating conditions, clock budget and attestation failure response
in a reviewed follow-up; changing 25 ns is a separate constant decision.

## D4 — unqualified timeout docstring

Evidence: `rpp/continuity.py:276–277` says state literally ceases to exist;
`spec/SPINTRONIC.md:278` prohibits conventional-hardware physical-enforcement
claims. The function only returns a table value. Options: (1) replace the claim
with a software-policy description (recommended); (2) retain the existing text
only inside a separately characterized optional device API; (3) keep the conflict
open and suppress the claim in all presentation material. Recommendation reason:
the existing function has no device/readout input or erasure primitive.

Exact proposed option 1 patch (docstring only; numbers unchanged):

```diff
--- a/rpp/continuity.py
+++ b/rpp/continuity.py
@@ -276,2 +276,3 @@
-    For Shell 0, the returned value is the physical T2 spintronic decoherence
-    time — not a soft deadline. The state literally ceases to exist after this.
+    For Shell 0, the reference software timeout is 25 ns.
+    This function returns a policy deadline; it does not establish physical erasure.
+    Device-specific enforcement requires independent characterization.
```

For option 2, the exact current function edit is the same safe description above;
device-specific wording would be placed in the new, characterized API after its
separate approval. For option 3 no source edit is authorized and this item stays
open. No physical claim is added or accepted by this packet.

## D5 — CX-003 quantities and sector profiles

The proposal source is `tools/prove_out/proposed.py`, pinned in the base tree.
`progress_index` uses exact observable-count ratios with the existing 165/509
policy weights; it does not reproduce the shipped per-term integer flooring.
`address_affinity` accepts only ordinary finite v2 coordinates and uses the
maximum integer theta separation 13, whereas shipped `address_distance` uses
13.5 and accepts constructor-valid reserved states. They are explicit alternative
quantities, not bug fixes that can silently replace the existing API.

Options: (1) keep both definitions as experiments; (2) add separately named,
documented optional package APIs while retaining shipped behavior; (3) select a
versioned replacement and migrate all consumers. Recommend option 1 pending an
operator-facing input/provenance contract; it already permits all experiments
without implying calibration or authorization. If RADIX selects option 2, the
exact source addition is the byte-for-byte contents of `tools/prove_out/proposed.py`
as a new `rpp/quantities.py`, changing only the module description as shown
in the exact proposed patch below.
Expose names only through explicit imports from that module; do not change
`rpp.coherence`, `rpp.address_canonical.coherence` or package-root aliases.

The sector recommendation is to retain the two profile mappings and their lossy
projection. A profileless number or semantic-name preservation claim is blocked:
CX-003 found 476/512 projected names differ. Exact proposed engineering-facing
contract after approval: “A sector result must identify `semantic-v1-theta8` or
`canonical-v2-repitan8`. Conversion projects coordinates and does not preserve
the named sector. A sector does not infer payload content.” This is a proposal
for prose/API metadata, not a layout field or header extension.

### E1 completion evidence and remaining authority choices

Updated verdicts: **coherence partly proved; sector partly proved**. The two
named sector partitions are individually proved only inside their declared
domains; a generic profile-independent readout remains unsupported. The complete
exact A/B conditions are preserved in
[COHERENCE_SECTOR_CONDITIONS.md](steward/COHERENCE_SECTOR_CONDITIONS.md):
coherence A-C1..A-C5 / B-C1..B-C5, sector A-S1..A-S4 / B-S1..B-S3.
Every applicable A and B condition must hold before the named-profile claim can
be “proved”; calibrated confidence would additionally need external labels,
calibration/error bounds and repeatable validation.

New actual finite evidence extends the original 256-row comparison:

| Check | Result | What remains blocked |
|---|---|---|
| Three RTL scorers, 256 inputs × 12 thresholds = 3,072 rows | Exact scorer 0 score / 0 threshold mismatches; approximate 3,060 / 967; LUT 2,940 / 345 | Interchangeability of the three score bindings |
| Both monotonic axes | Approximate decreases: entropy 5, completion 63; LUT: 0, 32 | A common monotonic weighted-policy claim |
| Consent derivation, 32 named cases | 13 differences under the explicitly declared bool-override → strength-3 test adapter | A shared two-bit RTL versus five-state Python policy |
| Fallback, 207,360 cases | Theta 134,400 differences; phi/omega/radius 0 under explicit raw-phi + 1 adapter | A common one-based versus zero-based theta-XOR contract |
| Registered completion, 256 cases | 31 differences | Input-field completion versus derived weighted-score completion |

For score and completion, RADIX may require the existing Python weighted policy
across bindings or retain explicitly named legacy profiles. Recommend preserving
the legacy profiles until the authority/rounding/cycle contract is approved;
calling unlike outputs equivalent would conceal observed routing differences.
For consent, options are a separately named legacy two-bit policy, a reviewed
three-bit/five-state adapter, or another explicitly specified policy. Recommend
the legacy profile as the interim default; do not widen a header or grant
permission by interpreting an override as consent. The exact follow-up for a
new adapter needs RADIX to select state codes, threshold meanings and override
authority first. This task supplies no invented header edit.

For fallback, select Python zero-based XOR or preserve the RTL one-based profile;
recommend explicit profiles until an authority is selected. If Python is selected,
the exact patch below is the prospective edit and acceptance is 0/207,360 theta
differences. For completion, if the derived score is selected, acceptance is
0/256 flag differences using the exact patch below. Neither patch is applied.

### Exact E1 proposals after an adoption/authority answer

The following is reproduced from E1's `tools/prove_out/CX005_PROPOSALS.md`.
Its interim default is to retain experiments pending the input contract;
the additive-API patch describes how to adopt if RADIX opts in.
An option to keep legacy profiles makes no executable edit and retains explicit
profile-specific limitations. The standalone copy is
[CX003_ADOPTION_PROPOSALS.md](steward/CX003_ADOPTION_PROPOSALS.md).

#### CX-005 exact proposed edits (not applied)

These patches are recommendations for a future authorized change. No core,
HDL, header, constant, specification or published outbox has been edited here.
Apply only the decision RADIX selects and rerun the finite evidence.

#### Add explicit named quantity APIs

Recommended default: retain the experiments pending provenance and steward review.
If RADIX chooses adoption, use additive APIs and preserve existing behavior until
consumers explicitly select the new named domain. The new module copies the already tested
reference definitions verbatim, with its module description changed to describe
the adopted scope. Add targeted core tests from the proposal tests upon adoption.

```diff
--- /dev/null
+++ b/rpp/quantities.py
@@ -0,0 +1,43 @@
+"""Explicit operational quantities on declared count and ordinary-v2 domains."""
+
+from fractions import Fraction
+import math
+
+
+def progress_index(engaged, opportunities, completed, required):
+    """Exact weighted progress from observable counts, not confidence or health.
+
+    IMPOSED operational definition: engagement=engaged/opportunities and
+    completion=completed/required. The existing 165/509 weights are retained as
+    policy weights; their physical significance is not asserted. Empty totals
+    and bool-as-count are rejected rather than inventing a meaning.
+    """
+    values = (engaged, opportunities, completed, required)
+    if any(type(x) is not int for x in values):
+        raise ValueError("counts must be integers")
+    if opportunities <= 0 or required <= 0 or not 0 <= engaged <= opportunities or not 0 <= completed <= required:
+        raise ValueError("counts must describe bounded nonempty tasks")
+    return (165 * Fraction(engaged, opportunities) + 509 * Fraction(completed, required)) / 674
+
+
+def address_affinity(a, b):
+    """Proposed dimensionless v2 address affinity on strict ordinary addresses.
+
+    Inputs are (theta 1..27, phi 1..6, omega 0..4, radius 0..1). It is a
+    geometric closeness score, never authorization, truth or a biometric result.
+    The circular theta normalization uses the actual maximum integer separation
+    13, so the range reaches zero. This changes the shipped 13.5 denominator and
+    is an IMPOSED proposal only; adopting it into core requires steward review.
+    """
+    def valid(x):
+        return (len(x) == 4 and all(type(v) is int for v in x[:3])
+                and 1 <= x[0] <= 27 and 1 <= x[1] <= 6 and 0 <= x[2] <= 4
+                and type(x[3]) in (int, float) and math.isfinite(x[3]) and 0 <= x[3] <= 1)
+    if not valid(a) or not valid(b):
+        raise ValueError("ordinary finite v2 address required")
+    theta = abs(a[0] - b[0])
+    distance = (Fraction(3, 10) * Fraction(min(theta, 27 - theta), 13)
+                + Fraction(4, 10) * Fraction(abs(a[1] - b[1]), 5)
+                + Fraction(2, 10) * Fraction(abs(a[2] - b[2]), 4)
+                + Fraction(1, 10) * abs(Fraction(a[3]) - Fraction(b[3])))
+    return float(1 - distance)
```

Usage after adoption: `from rpp.quantities import progress_index, address_affinity`.
No existing coherence call is silently redirected. The exact Fraction-vs-integer
rounding and address theta13 normalization remain explicit API distinctions.

#### Align the optional RTL fallback theta with the Python canonical contract

Option: choose Python zero-based XOR as authoritative. Preserve the port phi0..5
namespace and use the explicit phi+1 adapter in comparisons. This patch changes no
published constant or layout; it is still withheld because choosing an authority
is a steward decision. Expected acceptance: theta mismatch134,400→0 of207,360.

```diff
--- a/hardware/verilog/spiral_ra_coherence.v
+++ b/hardware/verilog/spiral_ra_coherence.v
@@ -312,7 +312,7 @@
     wire [1:0] omega_offset = fallback_vector[1:0];

     // XOR with primary values
-    wire [5:0] theta_xor = {1'b0, primary_theta} ^ {3'b0, theta_offset};
+    wire [5:0] theta_xor = ({1'b0, primary_theta} - 6'd1) ^ {3'b0, theta_offset};
     wire [3:0] phi_xor   = {1'b0, primary_phi} ^ {1'b0, phi_offset};
     wire [2:0] omega_xor = primary_omega ^ {1'b0, omega_offset};

@@ -327,12 +327,10 @@

     always @(*) begin
         // Theta wrapping: keep in 1-27 range
-        if (theta_xor > 6'd27)
-            theta_wrapped = theta_xor[4:0] - 5'd27;
-        else if (theta_xor == 6'd0)
-            theta_wrapped = 5'd27;
+        if (theta_xor >= 6'd27)
+            theta_wrapped = theta_xor[4:0] - 5'd27 + 5'd1;
         else
-            theta_wrapped = theta_xor[4:0];
+            theta_wrapped = theta_xor[4:0] + 5'd1;

         // Phi wrapping: keep in 0-5 range
         if (phi_xor > 4'd5)
```

#### Align the registered completion flag with Python derived completion

Option: select weighted-score completion as authoritative. Keep legacy input-field
completion as a separately named signal only if RADIX selects that contract.
Expected acceptance:31→0 mismatches across256 header codes.

```diff
--- a/hardware/verilog/coherence_evaluator_ra.v
+++ b/hardware/verilog/coherence_evaluator_ra.v
@@ -91,7 +91,7 @@
         end else if (enable) begin
             coherence_score <= total_score;
             coherence_valid <= (total_score >= threshold);
-            completion_flag <= (complecount_trace == 3'd7);  // Full completion when C=7
+            completion_flag <= (total_score == 10'd674);  // Derived weighted-score completion
             entropy_contribution <= entropy_term;
             complecount_contribution <= complecount_term;
         end
```

The alternate scorers and consent-state encoder need an authority/interface
decision before a repair patch can be selected. Recommended default: preserve
legacy names as separate profiles and block claims of interchangeability. A
three-bit five-state adapter must be reviewed as a header/core adoption, not
smuggled in as a testbench repair. No future edit is implied until RADIX chooses.

## D6 — E2 RA testbench disposition

Both original failures are expected-value defects: E15/C3 is low in both the
Python reference (297 < 300) and the approximate RTL (160), while the testbench
expected medium. Its unchanged header `0x61500000` has raw phi bits `[26:24]` = 1
(canonical external phi 2), while the testbench expected 3. Parsing that unchanged
header does not justify changing the parser, layout or golden vectors.

Options: (1) review corrected expectations and a separate medium probe;
(2) change fixture bytes to fit the old expectation; (3) change the decoder.
Recommend option 1: expected values should describe the unchanged inputs.
E2 branch `codex/ra-testbench` at `b0bd4d1b249a368d4c9703612845c5dc4cf45688`
carries the exact edits and evidence in `hardware/verilog/CX005_RA_VALIDATION.md`:
before **32 checks / 30 passed / 2 failed**, after **33 / 33 / 0**, with an
additional E15/C4 medium probe (RTL 450, Python 369). Its four exercised mutations
were killed, zero survived; one shared compiled clean control passed. There is
**no E2 core diff** to approve. This disposition does not excuse the independent approximate
and LUT score mismatches or completion semantics documented by E1/CX-003.

## D7 — E5 proposed resolver additions

The exact unapplied resolver patch is included below. Adoption is separate from approval of the deterministic
simulator. Same consent/trust checks govern every underlay; connectivity is not
membership, admission or consent. Control cannot carry START, grants, consent,
keys, models or prompt/answer text. Signed control and billboards remain design
requirements; the simulator implements no cryptography or key exchange.

Options: A retain the current resolver and experiment; B adopt the additive
contract through an RFC, with deployment and unfilled profile parameters reviewed
separately; C select a narrower/different transport profile. Recommend B as a
proposal for review: it defines explicit safety and interoperability boundaries
while reusing established protocols. This is not approval to deploy tunnels.

Recommended reuse: Tailscale clients with self-hosted Headscale and an authorized
DERP relay for IP LAN/Wi-Fi/internet paths; existing platform GATT APIs only for
bounded signed independent control after profile approval. Evaluate Reticulum
separately for LoRa/non-IP adapters after its exact custom license and backend
are reviewed. No listed protocol automatically supplies a GATT/LoRa tunnel from
an RPP URI. The prior-art review is read-only; sources, licenses and capability
limits are in `docs/design/MULTI_CHANNEL_OVERLAY.md` on `codex/overlay-design`.

Exact proposed option B patch, reproduced byte-for-byte from
`docs/design/RESOLVER_OVERLAY_PROPOSAL.diff` on `codex/overlay-design`:

````diff
--- a/spec/RESOLVER.md
+++ b/spec/RESOLVER.md
@@ -735,6 +735,57 @@
 }
 ```

+### 11.3 Optional Authenticated Multi-Channel Overlay Profile
+
+An implementation MAY resolve an RPP address through an existing encrypted
+overlay. The RPP address identifies the requested destination; an authenticated
+binding from the existing identity layer identifies the authorized overlay peer.
+Discovery and automatic tunnel formation MUST NOT create membership, carry an
+admission grant, replace a consent action, or bypass current consent and trust
+checks. The same checks apply to every direct, relay and underlay path.
+
+The overlay MUST reuse an existing reviewed tunnel protocol and implementation;
+this profile defines no cipher, handshake or key exchange. Peers MAY discover
+endpoints and form direct tunnels among already authorized members, or use an
+authorized relay when no direct path exists. Non-IP carriers require an explicit
+compatible adapter; a Bluetooth URI alone does not establish tunnel capability.
+
+Path selection MUST first filter by current authorization, consent, adapter
+capability, fresh availability and circuit state. It MUST then use timestamped
+latency, loss and jitter readings under a declared measurement/ranking profile
+with a deterministic tie break. The profile MUST state freshness, hysteresis,
+probe and circuit-breaker policies. No eligible path yields an explicit
+NO_CHANNEL result. An alternate path MAY be retried only before the operation's
+first emitted token; after that boundary, automatic replay MUST NOT occur.
+Every attempt and terminal outcome MUST retain a meter row, including denial,
+failure, partial delivery and no-path outcomes. Existing tried_modalities MUST
+retain the attempted modality history across direct and relay fallback.
+
+Implementations MUST distinguish three application traffic classes:
+
+- Data uses the best measured eligible path for the authorized operation.
+- Control contains only small signed ALIVE, MEMBER-CHANGED, STOP, PAUSE,
+  ROUTE-AROUND or RESUME notices in a closed, bounded envelope. It MUST NOT carry
+  START, grants, consent, keys, models, prompt text or answer text. Bluetooth MAY
+  provide an independent control path; independence MUST be assessed by failure
+  domain, not by URI or modality name alone. MEMBER-CHANGED invalidates/rechecks
+  membership and cannot admit a peer. RESUME cannot start an operation, undo
+  STOP/revocation or restore consent; current authorization is checked again.
+- Billboards contain signed scoped facts/rules with exactly the semantic fields
+  {machine, kind, fact, since, until, receipt}. Signature/issuer verification is
+  performed by an existing reviewed mechanism. Implementations MUST validate
+  issuer authority, receipt binding, type/size limits, kind allowlist and replay
+  state, and apply a fact only while since <= now < until. Expiry MUST be checked
+  on arrival and every application; caching or relaying cannot extend until.
+  A billboard cannot change agent instructions, execute code, expand authority,
+  create a grant, bypass consent or override STOP/revocation. The adopted profile
+  MUST specify time/skew handling, replay persistence and conflict precedence;
+  an unspecified conflict is rejected and reported.
+
+These traffic rules do not provision credentials or alter the consent header,
+address formats, Shell TTLs, published constants or existing trust decisions.
+
+
 ---

 ## 12. Version History
````

Patch SHA-256: `296bbc18a827dfc939b8dc704af0a6b424dcbba9fd98000e241128446816086e`.

## B1–B6 — all 243 Boundary F passages, grouped without accepting them

The appendix [BASELINE_CLASSES.md](steward/BASELINE_CLASSES.md) lists every frozen
id/path/line/hash exactly once, with its original rule, source text and proposed
annotation in [baseline-decisions.json](steward/baseline-decisions.json).
The JSON contains exact original/source-preserving passage text and a prospective
per-ID review-register edit, so approval can be reviewed without relying on
shifting line numbers. Each entry remains
IMPOSED and unresolved; none is silently removed, accepted or recataloged.

| Class | Count | What it blocks | Options and recommended next step |
|---|---:|---|---|
| B1 software policy/cross-profile enforcement | 37 | A uniform software/device enforcement story | Preserve anchors and annotate profile ambiguity (recommended); rewrite each profile separately; or defer. Reason: software obligations must survive any hardware cleanup. |
| B2 optional device profile | 108 | Claims of physical expiry or certified devices | Mark profile claims as unvalidated pending characterization (recommended); substantiate per-device claims; or remove them with steward-visible findings. Reason: simulation is not device evidence. |
| B3 geometry/extended model | 30 | Treating mathematical/simulation vocabulary as empirical support | Mark as computational model scope (recommended); provide independent evidence; or withdraw physical interpretations. Reason: reproducibility establishes calculations, not materials behavior. |
| B4 history/navigation references | 11 | Confusing historical/link text with current guarantees | Retain historical text and annotate that it is not validation (recommended); rewrite current index descriptions; or defer. Reason: preserve provenance without endorsing it. |
| B5 explanatory identity/address/routing prose | 42 | User-facing physical/biological interpretations | Annotate that software/transport behavior is the supported scope (recommended); rewrite each claim for a selected profile; or defer. Reason: links, examples and metaphors need distinct review from guarantees. |
| B6 package comments/docstrings | 15 | Honest package API explanations | Annotate the external review register while preserving source (recommended); rewrite misleading passages after D2–D4; or defer. Reason: code comments cannot establish physical enforcement. |
| **Total** | **243** | | |

The recommended **annotation** option is deliberately a review staging step,
not closure or acceptance. Exact external register lines and source-preserving
text are in the JSON. Annotation changes no source passage or catalog entry.
If RADIX chooses defer, make no edit. If RADIX chooses rewrite,
withdraw or substantiate, a class-wide answer is insufficient to invent missing
evidence: TR records affected IDs and the selected profile, then reviews exact
replacement text per passage before application. Deletions still emit
`BND-F-BASELINE-REMOVED`; changed physics passages get their normal severity;
software-MUST losses independently remain HIGH. Catalog baseline status does not
change simply because a note was inserted.

## A1–A2 — existing LOW radius advisories

**A1 `WORD-RADIUS-1`.** Blocks consistent API/encoded terminology, not the settled
byte layout. Evidence and all six exact passages are in the catalog. Options:
clarify all six (recommended), keep current prose and advisory, or change the API
(separate core decision). The exact proposed wording changes are:

| Path / old passage fragment | Exact replacement fragment |
|---|---|
| `VERSION_POLICY.md:83` `Normalized 0-1` | `Encoded byte; API radius = byte / 255 in 0–1` |
| `VERSION_POLICY.md:70` `(radius << 13)` | `(r_enc << 13)`; append `r_enc = round(radius * 255) & 0xFF` in a following explanatory sentence |
| `VERSION_POLICY.md:74` `(address >> 13) & 0xFF` | `r_enc = (address >> 13) & 0xFF; radius = r_enc / 255.0` |
| `spec/README.md:92` `Ankh-normalized` | `Encoded byte; normalized API radius 0–1` |
| `spec/PMA-SCHEMA-v1.md:116` `0-255 (normalized)` | `Encoded byte 0–255; API radius 0–1` |
| `spec/ADDRESSING-LAYERS.md:114` `Intensity scalar (Ankh-normalized emergence strength)` | `Encoded byte 0–255; API intensity scalar 0–1` |

Reason: these edits state the sourced API/byte distinction and leave all published
values intact. Explicit tie examples remain `1/510→0`, `5/510→2`, `0.5→128`
under the IMPOSED half-to-even clause. Do not apply this wording packet now.

**A2 `WORD-RADIUS-EDGE`.** Blocks strict type and URI round-trip guarantees.
The guard accepts `True` and `-0.0`; formatting emits `r:-0.00`, which the URI
regex refuses. Options: retain compatibility and document it; reject bool and
normalize negative zero; or broaden URI parsing. Recommend the second only as a
versioned core proposal: it prevents a non-round-trippable spelling while making
type intent explicit. Exact prospective edit at `RPPAddress.__post_init__`:
reject `type(self.radius) not in (int, float)` before the current range guard;
at `to_uri`, format `(0.0 if self.radius == 0 else self.radius)` in place of
`self.radius`. Preserve the same `.2f` formatting and all encoding constants.
Adoption requires explicit compatibility review and dedicated bool/negative-zero
tests; no such core edit is made in CX-005.

## Answer format and application boundary

TR can relay one line per decision, for example `D1=explicit-alternatives`,
`D2=reference-25ns`, `D3=experimental`, `D4=software-docstring`, `D5=experiments`,
`D6=expectation-fix`, `D7=review-proposal`, `B1..B6=annotate`, `A1=clarify`,
`A2=separate-core-proposal`, followed by any exceptions identified by baseline ID.
Those example answers are **not** RADIX's decisions. A later approved change
must preserve its RFC rationale, apply only the selected patch, run the full
required gates and report unresolved entries. No answer is inferred from silence.
