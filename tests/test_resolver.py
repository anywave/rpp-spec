"""
RPP Resolver Test Suite

Tests for the rpp.resolver module.
Validates the three core scenarios:
1. Allowed read (low phi)
2. Denied write (high phi)
3. Routed to archive (cold shell)
"""

import pytest

from rpp.address import from_components
from rpp.resolver import (
    RPPResolver,
    ResolveResult,
    resolve,
    get_resolver,
)
from rpp.adapters.memory import MemoryAdapter


class TestResolveResult:
    """Test ResolveResult dataclass."""

    def test_allowed_result(self):
        """Test creating an allowed result."""
        result = ResolveResult(
            allowed=True,
            route="memory://gene/grounded/12_40_1",
            reason="read permitted via memory",
        )
        assert result.allowed is True
        assert result.route is not None
        assert "permitted" in result.reason

    def test_denied_result(self):
        """Test creating a denied result."""
        result = ResolveResult(
            allowed=False,
            route=None,
            reason="Write blocked",
        )
        assert result.allowed is False
        assert result.route is None

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = ResolveResult(
            allowed=True,
            route="filesystem://memory/transitional/100_200_64",
            reason="test",
        )
        d = result.to_dict()
        assert d["allowed"] is True
        assert d["route"] == "filesystem://memory/transitional/100_200_64"
        assert d["reason"] == "test"

    def test_to_line(self):
        """Test line format (for terminal output)."""
        result = ResolveResult(
            allowed=True,
            route="test_route",
            reason="test reason",
        )
        line = result.to_line()
        assert "allowed=True" in line
        assert "route=test_route" in line
        assert "reason=test reason" in line

    def test_to_line_null_route(self):
        """Test line format with null route."""
        result = ResolveResult(allowed=False, route=None, reason="denied")
        line = result.to_line()
        assert "route=null" in line


class TestRPPResolver:
    """Test RPPResolver class."""

    def test_create_resolver(self):
        """Test resolver creation."""
        resolver = RPPResolver()
        assert resolver is not None

    def test_register_adapter(self):
        """Test registering an adapter."""
        resolver = RPPResolver()
        adapter = MemoryAdapter()
        resolver.register_adapter(0, adapter)

    def test_register_adapter_invalid_shell(self):
        """Test registering adapter with invalid shell."""
        resolver = RPPResolver()
        adapter = MemoryAdapter()
        with pytest.raises(ValueError):
            resolver.register_adapter(4, adapter)

    def test_resolve_invalid_address(self):
        """Test resolving invalid address."""
        resolver = RPPResolver()
        result = resolver.resolve(-1)
        assert result.allowed is False
        assert "Invalid" in result.reason


class TestCoreScenarios:
    """Test the three core scenarios that define RPP behavior."""

    def test_scenario_1_allowed_read_low_phi(self):
        """
        Scenario 1: Allowed read with low phi.

        Low phi (grounded) + read operation = ALLOWED
        """
        # Create address with low phi (grounded zone)
        addr = from_components(shell=0, theta=12, phi=40, harmonic=1)

        result = resolve(addr.raw, operation="read")

        assert result.allowed is True
        assert result.route is not None
        assert "memory" in result.route.lower()

    def test_scenario_2_denied_write_high_phi(self):
        """
        Scenario 2: Denied write with high phi.

        High phi (ethereal) + write operation = DENIED (requires consent)
        """
        # Create address with high phi (ethereal zone)
        addr = from_components(shell=0, theta=100, phi=450, harmonic=64)

        result = resolve(addr.raw, operation="write")

        assert result.allowed is False
        assert result.route is None
        assert "consent" in result.reason.lower() or "ethereal" in result.reason.lower()

    def test_scenario_2_allowed_write_high_phi_with_consent(self):
        """
        Scenario 2b: Allowed write with high phi when consent provided.
        """
        addr = from_components(shell=0, theta=100, phi=450, harmonic=64)

        result = resolve(addr.raw, operation="write", context={"consent": "explicit"})

        assert result.allowed is True
        assert result.route is not None

    def test_scenario_3_routed_to_archive(self):
        """
        Scenario 3: Routed to archive with cold shell.

        Cold shell (shell=2) = routes to archive backend
        """
        # Create address with cold shell
        addr = from_components(shell=2, theta=200, phi=128, harmonic=32)

        result = resolve(addr.raw, operation="read")

        assert result.allowed is True
        assert result.route is not None
        assert "archive" in result.route.lower()


