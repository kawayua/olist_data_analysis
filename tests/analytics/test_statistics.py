import numpy as np
import pytest

from src.analytics.statistics import compare_binary_groups


def test_group_comparison_reports_effect_direction():
    result = compare_binary_groups(
        values=np.array([1.0, 2.0, 8.0, 9.0]),
        groups=np.array([0, 0, 1, 1]),
    )

    assert result.group_one_median > result.group_zero_median
    assert 0.0 <= result.p_value <= 1.0


def test_group_comparison_detects_clearly_separated_groups():
    result = compare_binary_groups(
        values=np.array([1.0, 2.0, 3.0, 4.0, 10.0, 11.0, 12.0, 13.0]),
        groups=np.array([0, 0, 0, 0, 1, 1, 1, 1]),
    )

    assert result.p_value < 0.05
    assert result.rank_biserial_correlation == 1.0


def test_group_comparison_reports_no_rank_advantage_for_identical_groups():
    result = compare_binary_groups(
        values=np.array([1.0, 2.0, 3.0, 4.0, 1.0, 2.0, 3.0, 4.0]),
        groups=np.array([0, 0, 0, 0, 1, 1, 1, 1]),
    )

    assert result.p_value == 1.0
    assert result.rank_biserial_correlation == 0.0


def test_group_comparison_rejects_a_missing_binary_group():
    with pytest.raises(ValueError, match="both binary groups"):
        compare_binary_groups(
            values=np.array([1.0, 2.0, 3.0]),
            groups=np.array([0, 0, 0]),
        )


def test_group_comparison_reports_magnitude_and_uncertainty():
    result = compare_binary_groups(
        values=np.array([2.0, 4.0, 6.0, 8.0, 6.0, 8.0, 10.0, 12.0]),
        groups=np.array([0, 0, 0, 0, 1, 1, 1, 1]),
    )

    assert result.group_zero_count == 4
    assert result.group_one_count == 4
    assert result.median_difference == 4.0
    assert result.relative_median_difference_pct == 80.0
    assert result.median_difference_ci_lower <= result.median_difference
    assert result.median_difference_ci_upper >= result.median_difference
    assert result.test_name == "Mann-Whitney U (two-sided)"


def test_group_comparison_rejects_mismatched_value_and_group_lengths():
    with pytest.raises(ValueError, match="same length"):
        compare_binary_groups(
            values=np.array([1.0, 2.0, 3.0]),
            groups=np.array([0, 1]),
        )
