from dataclasses import dataclass

import numpy as np
from scipy.stats import mannwhitneyu


@dataclass(frozen=True)
class GroupComparison:
    """Minimal summary of a comparison between binary groups."""

    group_zero_count: int
    group_one_count: int
    group_zero_median: float
    group_one_median: float
    median_difference: float
    relative_median_difference_pct: float
    median_difference_ci_lower: float
    median_difference_ci_upper: float
    p_value: float
    rank_biserial_correlation: float
    test_name: str


def _bootstrap_median_difference_interval(
    group_zero: np.ndarray,
    group_one: np.ndarray,
    resamples: int = 2_000,
) -> tuple[float, float]:
    """Return a deterministic percentile bootstrap 95% interval."""
    generator = np.random.default_rng(seed=0)
    differences = np.empty(resamples)
    for index in range(resamples):
        zero_sample = generator.choice(group_zero, size=len(group_zero), replace=True)
        one_sample = generator.choice(group_one, size=len(group_one), replace=True)
        differences[index] = np.median(one_sample) - np.median(zero_sample)
    lower, upper = np.percentile(differences, [2.5, 97.5])
    return float(lower), float(upper)


def compare_binary_groups(values: np.ndarray, groups: np.ndarray) -> GroupComparison:
    """Compare the medians of observations labelled with binary group values."""
    if len(values) != len(groups):
        raise ValueError("values and groups must have the same length")
    group_zero = values[groups == 0]
    group_one = values[groups == 1]
    if len(group_zero) == 0 or len(group_one) == 0:
        raise ValueError("both binary groups must contain at least one value")
    test_result = mannwhitneyu(group_zero, group_one, alternative="two-sided")
    rank_biserial_correlation = 1 - (
        2 * float(test_result.statistic) / (len(group_zero) * len(group_one))
    )
    group_zero_median = float(np.median(group_zero))
    group_one_median = float(np.median(group_one))
    median_difference = group_one_median - group_zero_median
    if group_zero_median == 0:
        relative_median_difference_pct = float("nan")
    else:
        relative_median_difference_pct = median_difference / group_zero_median * 100
    ci_lower, ci_upper = _bootstrap_median_difference_interval(group_zero, group_one)
    return GroupComparison(
        group_zero_count=len(group_zero),
        group_one_count=len(group_one),
        group_zero_median=group_zero_median,
        group_one_median=group_one_median,
        median_difference=median_difference,
        relative_median_difference_pct=relative_median_difference_pct,
        median_difference_ci_lower=ci_lower,
        median_difference_ci_upper=ci_upper,
        p_value=float(test_result.pvalue),
        rank_biserial_correlation=rank_biserial_correlation,
        test_name="Mann-Whitney U (two-sided)",
    )
