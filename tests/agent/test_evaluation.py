from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from src.agent.orchestrator import AgentAnswer, ToolTrace
from src.config import Settings


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


def test_sql_success_rate_only_scores_cases_that_require_sql(tmp_path: Path):
    from src.agent.evaluation import evaluate_agent

    class UnexpectedSqlAgent:
        def run(self, question: str) -> AgentAnswer:
            return AgentAnswer(answer="result", tool_trace=(), sql="SELECT 1")

    report = evaluate_agent(
        UnexpectedSqlAgent(),
        [
            _case(),
            _case(
                id="definition-001",
                expected_tools=(),
                expected_sql_success=False,
                expected_numeric=None,
            ),
        ],
        tmp_path / "evaluation.json",
    )

    assert report.sql_success_rate == 1.0


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
    unanswerable = [case for case in cases if case.category == "不可回答"]
    assert unanswerable and all(case.should_reject for case in unanswerable)
    numeric_categories = {
        case.category for case in cases if case.expected_numeric is not None
    }
    assert {"增长", "留存", "客户", "商品", "履约"} <= numeric_categories


def test_question_config_rejects_duplicate_questions(tmp_path: Path):
    from src.agent.evaluation import load_golden_cases

    source = yaml.safe_load(
        Path("configs/agent_questions.yml").read_text(encoding="utf-8")
    )
    source["questions"][-1]["question"] = source["questions"][0]["question"]
    path = tmp_path / "duplicate-question.yml"
    path.write_text(yaml.safe_dump(source, allow_unicode=True), encoding="utf-8")

    with pytest.raises(ValueError, match="questions must be unique"):
        load_golden_cases(path)


def test_live_evaluation_requires_explicit_confirmation_before_agent_factory_runs(
    tmp_path: Path,
):
    from scripts.evaluate_agent import LiveEvaluationBudget, run_live_evaluation

    factory_called = False

    def factory(_: Settings) -> FakeAgent:
        nonlocal factory_called
        factory_called = True
        return FakeAgent()

    with pytest.raises(SystemExit, match="--confirm-live"):
        run_live_evaluation(
            Settings(llm_api_key="key", llm_model="model"),
            [_case()],
            tmp_path / "live.json",
            LiveEvaluationBudget(),
            confirmed=False,
            agent_factory=factory,
        )

    assert factory_called is False


def test_live_evaluation_uses_injected_agent_within_case_cost_and_latency_budgets(
    tmp_path: Path,
):
    from scripts.evaluate_agent import LiveEvaluationBudget, run_live_evaluation

    received: list[Settings] = []

    def factory(settings: Settings) -> FakeAgent:
        received.append(settings)
        return FakeAgent()

    settings = Settings(llm_api_key="key", llm_model="model")
    report = run_live_evaluation(
        settings,
        [_case()],
        tmp_path / "live.json",
        LiveEvaluationBudget(
            max_cases=1,
            max_total_latency_ms=100,
            max_estimated_cost_usd=0.01,
            estimated_cost_per_case_usd=0.01,
        ),
        confirmed=True,
        agent_factory=factory,
    )

    assert received == [settings]
    assert report.total_cases == 1
    assert report.estimated_cost_usd == 0.01


def test_live_evaluation_rejects_budget_that_exceeds_cost_cap(tmp_path: Path):
    from scripts.evaluate_agent import LiveEvaluationBudget, run_live_evaluation

    with pytest.raises(SystemExit, match="cost cap"):
        run_live_evaluation(
            Settings(llm_api_key="key", llm_model="model"),
            [_case(), _case(id="metric-002")],
            tmp_path / "live.json",
            LiveEvaluationBudget(
                max_cases=2,
                max_total_latency_ms=100,
                max_estimated_cost_usd=0.01,
                estimated_cost_per_case_usd=0.01,
            ),
            confirmed=True,
            agent_factory=lambda _: FakeAgent(),
        )


def test_live_evaluation_stops_after_total_latency_cap(tmp_path: Path):
    from scripts.evaluate_agent import LiveEvaluationBudget, run_live_evaluation

    class TimedAgent:
        def run(self, question: str) -> AgentAnswer:
            return AgentAnswer(
                answer="result",
                tool_trace=(
                    ToolTrace(
                        call_id="timed-1",
                        name="run_safe_sql",
                        arguments={},
                        status="success",
                        elapsed_ms=5,
                        result_summary="result",
                    ),
                ),
                sql="SELECT 1",
            )

    report = run_live_evaluation(
        Settings(llm_api_key="key", llm_model="model"),
        [_case(), _case(id="metric-002")],
        tmp_path / "live.json",
        LiveEvaluationBudget(
            max_cases=2,
            max_total_latency_ms=5,
            max_estimated_cost_usd=0.02,
            estimated_cost_per_case_usd=0.01,
        ),
        confirmed=True,
        agent_factory=lambda _: TimedAgent(),
    )

    assert report.total_cases == 1
    assert report.estimated_cost_usd == 0.01


def test_fake_evaluation_cli_runs_without_model_or_database():
    result = subprocess.run(
        [sys.executable, "scripts/evaluate_agent.py", "--mode", "fake"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "32 cases" in result.stdout
