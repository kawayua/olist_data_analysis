"""Governed metric definitions and deterministic monthly growth calculations."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    label: str
    description: str
    formula: str
    unit: str
    grain: str
    filters: str
    denominator: str


@lru_cache
def _metric_definitions() -> dict[str, MetricDefinition]:
    path = Path(__file__).resolve().parents[2] / "configs" / "metrics.yml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        name: MetricDefinition(name=name, **definition)
        for name, definition in payload["metrics"].items()
    }


def get_metric_definition(name: str) -> MetricDefinition:
    """Return the governed definition for one business metric."""
    return _metric_definitions()[name]


def summarize_monthly_growth(orders: pd.DataFrame) -> pd.DataFrame:
    """Aggregate delivered-order records into continuous monthly growth metrics."""
    required = {
        "order_id",
        "customer_key",
        "purchased_at",
        "item_revenue",
        "payment_value",
    }
    missing = required - set(orders.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    frame = orders.copy()
    frame["month"] = pd.to_datetime(frame["purchased_at"]).dt.to_period("M").dt.to_timestamp()
    first_month = frame.groupby("customer_key")["month"].transform("min")
    frame["is_new_customer"] = frame["month"].eq(first_month)
    grouped = (
        frame.groupby("month", as_index=False)
        .agg(
            item_revenue=("item_revenue", "sum"),
            payment_value=("payment_value", "sum"),
            orders=("order_id", "nunique"),
            customers=("customer_key", "nunique"),
            new_customers=("customer_key", lambda values: values[frame.loc[values.index, "is_new_customer"]].nunique()),
            returning_customers=("customer_key", lambda values: values[~frame.loc[values.index, "is_new_customer"]].nunique()),
        )
        .sort_values("month")
    )
    grouped["item_revenue_aov"] = grouped["item_revenue"] / grouped["orders"]
    grouped["payment_aov"] = grouped["payment_value"] / grouped["orders"]
    grouped["item_revenue_mom_pct"] = grouped["item_revenue"].pct_change() * 100
    return grouped
