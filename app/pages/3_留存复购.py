"""Retention and repurchase behavior analysis."""

import pandas as pd
import streamlit as st

from app.components.filters import DashboardFilters, render_cohort_filter
from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.components.presentation import display_dataframe
from app.Home import get_repository
from src.visualization.charts import ranked_bar_chart, retention_heatmap


@st.cache_data
def load_cohort_retention(filters: DashboardFilters) -> pd.DataFrame:
    return get_repository().cohort_retention(filters.to_repository_filters())


@st.cache_data
def load_repurchase_behavior() -> pd.DataFrame:
    return get_repository().repurchase_behavior()


@st.cache_data
def load_repurchase_intervals() -> pd.DataFrame:
    return get_repository().repurchase_intervals()


apply_dashboard_theme()
render_page_header(
    "留存与复购",
    "用月度 Cohort、30/60/90 天复购率与二购间隔识别持续购买的机会。",
    "Cohort 筛选仅影响留存矩阵；复购率使用具有完整观察期的客户作为分母。",
)
filters = render_cohort_filter()
cohort = load_cohort_retention(filters)
behavior = load_repurchase_behavior()
intervals = load_repurchase_intervals()
if cohort.empty or behavior.empty:
    st.info("当前筛选没有完整 Cohort 数据。请清除首购月份或包含不完整观察月后重试。")
else:
    rates = behavior.groupby("horizon_days", as_index=False).agg(
        eligible_customers=("eligible_customers", "sum"),
        repurchased_customers=("repurchased_customers", "sum"),
    )
    rates["repurchase_rate_pct"] = (
        rates.repurchased_customers / rates.eligible_customers * 100
    )
    for column, row in zip(st.columns(3), rates.itertuples(), strict=True):
        with column:
            st.metric(
                f"{int(row.horizon_days)}天复购率",
                f"{row.repurchase_rate_pct:.3f}%",
                help="满足对应观察期的首购客户",
            )
    matrix = cohort.pivot(
        index="cohort_month",
        columns="months_since_cohort",
        values="retention_rate_pct",
    )
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("Cohort 留存热力图（%）")
        st.plotly_chart(retention_heatmap(matrix), use_container_width=True)
    with right, st.container(border=True):
        st.subheader("首购品类 90 天复购率")
        ninety_days = behavior.loc[behavior.horizon_days == 90]
        st.plotly_chart(
            ranked_bar_chart(
                ninety_days,
                "first_purchase_category",
                "repurchase_rate_pct",
                "首购品类90天复购率",
            ),
            use_container_width=True,
        )
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("首购至二购间隔")
        st.plotly_chart(
            ranked_bar_chart(
                intervals, "interval_bucket", "customer_count", "二购间隔客户数"
            ),
            use_container_width=True,
        )
    with right, st.container(border=True):
        st.subheader("首购品类复购明细")
        st.dataframe(display_dataframe(behavior), use_container_width=True, hide_index=True)
    render_insight(
        "解读提示",
        "低频电商更适合用 30/60/90 天及月度 Cohort 观察复购，不应照搬 App 的次日留存。",
    )
