from dataclasses import dataclass
from math import sqrt

import pandas as pd
from scipy.stats import fisher_exact


@dataclass(frozen=True)
class BinaryProportionComparison:
    """Comparison of binary outcome rates for two independent groups."""

    group_zero_successes: int
    group_zero_total: int
    group_one_successes: int
    group_one_total: int
    group_zero_rate: float
    group_one_rate: float
    absolute_difference: float
    relative_difference_pct: float
    absolute_difference_ci_lower: float
    absolute_difference_ci_upper: float
    p_value: float
    test_name: str


def eligible_for_horizon(
    first_purchase: pd.Timestamp,
    data_end: pd.Timestamp,
    days: int,
) -> bool:
    """Return whether a customer has a complete post-purchase observation window."""
    return data_end >= first_purchase + pd.Timedelta(days=days)


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Return a Wilson confidence interval for a binomial rate."""
    if total <= 0:
        raise ValueError("total must be positive")
    if not 0 <= successes <= total:
        raise ValueError("successes must be between zero and total")
    rate = successes / total
    denominator = 1 + z**2 / total
    center = (rate + z**2 / (2 * total)) / denominator
    margin = z * sqrt(rate * (1 - rate) / total + z**2 / (4 * total**2))
    return center - margin / denominator, center + margin / denominator


def compare_binary_proportions(
    group_zero_successes: int,
    group_zero_total: int,
    group_one_successes: int,
    group_one_total: int,
) -> BinaryProportionComparison:
    """Compare independent binary rates with a Wald difference interval and Fisher test."""
    counts = (
        group_zero_successes,
        group_zero_total,
        group_one_successes,
        group_one_total,
    )
    if any(count < 0 for count in counts):
        raise ValueError("counts must be non-negative")
    if group_zero_total == 0 or group_one_total == 0:
        raise ValueError("both group totals must be positive")
    if group_zero_successes > group_zero_total or group_one_successes > group_one_total:
        raise ValueError("successes cannot exceed totals")

    group_zero_rate = group_zero_successes / group_zero_total
    group_one_rate = group_one_successes / group_one_total
    absolute_difference = group_one_rate - group_zero_rate
    standard_error = sqrt(
        group_zero_rate * (1 - group_zero_rate) / group_zero_total
        + group_one_rate * (1 - group_one_rate) / group_one_total
    )
    p_value = fisher_exact(
        [
            [group_zero_successes, group_zero_total - group_zero_successes],
            [group_one_successes, group_one_total - group_one_successes],
        ],
        alternative="two-sided",
    ).pvalue
    if group_zero_rate == 0:
        relative_difference_pct = float("nan")
    else:
        relative_difference_pct = absolute_difference / group_zero_rate * 100

    return BinaryProportionComparison(
        group_zero_successes=group_zero_successes,
        group_zero_total=group_zero_total,
        group_one_successes=group_one_successes,
        group_one_total=group_one_total,
        group_zero_rate=group_zero_rate,
        group_one_rate=group_one_rate,
        absolute_difference=absolute_difference,
        relative_difference_pct=relative_difference_pct,
        absolute_difference_ci_lower=absolute_difference - 1.96 * standard_error,
        absolute_difference_ci_upper=absolute_difference + 1.96 * standard_error,
        p_value=float(p_value),
        test_name="Fisher's exact test (two-sided)",
    )


def build_retention_matrix(activity: pd.DataFrame) -> pd.DataFrame:
    """Build a dense monthly Cohort matrix and represent absent activity as zero."""
    required = {"customer_key", "cohort_month", "purchase_month"}
    missing = required - set(activity.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    frame = activity.copy()
    for column in ("cohort_month", "purchase_month"):
        frame[column] = pd.to_datetime(frame[column]).dt.to_period("M").dt.to_timestamp()
    frame = frame.drop_duplicates(["customer_key", "cohort_month", "purchase_month"])
    cohort_sizes = frame.groupby("cohort_month")["customer_key"].nunique()
    last_month = frame["purchase_month"].max()
    calendar = pd.concat(
        [
            pd.DataFrame(
                {
                    "cohort_month": cohort_month,
                    "purchase_month": pd.date_range(
                        cohort_month, last_month, freq="MS"
                    ),
                }
            )
            for cohort_month in cohort_sizes.index
        ],
        ignore_index=True,
    )
    retained = (
        frame.groupby(["cohort_month", "purchase_month"])["customer_key"]
        .nunique()
        .rename("retained_customers")
        .reset_index()
    )
    result = calendar.merge(retained, how="left", on=["cohort_month", "purchase_month"])
    result["retained_customers"] = result["retained_customers"].fillna(0).astype(int)
    result["cohort_customers"] = result["cohort_month"].map(cohort_sizes).astype(int)
    result["months_since_cohort"] = (
        (result["purchase_month"].dt.year - result["cohort_month"].dt.year) * 12
        + result["purchase_month"].dt.month
        - result["cohort_month"].dt.month
    )
    result["retention_rate_pct"] = (
        result["retained_customers"] / result["cohort_customers"] * 100
    ).round(3)
    return result.sort_values(["cohort_month", "purchase_month"]).reset_index(drop=True)
