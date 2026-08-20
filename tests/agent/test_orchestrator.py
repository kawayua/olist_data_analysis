from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from src.agent.client import LLMResponse, ToolCall, ToolDefinition
from src.agent.orchestrator import AnalysisAgent


@dataclass
class ScriptedClient:
    responses: list[LLMResponse]
    seen_messages: list[list[dict[str, Any]]] = field(default_factory=list)

    def complete(self, messages: list[dict[str, Any]], tools: list[ToolDefinition]):
        self.seen_messages.append(messages.copy())
        return self.responses.pop(0)


class FakeTools:
    def definitions(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                "get_metric_definition",
                "获取指标口径",
                {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            )
        ]

    def get_metric_definition(self, name: str) -> dict[str, str]:
        return {"name": name, "definition": "已送达订单商品金额之和"}


def test_agent_executes_registered_tools_and_returns_audit_fields():
    client = ScriptedClient(
        [
            LLMResponse(
                "",
                [
                    ToolCall(
                        "m1",
                        "get_metric_definition",
                        {"name": "item_revenue"},
                    )
                ],
            ),
            LLMResponse("商品金额为 100。", []),
        ]
    )

    answer = AnalysisAgent(client, FakeTools(), max_steps=4).run("销售额？")

    assert [item.name for item in answer.tool_trace] == ["get_metric_definition"]
    assert answer.answer == "商品金额为 100。"
    assert answer.metric_definition == {
        "name": "item_revenue",
        "definition": "已送达订单商品金额之和",
    }
    assert answer.tool_trace[0].status == "success"


def _definition(name: str) -> ToolDefinition:
    schemas = {
        "run_safe_sql": {"sql": {"type": "string"}},
        "get_metric_definition": {"name": {"type": "string"}},
        "create_chart": {
            "chart_type": {"type": "string"},
            "data": {"type": "array"},
            "x": {"type": "string"},
            "y": {"type": "string"},
        },
        "predict_repurchase": {"features": {"type": "object"}},
        "simulate_campaign": {
            "probabilities": {"type": "array"},
            "budget": {"type": "number"},
            "contact_cost": {"type": "number"},
            "average_repurchase_revenue": {"type": "number"},
            "scenarios": {"type": "array"},
            "max_contact_fraction": {"type": "number"},
        },
    }
    return ToolDefinition(name, name, {"type": "object", "properties": schemas[name]})


class MultiFakeTools:
    def __init__(self, failing: bool = False):
        self.calls: list[tuple[str, Any]] = []
        self.failing = failing

    def definitions(self) -> list[ToolDefinition]:
        return [_definition(name) for name in (
            "run_safe_sql", "get_metric_definition", "create_chart",
            "predict_repurchase", "simulate_campaign",
        )]

    def run_safe_sql(self, sql: str) -> dict[str, Any]:
        self.calls.append(("run_safe_sql", sql))
        if self.failing:
            raise RuntimeError("private detail")
        return {
            "sql": sql,
            "rows": [{"month": "2018-01", "item_revenue": 100}],
            "data_range": {"start": "2018-01-01", "end": "2018-08-31"},
        }

    def create_chart(self, **arguments: Any) -> dict[str, Any]:
        self.calls.append(("create_chart", arguments))
        return {"figure": {"data": []}, "chart_type": "bar"}

    def get_metric_definition(self, name: str) -> dict[str, str]:
        self.calls.append(("get_metric_definition", name))
        return {"name": name}

    def predict_repurchase(self, **arguments: Any) -> dict[str, float]:
        self.calls.append(("predict_repurchase", arguments))
        return {"repurchase_probability": 0.1}

    def simulate_campaign(self, **arguments: Any) -> dict[str, Any]:
        self.calls.append(("simulate_campaign", arguments))
        return {"result": []}


def _call(call_id: str, name: str, arguments: dict[str, Any]) -> ToolCall:
    return ToolCall(call_id, name, arguments)


def test_agent_returns_structured_error_for_unknown_tool_without_execution():
    tools = MultiFakeTools()
    client = ScriptedClient(
        [LLMResponse("", [_call("u1", "delete_everything", {})]), LLMResponse("已拒绝", [])]
    )

    answer = AnalysisAgent(client, tools).run("删除数据")

    assert tools.calls == []
    assert answer.answer == "已拒绝"
    assert answer.tool_trace[0].status == "error"
    assert answer.tool_trace[0].result_summary == "unknown_tool"
    assert client.seen_messages[1][-1] == {
        "role": "tool",
        "tool_call_id": "u1",
        "content": '{"error": "unknown_tool", "status": "error"}',
    }


def test_agent_rejects_invalid_tool_arguments_without_execution():
    tools = MultiFakeTools()
    client = ScriptedClient(
        [LLMResponse("", [_call("s1", "run_safe_sql", {"sql": 123})]), LLMResponse("参数不合法", [])]
    )

    answer = AnalysisAgent(client, tools).run("查询")

    assert tools.calls == []
    assert answer.tool_trace[0].result_summary == "invalid_arguments"


def test_agent_stops_after_two_identical_failed_tool_calls():
    tools = MultiFakeTools(failing=True)
    client = ScriptedClient(
        [
            LLMResponse("", [_call("s1", "run_safe_sql", {"sql": "SELECT 1"})]),
            LLMResponse("", [_call("s2", "run_safe_sql", {"sql": "SELECT 1"})]),
            LLMResponse("should not be called", []),
        ]
    )

    answer = AnalysisAgent(client, tools, max_steps=4).run("查询")

    assert len(client.seen_messages) == 2
    assert [item.status for item in answer.tool_trace] == ["error", "error"]
    assert "连续失败" in answer.limitations[0]


