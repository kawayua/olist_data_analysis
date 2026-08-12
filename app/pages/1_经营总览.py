"""State-market operating overview."""

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
def load_state_performance(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().state_performance(filters.to_repository_filters())


apply_dashboard_theme()
render_page_header(
    "经营总览",
    "按客户收货地址州比较经营规模与履约风险。",
    "州筛选真实作用于本页；默认排除不完整月份。",
)
filters = render_filters(get_repository())
frame = load_state_performance(filters)
if frame.empty:
    st.info("当前筛选没有州表现数据。请清除客户所在州后重试。")
else:
    totals = frame.iloc[0] if filters.customer_state else frame.sum(numeric_only=True)
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
        st.subheader("客户所在州表现")
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
    with right:
        render_insight(
            "行动建议",
            "优先关注高收入且延迟率偏高的州，并在后续页面检查其增长与履约表现。",
        )
