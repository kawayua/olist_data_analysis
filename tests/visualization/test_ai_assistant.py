"""Behavior tests for the safe AI analytics assistant page."""

import importlib.util
from pathlib import Path

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
