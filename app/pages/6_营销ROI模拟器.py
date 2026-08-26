"""Synthetic marketing experiment dashboard."""
import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from app.components.kpis import format_kpi_value, render_kpis
from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.components.navigation import render_navigation
from app.Home import get_repository
from src.ml.experiment import (
    ExperimentConfig,
    evaluate_contact_thresholds,
    rank_simulated_uplift,
    recommend_threshold,
    simulate_experiment,
    summarize_experiment,
)
from src.ml.train import FEATURE_COLUMNS

ROOT = Path(__file__).resolve().parents[2]

@st.cache_data(ttl=3600)
def load_scored_customers() -> pd.DataFrame:
    schema = json.loads((ROOT / "artifacts/models/feature_schema.json").read_text(encoding="utf-8"))
    columns = tuple(schema["feature_columns"])
    if columns != FEATURE_COLUMNS or set(columns).intersection(schema["forbidden_future_fields"]):
        raise ValueError("保存的模型特征契约无效")
    bundle = joblib.load(ROOT / "artifacts/models/repurchase_pipeline.joblib")
    features = get_repository().ml_customer_features_for_scoring()
    if {"customer_key", *columns}.difference(features.columns):
        raise ValueError("当前集市缺少模型评分特征")
    scored = features.loc[:, ["customer_key"]].copy()
    raw = bundle["model"].predict_proba(features.loc[:, columns])[:, 1]
    scored["预测复购概率"] = bundle["calibrator"].predict_proba(raw)
    return scored.sort_values("预测复购概率", ascending=False).reset_index(drop=True)

st.set_page_config(page_title="营销实验与增量评估", layout="wide", initial_sidebar_state="collapsed")
apply_dashboard_theme(); render_navigation()
render_page_header("营销实验与增量评估", "用复购排序筛选试验名单，用模拟 A/B 实验演示增量评估流程。", "模拟实验优先；未来可按同一数据契约接入真实投放记录。")
st.warning("模拟实验：结果由公开假设与随机种子生成，不是实际投放因果结论。")
st.info("复购模型用于筛选试验名单；真实增量效果仍需处理组与对照组的完整观察数据。")
try:
    customers = load_scored_customers()
except (OSError, ValueError, KeyError) as error:
    st.error(f"无法加载客户评分：{error}"); st.stop()
with st.container(border=True):
    st.subheader("实验设计")
    left, middle, right = st.columns(3)
    with left:
        seed = st.number_input("随机种子", min_value=0, value=42, step=1)
        fraction = st.slider("处理组比例", 0.1, 0.9, 0.5, 0.1)
    with middle:
        unit_cost = st.number_input("单次触达成本（R$）", min_value=0.0, value=1.0)
        coupon_cost = st.number_input("单次优惠成本（R$）", min_value=0.0, value=2.0)
    with right:
        margin = st.number_input("单次复购毛利（R$）", min_value=0.0, value=80.0)
        uplift = st.number_input("假定绝对复购提升", 0.0, 0.5, 0.02, 0.005)
config = ExperimentConfig("模拟邮件优惠券", int(seed), fraction, unit_cost, coupon_cost, margin, (uplift,) * 10)
run = simulate_experiment(customers, config); summary = summarize_experiment(run)
thresholds = evaluate_contact_thresholds(run); recommendation = recommend_threshold(thresholds)
uplift_candidates = rank_simulated_uplift(run).head(5)
render_kpis([("处理组客户", format_kpi_value(summary.treatment_customers), "随机分组，模拟数据"), ("增量复购率", format_kpi_value(summary.incremental_repurchase_rate * 100, suffix="%", decimals=2), "处理组减对照组"), ("净增量利润", format_kpi_value(summary.net_incremental_profit, prefix="R$"), "毛利减模拟成本"), ("ROI", format_kpi_value((summary.roi or 0) * 100, suffix="%", decimals=1), "仅限模拟结果")])
left, right = st.columns((3, 2))
with left, st.container(border=True):
    st.subheader("按业务成本选择名单阈值")
    st.caption("Top 1% · Top 3% · Top 5% · Top 10%；不按 Lift 或 ROI 单独推荐。")
    st.dataframe(thresholds, hide_index=True, width="stretch")
with right, st.container(border=True):
    st.subheader("实验结论")
    if recommendation is None: st.warning("暂不扩大投放：所有阈值均未跨越风险线。")
    else: st.success(f"建议优先验证 Top {recommendation['触达比例']:.0%}：{recommendation['推荐依据']}。")
    st.caption(f"增量复购率 95% 区间：{summary.interval_low:.2%} 至 {summary.interval_high:.2%}。")
with st.container(border=True):
    st.subheader("真实数据接入契约")
    st.write("未来真实投放导入 `assignments.csv`、`touchpoints.csv`、`outcomes_90d.csv`；校验分组唯一性、非负成本与完整 90 天观察窗口。")
    st.caption("当前不提供上传入口，避免将模拟记录与真实实验结果混淆。")
with st.container(border=True):
    st.subheader("模拟 uplift 名单排序演示")
    st.caption("按公开模拟提升 × 毛利 − 触达成本排序；不是从真实实验训练的 uplift 模型。")
    st.dataframe(uplift_candidates, hide_index=True, width="stretch")
render_insight("模型与因果的边界", "复购模型只负责筛选优先试验名单；真实 uplift 模型需积累完整处理组、对照组和 90 天真实结果后才可启用。")
