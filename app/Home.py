"""Streamlit entry page for the governed e-commerce analytics Dashboard."""

import pandas as pd
import streamlit as st

from app.components.filters import DashboardFilters
from app.components.kpis import format_kpi_value, render_kpis
from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.components.navigation import render_navigation
from app.components.presentation import display_dataframe, summarize_state_performance
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
    st.switch_page("pages/1_经营总览.py")
    apply_dashboard_theme()
    render_navigation()
    render_page_header(
        "Olist 电商增长、留存与复购分析",
        "从市场表现进入增长、留存、客户价值与履约诊断。",
        "所有州均指客户收货地址州；默认排除不完整月份。",
    )

    state_performance = load_state_performance(DashboardFilters())
    if state_performance.empty:
        st.info("当前没有可展示的州表现数据。请重建分析集市后重试。")
        return

    row = summarize_state_performance(state_performance)
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
    with st.container(border=True):
        st.subheader("客户所在州表现")
        st.dataframe(
            display_dataframe(state_performance),
            use_container_width=True,
            hide_index=True,
        )
    render_insight(
        "分析导航",
        "从经营总览看现状，进入增长诊断解释变化，再用客户价值、留存复购和商品履约定位可执行机会。",
    )


if __name__ == "__main__":
    main()
