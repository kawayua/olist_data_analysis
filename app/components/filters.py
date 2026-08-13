"""Shared Dashboard filter state and Streamlit controls."""

from dataclasses import dataclass

import streamlit as st

from src.analytics.repository import AnalyticsFilters, AnalyticsRepository


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


def _render_filter_scope(scope: str) -> None:
    st.caption(f"本页筛选范围：{scope}")


def render_state_filter(repository: AnalyticsRepository) -> DashboardFilters:
    """Render a customer-receiving-state control for state-grain analysis."""
    state_frame = repository.available_customer_states()
    states = state_frame["customer_state"].dropna().tolist()
    with st.container(border=True):
        _render_filter_scope("仅影响客户收货州表现。")
        selected_state = st.selectbox("客户所在州", ["全部", *states])
    return DashboardFilters(
        customer_state=None if selected_state == "全部" else selected_state,
    )


def render_month_filter() -> DashboardFilters:
    """Render the supported date range for the monthly growth mart."""
    with st.container(border=True):
        _render_filter_scope("仅影响月度经营与增长趋势。")
        left, middle, right = st.columns(3)
        start_month = left.text_input("开始月份", placeholder="2017-01-01") or None
        end_month = middle.text_input("结束月份", placeholder="2018-08-01") or None
        include_incomplete_months = right.checkbox("包含不完整月份", value=False)
    return DashboardFilters(
        start_month=start_month,
        end_month=end_month,
        include_incomplete_months=include_incomplete_months,
    )


def render_cohort_filter() -> DashboardFilters:
    """Render the supported cohort-month and observation controls."""
    with st.container(border=True):
        _render_filter_scope("仅影响 Cohort 留存矩阵。")
        left, right = st.columns(2)
        cohort_month = left.text_input("Cohort 首购月份", placeholder="例如 2017-01-01") or None
        include_incomplete_months = right.checkbox("包含不完整观察月", value=False)
    return DashboardFilters(
        cohort_month=cohort_month,
        include_incomplete_months=include_incomplete_months,
    )


def render_category_filter() -> DashboardFilters:
    """Render the product-category control for category-grain analysis."""
    with st.container(border=True):
        _render_filter_scope("仅影响商品品类表现；履约汇总保持全局口径。")
        product_category = (
            st.text_input("商品品类", placeholder="例如 health_beauty") or None
        )
    return DashboardFilters(product_category=product_category)
