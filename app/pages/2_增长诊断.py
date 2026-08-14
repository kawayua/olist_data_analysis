"""Monthly growth diagnostics."""

import pandas as pd
import streamlit as st

from app.components.filters import DashboardFilters, render_month_filter
from app.components.kpis import format_kpi_value, render_kpis
from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.components.navigation import render_navigation
from app.Home import get_repository
from src.visualization.charts import bubble_scatter_chart, line_chart, ranked_bar_chart


@st.cache_data
def load_monthly_growth(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().monthly_growth(filters.to_repository_filters())


apply_dashboard_theme()
render_navigation()
render_page_header(
    "增长诊断",
    "拆解商品金额变化中的购买用户、购买频次、客单价与新老客贡献。",
    "筛选仅影响全局月度增长集市，默认排除不完整月份。",
)
filters = render_month_filter()
frame = load_monthly_growth(filters)
if frame.empty:
    st.info("当前日期范围没有完整月份数据。请扩大日期范围或包含不完整月份。")
else:
    latest = frame.iloc[-1]
    render_kpis(
        [
            (
                "最新商品金额",
                format_kpi_value(latest.item_revenue, prefix="R$"),
                "完整月份",
            ),
            ("购买用户环比", format_kpi_value(latest.active_customers_mom_pct, suffix="%", decimals=3), "最新完整月份"),
            (
                "订单环比",
                format_kpi_value(latest.order_count_mom_pct, suffix="%", decimals=3),
                "最新完整月份",
            ),
            (
                "客单价环比",
                format_kpi_value(latest.item_revenue_aov_mom_pct, suffix="%", decimals=3),
                "最新完整月份",
            ),
        ]
    )
    for metric, title in [
        ("item_revenue", "商品金额趋势"),
        ("active_customers", "购买用户趋势"),
        ("item_revenue_aov", "商品金额客单价趋势"),
    ]:
        with st.container(border=True):
            st.plotly_chart(line_chart(frame, "month_start", metric, title), use_container_width=True)
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.plotly_chart(
            bubble_scatter_chart(frame.dropna(subset=["item_revenue_mom_pct"]), "item_revenue_mom_pct", "item_revenue", "order_count", "月度增长机会矩阵"),
            use_container_width=True,
        )
        st.caption("横轴为商品金额环比，纵轴为商品金额，气泡面积为订单数。")
    with right, st.container(border=True):
        st.plotly_chart(ranked_bar_chart(frame, "month_start", "new_customer_item_revenue", "新客商品金额"), use_container_width=True)
        st.plotly_chart(ranked_bar_chart(frame, "month_start", "returning_customer_item_revenue", "老客商品金额"), use_container_width=True)
    with st.container(border=True):
        render_insight(
            "增长解读",
            "GMV = 购买用户 × 购买频次 × 客单价。这里用三条可观测趋势展示驱动，不将它们相加伪装成精确归因瀑布图。",
        )
