"""
Tests for the CCQPSG reference implementation.

Covers: verify_ccqpsg_compliance() as defined in spec/CCQPSG.md Section 7.

Test groups:
  TestCorrectPackets           — valid packets that return (True, [])
  TestV6_TTLViolation          — expired TTL / shell temporality (V7)
  TestConsentGating            — phi < node_phi_min scenarios (V4 routing)
  TestBidirectionality         — rules hold in both directions
  TestCorrectnessConjunction   — all criteria must hold simultaneously
  TestDeterminism              — same inputs always produce same outputs
  TestEdgeCases                — boundary values, phi=0, phi=511, shell=3

The verify_ccqpsg_compliance function is copied directly from spec/CCQPSG.md
Section 7 so tests do not depend on the spec file path.
"""

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure the rpp package is importable (mirrors conftest.py)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from rpp.address import decode, encode
from rpp.continuity import SHELL_LIMINAL_TIMEOUT_NS, compute_liminal_timeout

# ---------------------------------------------------------------------------
# Reference implementation — copied verbatim from spec/CCQPSG.md Section 7
# ---------------------------------------------------------------------------


def verify_ccqpsg_compliance(
    address_int: int,
    payload: bytes,
    node_phi_min: int,
    elapsed_ns: int,
) -> tuple:
    """
    Verify CCQPSG compliance for a packet at a given routing node.

    Args:
        address_int:  28-bit RPP address integer.
        payload:      Payload bytes (opaque; checked only for presence).
        node_phi_min: This node's minimum phi threshold (0-511).
        elapsed_ns:   Nanoseconds since the packet was encoded at the sender.

    Returns:
        (compliant, violations) where:
          - compliant is True iff violations is empty
          - violations is a list of human-readable violation strings
    """
    violations: list = []

    # --- Criterion 1: Syntactic validity ---
    # Address must fit in 28 bits; reserved bits [31:28] must be zero.
    if not isinstance(address_int, int) or not (0 <= address_int <= 0x0FFFFFFF):
        violations.append(
            f"V1: address {hex(address_int) if isinstance(address_int, int) else address_int!r} "
            f"is outside 28-bit range [0x0000000, 0x0FFFFFFF]"
        )
        # Cannot proceed with decode if address is invalid
        return False, violations

    shell, theta, phi, harmonic = decode(address_int)

    # --- Criterion 1 (field ranges, redundant check via decode but explicit here) ---
    if not (0 <= shell <= 3):
        violations.append(f"V2: shell={shell} outside valid range 0-3")
    if not (0 <= theta <= 511):
        violations.append(f"V2: theta={theta} outside valid range 0-511")
    if not (0 <= phi <= 511):
        violations.append(f"V2: phi={phi} outside valid range 0-511")
    if not (0 <= harmonic <= 255):
        violations.append(f"V2: harmonic={harmonic} outside valid range 0-255")

    # --- Criterion 6: TTL (Rule S1 — Shell Temporality) ---
    ttl_ns = compute_liminal_timeout(shell)
    if elapsed_ns >= ttl_ns:
        violations.append(
            f"V7: packet TTL expired — shell={shell} allows {ttl_ns} ns, "
            f"elapsed={elapsed_ns} ns (expired by {elapsed_ns - ttl_ns} ns)"
        )

    # --- Criterion 3: Routing decision arithmetic (Rule S3 — Phi Consent) ---
    if phi < node_phi_min:
        # Correct outcome is BARRIER; note this is not a violation of the packet
        # itself but confirms the node must issue BARRIER.
        violations.append(
            f"V4 (routing violation if not BARRIER): phi={phi} < node.phi_min={node_phi_min} "
            f"— correct decision is BARRIER; any other decision is a routing node violation"
        )
    # If phi >= node_phi_min: ACCEPT or FORWARD is correct; no violation from this packet.

    compliant = len(violations) == 0
    return compliant, violations


# ---------------------------------------------------------------------------
# Helper: build a valid 28-bit address from components
# ---------------------------------------------------------------------------


def make_address(shell: int, theta: int, phi: int, harmonic: int) -> int:
    """Build a valid 28-bit RPP address integer."""
    return encode(shell, theta, phi, harmonic)


# Shell TTL constants (from SHELL_LIMINAL_TIMEOUT_NS)
SHELL0_TTL = SHELL_LIMINAL_TIMEOUT_NS[0]   # 25 ns
SHELL1_TTL = SHELL_LIMINAL_TIMEOUT_NS[1]   # 300_000_000_000 ns  (5 min)
SHELL2_TTL = SHELL_LIMINAL_TIMEOUT_NS[2]   # 86_400_000_000_000 ns (24 h)
SHELL3_TTL = SHELL_LIMINAL_TIMEOUT_NS[3]   # 2_592_000_000_000_000 ns (30 days)


