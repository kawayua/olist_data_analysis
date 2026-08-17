from src.agent.client import LangChainOpenAIClient, ToolDefinition
from src.config import Settings


class FakeMessage:
    def __init__(self):
        self.content = "我将查询月度商品金额。"
        self.tool_calls = [
            {
                "name": "run_safe_sql",
                "args": {"sql": "select 1"},
                "id": "call_1",
            }
        ]


class FakeRunnable:
    def invoke(self, messages):
        return FakeMessage()


class ToolBindingFakeRunnable:
    def __init__(self):
        self.bound_tools = None
        self.messages = None

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        self.messages = messages
        return FakeMessage()


class MalformedMessage:
    def __init__(self):
        self.content = [1]
        self.tool_calls = []


class MalformedResponseRunnable:
    def invoke(self, messages):
        return MalformedMessage()


def test_client_normalizes_langchain_tool_calls_without_network():
    client = LangChainOpenAIClient(runnable=FakeRunnable())

    result = client.complete(
        [{"role": "user", "content": "查询"}],
        [ToolDefinition("run_safe_sql", "安全查询", {"type": "object"})],
    )

    assert result.text == "我将查询月度商品金额。"
    assert result.tool_calls[0].name == "run_safe_sql"
    assert result.tool_calls[0].arguments == {"sql": "select 1"}


def test_injected_runnable_binds_governed_tool_schema_when_supported():
    runnable = ToolBindingFakeRunnable()
    client = LangChainOpenAIClient(runnable=runnable)

    client.complete(
        [{"role": "user", "content": "查询"}],
        [ToolDefinition("run_safe_sql", "安全查询", {"type": "object"})],
    )

    assert runnable.bound_tools == [
        {
            "type": "function",
            "function": {
                "name": "run_safe_sql",
                "description": "安全查询",
                "parameters": {"type": "object"},
            },
        }
    ]
    assert runnable.messages[0].content == "查询"


def test_malformed_model_response_returns_safe_error():
    client = LangChainOpenAIClient(runnable=MalformedResponseRunnable())

    result = client.complete([{"role": "user", "content": "查询"}], [])

    assert result.error == "LLM request failed"
    assert result.text == ""
    assert result.tool_calls == []


def test_unconfigured_client_returns_error_without_constructing_a_runnable(monkeypatch):
    client = LangChainOpenAIClient(Settings(llm_api_key="", llm_model=""))

    def fail_if_constructed():
        raise AssertionError("unconfigured client must not construct a runnable")

    monkeypatch.setattr(client, "_build_runnable", fail_if_constructed)

    result = client.complete([{"role": "user", "content": "查询"}], [])

    assert result.error == "LLM is not configured"
    assert result.tool_calls == []
