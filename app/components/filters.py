"""Shared Dashboard filter state."""

from dataclasses import dataclass

from src.analytics.repository import AnalyticsFilters


@dataclass(frozen=True)
class DashboardFilters:
    """Filter values supplied only by a page whose mart supports them."""

    start_month: str | None = None
    end_month: str | None = None
    cohort_month: str | None = None
    customer_state: str | None = None
    product_category: str | None = None
    include_incomplete_months: bool = False

    def to_repository_filters(self) -> AnalyticsFilters:
        return AnalyticsFilters(
            start_month=self.start_month,
            end_month=self.end_month,
            cohort_month=self.cohort_month,
            customer_state=self.customer_state,
            product_category=self.product_category,
            include_incomplete_months=self.include_incomplete_months,
        )
