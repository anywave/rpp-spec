"""
Tests for Coherence Module
==========================

Validates Ra-symbolic coherence computation.
"""

import pytest

from rpp.coherence import (
    ComplecountState,
    CoherenceResult,
    compute_coherence_score,
    compute_binding_coefficient,
    is_binding_valid,
    compute_complecount,
    get_complecount_state,
    compute_coherence,
    score_to_percentage,
    percentage_to_score,
    minimum_binding_score,
    describe_coherence,
)
from rpp.ra_constants import (
    GREEN_PHI_SCALED,
    ANKH_SCALED,
    MAX_COHERENCE,
    BINDING_THRESHOLD,
    ALPHA_INV_SCALED,
)


class TestComplecountState:
    """Tests for ComplecountState enum."""

    def test_state_values(self):
        """Complecount states should have correct values."""
        assert ComplecountState.FRAGMENTED == 0
        assert ComplecountState.EMERGING == 1
        assert ComplecountState.DEVELOPING == 2
        assert ComplecountState.STABILIZING == 3
        assert ComplecountState.CONSOLIDATING == 4
        assert ComplecountState.MATURING == 5
        assert ComplecountState.COHERING == 6
        assert ComplecountState.COMPLETE == 7

    def test_state_count(self):
        """Should have exactly 8 states (0-7)."""
        assert len(ComplecountState) == 8


