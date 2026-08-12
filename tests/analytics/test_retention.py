import pandas as pd

from src.analytics.retention import (
    build_retention_matrix,
    compare_binary_proportions,
    eligible_for_horizon,
    wilson_interval,
)


def test_customer_without_full_horizon_is_excluded():
    first_purchase = pd.Timestamp("2018-07-01")
    data_end = pd.Timestamp("2018-08-31")

    assert eligible_for_horizon(first_purchase, data_end, days=90) is False


def test_customer_with_exactly_full_horizon_is_eligible():
    first_purchase = pd.Timestamp("2018-06-02")
    data_end = pd.Timestamp("2018-08-31")

    assert eligible_for_horizon(first_purchase, data_end, days=90) is True


def test_retention_matrix_fills_zero_activity_months():
    activity = pd.DataFrame(
        {
            "customer_key": [1, 1, 2],
            "cohort_month": pd.to_datetime(["2018-01-01"] * 3),
            "purchase_month": pd.to_datetime(
                ["2018-01-01", "2018-03-01", "2018-01-01"]
            ),
        }
    )

    matrix = build_retention_matrix(activity)

    assert matrix["retained_customers"].tolist() == [2, 0, 1]
    assert matrix["retention_rate_pct"].tolist() == [100.0, 0.0, 50.0]


def test_wilson_interval_bounds_a_rate():
    lower, upper = wilson_interval(successes=15, total=100)

    assert 0 < lower < 0.15 < upper < 1


def test_binary_proportion_comparison_reports_difference_interval_and_test():
    result = compare_binary_proportions(
        group_zero_successes=20,
        group_zero_total=100,
        group_one_successes=10,
        group_one_total=100,
    )

    assert result.group_zero_rate == 0.2
    assert result.group_one_rate == 0.1
    assert result.absolute_difference == -0.1
    assert result.relative_difference_pct == -50.0
    assert result.absolute_difference_ci_lower < result.absolute_difference
    assert result.absolute_difference_ci_upper > result.absolute_difference
    assert 0.0 <= result.p_value <= 1.0
    assert result.test_name == "Fisher's exact test (two-sided)"
