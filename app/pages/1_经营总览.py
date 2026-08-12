"""State-market operating overview."""

import pandas as pd
import streamlit as st

from app.components.filters import DashboardFilters, render_filters
from app.components.kpis import format_kpi_value, render_kpis
from app.Home import get_repository


@st.cache_data
def load_state_performance(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().state_performance(filters.to_repository_filters())


st.title("经营总览")
filters = render_filters(get_repository())
frame = load_state_performance(filters)
if frame.empty:
    st.info("当前筛选没有州表现数据。请清除客户所在州后重试。")
else:
    totals = frame.iloc[0] if filters.customer_state else frame.sum(numeric_only=True)
    render_kpis(
        [
            ("商品金额", format_kpi_value(totals.item_revenue, prefix="R$"), "已送达订单"),
            ("订单数", format_kpi_value(totals.order_count), "去重订单"),
            ("客户数", format_kpi_value(totals.customer_count), "去重客户"),
            (
                "延迟率",
                format_kpi_value(totals.delayed_delivery_rate_pct, suffix="%", decimals=3),
                "客户所在州口径",
            ),
        ]
    )
    st.subheader("客户所在州表现")
    st.bar_chart(frame.set_index("customer_state")["item_revenue"])
    st.caption("口径：州指客户收货地址州；该页面的州筛选真实生效。")
    st.info("优先关注高收入且延迟率偏高的州，并在后续页面检查其增长与履约表现。")