# ===========================================================================
# TestCorrectPackets — valid packets must return (True, [])
# ===========================================================================


class TestCorrectPackets:
    """Packets that satisfy all criteria must return (True, [])."""

    def test_spec_example1_compliant(self):
        """Reproduce spec/CCQPSG.md Example 1 exactly."""
        # Shell=1, theta=96 (Memory), phi=200 (Transitional), harmonic=128 (Enhanced)
        address = (1 << 26) | (96 << 17) | (200 << 8) | 128
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"example payload",
            node_phi_min=100,
            elapsed_ns=5_000_000_000,   # 5 s, within Shell=1 TTL of 300 s
        )
        assert compliant is True
        assert violations == []

    def test_shell1_well_inside_ttl(self):
        """Shell=1 packet with elapsed well inside 300-second TTL."""
        address = make_address(shell=1, theta=64, phi=256, harmonic=96)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"data",
            node_phi_min=0,
            elapsed_ns=1_000_000_000,   # 1 s
        )
        assert compliant is True
        assert violations == []

    def test_shell2_within_24h_ttl(self):
        """Shell=2 packet with elapsed well inside 24-hour TTL."""
        address = make_address(shell=2, theta=128, phi=300, harmonic=160)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"cold storage",
            node_phi_min=200,
            elapsed_ns=3_600_000_000_000,   # 1 hour
        )
        assert compliant is True
        assert violations == []

    def test_shell3_within_30day_ttl(self):
        """Shell=3 packet with elapsed well inside 30-day TTL."""
        address = make_address(shell=3, theta=448, phi=400, harmonic=200)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"frozen archive",
            node_phi_min=100,
            elapsed_ns=86_400_000_000_000,   # 1 day
        )
        assert compliant is True
        assert violations == []

    def test_phi_exactly_at_node_phi_min(self):
        """phi == node_phi_min means ACCEPT/FORWARD (not BARRIER) — compliant."""
        address = make_address(shell=1, theta=32, phi=128, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=128,           # Exactly equal: not a BARRIER scenario
            elapsed_ns=1_000_000_000,
        )
        assert compliant is True
        assert violations == []

    def test_phi_one_above_node_phi_min(self):
        """phi = node_phi_min + 1 is above threshold — compliant."""
        address = make_address(shell=1, theta=96, phi=201, harmonic=128)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"payload",
            node_phi_min=200,
            elapsed_ns=60_000_000_000,   # 60 s
        )
        assert compliant is True
        assert violations == []

    def test_empty_payload_compliant(self):
        """Empty payload is allowed — payload is opaque to routing."""
        address = make_address(shell=1, theta=0, phi=0, harmonic=0)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=1_000_000_000,
        )
        assert compliant is True
        assert violations == []

    def test_node_phi_min_zero_any_phi_passes(self):
        """node_phi_min=0 means every phi value passes the consent gate."""
        for phi in (0, 1, 127, 255, 511):
            address = make_address(shell=1, theta=64, phi=phi, harmonic=64)
            compliant, violations = verify_ccqpsg_compliance(
                address_int=address,
                payload=b"x",
                node_phi_min=0,
                elapsed_ns=1_000_000_000,
            )
            assert compliant is True, f"Expected compliant for phi={phi}"
            assert violations == []

    def test_minimum_valid_address(self):
        """Address 0x0000000 (all zeros) with node_phi_min=0 is compliant."""
        address = 0x0000000
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"min",
            node_phi_min=0,
            elapsed_ns=1,   # 1 ns, within Shell=0 TTL of 25 ns
        )
        assert compliant is True
        assert violations == []

    def test_maximum_valid_address_shell3(self):
        """Address with shell=3, theta=511, phi=511, harmonic=255 — compliant."""
        address = make_address(shell=3, theta=511, phi=511, harmonic=255)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"max",
            node_phi_min=511,   # phi == phi_min: not BARRIER
            elapsed_ns=1_000_000_000_000,
        )
        assert compliant is True
        assert violations == []

    def test_elapsed_zero_is_compliant(self):
        """elapsed_ns=0 is before the TTL for all shells — compliant."""
        address = make_address(shell=0, theta=32, phi=100, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"fresh",
            node_phi_min=0,
            elapsed_ns=0,
        )
        assert compliant is True
        assert violations == []

    def test_shell1_elapsed_one_ns_before_ttl(self):
        """elapsed_ns = TTL - 1 is still valid (boundary just inside)."""
        address = make_address(shell=1, theta=64, phi=200, harmonic=96)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"almost",
            node_phi_min=100,
            elapsed_ns=SHELL1_TTL - 1,
        )
        assert compliant is True
        assert violations == []

    def test_all_four_shells_within_ttl(self):
        """A valid packet for each shell tier returns compliant when well within TTL."""
        cases = [
            (0, 10),                   # Shell=0: 10 ns < 25 ns
            (1, 10_000_000_000),       # Shell=1: 10 s < 300 s
            (2, 3_600_000_000_000),    # Shell=2: 1 h < 24 h
            (3, 86_400_000_000_000),   # Shell=3: 1 day < 30 days
        ]
        for shell, elapsed_ns in cases:
            address = make_address(shell=shell, theta=64, phi=256, harmonic=96)
            compliant, violations = verify_ccqpsg_compliance(
                address_int=address,
                payload=b"ok",
                node_phi_min=0,
                elapsed_ns=elapsed_ns,
            )
            assert compliant is True, f"shell={shell} elapsed={elapsed_ns} should be compliant"
            assert violations == []


