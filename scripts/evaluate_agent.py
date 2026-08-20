"""Run the Day 19 golden-question scorecard without hidden model costs."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.evaluation import GoldenCase, evaluate_agent, load_golden_cases
from src.agent.orchestrator import AgentAnswer, ToolTrace
from src.config import Settings, get_settings

OUTPUT = ROOT / "artifacts" / "agent" / "evaluation.json"


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("fake", "live"), default="fake")
    args = parser.parse_args()
    cases = load_golden_cases(ROOT / "configs" / "agent_questions.yml")
    if args.mode == "live":
        _live_settings_or_exit(get_settings())
        raise SystemExit(
            "live evaluation is enabled only from the AI assistant runtime."
        )
    report = evaluate_agent(DeterministicFakeAgent(tuple(cases)), cases, OUTPUT)
    print(
        f"fake evaluation: {report.total_cases} cases, "
        f"rejection_accuracy={report.rejection_accuracy:.1%}, output={OUTPUT}"
    )


if __name__ == "__main__":
    main()
