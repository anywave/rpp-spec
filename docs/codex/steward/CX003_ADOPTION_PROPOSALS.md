# CX-005 exact proposed edits (not applied)

These patches are recommendations for a future authorized change. No core,
HDL, header, constant, specification or published outbox has been edited here.
Apply only the decision RADIX selects and rerun the finite evidence.

## Add explicit named quantity APIs

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

## Align the optional RTL fallback theta with the Python canonical contract

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

## Align the registered completion flag with Python derived completion

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
