"""State-market operating overview."""

import pandas as pd
import streamlit as st

from app.components.filters import DashboardFilters, render_state_filter
from app.components.kpis import format_kpi_value, render_kpis
from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.components.presentation import summarize_state_performance
from app.Home import get_repository
from src.visualization.charts import line_chart, ranked_bar_chart


@st.cache_data
def load_state_performance(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().state_performance(filters.to_repository_filters())


@st.cache_data
def load_monthly_growth() -> pd.DataFrame:
    return get_repository().monthly_growth(DashboardFilters().to_repository_filters())


@st.cache_data
def load_product_performance() -> pd.DataFrame:
    return get_repository().product_performance(DashboardFilters().to_repository_filters())


apply_dashboard_theme()
render_page_header(
    "经营总览",
    "从整体交易规模、月度趋势、核心品类与客户收货州观察经营现状。",
    "州筛选仅影响州表现；月度趋势和品类排名使用全局完整月份口径。",
)
filters = render_state_filter(get_repository())
frame = load_state_performance(filters)
monthly = load_monthly_growth()
products = load_product_performance()
if frame.empty:
    st.info("当前筛选没有州表现数据。请清除客户所在州后重试。")
else:
    totals = frame.iloc[0] if filters.customer_state else summarize_state_performance(frame)
    render_kpis(
        [
            (
                "商品金额",
                format_kpi_value(totals.item_revenue, prefix="R$"),
                "已送达订单",
            ),
            ("订单数", format_kpi_value(totals.order_count), "去重订单"),
            ("客户数", format_kpi_value(totals.customer_count), "去重客户"),
            (
                "商品金额客单价",
                format_kpi_value(totals.item_revenue / totals.order_count, prefix="R$", decimals=2),
                "商品金额 / 订单数",
            ),
            (
                "最新商品金额环比",
                format_kpi_value(monthly.iloc[-1].item_revenue_mom_pct, suffix="%", decimals=3),
                "最新完整月份",
            ),
            (
                "平均评分",
                format_kpi_value(
                    (frame.average_review_score * frame.order_count).sum() / frame.order_count.sum(),
                    decimals=3,
                ),
                "订单平均评分",
            ),
            (
                "延迟率",
                format_kpi_value(
                    totals.delayed_delivery_rate_pct, suffix="%", decimals=3
                ),
                "客户所在州口径",
            ),
        ]
    )
    left, right = st.columns((2, 1))
    with left, st.container(border=True):
        st.subheader("客户所在州商品金额")
        st.plotly_chart(
            ranked_bar_chart(
                frame,
                x="customer_state",
                y="item_revenue",
                title="客户所在州商品金额",
            ),
            use_container_width=True,
        )
        st.caption("口径：州指客户收货地址州；该页面的州筛选真实生效。")
        st.caption("州指客户收货地址州；州筛选只影响本图和 KPI。")
    with right, st.container(border=True):
        st.subheader("核心品类 Top 10")
        st.plotly_chart(
            ranked_bar_chart(products.head(10), "product_category", "item_revenue", "品类商品金额 Top 10"),
            use_container_width=True,
        )
    for metric, title in [
        ("item_revenue", "月度商品金额"),
        ("order_count", "月度订单数"),
        ("active_customers", "月度购买用户数"),
    ]:
        with st.container(border=True):
            st.plotly_chart(line_chart(monthly, "month_start", metric, title), use_container_width=True)
    with st.container(border=True):
        render_insight(
            "管理层结论提示",
            "先看 GMV、订单与购买用户是否同向变化，再关注高收入且延迟率偏高的州和贡献集中的品类。",
        )
