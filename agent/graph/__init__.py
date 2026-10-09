"""Graph assembly."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from ..mcp_client import MCPToolRegistry
from ..nodes import (
    approval_node,
    make_discover_node,
    make_execute_node,
    make_gate_node,
    make_reason_node,
    make_report_node,
    route_after_gate,
)
from ..state import AgentState


def build_graph(registry: MCPToolRegistry, llm: BaseChatModel, checkpointer, max_iterations: int = 12):
    g = StateGraph(AgentState)
    g.add_node("discover", make_discover_node(registry))
    g.add_node("reason", make_reason_node(registry, llm, max_iterations))
    g.add_node("gate", make_gate_node(registry))
    g.add_node("approval", approval_node)
    g.add_node("execute", make_execute_node(registry))
    g.add_node("report", make_report_node())

    g.add_edge(START, "discover")
    g.add_edge("discover", "reason")
    g.add_conditional_edges("reason", lambda s: s.get("next", "report"),
                            {"gate": "gate", "reason": "reason", "report": "report"})
    g.add_conditional_edges("gate", route_after_gate, {"approval": "approval", "execute": "execute"})
    g.add_edge("approval", "execute")
    g.add_edge("execute", "reason")
    g.add_edge("report", END)
    return g.compile(checkpointer=checkpointer)
