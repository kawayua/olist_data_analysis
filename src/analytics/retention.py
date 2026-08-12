from math import sqrt

import pandas as pd


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