class TestComputeCoherenceScore:
    """Tests for coherence score computation."""

    def test_zero_inputs(self):
        """Zero engagement and completion gives zero score."""
        assert compute_coherence_score(0.0, 0.0) == 0

    def test_full_inputs(self):
        """Full engagement and completion gives max score."""
        score = compute_coherence_score(1.0, 1.0)
        assert score == MAX_COHERENCE
        assert score == 674

    def test_engagement_only(self):
        """Full engagement, zero completion."""
        score = compute_coherence_score(1.0, 0.0)
        assert score == GREEN_PHI_SCALED
        assert score == 165

    def test_completion_only(self):
        """Zero engagement, full completion."""
        score = compute_coherence_score(0.0, 1.0)
        assert score == ANKH_SCALED
        assert score == 509

    def test_half_values(self):
        """Half engagement and completion."""
        score = compute_coherence_score(0.5, 0.5)
        expected = (GREEN_PHI_SCALED // 2) + (ANKH_SCALED // 2)
        assert score == expected

    def test_input_clamping(self):
        """Inputs outside 0-1 should be clamped."""
        # Negative values clamped to 0
        assert compute_coherence_score(-0.5, 0.5) == compute_coherence_score(0.0, 0.5)
        # Values > 1 clamped to 1
        assert compute_coherence_score(1.5, 0.5) == compute_coherence_score(1.0, 0.5)

    def test_score_bounds(self):
        """Score should always be 0-674."""
        for e in [0.0, 0.25, 0.5, 0.75, 1.0]:
            for c in [0.0, 0.25, 0.5, 0.75, 1.0]:
                score = compute_coherence_score(e, c)
                assert 0 <= score <= MAX_COHERENCE


class TestBindingCoefficient:
    """Tests for binding coefficient computation."""

    def test_zero_score(self):
        """Zero score gives zero coefficient."""
        assert compute_binding_coefficient(0) == 0.0

    def test_max_score(self):
        """Max score gives coefficient of 1.0."""
        assert compute_binding_coefficient(MAX_COHERENCE) == 1.0

    def test_mid_score(self):
        """Mid score gives coefficient of 0.5."""
        mid_score = MAX_COHERENCE // 2
        coef = compute_binding_coefficient(mid_score)
        assert abs(coef - 0.5) < 0.01

    def test_threshold_score(self):
        """Score at threshold boundary."""
        threshold_score = ALPHA_INV_SCALED
        coef = compute_binding_coefficient(threshold_score)
        assert abs(coef - BINDING_THRESHOLD) < 0.001

    def test_coefficient_bounds(self):
        """Coefficient should always be 0-1."""
        for score in range(0, MAX_COHERENCE + 1, 50):
            coef = compute_binding_coefficient(score)
            assert 0.0 <= coef <= 1.0


class TestIsBindingValid:
    """Tests for binding validity check."""

    def test_below_threshold(self):
        """Binding below threshold is invalid."""
        assert is_binding_valid(0.1) is False
        assert is_binding_valid(0.2) is False

    def test_at_threshold(self):
        """Binding at threshold is valid."""
        assert is_binding_valid(BINDING_THRESHOLD) is True

    def test_above_threshold(self):
        """Binding above threshold is valid."""
        assert is_binding_valid(0.3) is True
        assert is_binding_valid(0.5) is True
        assert is_binding_valid(1.0) is True

    def test_threshold_value(self):
        """Threshold should be approximately 0.203."""
        assert abs(BINDING_THRESHOLD - 0.203) < 0.001


class TestComputeComplecount:
    """Tests for complecount computation."""

    def test_zero_score(self):
        """Zero score gives complecount 0."""
        assert compute_complecount(0) == 0

    def test_max_score(self):
        """Max score gives complecount 7."""
        assert compute_complecount(MAX_COHERENCE) == 7

    def test_complecount_bounds(self):
        """Complecount should always be 0-7."""
        for score in range(0, MAX_COHERENCE + 1, 50):
            cc = compute_complecount(score)
            assert 0 <= cc <= 7

    def test_complecount_progression(self):
        """Complecount should increase with score."""
        prev_cc = -1
        for score in range(0, MAX_COHERENCE + 1, 100):
            cc = compute_complecount(score)
            assert cc >= prev_cc
            prev_cc = cc


class TestGetComplecountState:
    """Tests for complecount state mapping."""

    def test_state_mapping(self):
        """Each complecount value maps to correct state."""
        assert get_complecount_state(0) == ComplecountState.FRAGMENTED
        assert get_complecount_state(1) == ComplecountState.EMERGING
        assert get_complecount_state(2) == ComplecountState.DEVELOPING
        assert get_complecount_state(3) == ComplecountState.STABILIZING
        assert get_complecount_state(4) == ComplecountState.CONSOLIDATING
        assert get_complecount_state(5) == ComplecountState.MATURING
        assert get_complecount_state(6) == ComplecountState.COHERING
        assert get_complecount_state(7) == ComplecountState.COMPLETE

    def test_clamping(self):
        """Out of range values should be clamped."""
        assert get_complecount_state(-1) == ComplecountState.FRAGMENTED
        assert get_complecount_state(10) == ComplecountState.COMPLETE


class TestComputeCoherence:
    """Tests for high-level coherence computation."""

    def test_zero_coherence(self):
        """Zero inputs produce fragmented state."""
        result = compute_coherence(0.0, 0.0)
        assert result.score == 0
        assert result.complecount == 0
        assert result.state == ComplecountState.FRAGMENTED
        assert result.is_binding_valid is False
        assert result.completion_flag is False

    def test_full_coherence(self):
        """Full inputs produce complete state."""
        result = compute_coherence(1.0, 1.0)
        assert result.score == MAX_COHERENCE
        assert result.complecount == 7
        assert result.state == ComplecountState.COMPLETE
        assert result.is_binding_valid is True
        assert result.completion_flag is True

    def test_completion_flag(self):
        """Completion flag only triggers at complecount 7."""
        # Below complete
        result = compute_coherence(0.8, 0.8)
        assert result.completion_flag is False

        # At complete
        result = compute_coherence(1.0, 1.0)
        assert result.completion_flag is True

    def test_component_weights(self):
        """Engagement and completion weights are tracked."""
        result = compute_coherence(1.0, 1.0)
        assert result.engagement_weight == GREEN_PHI_SCALED
        assert result.completion_weight == ANKH_SCALED

        result = compute_coherence(0.5, 0.5)
        assert result.engagement_weight == GREEN_PHI_SCALED // 2
        assert result.completion_weight == ANKH_SCALED // 2

    def test_result_immutability(self):
        """CoherenceResult should be immutable."""
        result = compute_coherence(0.5, 0.5)
        with pytest.raises(AttributeError):
            result.score = 999

    def test_binding_threshold_boundary(self):
        """Test behavior around binding threshold."""
        # Just below threshold
        result = compute_coherence(0.2, 0.2)
        # Score = ~33 + ~102 = ~135, below 137
        if result.score < ALPHA_INV_SCALED:
            assert result.is_binding_valid is False

        # At threshold
        result = compute_coherence(0.21, 0.21)
        if result.score >= ALPHA_INV_SCALED:
            assert result.is_binding_valid is True


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_score_to_percentage(self):
        """Score to percentage conversion."""
        assert score_to_percentage(0) == 0.0
        assert score_to_percentage(MAX_COHERENCE) == 100.0
        assert abs(score_to_percentage(337) - 50.0) < 0.5

    def test_percentage_to_score(self):
        """Percentage to score conversion."""
        assert percentage_to_score(0.0) == 0
        assert percentage_to_score(100.0) == MAX_COHERENCE
        assert abs(percentage_to_score(50.0) - 337) < 2

    def test_percentage_clamping(self):
        """Percentages should be clamped."""
        assert percentage_to_score(-10.0) == 0
        assert percentage_to_score(150.0) == MAX_COHERENCE

    def test_minimum_binding_score(self):
        """Minimum binding score should be 137."""
        assert minimum_binding_score() == ALPHA_INV_SCALED
        assert minimum_binding_score() == 137


class TestDescribeCoherence:
    """Tests for coherence description."""

    def test_describe_fragmented(self):
        """Description for fragmented state."""
        result = compute_coherence(0.1, 0.1)
        desc = describe_coherence(result)
        assert "FRAGMENTED" in desc
        assert "threshold" in desc.lower()

    def test_describe_bound(self):
        """Description for bound state."""
        result = compute_coherence(0.5, 0.5)
        desc = describe_coherence(result)
        assert "BOUND" in desc

    def test_describe_complete(self):
        """Description for complete state."""
        result = compute_coherence(1.0, 1.0)
        desc = describe_coherence(result)
        assert "COMPLETE" in desc
        assert "674" in desc or "100" in desc


class TestCoherenceFormula:
    """Tests validating the Ra-symbolic coherence formula."""

    def test_formula_max_coherence(self):
        """(φ × E) + (𝔄 × C) = 674 at max."""
        # GREEN_PHI_SCALED (165) + ANKH_SCALED (509) = 674
        assert GREEN_PHI_SCALED + ANKH_SCALED == MAX_COHERENCE
        assert MAX_COHERENCE == 674

    def test_formula_components(self):
        """Verify formula components."""
        # φ component: GREEN_PHI_SCALED = 165
        assert GREEN_PHI_SCALED == 165

        # 𝔄 component: ANKH_SCALED = 509
        assert ANKH_SCALED == 509

    def test_binding_formula(self):
        """Binding threshold = α⁻¹ / MAX = 137/674."""
        expected = 137 / 674
        assert abs(BINDING_THRESHOLD - expected) < 0.001
