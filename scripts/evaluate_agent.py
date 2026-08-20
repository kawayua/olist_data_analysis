"""Run the Day 19 golden-question scorecard without hidden model costs."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine

from src.agent.client import LangChainOpenAIClient
from src.agent.evaluation import GoldenCase, evaluate_agent, load_golden_cases
from src.agent.orchestrator import AgentAnswer, AnalysisAgent, ToolTrace
from src.agent.tools import AnalysisTools, SQLAlchemyReadOnlyExecutor
from src.config import Settings, get_settings

OUTPUT = ROOT / "artifacts" / "agent" / "evaluation.json"
MAX_LIVE_CASES = 5
DEFAULT_LIVE_COST_PER_CASE_USD = 0.01
ALLOWED_MARTS = frozenset(
    {
        "marts.monthly_growth",
        "marts.cohort_retention",
        "marts.customer_360",
        "marts.product_performance",
        "marts.delivery_experience",
        "marts.delivery_order_analysis",
        "marts.delivery_rating_analysis",
        "marts.state_performance",
        "marts.customer_segment_strategy",
        "marts.customer_value_analysis",
        "marts.repurchase_behavior",
        "marts.repurchase_horizons",
        "marts.ml_customer_features",
    }
)


@dataclass(frozen=True)
class LiveEvaluationBudget:
    """Explicit caps that bound a user-confirmed live model evaluation."""

    max_cases: int = MAX_LIVE_CASES
    max_total_latency_ms: int = 15_000
    max_estimated_cost_usd: float = 0.05
    estimated_cost_per_case_usd: float = DEFAULT_LIVE_COST_PER_CASE_USD


AgentFactory = Callable[[Settings], "RunnableAgent"]


class RunnableAgent(Protocol):
    def run(self, question: str) -> AgentAnswer: ...


@dataclass
class DeterministicFakeAgent:
    """Answer the golden contract only; it has no network or database dependency."""

    cases: tuple[GoldenCase, ...]

    def run(self, question: str) -> AgentAnswer:
        case = next(case for case in self.cases if case.question == question)
        if case.should_reject:
            return AgentAnswer(
                answer="我不能执行写入、删除或不安全的查询请求。",
                tool_trace=(),
                limitations=("仅允许白名单数据集市上的只读分析。",),
            )
        traces = tuple(
            ToolTrace(
                call_id=f"fake-{index}",
                name=name,
                arguments={},
                status="success",
                elapsed_ms=0,
                result_summary="deterministic fake result",
            )
            for index, name in enumerate(case.expected_tools, start=1)
        )
        return AgentAnswer(
            answer=(
                f"确定性演示结果为 {case.expected_numeric}。"
                if case.expected_numeric is not None
                else "确定性演示结论。"
            ),
            tool_trace=traces,
            sql="SELECT 1" if case.expected_sql_success else None,
            rows=(
                [{"value": case.expected_numeric}]
                if case.expected_numeric is not None
                else None
            ),
        )


def _live_settings_or_exit(settings: Settings) -> None:
    if not settings.llm_api_key or not settings.llm_model:
        raise SystemExit(
            "--mode live requires configured LLM_API_KEY and LLM_MODEL in .env"
        )


def build_live_agent(settings: Settings) -> AnalysisAgent:
    """Create the production agent only after live evaluation was confirmed."""
    engine = create_engine(settings.database_url)
    tools = AnalysisTools(
        SQLAlchemyReadOnlyExecutor(engine), allowed_views=set(ALLOWED_MARTS)
    )
    return AnalysisAgent(LangChainOpenAIClient(settings), tools)


def run_live_evaluation(
    settings: Settings,
    cases: list[GoldenCase],
    output_path: Path,
    budget: LiveEvaluationBudget,
    *,
    confirmed: bool,
    agent_factory: AgentFactory = build_live_agent,
):
    """Run a deliberately small live sample through the same guarded agent."""
    if not confirmed:
        raise SystemExit("live evaluation requires --confirm-live")
    _live_settings_or_exit(settings)
    if not 1 <= budget.max_cases <= MAX_LIVE_CASES:
        raise SystemExit(f"live evaluation allows between 1 and {MAX_LIVE_CASES} cases")
    if budget.max_total_latency_ms <= 0:
        raise SystemExit("live evaluation latency cap must be positive")
    if budget.estimated_cost_per_case_usd < 0 or budget.max_estimated_cost_usd < 0:
        raise SystemExit("live evaluation cost values must be non-negative")
    selected_cases = cases[: budget.max_cases]
    planned_cost = len(selected_cases) * budget.estimated_cost_per_case_usd
    if planned_cost > budget.max_estimated_cost_usd:
        raise SystemExit("live evaluation planned cost exceeds the configured cost cap")
    return evaluate_agent(
        agent_factory(settings),
        selected_cases,
        output_path,
        estimated_cost_per_case_usd=budget.estimated_cost_per_case_usd,
        max_total_latency_ms=budget.max_total_latency_ms,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument("--max-cases", type=int, default=MAX_LIVE_CASES)
    parser.add_argument("--max-latency-ms", type=int, default=15_000)
    parser.add_argument("--max-cost-usd", type=float, default=0.05)
    args = parser.parse_args()
    cases = load_golden_cases(ROOT / "configs" / "agent_questions.yml")
    if args.mode == "live":
        report = run_live_evaluation(
            get_settings(),
            cases,
            OUTPUT,
            LiveEvaluationBudget(
                max_cases=args.max_cases,
                max_total_latency_ms=args.max_latency_ms,
                max_estimated_cost_usd=args.max_cost_usd,
            ),
            confirmed=args.confirm_live,
        )
        print(
            f"live evaluation: {report.total_cases} cases, "
            f"estimated_cost_usd={report.estimated_cost_usd:.4f}, output={OUTPUT}"
        )
        return
    report = evaluate_agent(DeterministicFakeAgent(tuple(cases)), cases, OUTPUT)
    print(
        f"fake evaluation: {report.total_cases} cases, "
        f"rejection_accuracy={report.rejection_accuracy:.1%}, output={OUTPUT}"
    )


if __name__ == "__main__":
    main()
