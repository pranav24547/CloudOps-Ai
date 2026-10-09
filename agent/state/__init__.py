"""Agent graph state."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class PlannedCall(TypedDict, total=False):
    id: str                 # LLM tool_call id
    qualified_name: str     # "<server>__<tool>"
    server: str
    tool: str
    arguments: dict[str, Any]
    risk: str               # read | low | medium | high
    approval_required: bool
    status: str             # ready | awaiting_approval | approved | rejected | denied | invalid | unknown
    reason: str             # why the agent wants to call it (LLM's preceding text)
    note: str               # rejection / validation message
    approved_by: str | None


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    run_id: str
    user_role: str
    iterations: int
    planned: list[PlannedCall]
    executed_writes: list[dict[str, Any]]
    needs_verification: bool
    verification_nudged: bool
    final_report: str
    next: str               # routing decision of the reason node: gate | reason | report
