"""Deterministic RFM scoring rules for customer analytics."""

import numpy as np
import pandas as pd


def _score_quartiles(values: pd.Series, higher_is_better: bool) -> pd.Series:
    p25, p50, p75 = values.quantile([0.25, 0.50, 0.75])
    if higher_is_better:
        conditions = [values <= p25, values <= p50, values <= p75]
        choices = [1, 2, 3]
        default = 4
    else:
        conditions = [values <= p25, values <= p50, values <= p75]
        choices = [4, 3, 2]
        default = 1
    return pd.Series(np.select(conditions, choices, default=default), index=values.index)


def score_recency(values: pd.Series) -> pd.Series:
    """Score recency in quartiles; fewer days since purchase is better."""
    return _score_quartiles(values, higher_is_better=False).astype("int64")


def assign_rfm_segments(
    frame: pd.DataFrame, as_of_date: pd.Timestamp
) -> pd.DataFrame:
    """Add RFM scores and an explainable business segment to customer features."""
    result = frame.copy()
    result["recency_days"] = (
        pd.Timestamp(as_of_date).normalize()
        - pd.to_datetime(result["last_purchase_at"]).dt.normalize()
    ).dt.days
    result["r_score"] = score_recency(result["recency_days"])
    result["f_score"] = np.select(
        [result["frequency_orders"].eq(1), result["frequency_orders"].eq(2)],
        [1, 2],
        default=3,
    )
    result["m_score"] = _score_quartiles(
        result["monetary_item_revenue"], higher_is_better=True
    ).astype("int64")
    result["customer_segment"] = np.select(
        [
            (result["r_score"] >= 3)
            & (result["f_score"] >= 2)
            & (result["m_score"] >= 3),
            (result["r_score"] >= 3)
            & (result["f_score"] == 1)
            & (result["m_score"] >= 3),
            (result["r_score"] <= 2) & (result["m_score"] >= 3),
            (result["f_score"] == 1) & (result["m_score"] <= 2),
        ],
        ["high_value", "potential", "needs_attention", "one_time_low_value"],
        default="standard",
    )
    return result
