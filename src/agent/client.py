"""OpenAI-compatible LangChain adapter with a network-free test seam."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI

from src.config import Settings, get_settings


@dataclass(frozen=True)
class ToolDefinition:
    """A governed tool definition exposed to the model."""

    name: str
    description: str
    parameters: dict[str, Any]

    def as_langchain_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    error: str | None = None


class LangChainOpenAIClient:
    """Normalize LangChain model replies without granting database access."""

    def __init__(
        self, settings: Settings | None = None, runnable: Any | None = None
    ) -> None:
        self._settings = settings or get_settings()
        self._runnable = runnable

    def complete(
        self, messages: list[dict[str, Any]], tools: list[ToolDefinition]
    ) -> LLMResponse:
        """Request one model response or return a safe configuration error."""
        if self._runnable is None and not self._is_configured():
            return LLMResponse(text="", tool_calls=[], error="LLM is not configured")

        try:
            runnable = self._runnable or self._build_runnable()
            if tools and hasattr(runnable, "bind_tools"):
                runnable = runnable.bind_tools(
                    [tool.as_langchain_schema() for tool in tools]
                )
            response = runnable.invoke(self._to_langchain_messages(messages))
            return LLMResponse(
                text=self._text_content(getattr(response, "content", "")),
                tool_calls=self._normalize_tool_calls(
                    getattr(response, "tool_calls", [])
                ),
            )
        except Exception:  # noqa: BLE001 - external model errors must not expose secrets.
            return LLMResponse(text="", tool_calls=[], error="LLM request failed")

    def _is_configured(self) -> bool:
        return bool(self._settings.llm_api_key and self._settings.llm_model)

    def _build_runnable(self) -> ChatOpenAI:
        return ChatOpenAI(
            api_key=self._settings.llm_api_key,
            base_url=self._settings.llm_base_url,
            model=self._settings.llm_model,
        )

    @staticmethod
    def _to_langchain_messages(messages: list[dict[str, Any]]) -> list[BaseMessage]:
        converted: list[BaseMessage] = []
        for message in messages:
            content = message.get("content", "")
            role = message.get("role")
            if role == "system":
                converted.append(SystemMessage(content=content))
            elif role == "assistant":
                converted.append(
                    AIMessage(
                        content=content,
                        tool_calls=LangChainOpenAIClient._history_tool_calls(
                            message.get("tool_calls", [])
                        ),
                    )
                )
            elif role == "tool":
                converted.append(
                    ToolMessage(
                        content=content,
                        tool_call_id=str(message.get("tool_call_id", "")),
                    )
                )
            else:
                converted.append(HumanMessage(content=content))
        return converted

    @staticmethod
    def _history_tool_calls(raw_calls: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_calls, list):
            raise TypeError("assistant tool calls must be a list")

        calls: list[dict[str, Any]] = []
        for raw_call in raw_calls:
            if isinstance(raw_call, ToolCall):
                call_id = raw_call.id
                name = raw_call.name
                arguments = raw_call.arguments
            elif isinstance(raw_call, dict):
                call_id = raw_call.get("id")
                name = raw_call.get("name")
                arguments = raw_call.get("args", raw_call.get("arguments"))
            else:
                raise TypeError("assistant tool call must be structured")

            if (
                not isinstance(call_id, str)
                or not call_id
                or not isinstance(name, str)
                or not name
                or not isinstance(arguments, dict)
            ):
                raise ValueError("assistant tool call is malformed")
            calls.append({"id": call_id, "name": name, "args": arguments})
        return calls

    @staticmethod
    def _text_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item if isinstance(item, str) else str(item.get("text", ""))
                for item in content
            )
        return str(content or "")

    @staticmethod
    def _normalize_tool_calls(raw_calls: Any) -> list[ToolCall]:
        calls: list[ToolCall] = []
        for raw_call in raw_calls or []:
            if not isinstance(raw_call, dict):
                continue
            name = raw_call.get("name")
            arguments = raw_call.get("args", raw_call.get("arguments", {}))
            if not isinstance(name, str) or not isinstance(arguments, dict):
                continue
            calls.append(
                ToolCall(
                    id=str(raw_call.get("id", "")),
                    name=name,
                    arguments=arguments,
                )
            )
        return calls