class TestConsentGating:
    """Test consent-based access gating."""

    def test_low_phi_no_consent_required(self):
        """Low phi should not require consent for reads."""
        addr = from_components(0, 100, 50, 128)  # phi=50 (grounded)
        result = resolve(addr.raw, operation="read")
        assert result.allowed is True

    def test_high_phi_write_denied(self):
        """High phi writes should be denied without consent."""
        addr = from_components(0, 100, 400, 128)  # phi=400 (ethereal)
        result = resolve(addr.raw, operation="write")
        assert result.allowed is False

    def test_high_phi_read_allowed(self):
        """High phi reads should still be allowed."""
        addr = from_components(0, 100, 400, 128)
        result = resolve(addr.raw, operation="read")
        assert result.allowed is True

    def test_very_high_phi_emergency_only(self):
        """Very high phi (>=480) requires emergency override for writes."""
        addr = from_components(0, 100, 490, 128)

        # Without emergency
        result1 = resolve(addr.raw, operation="write", context={"consent": "explicit"})
        assert result1.allowed is False

        # With emergency
        result2 = resolve(addr.raw, operation="write", context={"emergency_override": True})
        assert result2.allowed is True


class TestShellRouting:
    """Test routing based on shell value."""

    def test_shell_0_routes_to_memory(self):
        """Shell 0 (hot) should route to memory backend."""
        addr = from_components(0, 100, 100, 100)
        result = resolve(addr.raw)
        assert "memory" in result.route.lower()

    def test_shell_1_routes_to_filesystem(self):
        """Shell 1 (warm) should route to filesystem backend."""
        addr = from_components(1, 100, 100, 100)
        result = resolve(addr.raw)
        assert "filesystem" in result.route.lower()

    def test_shell_2_routes_to_archive(self):
        """Shell 2 (cold) should route to archive backend."""
        addr = from_components(2, 100, 100, 100)
        result = resolve(addr.raw)
        assert "archive" in result.route.lower()

    def test_shell_3_routes_to_glacier(self):
        """Shell 3 (frozen) should route to glacier backend."""
        addr = from_components(3, 100, 100, 100)
        result = resolve(addr.raw)
        assert "glacier" in result.route.lower()


class TestPathConstruction:
    """Test path construction from address."""

    def test_path_includes_sector(self):
        """Path should include sector name."""
        addr = from_components(0, 96, 100, 100)  # Memory sector
        result = resolve(addr.raw)
        assert "memory" in result.route.lower()

    def test_path_includes_grounding(self):
        """Path should include grounding level."""
        addr = from_components(0, 100, 64, 100)  # Grounded level
        result = resolve(addr.raw)
        assert "grounded" in result.route.lower()

    def test_path_includes_coordinates(self):
        """Path should include theta_phi_harmonic."""
        addr = from_components(0, 100, 64, 50)
        result = resolve(addr.raw)
        assert "100_64_50" in result.route


class TestModuleLevelResolve:
    """Test module-level resolve function."""

    def test_resolve_function_exists(self):
        """Test that resolve function is available at module level."""
        from rpp import resolve as rpp_resolve
        assert callable(rpp_resolve)

    def test_resolve_returns_result(self):
        """Test that resolve returns a ResolveResult."""
        addr = from_components(0, 100, 100, 100)
        result = resolve(addr.raw)
        assert isinstance(result, ResolveResult)

    def test_get_resolver_singleton(self):
        """Test that get_resolver returns same instance."""
        r1 = get_resolver()
        r2 = get_resolver()
        assert r1 is r2


class TestDeterminism:
    """Test that resolution is deterministic."""

    def test_same_input_same_output(self):
        """Same address should always produce same result."""
        addr = from_components(1, 200, 300, 128)

        result1 = resolve(addr.raw)
        result2 = resolve(addr.raw)

        assert result1.allowed == result2.allowed
        assert result1.route == result2.route
        assert result1.reason == result2.reason

    def test_encode_decode_resolve_roundtrip(self):
        """Encode-decode-resolve should be deterministic."""
        from rpp.address import encode

        for shell in range(4):
            for theta in [0, 100, 300, 511]:
                for phi in [0, 127, 256, 511]:
                    addr = encode(shell, theta, phi, 128)
                    result = resolve(addr)
                    assert isinstance(result.allowed, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