def test_agent_stops_at_configured_step_limit():
    tools = MultiFakeTools()
    client = ScriptedClient(
        [
            LLMResponse("", [_call("s1", "run_safe_sql", {"sql": "SELECT 1"})]),
            LLMResponse("", [_call("s2", "run_safe_sql", {"sql": "SELECT 2"})]),
        ]
    )

    answer = AnalysisAgent(client, tools, max_steps=2).run("查询")

    assert len(tools.calls) == 2
    assert answer.answer == "分析未在允许步数内完成。"
    assert "2 步" in answer.limitations[0]


def test_agent_extracts_sql_rows_chart_and_data_range_from_tool_results():
    tools = MultiFakeTools()
    client = ScriptedClient(
        [
            LLMResponse("", [_call("s1", "run_safe_sql", {"sql": "SELECT 1"})]),
            LLMResponse(
                "",
                [
                    _call(
                        "c1",
                        "create_chart",
                        {"chart_type": "bar", "data": [{"x": 1, "y": 2}], "x": "x", "y": "y"},
                    )
                ],
            ),
            LLMResponse("完成", []),
        ]
    )

    answer = AnalysisAgent(client, tools).run("查询并画图")

    assert answer.sql == "SELECT 1"
    assert answer.rows == [{"month": "2018-01", "item_revenue": 100}]
    assert answer.chart == {"figure": {"data": []}, "chart_type": "bar"}
    assert answer.data_range == {"start": "2018-01-01", "end": "2018-08-31"}


@pytest.mark.parametrize("max_steps", [0, 7])
def test_agent_rejects_step_limits_outside_hard_safety_bound(max_steps: int):
    with pytest.raises(ValueError, match="between one and six"):
        AnalysisAgent(ScriptedClient([]), MultiFakeTools(), max_steps=max_steps)


def test_agent_counts_each_tool_call_against_step_budget():
    tools = MultiFakeTools()
    client = ScriptedClient(
        [
            LLMResponse(
                "",
                [
                    _call("s1", "run_safe_sql", {"sql": "SELECT 1"}),
                    _call("s2", "run_safe_sql", {"sql": "SELECT 2"}),
                    _call("s3", "run_safe_sql", {"sql": "SELECT 3"}),
                ],
            )
        ]
    )

    answer = AnalysisAgent(client, tools, max_steps=2).run("查询")

    assert [value for _, value in tools.calls] == ["SELECT 1", "SELECT 2"]
    assert [item.call_id for item in answer.tool_trace] == ["s1", "s2"]
    assert "2 步" in answer.limitations[0]


def test_tool_trace_redacts_secrets_and_bounds_large_audit_arguments():
    tools = MultiFakeTools()
    secret = "super-secret-token"
    huge_value = "x" * 2_000
    client = ScriptedClient(
        [
            LLMResponse(
                "",
                [
                    _call(
                        "s1",
                        "run_safe_sql",
                        {"sql": "SELECT 1", "api_key": secret, "note": huge_value},
                    )
                ],
            ),
            LLMResponse("完成", []),
        ]
    )

    answer = AnalysisAgent(client, tools).run("查询")

    assert tools.calls == []
    trace_arguments = answer.tool_trace[0].arguments
    serialized = str(trace_arguments)
    assert secret not in serialized
    assert huge_value not in serialized
    assert trace_arguments["api_key"] == "[REDACTED]"


def test_direct_final_answer_includes_explicit_missing_evidence_contract():
    answer = AnalysisAgent(
        ScriptedClient([LLMResponse("当前没有可查询证据。", [])]), MultiFakeTools()
    ).run("告诉我结论")

    assert answer.metric_definition == {"name": "未提供", "definition": "未提供"}
    assert answer.data_range == {"start": "未提供", "end": "未提供"}
    assert any("未提供" in limitation for limitation in answer.limitations)


def test_successful_trace_is_json_serializable_and_redacts_nested_secrets():
    tools = MultiFakeTools()
    secret = "nested-secret"
    client = ScriptedClient(
        [
            LLMResponse(
                "",
                [
                    _call(
                        "c1",
                        "create_chart",
                        {
                            "chart_type": "bar",
                            "data": [
                                {
                                    "x": Decimal("1.20"),
                                    "y": datetime(2026, 8, 20, 9, 30, tzinfo=UTC),
                                    "metadata": {"api_key": secret},
                                    "audit_entries": [{"token": secret}],
                                    "tags": {"one", "two"},
                                }
                            ],
                            "x": "x",
                            "y": "y",
                        },
                    )
                ],
            ),
            LLMResponse("完成", []),
        ]
    )

    answer = AnalysisAgent(client, tools).run("画图")

    serialized = json.dumps(asdict(answer.tool_trace[0]), ensure_ascii=False)
    assert secret not in serialized
    assert answer.tool_trace[0].arguments["data"][0]["metadata"]["api_key"] == "[REDACTED]"
    assert (
        answer.tool_trace[0].arguments["data"][0]["audit_entries"][0]["token"]
        == "[REDACTED]"
    )


def test_unvalidated_sql_is_not_retained_in_audit_arguments():
    client = ScriptedClient(
        [
            LLMResponse(
                "",
                [_call("s1", "run_safe_sql", {"sql": "SELECT 'secret'", "extra": 1})],
            ),
            LLMResponse("拒绝", []),
        ]
    )

    answer = AnalysisAgent(client, MultiFakeTools()).run("查询")

    assert answer.tool_trace[0].arguments["sql"] == "[REDACTED]"
