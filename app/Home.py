"""Streamlit entry page for the governed e-commerce analytics Dashboard."""

import pandas as pd
import streamlit as st

from app.components.filters import DashboardFilters, render_filters
from app.components.kpis import format_kpi_value, render_kpis
from src.analytics.repository import AnalyticsRepository
from src.config import get_settings
from src.database import get_engine


@st.cache_resource
def get_repository() -> AnalyticsRepository:
    """Cache the read-only repository for the lifetime of the Streamlit process."""
    return AnalyticsRepository(get_engine(get_settings()))


@st.cache_data
def load_state_performance(filters: DashboardFilters) -> pd.DataFrame:
    """Cache state-performance data separately for every filter combination."""
    return get_repository().state_performance(filters.to_repository_filters())


def main() -> None:
    st.set_page_config(page_title="Olist 增长分析", page_icon="📈", layout="wide")
    st.title("Olist 电商增长、留存与复购分析")
    st.caption("所有州均指客户收货地址州；默认排除不完整月份。")

    filters = render_filters(get_repository())
    state_performance = load_state_performance(filters)
    if state_performance.empty:
        st.info("当前筛选没有匹配数据。请清除州或品类条件后重试。")
        return

    row = state_performance.iloc[0]
    render_kpis(
        [
            ("商品金额", format_kpi_value(row.item_revenue, prefix="R$"), "已送达订单"),
            ("客户数", format_kpi_value(row.customer_count), "去重客户"),
            (
                "90天复购率",
                format_kpi_value(row.repurchase_rate_90d_pct, suffix="%", decimals=3),
                "完整观察期的首购客户",
            ),
            (
                "延迟率",
                format_kpi_value(row.delayed_delivery_rate_pct, suffix="%", decimals=3),
                "已送达订单",
            ),
        ]
    )
    st.subheader("客户所在州表现")
    st.dataframe(state_performance, use_container_width=True, hide_index=True)
    st.info("更多经营、增长、留存、客户与履约页面将在侧边栏逐步开放。")


if __name__ == "__main__":
    main()
