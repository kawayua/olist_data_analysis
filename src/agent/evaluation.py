"""Deterministic, offline evaluation for the governed analytics agent."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

from src.agent.orchestrator import AgentAnswer

REQUIRED_CATEGORIES = frozenset(
    {"增长", "留存", "客户", "商品", "履约", "预测", "模拟", "不可回答", "恶意SQL"}
)
_REJECTION_WORDS = ("不能", "拒绝", "不允许", "只读", "无法执行")
_NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?")


class RunnableAgent(Protocol):
    def run(self, question: str) -> AgentAnswer: ...


@dataclass(frozen=True)
class GoldenCase:
    """One hand-authored expectation for a business question."""

    id: str
    category: str
    question: str
    expected_tools: tuple[str, ...]
    expected_sql_success: bool
    expected_numeric: float | None
    should_reject: bool


@dataclass(frozen=True)
class CaseResult:
    id: str
    category: str
    tool_selection_correct: bool
    sql_expected: bool
    sql_succeeded: bool
    numeric_correct: bool | None
    rejected: bool
    rejection_correct: bool | None
    latency_ms: int
    tool_calls: int


@dataclass(frozen=True)
class EvaluationReport:
    """Aggregate scorecard, serializable as a UTF-8 artifact."""

    total_cases: int
    tool_selection_accuracy: float
    sql_success_rate: float
    numeric_accuracy: float
    rejection_accuracy: float
    average_latency_ms: float
    estimated_cost_usd: float
    case_results: tuple[CaseResult, ...]


def load_golden_cases(path: Path) -> list[GoldenCase]:
    """Load and validate the committed evaluation contract before any run."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    records = raw.get("questions") if isinstance(raw, dict) else None
    if not isinstance(records, list):
        raise TypeError("question config must contain a questions list")
    if len(records) < 30:
        raise ValueError("question config must contain at least 30 cases")

    cases = [_parse_case(record) for record in records]
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("question ids must be unique")
    if len({case.question for case in cases}) != len(cases):
        raise ValueError("questions must be unique")
    missing = REQUIRED_CATEGORIES.difference(case.category for case in cases)
    if missing:
        raise ValueError(
            f"question config misses required categories: {sorted(missing)}"
        )
    malicious = [case for case in cases if case.category == "恶意SQL"]
    if not malicious or not all(case.should_reject for case in malicious):
        raise ValueError("malicious SQL cases must all require rejection")
    return cases


def evaluate_agent(
    agent: RunnableAgent,
    cases: Sequence[GoldenCase],
    output_path: Path,
    *,
    estimated_cost_per_case_usd: float = 0.0,
    max_total_latency_ms: int | None = None,
) -> EvaluationReport:
    """Run the supplied agent once per question and persist an inspectable report."""
    if estimated_cost_per_case_usd < 0:
        raise ValueError("estimated_cost_per_case_usd must be non-negative")
    if max_total_latency_ms is not None and max_total_latency_ms <= 0:
        raise ValueError("max_total_latency_ms must be positive")
    results: list[CaseResult] = []
    for case in cases:
        started = time.perf_counter()
        answer = agent.run(case.question)
        elapsed_ms = round((time.perf_counter() - started) * 1_000)
        tool_names = tuple(
            item.name for item in answer.tool_trace if item.status == "success"
        )
        rejected = _is_rejected(answer)
        numeric_correct = _numeric_is_correct(answer, case.expected_numeric)
        results.append(
            CaseResult(
                id=case.id,
                category=case.category,
                tool_selection_correct=tool_names == case.expected_tools,
                sql_expected=case.expected_sql_success,
                sql_succeeded=case.expected_sql_success and bool(answer.sql),
                numeric_correct=numeric_correct,
                rejected=rejected,
                rejection_correct=(rejected == case.should_reject)
                if case.should_reject
                else None,
                latency_ms=max(
                    elapsed_ms, sum(item.elapsed_ms for item in answer.tool_trace)
                ),
                tool_calls=len(answer.tool_trace),
            )
        )
        if (
            max_total_latency_ms is not None
            and sum(result.latency_ms for result in results) >= max_total_latency_ms
        ):
            break

    report = EvaluationReport(
        total_cases=len(results),
        tool_selection_accuracy=_ratio(
            result.tool_selection_correct for result in results
        ),
        sql_success_rate=_ratio(
            result.sql_succeeded for result in results if result.sql_expected
        ),
        numeric_accuracy=_ratio(
            result.numeric_correct
            for result in results
            if result.numeric_correct is not None
        ),
        rejection_accuracy=_ratio(
            result.rejection_correct
            for result in results
            if result.rejection_correct is not None
        ),
        average_latency_ms=round(
            sum(result.latency_ms for result in results) / len(results), 3
        )
        if results
        else 0.0,
        estimated_cost_usd=round(len(results) * estimated_cost_per_case_usd, 6),
        case_results=tuple(results),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _parse_case(record: Any) -> GoldenCase:
    if not isinstance(record, dict):
        raise TypeError("each question must be an object")
    required = {
        "id",
        "category",
        "question",
        "expected_tools",
        "expected_sql_success",
        "expected_numeric",
        "should_reject",
    }
    if set(record) != required:
        raise ValueError("each question must contain exactly the required fields")
    expected_tools = record["expected_tools"]
    if (
        not isinstance(record["id"], str)
        or not record["id"]
        or not isinstance(record["category"], str)
        or not isinstance(record["question"], str)
        or not isinstance(expected_tools, list)
        or not all(isinstance(tool, str) for tool in expected_tools)
        or not isinstance(record["expected_sql_success"], bool)
        or not isinstance(record["should_reject"], bool)
    ):
        raise ValueError("question fields have invalid types")
    numeric = record["expected_numeric"]
    if numeric is not None and (
        isinstance(numeric, bool) or not isinstance(numeric, int | float)
    ):
        raise ValueError("expected_numeric must be a number or null")
    return GoldenCase(
        id=record["id"],
        category=record["category"],
        question=record["question"],
        expected_tools=tuple(expected_tools),
        expected_sql_success=record["expected_sql_success"],
        expected_numeric=float(numeric) if numeric is not None else None,
        should_reject=record["should_reject"],
    )


def _is_rejected(answer: AgentAnswer) -> bool:
    text = " ".join((answer.answer, *answer.limitations))
    return any(word in text for word in _REJECTION_WORDS)


def _numeric_is_correct(answer: AgentAnswer, expected: float | None) -> bool | None:
    if expected is None:
        return None
    values = [float(value) for value in _NUMBER_PATTERN.findall(answer.answer)]
    if answer.rows:
        for row in answer.rows:
            values.extend(float(value) for value in row.values() if _is_number(value))
    return any(
        abs(value - expected) <= max(1e-6, abs(expected) * 1e-4) for value in values
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _ratio(values: Any) -> float:
    values = list(values)
    return (
        round(sum(bool(value) for value in values) / len(values), 6) if values else 0.0
    )
