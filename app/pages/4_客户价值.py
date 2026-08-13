"""Customer value, lifecycle, and RFM-segment analysis."""

import pandas as pd
import streamlit as st

from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.components.presentation import display_dataframe
from app.Home import get_repository
from src.visualization.charts import bubble_scatter_chart, ranked_bar_chart


@st.cache_data
def load_customer_value() -> pd.DataFrame:
    return get_repository().customer_value_analysis()


apply_dashboard_theme()
render_page_header(
    "客户价值",
    "识别不同 RFM 分群的客户规模、消费贡献与购买阶段。",
    "统一快照时点下的全局 RFM 分群；不提供无效筛选条件。",
)
frame = load_customer_value()
if frame.empty:
    st.info("当前没有客户价值数据。请重建分析集市后重试。")
else:
    totals = frame.sum(numeric_only=True)
    repeat_rate = (
        (totals.second_purchase_customers + totals.multi_purchase_customers)
        / totals.customer_count
        * 100
    )
    metrics = [
        ("客户数", totals.customer_count, "RFM 快照客户"),
        ("新购客户", totals.first_purchase_customers, "仅一笔已送达订单"),
        ("老客商品金额", f"R${totals.repeat_customer_item_revenue:,.0f}", "两笔及以上订单客户"),
        ("复购率", f"{repeat_rate:.3f}%", "两笔及以上已送达订单"),
        (
            "平均购买次数",
            f"{(frame.average_frequency_orders * frame.customer_count).sum() / totals.customer_count:.3f}",
            "按客户数加权",
        ),
    ]
    for column, (label, value, help_text) in zip(
        st.columns(5), metrics, strict=True
    ):
        with column:
            st.metric(label, value, help=help_text)
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.plotly_chart(
            bubble_scatter_chart(
                frame,
                "average_frequency_orders",
                "average_monetary_item_revenue",
                "customer_count",
                "RFM 分群价值分布",
                color="customer_segment",
            ),
            use_container_width=True,
        )
        st.caption("横轴为平均购买次数，纵轴为平均客户商品金额，气泡面积为客户数。")
    with right, st.container(border=True):
        st.plotly_chart(
            ranked_bar_chart(
                frame, "customer_segment", "item_revenue", "客户分群商品金额"
            ),
            use_container_width=True,
        )
        st.dataframe(display_dataframe(frame), use_container_width=True, hide_index=True)
    render_insight(
        "解读提示",
        "购买阶段描述已观测订单频次，不把近期未购直接解释为流失；召回优先结合 RFM 的最近购买间隔判断。",
    )