# ===========================================================================
# TestV6_TTLViolation — V7: expired TTL causes non-compliance
# ===========================================================================


class TestV6_TTLViolation:
    """
    TTL violations (V7 per Section 6).

    Shell=0 TTL is 25 ns.  Shell=1 TTL is 300_000_000_000 ns (5 min).
    elapsed_ns >= ttl_ns triggers V7.
    """

    def test_spec_example2_expired_shell0(self):
        """Reproduce spec/CCQPSG.md Example 2: Shell=0, elapsed=100 ns (> 25 ns)."""
        address = (0 << 26) | (32 << 17) | (150 << 8) | 64
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=100,
            elapsed_ns=100,   # 100 ns > 25 ns TTL
        )
        assert compliant is False
        assert len(violations) == 1
        assert "V7" in violations[0]

    def test_shell0_expired_at_exactly_25ns(self):
        """elapsed_ns == 25 == SHELL0_TTL triggers V7 (boundary: >= not >)."""
        address = make_address(shell=0, theta=32, phi=150, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=25,   # Equal to TTL: expired
        )
        assert compliant is False
        v7_violations = [v for v in violations if "V7" in v]
        assert len(v7_violations) == 1

    def test_shell0_expired_at_26ns(self):
        """elapsed_ns = 26 > 25 ns Shell=0 TTL."""
        address = make_address(shell=0, theta=10, phi=200, harmonic=32)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"transient",
            node_phi_min=0,
            elapsed_ns=26,
        )
        assert compliant is False
        assert any("V7" in v for v in violations)

    def test_shell1_expired_at_300s_exactly(self):
        """elapsed_ns == 300_000_000_000 == SHELL1_TTL triggers V7."""
        address = make_address(shell=1, theta=96, phi=200, harmonic=128)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"warm",
            node_phi_min=100,
            elapsed_ns=300_000_000_000,   # Exactly at TTL boundary
        )
        assert compliant is False
        assert any("V7" in v for v in violations)

    def test_shell1_expired_at_301s(self):
        """elapsed_ns corresponding to 301 seconds exceeds Shell=1 TTL."""
        address = make_address(shell=1, theta=64, phi=250, harmonic=96)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"data",
            node_phi_min=0,
            elapsed_ns=301_000_000_000,
        )
        assert compliant is False
        assert any("V7" in v for v in violations)

    def test_shell2_expired_after_24h(self):
        """Shell=2 packet expired after exactly 24 hours."""
        address = make_address(shell=2, theta=128, phi=300, harmonic=160)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"cold",
            node_phi_min=0,
            elapsed_ns=SHELL2_TTL,   # Exactly at TTL
        )
        assert compliant is False
        assert any("V7" in v for v in violations)

    def test_shell3_expired_after_30_days(self):
        """Shell=3 packet expired after exactly 30 days."""
        address = make_address(shell=3, theta=448, phi=400, harmonic=200)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"frozen",
            node_phi_min=0,
            elapsed_ns=SHELL3_TTL,   # Exactly at TTL boundary
        )
        assert compliant is False
        assert any("V7" in v for v in violations)

    def test_v7_violation_string_contains_shell_and_elapsed(self):
        """V7 violation message must reference shell tier and elapsed value."""
        address = make_address(shell=1, theta=64, phi=200, harmonic=64)
        elapsed = 400_000_000_000   # 400 s > 300 s Shell=1 TTL
        _, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=elapsed,
        )
        v7 = [v for v in violations if "V7" in v][0]
        assert "shell=1" in v7
        assert str(elapsed) in v7

    def test_shell0_valid_at_24ns(self):
        """Shell=0 at 24 ns is still valid (TTL=25 ns, 24 < 25)."""
        address = make_address(shell=0, theta=32, phi=100, harmonic=32)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=24,
        )
        assert compliant is True
        assert violations == []

    def test_shell1_valid_just_before_300s(self):
        """Shell=1 at 299_999_999_999 ns (just under 300 s) is still valid."""
        address = make_address(shell=1, theta=64, phi=256, harmonic=96)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=299_999_999_999,
        )
        assert compliant is True
        assert violations == []

    def test_expired_packet_reports_only_v7_when_phi_passes(self):
        """When only TTL fails (phi passes), only V7 is reported."""
        address = make_address(shell=0, theta=32, phi=300, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=100,   # phi=300 >= 100: consent gate passes
            elapsed_ns=100,     # Expired for Shell=0
        )
        assert compliant is False
        assert len(violations) == 1
        assert "V7" in violations[0]


