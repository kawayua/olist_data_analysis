"""State-market operating overview."""

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
from app.components.presentation import summarize_state_performance
from app.Home import get_repository
from src.visualization.charts import line_chart, ranked_bar_chart
from src.visualization.maps import (
    brazil_state_polygon_map,
    load_brazil_states_geojson,
)


@st.cache_data
def load_state_performance(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().state_performance(filters.to_repository_filters())


@st.cache_data
def load_monthly_growth() -> pd.DataFrame:
    return get_repository().monthly_growth(DashboardFilters().to_repository_filters())


@st.cache_data
def load_product_performance() -> pd.DataFrame:
    return get_repository().product_performance(DashboardFilters().to_repository_filters())


@st.cache_data(ttl=86_400)
def load_brazil_state_boundaries() -> dict:
    """Cache the official state boundaries so page refreshes stay responsive."""
    return load_brazil_states_geojson()


st.set_page_config(page_title="经营总览", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
apply_dashboard_theme()
render_navigation()
render_page_header(
    "经营总览",
    "从整体交易规模、月度趋势、核心品类与客户收货州观察经营现状。",
    "全局完整月份口径；不提供页面筛选。",
)
frame = load_state_performance(DashboardFilters())
monthly = load_monthly_growth()
products = load_product_performance()
if frame.empty:
    st.info("当前没有州表现数据。请重建分析集市后重试。")
else:
    totals = summarize_state_performance(frame)
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
    st.subheader("州级经营表现")
    st.caption("桌面端悬停州块可查看详细指标；触屏设备可使用图表工具栏缩放查看。")
    try:
        brazil_boundaries = load_brazil_state_boundaries()
    except (OSError, ValueError, KeyError) as error:
        brazil_boundaries = None
        st.warning(f"暂时无法加载巴西州界地图：{error}")

    if brazil_boundaries is not None:
        payment_map, product_map = st.columns(2)
        with payment_map, st.container(border=True):
            st.plotly_chart(
                brazil_state_polygon_map(
                    frame,
                    geojson=brazil_boundaries,
                    color_metric="payment_value",
                    hover_metrics=("payment_value", "customer_count"),
                    title="客户支付金额与人数分布",
                ),
                width="stretch",
            )
            st.caption("悬停州块查看支付金额与去重客户数。")
        with product_map, st.container(border=True):
            st.plotly_chart(
                brazil_state_polygon_map(
                    frame,
                    geojson=brazil_boundaries,
                    color_metric="item_revenue",
                    hover_metrics=(
                        "item_revenue",
                        "customer_count",
                        "average_review_score",
                    ),
                    title="商品销售额、人数与平均评分",
                ),
                width="stretch",
            )
            st.caption("悬停州块查看商品销售额、去重客户数与平均评分。")
    else:
        with st.container(border=True):
            st.plotly_chart(
                ranked_bar_chart(frame, "customer_state", "item_revenue", "客户所在州商品金额"),
                width="stretch",
            )

    with st.container(border=True):
        st.subheader("核心品类 Top 10")
        st.plotly_chart(
            ranked_bar_chart(products.head(10), "product_category", "item_revenue", "品类商品金额 Top 10"),
            width="stretch",
        )
    for metric, title in [
        ("item_revenue", "月度商品金额"),
        ("order_count", "月度订单数"),
        ("active_customers", "月度购买用户数"),
    ]:
        with st.container(border=True):
            st.plotly_chart(line_chart(monthly, "month_start", metric, title), width="stretch")
    with st.container(border=True):
        render_insight(
            "管理层结论提示",
            "先看 GMV、订单与购买用户是否同向变化，再关注高收入且延迟率偏高的州和贡献集中的品类。",
        )
