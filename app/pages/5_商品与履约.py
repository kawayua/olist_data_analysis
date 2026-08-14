"""Product and delivery experience analysis."""

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
from app.components.presentation import display_dataframe
from app.Home import get_repository
from src.visualization.charts import bubble_scatter_chart, ranked_bar_chart


@st.cache_data
def load_product_performance(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().product_performance(filters.to_repository_filters())


@st.cache_data
def load_state_performance() -> pd.DataFrame:
    return get_repository().state_performance(DashboardFilters().to_repository_filters())


@st.cache_data
def load_delivery_rating_analysis() -> pd.DataFrame:
    return get_repository().delivery_rating_analysis()


st.set_page_config(page_title="商品与履约", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
apply_dashboard_theme()
render_navigation()
render_page_header(
    "商品与履约",
    "沿着商品、订单、配送与评分的链路定位体验风险。",
    "全局商品、履约与评分口径；不提供页面筛选。",
)
products = load_product_performance(DashboardFilters())
states = load_state_performance()
ratings = load_delivery_rating_analysis()
if products.empty or states.empty or ratings.empty:
    st.info("当前没有商品或履约数据。请重建分析集市后重试。")
else:
    top_ten_share = products.head(10).item_revenue.sum() / products.item_revenue.sum() * 100
    weighted_review = (states.average_review_score * states.order_count).sum() / states.order_count.sum()
    render_kpis(
        [
            ("品类数", format_kpi_value(len(products)), "商品表现集市"),
            ("Top 10 商品金额占比", format_kpi_value(top_ten_share, suffix="%", decimals=3), "全局商品表现"),
            ("平均配送天数", format_kpi_value((states.average_delivery_days * states.order_count).sum() / states.order_count.sum(), decimals=3), "全局客户收货州"),
            ("延迟率", format_kpi_value((states.delayed_delivery_rate_pct * states.order_count).sum() / states.order_count.sum(), suffix="%", decimals=3), "全局已送达订单"),
            ("平均评分", format_kpi_value(weighted_review, decimals=3), "订单平均评分"),
            ("延迟8天及以上评分", format_kpi_value(ratings.loc[ratings.delivery_delay_bucket == "延迟8天及以上", "average_review_score"].iloc[0], decimals=3), "相对预计送达"),
        ]
    )
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.plotly_chart(bubble_scatter_chart(products, "order_count", "item_revenue", "average_review_score", "品类商品金额与订单量", color="product_category"), use_container_width=True)
        st.caption("横轴为订单数，纵轴为商品金额，气泡面积为平均评分。")
    with right, st.container(border=True):
        st.plotly_chart(ranked_bar_chart(states, "customer_state", "delayed_delivery_rate_pct", "客户收货州延迟率"), use_container_width=True)
        st.dataframe(display_dataframe(states), use_container_width=True, hide_index=True)
    with st.container(border=True):
        st.plotly_chart(bubble_scatter_chart(ratings, "average_delivery_vs_estimate_days", "average_review_score", "order_count", "相对预计送达天数与评分"), use_container_width=True)
        st.caption("配送延迟与评分差异是相关性线索，不能仅凭该图做因果解释。")
    render_insight("行动建议", "优先排查高订单量、高延迟率且低评分的客户收货州；再结合相应品类与物流链路安排改进实验。")
