"""Product performance and delivery-experience evidence."""

import pandas as pd
import streamlit as st

from app.components.filters import DashboardFilters, render_category_filter
from app.components.kpis import format_kpi_value, render_kpis
from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.components.presentation import display_dataframe
from app.Home import get_repository
from src.visualization.charts import ranked_bar_chart


@st.cache_data
def load_product_performance(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().product_performance(filters.to_repository_filters())


@st.cache_data
def load_delivery_experience(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().delivery_experience(filters.to_repository_filters())


apply_dashboard_theme()
render_page_header(
    "商品与履约",
    "结合商品品类表现与履约体验，识别收入和服务质量的关联。",
    "品类筛选作用于商品表现；履约汇总保持全局口径。",
)
filters = render_category_filter()
products = load_product_performance(filters)
delivery = load_delivery_experience(filters)
if products.empty or delivery.empty:
    st.info("当前筛选没有商品或履约数据。请清除品类条件后重试。")
else:
    late = delivery.loc[delivery["delivery_status"] == "late"].iloc[0]
    on_time = delivery.loc[delivery["delivery_status"] == "on_time"].iloc[0]
    render_kpis(
        [
            ("延迟订单", format_kpi_value(late.order_count), "延迟履约订单"),
            (
                "延迟平均评分",
                format_kpi_value(late.average_review_score, decimals=3),
                "订单平均评分",
            ),
            (
                "按时平均评分",
                format_kpi_value(on_time.average_review_score, decimals=3),
                "订单平均评分",
            ),
            (
                "评分差异",
                format_kpi_value(
                    late.average_review_score - on_time.average_review_score,
                    decimals=3,
                ),
                "延迟减按时；关联而非因果",
            ),
        ]
    )
    left, right = st.columns((2, 1))
    with left, st.container(border=True):
        st.plotly_chart(
            ranked_bar_chart(
                products.head(10),
                x="product_category",
                y="item_revenue",
                title="前十品类商品金额",
            ),
            use_container_width=True,
        )
        st.caption("品类筛选真实作用于商品表现；履约汇总保持全局口径。")
    with right:
        with st.container(border=True):
            st.subheader("履约体验")
            delivery_display = delivery.assign(
                delivery_status=delivery["delivery_status"].replace(
                    {"late": "延迟", "on_time": "按时"}
                )
            )
            st.dataframe(
                display_dataframe(delivery_display),
                use_container_width=True,
                hide_index=True,
            )
        render_insight(
            "解读提示",
            "延迟履约与较低评分存在强关联，但不能据此做因果解释。",
        )
