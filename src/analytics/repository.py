"""Read-only data access for the Streamlit analytics dashboard."""

from dataclasses import dataclass

import pandas as pd
from sqlalchemy import Engine, text


@dataclass(frozen=True)
class AnalyticsFilters:
    """Supported dashboard filters using governed mart dimensions only."""

    start_month: str | None = None
    end_month: str | None = None
    cohort_month: str | None = None
    customer_state: str | None = None
    product_category: str | None = None
    include_incomplete_months: bool = False


class AnalyticsRepository:
    """Query governed marts with bound parameters and no write operations."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def monthly_growth(self, filters: AnalyticsFilters) -> pd.DataFrame:
        clauses = []
        params: dict[str, str] = {}
        if not filters.include_incomplete_months:
            clauses.append("is_complete_month")
        if filters.start_month is not None:
            clauses.append("month_start >= :start_month")
            params["start_month"] = filters.start_month
        if filters.end_month is not None:
            clauses.append("month_start <= :end_month")
            params["end_month"] = filters.end_month
        return self._read_mart("marts.monthly_growth", clauses, params, "month_start")

    def cohort_retention(self, filters: AnalyticsFilters) -> pd.DataFrame:
        clauses = []
        params: dict[str, str] = {}
        if filters.cohort_month is not None:
            clauses.append("cohort_month = :cohort_month")
            params["cohort_month"] = filters.cohort_month
        if not filters.include_incomplete_months:
            clauses.append("is_complete_observation_month")
        return self._read_mart(
            "marts.cohort_retention", clauses, params, "cohort_month, activity_month"
        )

    def customer_segments(self, filters: AnalyticsFilters) -> pd.DataFrame:
        return self._read_mart(
            "marts.customer_segment_strategy", [], {}, "item_revenue DESC"
        )

    def product_performance(self, filters: AnalyticsFilters) -> pd.DataFrame:
        clauses = []
        params: dict[str, str] = {}
        if filters.product_category is not None:
            clauses.append("product_category = :product_category")
            params["product_category"] = filters.product_category
        return self._read_mart(
            "marts.product_performance", clauses, params, "item_revenue DESC"
        )

    def delivery_experience(self, filters: AnalyticsFilters) -> pd.DataFrame:
        return self._read_mart("marts.delivery_experience", [], {}, "delivery_status")

    def available_customer_states(self) -> pd.DataFrame:
        """Return customer receiving states available to the Dashboard filter."""
        return self._read_mart("marts.state_performance", [], {}, "customer_state")

    def state_performance(self, filters: AnalyticsFilters) -> pd.DataFrame:
        clauses = []
        params: dict[str, str] = {}
        if filters.customer_state is not None:
            clauses.append("customer_state = :customer_state")
            params["customer_state"] = filters.customer_state
        return self._read_mart("marts.state_performance", clauses, params, "item_revenue DESC")

    def _read_mart(
        self,
        mart: str,
        clauses: list[str],
        params: dict[str, str],
        order_by: str,
    ) -> pd.DataFrame:
        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        query = text(f"SELECT * FROM {mart}{where_clause} ORDER BY {order_by}")
        return pd.read_sql(query, self._engine, params=params)
