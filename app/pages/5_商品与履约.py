"""Product performance and delivery-experience evidence."""

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.filters import DashboardFilters, render_filters
from app.components.kpis import format_kpi_value, render_kpis
from app.Home import get_repository


@st.cache_data
def load_product_performance(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().product_performance(filters.to_repository_filters())


@st.cache_data
def load_delivery_experience(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().delivery_experience(filters.to_repository_filters())


st.title("商品与履约")
filters = render_filters(get_repository())
products = load_product_performance(filters)
delivery = load_delivery_experience(filters)
if products.empty or delivery.empty:
    st.info("当前筛选没有商品或履约数据。请清除品类条件后重试。")
else:
    late = delivery.loc[delivery["delivery_status"] == "late"].iloc[0]
    on_time = delivery.loc[delivery["delivery_status"] == "on_time"].iloc[0]
    render_kpis(
        [
            ("延迟订单", format_kpi_value(late.order_count), "履约状态为 late"),
            ("延迟平均评分", format_kpi_value(late.average_review_score, decimals=3), "订单平均评分"),
            ("按时平均评分", format_kpi_value(on_time.average_review_score, decimals=3), "订单平均评分"),
            (
                "评分差异",
                format_kpi_value(late.average_review_score - on_time.average_review_score, decimals=3),
                "延迟减按时；关联而非因果",
            ),
        ]
    )
    figure = px.bar(
        products.head(10),
        x="product_category",
        y="item_revenue",
        title="前十品类商品金额",
    )
    st.plotly_chart(figure, use_container_width=True)
    st.dataframe(delivery, use_container_width=True, hide_index=True)
    st.caption("品类筛选真实作用于商品表现；履约汇总保持全局口径。")
    st.info("延迟履约与较低评分存在强关联，但不能据此做因果解释。")
