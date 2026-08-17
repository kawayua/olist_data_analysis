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


def test_client_normalizes_langchain_tool_calls_without_network():
    client = LangChainOpenAIClient(runnable=FakeRunnable())

    result = client.complete(
        [{"role": "user", "content": "查询"}],
        [ToolDefinition("run_safe_sql", "安全查询", {"type": "object"})],
    )

    assert result.text == "我将查询月度商品金额。"
    assert result.tool_calls[0].name == "run_safe_sql"
    assert result.tool_calls[0].arguments == {"sql": "select 1"}


def test_unconfigured_client_returns_error_without_creating_a_network_request():
    client = LangChainOpenAIClient(Settings(llm_api_key="", llm_model=""))

    result = client.complete([{"role": "user", "content": "查询"}], [])

    assert result.error == "LLM is not configured"
    assert result.tool_calls == []
