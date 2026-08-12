"""Shared Dashboard filter state and Streamlit controls."""

from dataclasses import dataclass

import streamlit as st

from src.analytics.repository import AnalyticsFilters, AnalyticsRepository


@dataclass(frozen=True)
class DashboardFilters:
    """Dashboard-wide filter values using customer receiving state."""

    start_month: str | None = None
    end_month: str | None = None
    customer_state: str | None = None
    product_category: str | None = None
    include_incomplete_months: bool = False

    def to_repository_filters(self) -> AnalyticsFilters:
        return AnalyticsFilters(
            start_month=self.start_month,
            end_month=self.end_month,
            customer_state=self.customer_state,
            product_category=self.product_category,
            include_incomplete_months=self.include_incomplete_months,
        )


def render_filters(repository: AnalyticsRepository) -> DashboardFilters:
    """Render shared sidebar controls and return the selected filter state."""
    state_frame = repository.available_customer_states()
    states = state_frame["customer_state"].dropna().tolist()

    with st.sidebar:
        st.header("筛选条件")
        start_month = st.text_input("开始月份", placeholder="2017-01-01") or None
        end_month = st.text_input("结束月份", placeholder="2018-08-01") or None
        selected_state = st.selectbox("客户所在州", ["全部", *states])
        product_category = st.text_input("商品品类", placeholder="例如 health_beauty") or None
        include_incomplete_months = st.checkbox("包含不完整月份", value=False)

    return DashboardFilters(
        start_month=start_month,
        end_month=end_month,
        customer_state=None if selected_state == "全部" else selected_state,
        product_category=product_category,
        include_incomplete_months=include_incomplete_months,
    )
