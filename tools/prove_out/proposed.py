"""Proposed explicit operational quantities; no change to the shipped protocol."""

from fractions import Fraction
import math


def progress_index(engaged, opportunities, completed, required):
    """Exact weighted progress from observable counts, not confidence or health.

    IMPOSED operational definition: engagement=engaged/opportunities and
    completion=completed/required. The existing 165/509 weights are retained as
    policy weights; their physical significance is not asserted. Empty totals
    and bool-as-count are rejected rather than inventing a meaning.
    """
    values = (engaged, opportunities, completed, required)
    if any(type(x) is not int for x in values):
        raise ValueError("counts must be integers")
    if opportunities <= 0 or required <= 0 or not 0 <= engaged <= opportunities or not 0 <= completed <= required:
        raise ValueError("counts must describe bounded nonempty tasks")
    return (165 * Fraction(engaged, opportunities) + 509 * Fraction(completed, required)) / 674


def address_affinity(a, b):
    """Proposed dimensionless v2 address affinity on strict ordinary addresses.

    Inputs are (theta 1..27, phi 1..6, omega 0..4, radius 0..1). It is a
    geometric closeness score, never authorization, truth or a biometric result.
    The circular theta normalization uses the actual maximum integer separation
    13, so the range reaches zero. This changes the shipped 13.5 denominator and
    is an IMPOSED proposal only; adopting it into core requires steward review.
    """
    def valid(x):
        return (len(x) == 4 and all(type(v) is int for v in x[:3])
                and 1 <= x[0] <= 27 and 1 <= x[1] <= 6 and 0 <= x[2] <= 4
                and type(x[3]) in (int, float) and math.isfinite(x[3]) and 0 <= x[3] <= 1)
    if not valid(a) or not valid(b):
        raise ValueError("ordinary finite v2 address required")
    theta = abs(a[0] - b[0])
    distance = (Fraction(3, 10) * Fraction(min(theta, 27 - theta), 13)
                + Fraction(4, 10) * Fraction(abs(a[1] - b[1]), 5)
                + Fraction(2, 10) * Fraction(abs(a[2] - b[2]), 4)
                + Fraction(1, 10) * abs(Fraction(a[3]) - Fraction(b[3])))
    return float(1 - distance)