# ===========================================================================
# TestConsentGating — phi < node_phi_min must produce V4/BARRIER violation
# ===========================================================================


class TestConsentGating:
    """Rule S3: phi < node_phi_min triggers the BARRIER routing decision (V4)."""

    def test_spec_example3_phi_mismatch(self):
        """Reproduce spec/CCQPSG.md Example 3: phi=80, node_phi_min=200."""
        address = (1 << 26) | (64 << 17) | (80 << 8) | 96
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"blocked payload",
            node_phi_min=200,
            elapsed_ns=1_000_000_000,   # 1 s, within Shell=1 TTL
        )
        assert compliant is False
        assert len(violations) == 1
        assert "V4" in violations[0]
        assert "phi=80" in violations[0]
        assert "node.phi_min=200" in violations[0]

    def test_phi_zero_with_nonzero_phi_min(self):
        """phi=0 is always blocked by any node with phi_min >= 1."""
        address = make_address(shell=1, theta=64, phi=0, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=1,
            elapsed_ns=1_000_000_000,
        )
        assert compliant is False
        assert any("V4" in v for v in violations)

    def test_phi_one_below_phi_min(self):
        """phi = node_phi_min - 1 triggers BARRIER."""
        phi_min = 200
        address = make_address(shell=1, theta=96, phi=phi_min - 1, harmonic=128)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"data",
            node_phi_min=phi_min,
            elapsed_ns=5_000_000_000,
        )
        assert compliant is False
        assert any("V4" in v for v in violations)

    def test_phi_equal_phi_min_is_not_barrier(self):
        """phi == node_phi_min does NOT trigger BARRIER — must be ACCEPT/FORWARD."""
        phi_min = 200
        address = make_address(shell=1, theta=96, phi=phi_min, harmonic=128)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"data",
            node_phi_min=phi_min,
            elapsed_ns=5_000_000_000,
        )
        assert compliant is True
        assert violations == []

    def test_phi_max_511_with_phi_min_511(self):
        """phi=511, node_phi_min=511: exactly equal, not BARRIER."""
        address = make_address(shell=1, theta=64, phi=511, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=511,
            elapsed_ns=1_000_000_000,
        )
        assert compliant is True
        assert violations == []

    def test_phi_510_with_phi_min_511(self):
        """phi=510, node_phi_min=511: one below, triggers BARRIER."""
        address = make_address(shell=1, theta=64, phi=510, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=511,
            elapsed_ns=1_000_000_000,
        )
        assert compliant is False
        assert any("V4" in v for v in violations)

    def test_v4_violation_message_contains_barrier_text(self):
        """V4 violation message must mention BARRIER routing decision."""
        address = make_address(shell=1, theta=64, phi=50, harmonic=64)
        _, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=100,
            elapsed_ns=1_000_000_000,
        )
        v4_msg = [v for v in violations if "V4" in v][0]
        assert "BARRIER" in v4_msg

    def test_various_phi_below_phi_min(self):
        """Multiple phi < node_phi_min combinations all produce V4."""
        cases = [
            (0, 1),
            (1, 2),
            (100, 101),
            (255, 256),
            (0, 511),
        ]
        for phi, phi_min in cases:
            address = make_address(shell=1, theta=64, phi=phi, harmonic=64)
            compliant, violations = verify_ccqpsg_compliance(
                address_int=address,
                payload=b"",
                node_phi_min=phi_min,
                elapsed_ns=1_000_000_000,
            )
            assert compliant is False, f"phi={phi}, phi_min={phi_min} should fail"
            assert any("V4" in v for v in violations)

    def test_consent_violation_only_when_phi_below_min(self):
        """Only phi < node_phi_min produces a V4 violation — not phi > node_phi_min."""
        address = make_address(shell=1, theta=64, phi=300, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=200,
            elapsed_ns=1_000_000_000,
        )
        # phi=300 > phi_min=200: no V4
        assert not any("V4" in v for v in violations)
        assert compliant is True

    def test_high_phi_with_zero_phi_min(self):
        """Any phi value passes when node_phi_min=0."""
        for phi in (0, 1, 255, 511):
            address = make_address(shell=1, theta=64, phi=phi, harmonic=64)
            compliant, violations = verify_ccqpsg_compliance(
                address_int=address,
                payload=b"",
                node_phi_min=0,
                elapsed_ns=1_000_000_000,
            )
            assert compliant is True, f"phi={phi} should pass node_phi_min=0"


