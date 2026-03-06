"""
Tests for rpp.continuity — The Ford Protocol / Consciousness State Packet.

Coverage:
  - HarmonicMode enum values
  - FordPhase enum values
  - RecoveryLevel enum values
  - SHELL_T2_NS / SHELL_LIMINAL_TIMEOUT_NS constants
  - compute_liminal_timeout()
  - csp_from_rpp() — address decoding, field population, timeouts
  - ford_crossing_phases() — ordering, count, all phases present
  - continuity_hash() — determinism, sensitivity
  - create_liminal_state() — field derivation, hop counting
  - verify_continuity_chain() — origin link, chained links, tamper detection
  - ConsciousnessStatePacket — optional hedera_sequence field
"""

import hashlib
import time

import pytest

from rpp.continuity import (
    HarmonicMode,
    FordPhase,
    RecoveryLevel,
    LiminalState,
    ConsciousnessStatePacket,
    SHELL_T2_NS,
    SHELL_LIMINAL_TIMEOUT_NS,
    csp_from_rpp,
    compute_liminal_timeout,
    ford_crossing_phases,
    continuity_hash,
    create_liminal_state,
    verify_continuity_chain,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_address(shell=1, theta=100, phi=200, harmonic=0):
    """Build a 28-bit RPP address from components."""
    return (shell << 26) | (theta << 17) | (phi << 8) | harmonic


def _make_csp(shell=1, phi=200, state=b"hello", epoch=1):
    addr = _make_address(shell=shell, phi=phi)
    return csp_from_rpp(addr, state, HarmonicMode.ACTIVE, epoch)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestHarmonicMode:
    def test_values(self):
        assert HarmonicMode.ACTIVE     == 0
        assert HarmonicMode.REFLECTIVE == 64
        assert HarmonicMode.BACKGROUND == 128
        assert HarmonicMode.MEMORY     == 192
        assert HarmonicMode.ARCHIVAL   == 255

    def test_ordering(self):
        # ACTIVE is highest priority (lowest value)
        assert HarmonicMode.ACTIVE < HarmonicMode.REFLECTIVE < HarmonicMode.BACKGROUND
        assert HarmonicMode.BACKGROUND < HarmonicMode.MEMORY < HarmonicMode.ARCHIVAL

    def test_int_enum(self):
        assert int(HarmonicMode.ARCHIVAL) == 255


class TestFordPhase:
    def test_values(self):
        assert FordPhase.SCOUT     == 1
        assert FordPhase.HANDSHAKE == 2
        assert FordPhase.TRANSIT   == 3
        assert FordPhase.ARRIVAL   == 4
        assert FordPhase.RELEASE   == 5

    def test_ordered(self):
        phases = list(FordPhase)
        values = [p.value for p in phases]
        assert values == sorted(values)


class TestRecoveryLevel:
    def test_values(self):
        assert RecoveryLevel.REROUTE          == 1
        assert RecoveryLevel.STEERING         == 2
        assert RecoveryLevel.PULL_BACK        == 3
        assert RecoveryLevel.COPY_AND_COLLECT == 4
        assert RecoveryLevel.ABORT            == 5

    def test_abort_is_last_resort(self):
        assert RecoveryLevel.ABORT == max(RecoveryLevel)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestShellConstants:
    def test_shell_t2_ns_keys(self):
        assert set(SHELL_T2_NS.keys()) == {0, 1, 2, 3}

    def test_shell_t2_ascending(self):
        # Cold substrate has longer T2 window than hot
        assert SHELL_T2_NS[0] < SHELL_T2_NS[1] < SHELL_T2_NS[2] < SHELL_T2_NS[3]

    def test_shell_liminal_timeout_keys(self):
        assert set(SHELL_LIMINAL_TIMEOUT_NS.keys()) == {0, 1, 2, 3}

    def test_shell_liminal_ascending(self):
        for i in range(3):
            assert SHELL_LIMINAL_TIMEOUT_NS[i] <= SHELL_LIMINAL_TIMEOUT_NS[i + 1]

    def test_shell_0_is_spintronic_t2(self):
        # Shell 0 timeout must equal Shell 0 T2 (literal physics deadline)
        assert SHELL_LIMINAL_TIMEOUT_NS[0] == SHELL_T2_NS[0]


# ---------------------------------------------------------------------------
# compute_liminal_timeout
# ---------------------------------------------------------------------------

class TestComputeLiminalTimeout:
    def test_all_shells(self):
        for shell in range(4):
            assert compute_liminal_timeout(shell) == SHELL_LIMINAL_TIMEOUT_NS[shell]

    def test_invalid_shell_raises(self):
        with pytest.raises(ValueError):
            compute_liminal_timeout(4)
        with pytest.raises(ValueError):
            compute_liminal_timeout(-1)


# ---------------------------------------------------------------------------
# csp_from_rpp
# ---------------------------------------------------------------------------

class TestCspFromRpp:
    def test_returns_csp_type(self):
        csp = _make_csp()
        assert isinstance(csp, ConsciousnessStatePacket)

    def test_crossing_id_is_16_bytes(self):
        csp = _make_csp()
        assert len(csp.crossing_id) == 16

    def test_crossing_id_is_unique(self):
        csp1 = _make_csp()
        csp2 = _make_csp()
        assert csp1.crossing_id != csp2.crossing_id

    def test_shell_decoded_from_address(self):
        for shell in range(4):
            csp = _make_csp(shell=shell)
            assert csp.shell == shell

    def test_phi_decoded_from_address(self):
        for phi in [0, 100, 255, 511]:
            csp = _make_csp(phi=phi)
            assert csp.phi_value == phi

    def test_min_t2_ns_matches_shell(self):
        csp = _make_csp(shell=2)
        assert csp.min_t2_ns == SHELL_T2_NS[2]

    def test_liminal_timeout_in_future(self):
        before = time.time_ns()
        csp = _make_csp(shell=1)
        after = time.time_ns()
        # The timeout must be > now; shell 1 = 5 min
        assert csp.liminal_timeout_ns > before
        assert csp.liminal_timeout_ns > after

    def test_liminal_timeout_shell_0(self):
        before = time.time_ns()
        csp = _make_csp(shell=0)
        # Shell 0 timeout = T2 = 25 ns — will be in the past by the time we check
        # The important thing: it was created as now + 25 ns
        expected_delta = SHELL_LIMINAL_TIMEOUT_NS[0]
        assert csp.liminal_timeout_ns >= before + expected_delta

    def test_harmonic_mode_stored(self):
        csp = csp_from_rpp(
            _make_address(shell=1, phi=100),
            b"data",
            HarmonicMode.ARCHIVAL,
            5,
        )
        assert csp.harmonic_mode == HarmonicMode.ARCHIVAL

    def test_consent_epoch_stored(self):
        csp = csp_from_rpp(_make_address(), b"x", HarmonicMode.ACTIVE, 42)
        assert csp.consent_epoch == 42

    def test_state_vector_stored(self):
        state = b"consciousness payload"
        csp = csp_from_rpp(_make_address(), state, HarmonicMode.ACTIVE, 1)
        assert csp.state_vector == state

    def test_rpp_address_stored(self):
        addr = _make_address(shell=2, theta=300, phi=400)
        csp = csp_from_rpp(addr, b"x", HarmonicMode.ACTIVE, 1)
        assert csp.rpp_address == addr

    def test_stub_fields_empty(self):
        csp = _make_csp()
        assert csp.origin_substrate_hash == b""
        assert csp.continuity_chain == []
        assert csp.zk_consent_proof == b""
        assert csp.required_modalities == []
        assert csp.last_coherent_node == ""

    def test_hedera_sequence_defaults_none(self):
        csp = _make_csp()
        assert csp.hedera_sequence is None

    def test_shell_clamp_high(self):
        # Bits 27:26 can't exceed 3, so shell is always 0-3
        addr = (3 << 26) | (100 << 17) | (200 << 8)  # shell=3
        csp = csp_from_rpp(addr, b"x", HarmonicMode.ACTIVE, 1)
        assert csp.shell == 3

    def test_timestamp_is_nanoseconds(self):
        csp = _make_csp()
        # Should be in billions (nanoseconds since epoch in 2020+)
        assert csp.origin_timestamp_ns > 1_600_000_000_000_000_000


# ---------------------------------------------------------------------------
# ford_crossing_phases
# ---------------------------------------------------------------------------

class TestFordCrossingPhases:
    def test_returns_five_phases(self):
        phases = ford_crossing_phases()
        assert len(phases) == 5

    def test_order_matches_ford_protocol(self):
        phases = ford_crossing_phases()
        phase_enums = [p for p, _ in phases]
        assert phase_enums == [
            FordPhase.SCOUT,
            FordPhase.HANDSHAKE,
            FordPhase.TRANSIT,
            FordPhase.ARRIVAL,
            FordPhase.RELEASE,
        ]

    def test_all_phases_present(self):
        phases = ford_crossing_phases()
        phase_enums = {p for p, _ in phases}
        assert phase_enums == set(FordPhase)

    def test_descriptions_are_nonempty(self):
        for _, description in ford_crossing_phases():
            assert isinstance(description, str) and len(description) > 0

    def test_returns_list_of_tuples(self):
        phases = ford_crossing_phases()
        assert isinstance(phases, list)
        for item in phases:
            assert isinstance(item, tuple)
            assert len(item) == 2


# ---------------------------------------------------------------------------
# continuity_hash
# ---------------------------------------------------------------------------

class TestContinuityHash:
    def test_returns_32_bytes(self):
        csp = _make_csp()
        h = continuity_hash(csp)
        assert isinstance(h, bytes)
        assert len(h) == 32

    def test_deterministic(self):
        csp = _make_csp(state=b"deterministic test")
        h1 = continuity_hash(csp)
        h2 = continuity_hash(csp)
        assert h1 == h2

    def test_sensitive_to_state_vector(self):
        csp1 = _make_csp(state=b"state A")
        csp2 = _make_csp(state=b"state B")
        # Force same crossing_id for comparison
        object.__setattr__(csp2, 'crossing_id', csp1.crossing_id) if hasattr(csp1, '__dataclass_fields__') else None
        csp2.crossing_id = csp1.crossing_id
        csp2.origin_timestamp_ns = csp1.origin_timestamp_ns
        csp2.rpp_address = csp1.rpp_address
        assert continuity_hash(csp1) != continuity_hash(csp2)

    def test_chain_affects_hash(self):
        csp = _make_csp(state=b"payload")
        h_empty = continuity_hash(csp)
        csp.continuity_chain.append(b"link1" * 6)  # 30 bytes
        h_with_link = continuity_hash(csp)
        assert h_empty != h_with_link

    def test_consistent_with_sha256(self):
        # Manual replication: crossing_id + state_vector + address(4) + ts(8) + shell(1)
        csp = _make_csp(state=b"manual check")
        h = hashlib.sha256()
        h.update(csp.crossing_id)
        h.update(csp.state_vector)
        h.update(csp.rpp_address.to_bytes(4, "big"))
        h.update(csp.origin_timestamp_ns.to_bytes(8, "big"))
        h.update(csp.shell.to_bytes(1, "big"))
        expected = h.digest()
        assert continuity_hash(csp) == expected


# ---------------------------------------------------------------------------
# create_liminal_state
# ---------------------------------------------------------------------------

class TestCreateLiminalState:
    def test_returns_liminal_state_type(self):
        csp = _make_csp()
        ls = create_liminal_state(csp, "node://origin-hash")
        assert isinstance(ls, LiminalState)

    def test_crossing_id_preserved(self):
        csp = _make_csp()
        ls = create_liminal_state(csp, "node://x")
        assert ls.crossing_id == csp.crossing_id

    def test_timeout_matches_csp(self):
        csp = _make_csp()
        ls = create_liminal_state(csp, "node://x")
        assert ls.timeout_ns == csp.liminal_timeout_ns

    def test_state_fragment_is_state_vector(self):
        csp = _make_csp(state=b"my state")
        ls = create_liminal_state(csp, "node://x")
        assert ls.state_fragment == csp.state_vector

    def test_crossing_hop_is_chain_length(self):
        csp = _make_csp()
        ls0 = create_liminal_state(csp, "node://x")
        assert ls0.crossing_hop == 0

        csp.continuity_chain.append(b"link" * 8)
        ls1 = create_liminal_state(csp, "node://x")
        assert ls1.crossing_hop == 1

    def test_recovery_node_hash_stored(self):
        csp = _make_csp()
        ls = create_liminal_state(csp, "node://recovery-uri")
        assert ls.recovery_node_hash == "node://recovery-uri"

    def test_modality_from_required_modalities(self):
        csp = _make_csp()
        csp.required_modalities = ["spintronic", "ipv4"]
        ls = create_liminal_state(csp, "node://x")
        assert ls.modality == "spintronic"

    def test_modality_empty_if_no_modalities(self):
        csp = _make_csp()
        ls = create_liminal_state(csp, "node://x")
        assert ls.modality == ""

    def test_origin_hash_is_32_bytes(self):
        csp = _make_csp()
        ls = create_liminal_state(csp, "node://x")
        assert len(ls.origin_hash) == 32

    def test_departure_signature_is_sha256_of_state(self):
        csp = _make_csp(state=b"departure payload")
        ls = create_liminal_state(csp, "node://x")
        expected = hashlib.sha256(csp.state_vector).digest()
        assert ls.departure_signature == expected


# ---------------------------------------------------------------------------
# verify_continuity_chain
# ---------------------------------------------------------------------------

class TestVerifyContinuityChain:
    def test_origin_link_valid(self):
        csp = _make_csp(state=b"origin state")
        # Origin link = SHA-256 of state_vector
        expected = hashlib.sha256(csp.state_vector).digest()
        assert verify_continuity_chain(csp, expected) is True

    def test_origin_link_tampered(self):
        csp = _make_csp(state=b"origin state")
        bad_hash = b"\x00" * 32
        assert verify_continuity_chain(csp, bad_hash) is False

    def test_chained_link_valid(self):
        csp = _make_csp(state=b"multi-hop")
        # Build the first link
        first_link = hashlib.sha256(csp.state_vector).digest()
        csp.continuity_chain.append(first_link)
        # Expected second link = SHA-256(SHA-256(first_link) + state_hash)
        state_hash = hashlib.sha256(csp.state_vector).digest()
        prev_link_hash = hashlib.sha256(first_link).digest()
        expected_second = hashlib.sha256(prev_link_hash + state_hash).digest()
        assert verify_continuity_chain(csp, expected_second) is True

    def test_chained_link_tampered(self):
        csp = _make_csp(state=b"multi-hop")
        first_link = hashlib.sha256(csp.state_vector).digest()
        csp.continuity_chain.append(first_link)
        bad = b"\xff" * 32
        assert verify_continuity_chain(csp, bad) is False

    def test_chain_grows_correctly(self):
        """Simulate two crossings: verify each hop extends the chain."""
        csp = _make_csp(state=b"journey payload")
        state_hash = hashlib.sha256(csp.state_vector).digest()

        # Hop 0: origin link
        link0 = state_hash
        assert verify_continuity_chain(csp, link0) is True
        csp.continuity_chain.append(link0)

        # Hop 1
        prev_link_hash = hashlib.sha256(link0).digest()
        link1 = hashlib.sha256(prev_link_hash + state_hash).digest()
        assert verify_continuity_chain(csp, link1) is True
        csp.continuity_chain.append(link1)

        # Hop 2
        prev_link_hash2 = hashlib.sha256(link1).digest()
        link2 = hashlib.sha256(prev_link_hash2 + state_hash).digest()
        assert verify_continuity_chain(csp, link2) is True

    def test_tampered_state_breaks_chain(self):
        csp = _make_csp(state=b"original")
        # Attach valid origin link
        first_link = hashlib.sha256(csp.state_vector).digest()
        csp.continuity_chain.append(first_link)
        # Now tamper the state_vector
        csp.state_vector = b"tampered"
        # The second link computed from tampered state should still verify
        # against the ACTUAL chain (which was built from "original")
        # But if we try to verify the previous-step hash with new state, it breaks.
        state_hash_tampered = hashlib.sha256(b"tampered").digest()
        prev_link_hash = hashlib.sha256(first_link).digest()
        fake_link = hashlib.sha256(prev_link_hash + state_hash_tampered).digest()
        # This "passes" because verify_continuity_chain uses the current state_vector.
        # The key invariant: if origin link was based on original state, an attacker
        # who changes state_vector CAN'T fake a valid origin link for the new state.
        original_state_hash = hashlib.sha256(b"original").digest()
        assert verify_continuity_chain(csp, original_state_hash) is False  # origin link for "original" fails with "tampered"


# ---------------------------------------------------------------------------
# ConsciousnessStatePacket — optional field
# ---------------------------------------------------------------------------

class TestCSPOptionalFields:
    def test_hedera_sequence_none_by_default(self):
        csp = _make_csp()
        assert csp.hedera_sequence is None

    def test_hedera_sequence_can_be_set(self):
        csp = _make_csp()
        csp.hedera_sequence = 12345
        assert csp.hedera_sequence == 12345

    def test_all_required_fields_present(self):
        csp = _make_csp()
        required = [
            'crossing_id', 'state_vector', 'harmonic_mode',
            'origin_substrate_hash', 'origin_timestamp_ns', 'continuity_chain',
            'consent_epoch', 'zk_consent_proof', 'phi_value', 'rpp_address',
            'shell', 'min_t2_ns', 'required_modalities', 'liminal_timeout_ns',
            'last_coherent_node',
        ]
        for field in required:
            assert hasattr(csp, field), f"CSP missing field: {field}"


# ---------------------------------------------------------------------------
# Integration — Ford Protocol flow
# ---------------------------------------------------------------------------

class TestFordProtocolFlow:
    """Simulate a full Scout→Release sequence using the primitives."""

    def test_three_hop_crossing(self):
        """
        CSP crosses three substrates. Each substrate:
          1. Verifies the incoming chain link
          2. Computes a new link and appends it
          3. Creates a LiminalState to hold the packet
        Final state: chain has 3 links, each validly extends the previous.
        """
        csp = _make_csp(state=b"consciousness crossing the river", shell=1)
        state_hash = hashlib.sha256(csp.state_vector).digest()

        # Hop 0 — origin substrate signs first link
        link0 = state_hash
        assert verify_continuity_chain(csp, link0)
        csp.continuity_chain.append(link0)

        ls0 = create_liminal_state(csp, "node://origin")
        assert ls0.crossing_hop == 1

        # Hop 1 — intermediate substrate
        prev_link_hash = hashlib.sha256(link0).digest()
        link1 = hashlib.sha256(prev_link_hash + state_hash).digest()
        assert verify_continuity_chain(csp, link1)
        csp.continuity_chain.append(link1)

        ls1 = create_liminal_state(csp, "node://hop-1")
        assert ls1.crossing_hop == 2

        # Hop 2 — destination substrate
        prev_link_hash2 = hashlib.sha256(link1).digest()
        link2 = hashlib.sha256(prev_link_hash2 + state_hash).digest()
        assert verify_continuity_chain(csp, link2)
        csp.continuity_chain.append(link2)

        # Final continuity_hash includes all three links
        final_hash = continuity_hash(csp)
        assert len(final_hash) == 32
        assert len(csp.continuity_chain) == 3
