"""Cohort retention and 90-day repurchase overview."""

import pandas as pd
import streamlit as st

from app.components.filters import DashboardFilters, render_filters
from app.components.kpis import format_kpi_value, render_kpis
from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.components.presentation import display_dataframe
from app.Home import get_repository
from src.visualization.charts import retention_heatmap


@st.cache_data
def load_cohort_retention(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().cohort_retention(filters.to_repository_filters())


apply_dashboard_theme()
render_page_header(
    "留存与复购",
    "用 Cohort 矩阵识别首购客户在后续月份的留存变化。",
    "仅展示拥有完整观察期的 Cohort 数据。",
)
filters = render_filters(get_repository())
frame = load_cohort_retention(filters)
if frame.empty:
    st.info("当前 Cohort 筛选没有完整观察月份。请清除条件或包含不完整月份。")
else:
    cohort_count = frame["cohort_month"].nunique()
    first_month = frame.loc[frame["months_since_cohort"] == 1, "retention_rate_pct"]
    render_kpis(
        [
            ("Cohort 数", format_kpi_value(cohort_count), "首购月份 Cohort"),
            (
                "第1月留存中位数",
                format_kpi_value(first_month.median(), suffix="%", decimals=3),
                "完整观察月",
            ),
            ("可用单元", format_kpi_value(len(frame)), "Cohort-活动月"),
        ]
    )
    matrix = frame.pivot(
        index="cohort_month",
        columns="months_since_cohort",
        values="retention_rate_pct",
    )
    left, right = st.columns((2, 1))
    with left, st.container(border=True):
        st.subheader("Cohort 留存热力图（%）")
        st.plotly_chart(retention_heatmap(matrix), use_container_width=True)
        st.caption("留存率为对应活动月仍有购买行为的客户占该 Cohort 初始客户的比例。")
    with right:
        with st.container(border=True):
            st.subheader("Cohort 留存矩阵（%）")
            display_matrix = matrix.rename_axis(
                index="首购月份",
                columns="距首购月数",
            )
            st.dataframe(display_dataframe(display_matrix), use_container_width=True)
        render_insight(
            "解读提示",
            "不要将最新 Cohort 的未完整观察月误读为 0% 留存。",
        )