# ===========================================================================
# TestBidirectionality — rules hold in both directions per Section 3
# ===========================================================================


class TestBidirectionality:
    """
    Each semantic rule is bidirectional (Section 3 of the spec).
    Tests verify both directions for S1 (Shell Temporality) and S3 (Phi Consent).
    """

    # ---- S1 Bidirectionality: Shell encodes TTL, TTL comes from shell -------

    def test_s1_forward_shell0_means_25ns_ttl(self):
        """IF shell=0 THEN TTL = 25 ns — violation at elapsed=25."""
        address = make_address(shell=0, theta=32, phi=100, harmonic=32)
        compliant, _ = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=25,  # Boundary: expired
        )
        assert compliant is False

    def test_s1_converse_shell0_within_25ns_valid(self):
        """IF TTL not expired (elapsed < 25 ns) THEN shell=0 packet is valid."""
        address = make_address(shell=0, theta=32, phi=100, harmonic=32)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=24,  # Under 25 ns
        )
        assert compliant is True
        assert violations == []

    def test_s1_forward_shell1_300s_ttl(self):
        """IF shell=1 THEN TTL = 300_000_000_000 ns — violation at that boundary."""
        address = make_address(shell=1, theta=64, phi=200, harmonic=64)
        _, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=SHELL1_TTL,
        )
        assert any("V7" in v for v in violations)

    def test_s1_converse_shell1_under_300s_valid(self):
        """IF elapsed < 300 s THEN shell=1 packet is valid (TTL rule respected)."""
        address = make_address(shell=1, theta=64, phi=200, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=SHELL1_TTL - 1,
        )
        assert compliant is True
        assert violations == []

    def test_s1_forward_shell2_24h_ttl(self):
        """IF shell=2 THEN TTL = 86_400 s — violation at that boundary."""
        address = make_address(shell=2, theta=128, phi=200, harmonic=64)
        _, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=SHELL2_TTL,
        )
        assert any("V7" in v for v in violations)

    def test_s1_converse_shell2_under_24h_valid(self):
        """IF elapsed < 24 h THEN shell=2 packet is valid."""
        address = make_address(shell=2, theta=128, phi=200, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=SHELL2_TTL - 1,
        )
        assert compliant is True
        assert violations == []

    # ---- S3 Bidirectionality: phi < phi_min ↔ BARRIER ----------------------

    def test_s3_forward_phi_less_than_phi_min_implies_barrier(self):
        """IF phi < node_phi_min THEN routing must be BARRIER (V4 reported)."""
        phi = 99
        phi_min = 100
        address = make_address(shell=1, theta=64, phi=phi, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=phi_min,
            elapsed_ns=1_000_000_000,
        )
        assert compliant is False
        assert any("V4" in v for v in violations)

    def test_s3_converse_phi_gte_phi_min_no_barrier(self):
        """IF phi >= node_phi_min THEN no BARRIER — V4 is NOT reported."""
        for phi in (100, 200, 511):
            phi_min = 100
            address = make_address(shell=1, theta=64, phi=phi, harmonic=64)
            _, violations = verify_ccqpsg_compliance(
                address_int=address,
                payload=b"",
                node_phi_min=phi_min,
                elapsed_ns=1_000_000_000,
            )
            assert not any("V4" in v for v in violations), \
                f"phi={phi} >= phi_min={phi_min} should not produce V4"

    def test_s3_barrier_only_from_phi_arithmetic(self):
        """The ONLY valid reason for BARRIER is phi < node_phi_min."""
        # A compliant packet (phi >= phi_min, within TTL) should never have V4
        address = make_address(shell=1, theta=64, phi=300, harmonic=96)
        _, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=200,
            elapsed_ns=1_000_000_000,
        )
        assert not any("V4" in v for v in violations)

    def test_s3_no_v4_when_phi_equals_phi_min(self):
        """phi == node_phi_min: ACCEPT/FORWARD, no BARRIER, no V4."""
        phi_min = 150
        address = make_address(shell=1, theta=64, phi=phi_min, harmonic=64)
        _, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=phi_min,
            elapsed_ns=1_000_000_000,
        )
        assert not any("V4" in v for v in violations)


# ===========================================================================
# TestCorrectnessConjunction — ALL criteria must hold simultaneously
# ===========================================================================


