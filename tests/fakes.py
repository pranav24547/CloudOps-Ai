"""Test double for the LLM.

Only the *language model* is replaced. Each scripted step is a function that receives the
messages the model would see (including real MCP tool results) and returns the next AIMessage,
so tests can assert the agent loop feeds tool output back and acts on it.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

Step = Callable[[list[BaseMessage]], AIMessage]


def call(name: str, **args: Any) -> dict[str, Any]:
    return {"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:10]}", "type": "tool_call"}


def say(text: str = "", *calls: dict[str, Any]) -> Step:
    return lambda _msgs: AIMessage(content=text, tool_calls=list(calls))


def tool_results(messages: list[BaseMessage]) -> list[Any]:
    """JSON payloads of the most recent batch of ToolMessages."""
    out: list[Any] = []
    for m in reversed(messages):
        if isinstance(m, ToolMessage):
            try:
                out.insert(0, json.loads(m.content))
            except ValueError:
                out.insert(0, m.content)
        elif out:
            break
    return out


class ScriptedChatModel(BaseChatModel):
    steps: list[Any]
    _i: int = PrivateAttr(default=0)
    _bound_tools: list[list[str]] = PrivateAttr(default_factory=list)
    _seen: list[list[BaseMessage]] = PrivateAttr(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):  # type: ignore[override]
        self._bound_tools.append([t["function"]["name"] for t in tools])
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self._seen.append(list(messages))
        if self._i >= len(self.steps):
            msg = AIMessage(content="## Done\n**Severity:** INFO\nNo further steps scripted.")
        else:
            msg = self.steps[self._i](list(messages))
            self._i += 1
        return ChatResult(generations=[ChatGeneration(message=msg)])

    @property
    def bound_tools(self) -> list[list[str]]:
        return self._bound_tools

    @property
    def seen(self) -> list[list[BaseMessage]]:
        return self._seen
