"""Marketing ROI simulator using saved, leakage-safe repurchase scores."""

import json
from dataclasses import asdict
from pathlib import Path

import joblib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components.kpis import format_kpi_value, render_kpis
from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.components.navigation import render_navigation
from app.Home import get_repository
from src.ml.roi import (
    Scenario,
    build_profit_curve,
    recommend_profit_maximizing_plan,
    simulate_roi,
)
from src.ml.train import FEATURE_COLUMNS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIRECTORY = PROJECT_ROOT / "artifacts" / "models"


@st.cache_data(ttl=3600)
def load_scored_customers() -> pd.DataFrame:
    """Load the saved model contract and score current time-safe customers."""
    schema = json.loads(
        (MODEL_DIRECTORY / "feature_schema.json").read_text(encoding="utf-8")
    )
    feature_columns = tuple(schema["feature_columns"])
    if feature_columns != FEATURE_COLUMNS:
        raise ValueError("保存的特征 schema 与当前安全特征不一致")
    if set(feature_columns).intersection(schema["forbidden_future_fields"]):
        raise ValueError("保存的特征 schema 包含未来字段")

    bundle = joblib.load(MODEL_DIRECTORY / "repurchase_pipeline.joblib")
    if tuple(bundle["feature_columns"]) != feature_columns:
        raise ValueError("模型包与特征 schema 不一致")

    features = get_repository().ml_customer_features_for_scoring()
    required_columns = {"customer_key", *feature_columns}
    missing_columns = required_columns.difference(features.columns)
    if missing_columns:
        raise ValueError(f"当前客户特征缺少字段：{sorted(missing_columns)}")

    raw_probabilities = bundle["model"].predict_proba(
        features.loc[:, feature_columns]
    )[:, 1]
    calibrated_probabilities = bundle["calibrator"].predict_proba(raw_probabilities)
    scored = features.loc[:, ["customer_key"]].copy()
    scored["预测复购概率"] = calibrated_probabilities
    return scored.sort_values(
        ["预测复购概率", "customer_key"],
        ascending=[False, True],
    ).reset_index(drop=True)


def _scenario_frame(results: list) -> pd.DataFrame:
    """Return simulation results with Chinese display labels."""
    frame = pd.DataFrame(asdict(result) for result in results)
    frame["uplift_rate"] = frame["scenario"].map(
        {"保守": conservative_uplift, "基准": baseline_uplift, "乐观": optimistic_uplift}
    )
    return frame.rename(
        columns={
            "scenario": "情景",
            "uplift_rate": "假设提升率",
            "contacted_customers": "触达客户数",
            "incremental_repurchases": "增量复购数",
            "incremental_revenue": "增量收入",
            "marketing_cost": "营销成本",
            "net_incremental_profit": "净增量利润",
            "roi": "ROI",
        }
    )


def _profit_curve_chart(curve: pd.DataFrame) -> go.Figure:
    """Render the baseline budget-to-profit relationship with direct labels."""
    figure = go.Figure(
        go.Scatter(
            x=curve["预算"],
            y=curve["净增量利润"],
            customdata=curve["ROI"],
            mode="lines+markers+text",
            line={"color": "#172b4d", "width": 3},
            marker={"color": "#d49231", "size": 9},
            text=[f"R${value:,.0f}" for value in curve["净增量利润"]],
            textposition="top center",
            hovertemplate="预算 R$%{x:,.0f}<br>净增量利润 R$%{y:,.0f}<br>ROI %{customdata:.1%}<extra></extra>",
            name="基准情景",
        )
    )
    figure.add_hline(line_color="#8b98aa", line_dash="dash", y=0)
    figure.update_layout(
        title="基准情景：预算与净增量利润",
        xaxis_title="营销预算（R$）",
        yaxis_title="净增量利润（R$）",
        hovermode="x unified",
        margin={"l": 30, "r": 20, "t": 70, "b": 30},
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
    )
    figure.update_xaxes(gridcolor="#e5eaf1")
    figure.update_yaxes(gridcolor="#e5eaf1")
    return figure


st.set_page_config(page_title="营销ROI模拟器", layout="wide", initial_sidebar_state="collapsed")
apply_dashboard_theme()
render_navigation()
render_page_header(
    "营销 ROI 模拟器",
    "用已校准的复购概率排序，评估不同预算与提升率假设下的增量经济性。",
    "当前安全特征快照；仅计入营销带来的增量复购与收益。",
)
st.warning("提升率是业务假设，需 A/B 测试验证；预测关联不代表营销因果效果。")

try:
    scored_customers = load_scored_customers()