class TestCorrectnessConjunction:
    """
    Section 5: CORRECT is conjunctive. A communication satisfying n-1 of n
    criteria is INCORRECT. No partial credit.
    """

    def test_all_six_criteria_met_returns_true(self):
        """When all criteria hold, result is (True, [])."""
        address = make_address(shell=1, theta=96, phi=200, harmonic=128)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"all good",
            node_phi_min=100,
            elapsed_ns=5_000_000_000,
        )
        assert compliant is True
        assert violations == []

    def test_ttl_violation_alone_makes_incorrect(self):
        """TTL failure alone is sufficient to make the packet INCORRECT."""
        address = make_address(shell=0, theta=32, phi=300, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,   # No consent issue
            elapsed_ns=100,   # Expired Shell=0
        )
        assert compliant is False
        assert len(violations) >= 1

    def test_phi_violation_alone_makes_incorrect(self):
        """Phi consent failure alone is sufficient to make the packet INCORRECT."""
        address = make_address(shell=1, theta=64, phi=50, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=100,   # phi=50 < 100
            elapsed_ns=1_000_000_000,   # No TTL issue
        )
        assert compliant is False
        assert len(violations) >= 1

    def test_both_violations_accumulate(self):
        """Both TTL and phi violations accumulate when both criteria fail."""
        # Shell=0 expired + phi below threshold
        address = make_address(shell=0, theta=32, phi=50, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=100,   # phi=50 < 100
            elapsed_ns=100,     # Expired Shell=0
        )
        assert compliant is False
        # Both V7 and V4 should be present
        v7_present = any("V7" in v for v in violations)
        v4_present = any("V4" in v for v in violations)
        assert v7_present, "V7 should be in violations"
        assert v4_present, "V4 should be in violations"
        assert len(violations) == 2

    def test_syntactic_violation_alone_makes_incorrect(self):
        """An address outside 28-bit range alone is sufficient for INCORRECT."""
        compliant, violations = verify_ccqpsg_compliance(
            address_int=0x10000000,   # Exceeds 28 bits
            payload=b"",
            node_phi_min=0,
            elapsed_ns=0,
        )
        assert compliant is False
        assert any("V1" in v for v in violations)

    def test_compliant_false_iff_violations_nonempty(self):
        """The first return value is True if and only if violations is empty."""
        # Compliant case
        address = make_address(shell=1, theta=64, phi=200, harmonic=96)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=100,
            elapsed_ns=1_000_000_000,
        )
        assert compliant == (len(violations) == 0)

        # Non-compliant case
        address = make_address(shell=0, theta=32, phi=50, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=100,
            elapsed_ns=100,
        )
        assert compliant == (len(violations) == 0)
        assert compliant is False

    def test_violation_list_empty_means_compliant(self):
        """An empty violations list always corresponds to compliant=True."""
        address = make_address(shell=2, theta=192, phi=400, harmonic=200)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=200,
            elapsed_ns=3_600_000_000_000,
        )
        if violations:
            assert compliant is False
        else:
            assert compliant is True

    def test_no_partial_credit_ttl_plus_phi(self):
        """No combination of failures results in partial compliance."""
        address = make_address(shell=1, theta=64, phi=10, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=200,
            elapsed_ns=SHELL1_TTL + 1,
        )
        assert compliant is False
        assert len(violations) == 2


# ===========================================================================
# TestDeterminism — same inputs always produce same outputs
# ===========================================================================


class TestDeterminism:
    """
    Section 4.3: The collapse is deterministic, not probabilistic.
    Quantum Parse is epistemic (sender's incomplete knowledge), not random.
    The same inputs must always produce the same outputs.
    """

    def test_repeated_calls_same_inputs_same_output_compliant(self):
        """A compliant packet produces (True, []) on repeated calls."""
        address = make_address(shell=1, theta=96, phi=200, harmonic=128)
        results = [
            verify_ccqpsg_compliance(
                address_int=address,
                payload=b"determinism",
                node_phi_min=100,
                elapsed_ns=5_000_000_000,
            )
            for _ in range(10)
        ]
        assert all(r == (True, []) for r in results)

    def test_repeated_calls_same_inputs_same_output_expired(self):
        """An expired packet produces the same (False, [V7...]) on repeated calls."""
        address = make_address(shell=0, theta=32, phi=200, harmonic=64)
        results = [
            verify_ccqpsg_compliance(
                address_int=address,
                payload=b"",
                node_phi_min=0,
                elapsed_ns=100,
            )
            for _ in range(10)
        ]
        first = results[0]
        assert first[0] is False
        assert all(r == first for r in results)

    def test_repeated_calls_phi_violation(self):
        """A phi-violating packet always produces the same violations."""
        address = make_address(shell=1, theta=64, phi=50, harmonic=64)
        results = [
            verify_ccqpsg_compliance(
                address_int=address,
                payload=b"",
                node_phi_min=100,
                elapsed_ns=1_000_000_000,
            )
            for _ in range(10)
        ]
        first = results[0]
        assert first[0] is False
        assert all(r == first for r in results)

    def test_different_address_different_result(self):
        """Different addresses yield different results when fields differ."""
        addr_compliant = make_address(shell=1, theta=64, phi=200, harmonic=64)
        addr_expired = make_address(shell=0, theta=64, phi=200, harmonic=64)

        result_compliant, _ = verify_ccqpsg_compliance(
            address_int=addr_compliant,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=1_000_000_000,
        )
        result_expired, _ = verify_ccqpsg_compliance(
            address_int=addr_expired,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=100,
        )
        # Different inputs, different outcomes
        assert result_compliant is True
        assert result_expired is False

    def test_output_independent_of_payload_content(self):
        """Routing decision does not depend on payload bytes (payload is opaque)."""
        address = make_address(shell=1, theta=64, phi=200, harmonic=64)
        payloads = [b"", b"a", b"\x00\xff", b"hello world", b"\x01" * 1000]
        results = [
            verify_ccqpsg_compliance(
                address_int=address,
                payload=p,
                node_phi_min=0,
                elapsed_ns=1_000_000_000,
            )
            for p in payloads
        ]
        # All must produce the same compliance decision
        assert all(r[0] is True for r in results), "Payload content should not affect compliance"
        assert all(r[1] == [] for r in results)

    def test_arithmetic_determines_outcome_not_randomness(self):
        """The phi gate outcome is fully determined by the arithmetic."""
        # phi=100, phi_min=100: exactly equal, always ACCEPT
        address = make_address(shell=1, theta=64, phi=100, harmonic=64)
        for _ in range(20):
            compliant, violations = verify_ccqpsg_compliance(
                address_int=address,
                payload=b"",
                node_phi_min=100,
                elapsed_ns=1_000_000_000,
            )
            assert compliant is True
            assert violations == []

        # phi=99, phi_min=100: always BARRIER
        address2 = make_address(shell=1, theta=64, phi=99, harmonic=64)
        for _ in range(20):
            compliant, violations = verify_ccqpsg_compliance(
                address_int=address2,
                payload=b"",
                node_phi_min=100,
                elapsed_ns=1_000_000_000,
            )
            assert compliant is False
            assert any("V4" in v for v in violations)


