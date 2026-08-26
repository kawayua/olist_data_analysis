"""Behavior tests for the safe AI analytics assistant page."""

import importlib.util
from pathlib import Path

import pytest

from src.config import Settings


def _load_page_module():
    path = Path("app/pages/7_AI分析助手.py")
    spec = importlib.util.spec_from_file_location("ai_assistant_page", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_demo_answer_is_explicitly_labelled_and_never_constructs_model_client():
    """Catch a regression that constructs a live client without model configuration."""
    page = _load_page_module()

    def unexpected_client():
        raise AssertionError("demo mode must not construct a model client")

    answer = page.answer_for_question(
        "上月销售额如何？",
        Settings(llm_api_key="", llm_model=""),
        client_factory=unexpected_client,
    )

    assert "演示数据，非实时模型回答" in answer.answer
    assert answer.tool_trace
    assert answer.rows
    assert answer.chart


def test_navigation_includes_ai_assistant_page():
    """Catch a page that is unreachable from the shared dashboard navigation."""
    from app.components.navigation import NAVIGATION_PAGES

    assert ("pages/7_AI分析助手.py", "AI分析助手") in NAVIGATION_PAGES


def test_ai_assistant_allows_monthly_state_performance_queries():
    page = _load_page_module()

    assert "marts.state_monthly_performance" in page.ALLOWED_AGENT_VIEWS


def test_ai_assistant_allows_monthly_product_performance_queries():
    page = _load_page_module()

    assert "marts.product_monthly_performance" in page.ALLOWED_AGENT_VIEWS


def test_ai_assistant_allows_state_product_performance_queries():
    page = _load_page_module()

    assert "marts.state_product_performance" in page.ALLOWED_AGENT_VIEWS


def test_ai_assistant_keeps_question_with_its_analysis_answer():
    page = _load_page_module()
    answer = page.build_demo_answer()

    history = page.append_conversation_turn(
        [{"question": "上一个问题", "answer": answer}],
        "2017年销售额如何？",
        answer,
    )

    assert len(history) == 1
    assert history[0]["question"] == "2017年销售额如何？"
    assert history[0]["answer"] == answer


def test_ai_assistant_renders_chart_table_and_json_evidence(
    monkeypatch: pytest.MonkeyPatch,
):
    page = _load_page_module()
    events: list[str] = []

    class Context:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object):
            return False

    class FakeStreamlit:
        def subheader(self, _value: str):
            events.append("subheader")

        def write(self, _value: object):
            events.append("write")

        def dataframe(self, _value: object, **_kwargs: object):
            events.append("dataframe")

        def plotly_chart(self, _value: object, **_kwargs: object):
            events.append("plotly_chart")

        def expander(self, _value: str):
            events.append("expander")
            return Context()

        def code(self, _value: str, **_kwargs: object):
            events.append("code")

        def columns(self, _count: int):
            return Context(), Context()

        def json(self, _value: object):
            events.append("json")

        def warning(self, _value: str):
            events.append("warning")

    monkeypatch.setattr(page, "st", FakeStreamlit())

    page._render_answer(page.build_demo_answer())

    assert {"dataframe", "plotly_chart", "json", "code"} <= set(events)
