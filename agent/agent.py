"""CloudOps agent facade used by the backend (and runnable from the CLI).

    python -m agent.agent "Why is the orders API slow?"
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Any, AsyncIterator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from .graph import build_graph
from .llm import get_chat_model
from .mcp_client import MCPToolRegistry
from .utils import now_iso


def _get_default_checkpointer():
    return InMemorySaver()


class CloudOpsAgent:
    def __init__(self, registry: MCPToolRegistry | None = None, llm: BaseChatModel | None = None,
                 checkpointer: Any = None, max_iterations: int = 12) -> None:
        self.registry = registry or MCPToolRegistry()
        self._llm = llm
        self.checkpointer = checkpointer if checkpointer is not None else _get_default_checkpointer()
        self.max_iterations = max_iterations
        self._graph = None

    @property
    def graph(self):
        if self._graph is None:
            llm = self._llm or get_chat_model()  # raises LLMNotConfigured if no key
            self._graph = build_graph(self.registry, llm, self.checkpointer, self.max_iterations)
        return self._graph

    @staticmethod
    def _config(thread_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}

    async def run(self, *, thread_id: str, run_id: str, message: str, user_role: str,
                  playbook: str | None = None) -> AsyncIterator[dict]:
        inputs: dict[str, Any] = {"messages": [HumanMessage(message)], "run_id": run_id, "user_role": user_role}
        if playbook:
            inputs["playbook"] = playbook
        async for ev in self._stream(inputs, thread_id):
            yield ev

    async def resume(self, *, thread_id: str, decision: dict[str, Any]) -> AsyncIterator[dict]:
        async for ev in self._stream(Command(resume=decision), thread_id):
            yield ev

    async def _stream(self, inputs: Any, thread_id: str) -> AsyncIterator[dict]:
        config = self._config(thread_id)
        try:
            async for chunk in self.graph.astream(inputs, config, stream_mode="custom"):
                yield chunk
            snapshot = await self.graph.aget_state(config)
            if snapshot.interrupts:
                for intr in snapshot.interrupts:
                    yield {"type": "approval_required", "ts": now_iso(), "interrupt_id": intr.id, **intr.value}
            else:
                yield {"type": "run_completed", "ts": now_iso(),
                       "report": snapshot.values.get("final_report", "")}
        except Exception as e:  # noqa: BLE001
            yield {"type": "run_failed", "ts": now_iso(), "error": f"{type(e).__name__}: {e}"}


async def _cli(question: str) -> None:
    agent = CloudOpsAgent()
    thread = run_id = f"cli-{uuid.uuid4().hex[:8]}"
    stream = agent.run(thread_id=thread, run_id=run_id, message=question, user_role="operator")
    while True:
        pending = None
        async for ev in stream:
            t = ev["type"]
            if t == "tool_call_started":
                print(f"  → {ev['server']}.{ev['tool']}({ev['arguments']})")
            elif t == "tool_call_finished":
                print(f"  ✓ {ev['tool']} ok={ev['ok']} {ev['duration_ms']}ms")
            elif t == "agent_message":
                print(f"\n[agent] {ev['text']}\n")
            elif t == "approval_required":
                pending = ev
            elif t == "run_completed":
                print("\n" + ev["report"])
            elif t == "run_failed":
                print("FAILED:", ev["error"])
        if not pending:
            break
        print(f"\nAPPROVAL REQUIRED (risk={pending['risk']}): {pending['actions']}")
        ok = input("Approve? [y/N] ").strip().lower() == "y"
        stream = agent.resume(thread_id=thread, decision={"approved": ok, "approved_by": "cli",
                                                           "approver_role": "operator"})


if __name__ == "__main__":
    asyncio.run(_cli(" ".join(sys.argv[1:]) or "Give me an overview of the infrastructure health."))