# ===========================================================================
# TestEdgeCases — boundary values and extreme inputs
# ===========================================================================


class TestEdgeCases:
    """Boundary values, extremes, and interesting corner cases."""

    # ---- Address boundary values -------------------------------------------

    def test_address_zero(self):
        """Address 0x0000000 with elapsed=0 and phi_min=0 is compliant."""
        compliant, violations = verify_ccqpsg_compliance(
            address_int=0,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=0,
        )
        assert compliant is True
        assert violations == []

    def test_address_max_28bit(self):
        """Address 0x0FFFFFFF is the maximum valid 28-bit address."""
        # shell=3, theta=511, phi=511, harmonic=255
        address = 0x0FFFFFFF
        shell, theta, phi, harmonic = decode(address)
        assert shell == 3
        assert theta == 511
        assert phi == 511
        assert harmonic == 255

        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=0,
        )
        assert compliant is True
        assert violations == []

    def test_address_one_above_28bit_is_v1(self):
        """Address 0x10000000 exceeds 28-bit range — V1 violation, early return."""
        compliant, violations = verify_ccqpsg_compliance(
            address_int=0x10000000,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=0,
        )
        assert compliant is False
        assert len(violations) == 1
        assert "V1" in violations[0]

    def test_negative_address_is_v1(self):
        """Negative integer address is V1 — outside 28-bit range."""
        compliant, violations = verify_ccqpsg_compliance(
            address_int=-1,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=0,
        )
        assert compliant is False
        assert any("V1" in v for v in violations)

    def test_non_integer_address_is_v1(self):
        """Non-integer address type triggers V1 — early return."""
        compliant, violations = verify_ccqpsg_compliance(
            address_int="not_an_int",
            payload=b"",
            node_phi_min=0,
            elapsed_ns=0,
        )
        assert compliant is False
        assert len(violations) == 1
        assert "V1" in violations[0]

    # ---- phi boundary values -----------------------------------------------

    def test_phi_zero_node_phi_min_zero(self):
        """phi=0, node_phi_min=0: phi >= phi_min, so ACCEPT (no V4)."""
        address = make_address(shell=1, theta=64, phi=0, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=1_000_000_000,
        )
        assert compliant is True
        assert violations == []

    def test_phi_511_max_value(self):
        """phi=511 is the maximum consent value — always passes phi_min <= 511."""
        address = make_address(shell=1, theta=64, phi=511, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=511,
            elapsed_ns=1_000_000_000,
        )
        assert compliant is True
        assert violations == []

    def test_phi_511_with_phi_min_512_would_be_out_of_range(self):
        """node_phi_min > 511 would always BARRIER any valid packet — test phi=511."""
        # The implementation does not validate node_phi_min range itself,
        # but phi=511 < 512 would trigger V4
        address = make_address(shell=1, theta=64, phi=511, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=512,   # Out-of-spec but tests arithmetic
            elapsed_ns=1_000_000_000,
        )
        # phi=511 < node_phi_min=512 triggers V4
        assert compliant is False
        assert any("V4" in v for v in violations)

    # ---- Shell=3 very long TTL ---------------------------------------------

    def test_shell3_long_ttl_valid_at_29_days(self):
        """Shell=3 packet at 29 days elapsed is still within 30-day TTL."""
        twenty_nine_days_ns = 29 * 86_400 * 1_000_000_000
        address = make_address(shell=3, theta=448, phi=400, harmonic=200)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"frozen",
            node_phi_min=0,
            elapsed_ns=twenty_nine_days_ns,
        )
        assert compliant is True
        assert violations == []

    def test_shell3_expired_at_30_days_exactly(self):
        """Shell=3 TTL = 30 days in ns; expired at exactly that boundary."""
        address = make_address(shell=3, theta=448, phi=400, harmonic=200)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"frozen",
            node_phi_min=0,
            elapsed_ns=SHELL3_TTL,
        )
        assert compliant is False
        assert any("V7" in v for v in violations)

    def test_shell3_expired_at_31_days(self):
        """Shell=3 packet at 31 days elapsed is V7 expired."""
        thirty_one_days_ns = 31 * 86_400 * 1_000_000_000
        address = make_address(shell=3, theta=448, phi=400, harmonic=200)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"frozen",
            node_phi_min=0,
            elapsed_ns=thirty_one_days_ns,
        )
        assert compliant is False
        assert any("V7" in v for v in violations)

    # ---- Return type verification -------------------------------------------

    def test_return_type_is_tuple_of_bool_and_list(self):
        """Return value must be a 2-tuple of (bool, list)."""
        address = make_address(shell=1, theta=64, phi=200, harmonic=64)
        result = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=1_000_000_000,
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        compliant, violations = result
        assert isinstance(compliant, bool)
        assert isinstance(violations, list)

    def test_violations_are_strings(self):
        """Each violation entry must be a string."""
        address = make_address(shell=0, theta=32, phi=50, harmonic=64)
        _, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=100,
            elapsed_ns=100,
        )
        assert len(violations) > 0
        for v in violations:
            assert isinstance(v, str)

    # ---- SHELL_LIMINAL_TIMEOUT_NS constant values --------------------------

    def test_shell0_ttl_constant_is_25ns(self):
        """SHELL_LIMINAL_TIMEOUT_NS[0] must be exactly 25 per spec."""
        assert SHELL_LIMINAL_TIMEOUT_NS[0] == 25

    def test_shell1_ttl_constant_is_300s_in_ns(self):
        """SHELL_LIMINAL_TIMEOUT_NS[1] must be 300 * 1e9 = 300_000_000_000."""
        assert SHELL_LIMINAL_TIMEOUT_NS[1] == 300_000_000_000

    def test_shell2_ttl_constant_is_24h_in_ns(self):
        """SHELL_LIMINAL_TIMEOUT_NS[2] must be 86400 * 1e9."""
        assert SHELL_LIMINAL_TIMEOUT_NS[2] == 86_400_000_000_000

    def test_shell3_ttl_constant_is_30days_in_ns(self):
        """SHELL_LIMINAL_TIMEOUT_NS[3] must be 30 * 86400 * 1e9."""
        assert SHELL_LIMINAL_TIMEOUT_NS[3] == 2_592_000_000_000_000

    def test_compute_liminal_timeout_matches_dict(self):
        """compute_liminal_timeout(n) must return SHELL_LIMINAL_TIMEOUT_NS[n]."""
        for shell in (0, 1, 2, 3):
            assert compute_liminal_timeout(shell) == SHELL_LIMINAL_TIMEOUT_NS[shell]

    # ---- decode/encode round-trip -------------------------------------------

    def test_encode_decode_round_trip(self):
        """encode(decode(x)) == x for all valid field combinations."""
        test_cases = [
            (0, 0, 0, 0),
            (3, 511, 511, 255),
            (1, 96, 200, 128),
            (2, 384, 300, 160),
            (0, 63, 127, 31),
        ]
        for shell, theta, phi, harmonic in test_cases:
            addr = encode(shell, theta, phi, harmonic)
            decoded = decode(addr)
            assert decoded == (shell, theta, phi, harmonic), \
                f"Round-trip failed for ({shell},{theta},{phi},{harmonic})"

    # ---- Large elapsed values -----------------------------------------------

    def test_very_large_elapsed_ns_still_reports_v7(self):
        """Extremely large elapsed value still triggers V7 for any shell."""
        very_large = 10 ** 20   # Vastly larger than any shell TTL
        address = make_address(shell=3, theta=64, phi=200, harmonic=64)
        compliant, violations = verify_ccqpsg_compliance(
            address_int=address,
            payload=b"",
            node_phi_min=0,
            elapsed_ns=very_large,
        )
        assert compliant is False
        assert any("V7" in v for v in violations)
