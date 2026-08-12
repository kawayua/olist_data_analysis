"""Customer segment value overview."""

import pandas as pd
import streamlit as st

from app.components.filters import DashboardFilters, render_filters
from app.components.kpis import format_kpi_value, render_kpis
from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.Home import get_repository
from src.visualization.charts import ranked_bar_chart


@st.cache_data
def load_customer_segments(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().customer_segments(filters.to_repository_filters())


apply_dashboard_theme()
render_page_header(
    "客户价值",
    "比较 RFM 客户分群的商品金额与贡献占比。",
    "客户分群来自统一 RFM 规则，不代表个体复购预测。",
)
filters = render_filters(get_repository())
frame = load_customer_segments(filters)
if frame.empty:
    st.info("当前没有客户分群数据。请重建集市后重试。")
else:
    top_segment = frame.iloc[0]
    render_kpis(
        [
            ("分群数", format_kpi_value(len(frame)), "RFM 策略分群"),
            ("最高收入分群", str(top_segment.customer_segment), "按商品金额排序"),
            (
                "最高分群收入占比",
                format_kpi_value(
                    top_segment.item_revenue_share_pct,
                    suffix="%",
                    decimals=3,
                ),
                "商品金额占比",
            ),
        ]
    )
    left, right = st.columns((2, 1))
    with left, st.container(border=True):
        st.plotly_chart(
            ranked_bar_chart(
                frame,
                x="customer_segment",
                y="item_revenue",
                title="客户分群商品金额",
            ),
            use_container_width=True,
        )
        st.caption("RFM 是规则分群，不是个体复购概率预测。")
    with right:
        render_insight(
            "行动建议",
            "优先把 potential 与 needs_attention 作为不同运营实验的候选池。",
        )
