"""Monthly growth diagnostics."""

import pandas as pd
import streamlit as st

from app.components.filters import DashboardFilters, render_filters
from app.components.kpis import format_kpi_value, render_kpis
from app.Home import get_repository
from src.visualization.charts import line_chart


@st.cache_data
def load_monthly_growth(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().monthly_growth(filters.to_repository_filters())


st.title("增长诊断")
filters = render_filters(get_repository())
frame = load_monthly_growth(filters)
if frame.empty:
    st.info("当前日期范围没有完整月份数据。请扩大日期范围或包含不完整月份。")
else:
    latest = frame.iloc[-1]
    render_kpis(
        [
            ("最新商品金额", format_kpi_value(latest.item_revenue, prefix="R$"), "完整月份"),
            ("新客户", format_kpi_value(latest.new_customers), "首次购买客户"),
            ("回访客户", format_kpi_value(latest.returning_customers), "此前有购买记录"),
            (
                "环比",
                format_kpi_value(latest.item_revenue_mom_pct, suffix="%", decimals=3),
                "商品金额环比",
            ),
        ]
    )
    st.plotly_chart(
        line_chart(frame, x="month_start", y="item_revenue", title="月度商品金额"),
        use_container_width=True,
    )
    st.caption("默认排除不完整月份；州和品类筛选不适用于当前全局月度集市。")
    st.info("观察增长是否由新客户、回访客户，或客单价变化共同驱动。")