except (KeyError, OSError, TypeError, ValueError) as error:
    st.error(f"无法读取当前客户评分：{error}")
    st.stop()

if scored_customers.empty:
    st.info("当前没有可用于模拟的客户特征。请重建分析集市后重试。")
    st.stop()

with st.container(border=True):
    st.subheader("模拟参数")
    parameter_columns = st.columns(4)
    with parameter_columns[0]:
        budget = st.number_input("营销预算（R$）", min_value=1.0, value=10_000.0, step=500.0)
        contact_cost = st.number_input("单次触达成本（R$）", min_value=0.01, value=10.0, step=1.0)
    with parameter_columns[1]:
        average_repurchase_revenue = st.number_input(
            "平均复购收入（R$）", min_value=0.0, value=150.0, step=10.0
        )
        max_contact_fraction = st.number_input(
            "最大触达客户比例（0–1）",
            min_value=0.01,
            max_value=1.0,
            value=0.10,
            step=0.01,
        )
    with parameter_columns[2]:
        conservative_uplift = st.number_input(
            "保守提升率（0–1）", min_value=0.0, max_value=1.0, value=0.03, step=0.01
        )
        baseline_uplift = st.number_input(
            "基准提升率（0–1）", min_value=0.0, max_value=1.0, value=0.06, step=0.01
        )
    with parameter_columns[3]:
        optimistic_uplift = st.number_input(
            "乐观提升率（0–1）", min_value=0.0, max_value=1.0, value=0.10, step=0.01
        )
        st.caption("保守 ≤ 基准 ≤ 乐观；预算需至少覆盖一次触达。")

probabilities = scored_customers["预测复购概率"]
scenarios = (
    Scenario("保守", conservative_uplift),
    Scenario("基准", baseline_uplift),
    Scenario("乐观", optimistic_uplift),
)
budget_options = tuple(
    dict.fromkeys(float(budget * fraction) for fraction in (0.25, 0.50, 0.75, 1.0))
)

try:
    scenario_results = simulate_roi(
        probabilities,
        budget,
        contact_cost,
        average_repurchase_revenue,
        scenarios,
        max_contact_fraction,
    )
    recommendation = recommend_profit_maximizing_plan(
        probabilities,
        budget_options,
        contact_cost,
        average_repurchase_revenue,
        scenarios[1],
        max_contact_fraction,
    )
    profit_curve = build_profit_curve(
        probabilities,
        budget_options,
        contact_cost,
        average_repurchase_revenue,
        scenarios[1],
        max_contact_fraction,
    )
except ValueError as error:
    st.error(f"参数无法形成可执行方案：{error}")
    st.stop()

render_kpis(
    [
        ("建议触达客户", format_kpi_value(recommendation.contacted_customers), "基准情景利润最大化"),
        ("建议净增量利润", format_kpi_value(recommendation.net_incremental_profit, prefix="R$", decimals=0), "增量收入减营销成本"),
        ("建议 ROI", format_kpi_value(recommendation.roi * 100, suffix="%", decimals=1), "仅作辅助指标"),
        ("预计增量复购", format_kpi_value(recommendation.incremental_repurchases, decimals=2), "概率期望值，非确定人数"),
    ]
)

left, right = st.columns((3, 2))
with left, st.container(border=True):
    st.plotly_chart(_profit_curve_chart(profit_curve), use_container_width=True)
    st.caption("深蓝线表示基准提升率下的净增量利润；灰色虚线是盈亏平衡线。")
    with st.expander("查看利润曲线明细"):
        st.dataframe(profit_curve, use_container_width=True, hide_index=True)
with right, st.container(border=True):
    st.subheader("三种提升情景")
    scenario_table = _scenario_frame(scenario_results)
    st.dataframe(
        scenario_table.style.format(
            {
                "假设提升率": "{:.1%}",
                "增量复购数": "{:.2f}",
                "增量收入": "R${:,.0f}",
                "营销成本": "R${:,.0f}",
                "净增量利润": "R${:,.0f}",
                "ROI": "{:.1%}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

with st.container(border=True):
    st.subheader("五位高概率代表客户")
    representatives = scored_customers.head(5).rename(
        columns={"customer_key": "客户标识", "预测复购概率": "预测复购概率（%）"}
    )
    representatives["预测复购概率（%）"] *= 100
    st.dataframe(
        representatives.style.format({"预测复购概率（%）": "{:.3f}"}),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("仅用于展示当前模型排序，不表示这些客户必然复购。")

render_insight(
    "决策边界",
    "默认建议按净增量利润排序，而非追求最高 ROI；自然复购收入不计为营销收益。正式投放前需用随机 A/B 测试验证提升率与因果效果。",
)
