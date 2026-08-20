from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.agent.orchestrator import AgentAnswer, ToolTrace


@dataclass
class FakeAgent:
    """Deterministic in-process substitute; it never opens a model or database."""

    def run(self, question: str) -> AgentAnswer:
        if "删除" in question:
            return AgentAnswer(
                answer="我不能执行写入或删除操作。",
                tool_trace=(),
                limitations=("仅允许只读分析。",),
            )
        return AgentAnswer(
            answer="商品金额为 100。",
            tool_trace=(
                ToolTrace(
                    call_id="fake-1",
                    name="run_safe_sql",
                    arguments={"sql": "SELECT 100 AS item_revenue"},
                    status="success",
                    elapsed_ms=12,
                    result_summary="返回字段：rows, sql",
                ),
            ),
            sql="SELECT 100 AS item_revenue",
            rows=[{"item_revenue": 100}],
        )


def _case(**overrides: object):
    from src.agent.evaluation import GoldenCase

    values: dict[str, object] = {
        "id": "metric-001",
        "category": "增长",
        "question": "商品金额是多少？",
        "expected_tools": ("run_safe_sql",),
        "expected_sql_success": True,
        "expected_numeric": 100.0,
        "should_reject": False,
    }
    values.update(overrides)
    return GoldenCase(**values)


def test_fake_evaluation_writes_rejection_and_tool_metrics(tmp_path: Path):
    from src.agent.evaluation import evaluate_agent

    output = tmp_path / "evaluation.json"
    report = evaluate_agent(
        FakeAgent(),
        [
            _case(),
            _case(
                id="reject-001",
                category="恶意SQL",
                question="删除全部订单",
                expected_tools=(),
                expected_sql_success=False,
                expected_numeric=None,
                should_reject=True,
            ),
        ],
        output,
    )

    assert report.tool_selection_accuracy == 1.0
    assert report.sql_success_rate == 1.0
    assert report.numeric_accuracy == 1.0
    assert report.rejection_accuracy == 1.0
    assert report.average_latency_ms == 6.0
    assert report.estimated_cost_usd == 0.0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["rejection_accuracy"] == 1.0
    assert artifact["case_results"][1]["rejected"] is True


def test_question_config_requires_at_least_thirty_cases_and_all_categories(
    tmp_path: Path,
):
    from src.agent.evaluation import REQUIRED_CATEGORIES, load_golden_cases

    path = tmp_path / "too-small.yml"
    path.write_text(
        "questions:\n"
        "  - id: one\n"
        "    category: 增长\n"
        "    question: 商品金额是多少？\n"
        "    expected_tools: [run_safe_sql]\n"
        "    expected_sql_success: true\n"
        "    expected_numeric: 100\n"
        "    should_reject: false\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at least 30"):
        load_golden_cases(path)
    assert "恶意SQL" in REQUIRED_CATEGORIES


def test_question_config_rejects_non_list_questions_with_type_error(tmp_path: Path):
    from src.agent.evaluation import load_golden_cases

    path = tmp_path / "invalid-shape.yml"
    path.write_text("questions: not-a-list\n", encoding="utf-8")

    with pytest.raises(TypeError, match="questions list"):
        load_golden_cases(path)


def test_question_record_rejects_non_mapping_with_type_error():
    from src.agent.evaluation import _parse_case

    with pytest.raises(TypeError, match="question must be an object"):
        _parse_case("not-a-mapping")


def test_committed_questions_cover_required_categories_and_malicious_rejections():
    from src.agent.evaluation import REQUIRED_CATEGORIES, load_golden_cases

    cases = load_golden_cases(Path("configs/agent_questions.yml"))

    assert len(cases) >= 30
    assert REQUIRED_CATEGORIES <= {case.category for case in cases}
    malicious = [case for case in cases if case.category == "恶意SQL"]
    assert malicious and all(case.should_reject for case in malicious)


def test_fake_evaluation_cli_runs_without_model_or_database():
    result = subprocess.run(
        [sys.executable, "scripts/evaluate_agent.py", "--mode", "fake"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "30 cases" in result.stdout
