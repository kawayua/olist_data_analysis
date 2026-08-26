"""Explicit, bounded orchestration for governed analytics tools."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from src.agent.client import LLMResponse, ToolCall, ToolDefinition
from src.agent.safety import UnsafeQueryError


class _StrictArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _MetricArguments(_StrictArguments):
    name: str


class _SqlArguments(_StrictArguments):
    sql: str


class _ChartArguments(_StrictArguments):
    chart_type: str
    data: list[dict[str, Any]]
    x: str
    y: str


class _PredictionArguments(_StrictArguments):
    features: dict[str, Any]


class _SimulationArguments(_StrictArguments):
    probabilities: list[float]
    budget: float
    contact_cost: float
    average_repurchase_revenue: float
    scenarios: list[dict[str, Any]]
    max_contact_fraction: float


ARGUMENT_MODELS: dict[str, type[_StrictArguments]] = {
    "get_metric_definition": _MetricArguments,
    "run_safe_sql": _SqlArguments,
    "create_chart": _ChartArguments,
    "predict_repurchase": _PredictionArguments,
    "simulate_campaign": _SimulationArguments,
}


class CompletionClient(Protocol):
    def complete(
        self, messages: list[dict[str, Any]], tools: list[ToolDefinition]
    ) -> LLMResponse: ...


class GovernedTools(Protocol):
    def definitions(self) -> list[ToolDefinition]: ...


@dataclass(frozen=True)
class ToolTrace:
    """One model-requested tool call with a privacy-safe result summary."""

    call_id: str
    name: str
    arguments: dict[str, Any]
    status: str
    elapsed_ms: int
    result_summary: str
    started_at: str = "未提供"
    finished_at: str = "未提供"


@dataclass(frozen=True)
class AgentAnswer:
    """A response whose evidence and execution trail stay inspectable."""

    answer: str
    tool_trace: tuple[ToolTrace, ...]
    sql: str | None = None
    metric_definition: dict[str, Any] | None = None
    data_range: dict[str, Any] | None = None
    limitations: tuple[str, ...] = ()
    rows: list[dict[str, Any]] | None = None
    chart: dict[str, Any] | None = None


class AnalysisAgent:
    """Run only declared tools in a small, explicit LangChain-protocol loop."""

    def __init__(
        self, client: CompletionClient, tools: GovernedTools, max_steps: int = 6
    ) -> None:
        if not 1 <= max_steps <= 6:
            raise ValueError("max_steps must be between one and six")
        self._client = client
        self._tools = tools
        self._max_steps = max_steps

    def run(self, question: str) -> AgentAnswer:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "你是受控数据分析助手。只使用已注册工具；结论须说明证据和限制。"
                    "指标名称仅可使用：gmv、item_revenue、orders、customers、"
                    "item_revenue_aov、new_customers、returning_customers、"
                    "repeat_rate_30d、repeat_rate_60d、repeat_rate_90d、late_delivery_rate。"
                    "州维度销售额使用 marts.state_performance 的 customer_state 与 item_revenue；"
                "州维度且指定月份范围的销售额使用 marts.state_monthly_performance 的 "
                    "month_start、customer_state 与 item_revenue；"
                    "数据目录：marts.monthly_growth（月度总体：month_start、item_revenue、"
                    "order_count）；marts.product_performance（全周期商品品类：product_category、"
                    "item_revenue、order_count）；marts.product_monthly_performance（月度商品品类："
                    "month_start、product_category、item_revenue、order_count、is_complete_month）；"
                    "marts.state_performance（全周期州：customer_state、item_revenue）；"
                    "marts.state_monthly_performance（月度州：month_start、customer_state、"
                    "item_revenue、is_complete_month）。"
                    "marts.state_product_performance（州与商品品类：customer_state、"
                    "product_category、item_revenue、order_count）。"
                    "其余可查询表：marts.cohort_retention（cohort_month、activity_month、"
                    "months_since_cohort、retention_rate_pct）；marts.customer_segment_strategy（"
                    "customer_segment、customer_count、item_revenue、recommended_action）；"
                    "marts.customer_value_analysis（customer_segment、customer_count、item_revenue、"
                    "average_recency_days、average_frequency_orders）；marts.delivery_experience（"
                    "delivery_status、order_count、average_delivery_days、average_review_score）；"
                    "marts.delivery_rating_analysis（delivery_delay_bucket、order_count、"
                    "average_delivery_vs_estimate_days、average_review_score）；"
                    "marts.repurchase_behavior（first_purchase_category、horizon_days、"
                    "eligible_customers、repurchased_customers、repurchase_rate_pct）。"
                    "问题同时包含月份和商品品类时，必须使用 marts.product_monthly_performance；"
                    "例如“2018年6月份什么商品销售额最好”只调用一次 run_safe_sql，SQL 为 "
                    "SELECT product_category, item_revenue FROM marts.product_monthly_performance "
                    "WHERE month_start = DATE '2018-06-01' ORDER BY item_revenue DESC LIMIT 1。"
                    "问某品类在某年销售额变化时，返回 month_start 与 item_revenue，按 month_start 升序；"
                    "例如 2017 年健康美容类：SELECT month_start, item_revenue FROM "
                    "marts.product_monthly_performance WHERE product_category = 'health_beauty' "
                    "AND month_start >= DATE '2017-01-01' AND month_start < DATE '2018-01-01' "
                    "ORDER BY month_start。"
                    "问题同时包含州和商品品类时，必须使用 marts.state_product_performance；"
                    "例如“SP州哪一个商品最畅销”使用 SELECT product_category, item_revenue FROM "
                    "marts.state_product_performance WHERE customer_state = 'SP' "
                    "ORDER BY item_revenue DESC LIMIT 1。"
                    "涉及业务指标的分析，先调用 get_metric_definition 获取指标口径，再调用 "
                    "run_safe_sql；涉及时间的问题，查询结果必须保留对应的时间字段，以生成数据范围。"
                    "先取得一次受控查询结果，再直接给出结论，不要重复相同调用。"
                ),
            },
            {"role": "user", "content": question},
        ]
        definitions = self._tools.definitions()
        allowed_names = {definition.name for definition in definitions}
        trace: list[ToolTrace] = []
        evidence: dict[str, Any] = {}
        limitations: list[str] = []
        last_failure: tuple[str, str] | None = None
        repeated_failures = 0
        rejected_sql_calls = 0

        while len(trace) < self._max_steps:
            response = self._client.complete(messages, definitions)
            if response.error:
                limitations.append("模型服务暂不可用，未执行额外查询。")
                return self._answer("暂时无法完成分析。", trace, evidence, limitations)
            if not response.tool_calls:
                return self._answer(
                    response.text or "未获得可用分析结论。", trace, evidence, limitations
                )

            remaining_calls = self._max_steps - len(trace)
            calls_to_execute = response.tool_calls[:remaining_calls]
            messages.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": [
                        {"id": call.id, "name": call.name, "args": call.arguments}
                        for call in calls_to_execute
                    ],
                }
            )
            for call in calls_to_execute:
                result, item = self._execute_call(call, allowed_names)
                trace.append(item)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": _json_text(result),
                    }
                )
                if item.status == "success":
                    last_failure = None
                    repeated_failures = 0
                    _collect_evidence(evidence, call.name, result)
                    continue

                fingerprint = (call.name, _json_text(call.arguments))
                repeated_failures = (
                    repeated_failures + 1 if fingerprint == last_failure else 1
                )
                last_failure = fingerprint
                if repeated_failures >= 2:
                    limitations.append("相同工具调用连续失败，已安全停止。")
                    return self._answer("未能完成该分析。", trace, evidence, limitations)

                if call.name == "run_safe_sql" and item.result_summary == "query_rejected":
                    rejected_sql_calls += 1
                    if rejected_sql_calls >= 2:
                        limitations.append("两次 SQL 查询均被安全规则拒绝，已停止重试。")
                        return self._answer("未能完成该分析。", trace, evidence, limitations)

                if len(trace) == self._max_steps:
                    return self._step_limit_answer(trace, evidence, limitations)

            if len(trace) == self._max_steps:
                return self._step_limit_answer(trace, evidence, limitations)

        return self._step_limit_answer(trace, evidence, limitations)

    def _execute_call(
        self, call: ToolCall, allowed_names: set[str]
    ) -> tuple[dict[str, Any], ToolTrace]:
        started = time.perf_counter()
        started_at = _utc_timestamp()
        if call.name not in allowed_names or call.name not in ARGUMENT_MODELS:
            return self._failure_trace(call, started, started_at, "unknown_tool")
        try:
            arguments = ARGUMENT_MODELS[call.name].model_validate(call.arguments)
        except ValidationError:
            return self._failure_trace(call, started, started_at, "invalid_arguments")
        try:
            method = getattr(self._tools, call.name)
            raw_result = method(**arguments.model_dump())
            result = raw_result if isinstance(raw_result, dict) else {"result": raw_result}
        except KeyError:
            return self._failure_trace(call, started, started_at, "metric_not_found")
        except UnsafeQueryError:
            return self._failure_trace(call, started, started_at, "query_rejected")
        except Exception:  # noqa: BLE001 - tool internals must not leak to the model.
            return self._failure_trace(
                call, started, started_at, "tool_execution_failed"
            )

        elapsed = _elapsed_ms(started)
        return result, ToolTrace(
            call_id=call.id,
            name=call.name,
            arguments=_audit_arguments(call.arguments, retain_sql=call.name == "run_safe_sql"),
            status="success",
            started_at=started_at,
            finished_at=_utc_timestamp(),
            elapsed_ms=elapsed,
            result_summary=_summarize(result),
        )

    @staticmethod
    def _failure_trace(
        call: ToolCall, started: float, started_at: str, error: str
    ) -> tuple[dict[str, Any], ToolTrace]:
        return {"status": "error", "error": error}, ToolTrace(
            call_id=call.id,
            name=call.name,
            arguments=_audit_arguments(call.arguments, retain_sql=False),
            status="error",
            started_at=started_at,
            finished_at=_utc_timestamp(),
            elapsed_ms=_elapsed_ms(started),
            result_summary=error,
        )

    @staticmethod
    def _answer(
        answer: str,
        trace: list[ToolTrace],
        evidence: dict[str, Any],
        limitations: list[str],
    ) -> AgentAnswer:
        metric_definition = evidence.get("metric_definition")
        data_range = evidence.get("data_range")
        if metric_definition is None:
            metric_definition = {"name": "未提供", "definition": "未提供"}
            limitations.append("指标口径未提供。")
        if data_range is None:
            data_range = {"start": "未提供", "end": "未提供"}
            limitations.append("数据范围未提供。")
        return AgentAnswer(
            answer=answer,
            tool_trace=tuple(trace),
            sql=evidence.get("sql"),
            metric_definition=metric_definition,
            data_range=data_range,
            limitations=tuple(limitations),
            rows=evidence.get("rows"),
            chart=evidence.get("chart"),
        )

    def _step_limit_answer(
        self,
        trace: list[ToolTrace],
        evidence: dict[str, Any],
        limitations: list[str],
    ) -> AgentAnswer:
        limitations.append(f"已达到 {self._max_steps} 步工具调用上限。")
        return self._answer("分析未在允许步数内完成。", trace, evidence, limitations)


def _collect_evidence(
    evidence: dict[str, Any], name: str, result: dict[str, Any]) -> None:
    if name == "get_metric_definition":
        evidence["metric_definition"] = result
    for field in ("sql", "rows", "chart", "data_range"):
        if field in result:
            evidence[field] = result[field]
    if name == "create_chart" and "figure" in result:
        evidence["chart"] = result


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1_000)


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _summarize(result: dict[str, Any]) -> str:
    keys = ", ".join(sorted(result)[:4])
    return f"返回字段：{keys}" if keys else "工具执行成功"


_SENSITIVE_ARGUMENT_MARKERS = ("api_key", "authorization", "password", "secret", "token")
_MAX_AUDIT_STRING_LENGTH = 256
_MAX_AUDIT_ITEMS = 20


def _audit_arguments(
    arguments: dict[str, Any], *, retain_sql: bool
) -> dict[str, Any]:
    """Copy arguments for the audit trail without retaining secrets or huge payloads."""
    return {
        str(key): _audit_value(
            value,
            sensitive=_is_sensitive_key(str(key))
            or (str(key).lower() == "sql" and not retain_sql),
        )
        for key, value in list(arguments.items())[:_MAX_AUDIT_ITEMS]
    }


def _audit_value(value: Any, *, sensitive: bool = False) -> Any:
    if sensitive:
        return "[REDACTED]"
    if isinstance(value, str):
        if len(value) <= _MAX_AUDIT_STRING_LENGTH:
            return value
        return value[:_MAX_AUDIT_STRING_LENGTH] + "…[已截断]"
    if isinstance(value, dict):
        return {
            str(key): _audit_value(item, sensitive=_is_sensitive_key(str(key)))
            for key, item in list(value.items())[:_MAX_AUDIT_ITEMS]
        }
    if isinstance(value, list):
        return [_audit_value(item) for item in value[:_MAX_AUDIT_ITEMS]]
    if isinstance(value, tuple | set):
        return [_audit_value(item) for item in list(value)[:_MAX_AUDIT_ITEMS]]
    if isinstance(value, bool | int | float) or value is None:
        return value
    return _bounded_text(str(value))


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(marker in normalized for marker in _SENSITIVE_ARGUMENT_MARKERS)


def _bounded_text(value: str) -> str:
    if len(value) <= _MAX_AUDIT_STRING_LENGTH:
        return value
    return value[:_MAX_AUDIT_STRING_LENGTH] + "…[已截断]"
