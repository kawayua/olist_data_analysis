"""Auditable AI assistant with a clearly bounded live-model path."""

from __future__ import annotations

import json
from collections.abc import Callable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.components.layout import (
    apply_dashboard_theme,
    render_insight,
    render_page_header,
)
from app.components.navigation import render_navigation
from src.agent.client import LangChainOpenAIClient
from src.agent.orchestrator import (
    AgentAnswer,
    AnalysisAgent,
    CompletionClient,
    GovernedTools,
    ToolTrace,
)
from src.agent.tools import AnalysisTools, SQLAlchemyReadOnlyExecutor
from src.config import Settings, get_settings
from src.database import get_engine

ALLOWED_AGENT_VIEWS = {
    "marts.monthly_growth",
    "marts.cohort_retention",
    "marts.customer_segment_strategy",
    "marts.customer_value_analysis",
    "marts.product_performance",
    "marts.delivery_experience",
    "marts.delivery_rating_analysis",
    "marts.repurchase_behavior",
    "marts.state_performance",
}


def is_live_configured(settings: Settings) -> bool:
    """Require both key and model before a model client may be constructed."""
    return bool(settings.llm_api_key.strip() and settings.llm_model.strip())


def build_demo_answer() -> AgentAnswer:
    """Return a fixed, transparent example without reading models or configuration."""
    rows = [
        {"月份": "2018-06", "商品金额（R$）": 1_120_000},
        {"月份": "2018-07", "商品金额（R$）": 1_240_000},
        {"月份": "2018-08", "商品金额（R$）": 1_310_000},
    ]
    figure = px.line(
        pd.DataFrame(rows),
        x="月份",
        y="商品金额（R$）",
        markers=True,
        title="演示：完整月份商品金额趋势",
    )
    figure.update_layout(margin={"l": 30, "r": 20, "t": 55, "b": 30})
    return AgentAnswer(
        answer=(
            "演示数据，非实时模型回答：示例中商品金额连续三个月增长；"
            "正式结论应在配置模型后根据受控查询结果生成。"
        ),
        tool_trace=(
            ToolTrace(
                call_id="demo-metric",
                name="get_metric_definition",
                arguments={"name": "item_revenue"},
                status="success",
                elapsed_ms=0,
                result_summary="演示：已读取商品金额口径。",
            ),
            ToolTrace(
                call_id="demo-sql",
                name="run_safe_sql",
                arguments={"sql": "SELECT ... FROM marts.monthly_growth LIMIT 3"},
                status="success",
                elapsed_ms=0,
                result_summary="演示：返回三个完整月份。",
            ),
        ),
        sql=(
            "SELECT month_start, item_revenue FROM marts.monthly_growth "
            "WHERE is_complete_month ORDER BY month_start LIMIT 3"
        ),
        metric_definition={
            "name": "item_revenue",
            "definition": "已送达订单的商品金额，不含运费。",
        },
        data_range={"start": "2018-06-01", "end": "2018-08-31"},
        limitations=("此处为固定演示数据，不可用于业务决策。",),
        rows=rows,
        chart={"figure": json.loads(figure.to_json())},
    )


def _build_live_tools(settings: Settings) -> AnalysisTools:
    return AnalysisTools(
        executor=SQLAlchemyReadOnlyExecutor(get_engine(settings)),
        allowed_views=ALLOWED_AGENT_VIEWS,
    )


def answer_for_question(
    question: str,
    settings: Settings,
    *,
    client_factory: Callable[[], CompletionClient] | None = None,
    tools_factory: Callable[[], GovernedTools] | None = None,
) -> AgentAnswer:
    """Use the live guarded agent only after explicit complete configuration."""
    if not is_live_configured(settings):
        return build_demo_answer()

    client = (client_factory or (lambda: LangChainOpenAIClient(settings)))()
    tools = (tools_factory or (lambda: _build_live_tools(settings)))()
    return AnalysisAgent(client, tools).run(question)


def _render_answer(answer: AgentAnswer) -> None:
    st.subheader("分析回答")
    st.write(answer.answer)

    if answer.rows:
        st.subheader("查询结果")
        st.dataframe(pd.DataFrame(answer.rows), use_container_width=True, hide_index=True)
    if answer.chart and isinstance(answer.chart.get("figure"), dict):
        st.subheader("图表")
        st.plotly_chart(go.Figure(answer.chart["figure"]), use_container_width=True)
    if answer.sql:
        with st.expander("查看受控 SQL"):
            st.code(answer.sql, language="sql")

    left, right = st.columns(2)
    with left:
        st.subheader("指标口径")
        st.json(answer.metric_definition or {"definition": "未提供"})
    with right:
        st.subheader("数据范围")
        st.json(answer.data_range or {"range": "未提供"})

    if answer.limitations:
        st.warning("限制：" + "；".join(answer.limitations))
    with st.expander("查看工具调用轨迹"):
        st.dataframe(
            pd.DataFrame(
                {
                    "工具": item.name,
                    "状态": item.status,
                    "耗时（毫秒）": item.elapsed_ms,
                    "参数摘要": json.dumps(item.arguments, ensure_ascii=False),
                    "结果摘要": item.result_summary,
                }
                for item in answer.tool_trace
            ),
            use_container_width=True,
            hide_index=True,
        )


def main() -> None:
    st.set_page_config(page_title="AI分析助手", page_icon="🤖", layout="wide")
    apply_dashboard_theme()
    render_navigation()
    render_page_header(
        "AI 分析助手",
        "以受控工具查询指标、数据与模型结果，并保留完整审计轨迹。",
        "仅允许白名单分析集市的单条只读查询；最多六步工具调用。",
    )
    settings = get_settings()
    live_ready = is_live_configured(settings)
    if not live_ready:
        st.info("演示模式：未配置模型。以下内容为演示数据，非实时模型回答。")
    else:
        st.success("实时模式已启用：模型调用仍只能使用受控工具。")

    question = st.chat_input("例如：最近完整月份的商品金额变化如何？")
    answer = (
        answer_for_question(question, settings)
        if question and live_ready
        else build_demo_answer()
    )
    _render_answer(answer)
    render_insight(
        "使用边界",
        "模型只提出工具调用；SQL、预测与营销模拟仍由项目的白名单、参数校验和只读执行层控制。",
    )


if __name__ == "__main__":
    main()
