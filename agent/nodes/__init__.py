"""LangGraph nodes for the CloudOps agent.

discover → reason ⇄ (gate → [approval] → execute) … → report

* discover  - dynamic MCP tool discovery for this run
* reason    - LLM decides: which tools next, or final report
* gate      - policy: validate args, classify risk, RBAC, decide if approval needed
* approval  - human-in-the-loop interrupt (graph pauses until a human decides)
* execute   - call MCP tools, feed results back as context, track writes for verification
* report    - finalise the report
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.types import interrupt

from ..mcp_client import MCPToolRegistry
from ..policy import (
    InvalidArguments,
    Risk,
    requires_approval,
    role_can_approve,
    role_can_request,
    validate_arguments,
)
from ..prompts import FORCE_REPORT, SYSTEM_PROMPT, VERIFY_NUDGE
from ..state import AgentState, PlannedCall
from ..utils import compact, emit, message_text, to_json

RESULT_EVENT_LIMIT = 6000   # chars of a tool result kept in events / audit log
RESULT_LLM_LIMIT = 12000    # chars of a tool result sent to the LLM


def make_discover_node(registry: MCPToolRegistry):
    async def discover(state: AgentState) -> dict[str, Any]:
        emit("run_started", run_id=state.get("run_id"), role=state.get("user_role"))
        await registry.refresh()
        by_server: dict[str, int] = {}
        for spec in registry.tools.values():
            by_server[spec.server] = by_server.get(spec.server, 0) + 1
        emit("tools_discovered", servers=registry.server_status, tool_counts=by_server,
             total=len(registry.tools))
        return {"iterations": 0, "needs_verification": False, "verification_nudged": False,
                "executed_writes": [], "planned": []}

    return discover


def make_reason_node(registry: MCPToolRegistry, llm: BaseChatModel, max_iterations: int):
    async def reason(state: AgentState) -> dict[str, Any]:
        role = state.get("user_role", "viewer")
        iterations = state.get("iterations", 0)
        servers = "\n".join(
            f"- {name}: {st.get('status')} ({st.get('tools', 0)} tools)" for name, st in registry.server_status.items()
        ) or "- none"

        sys_prompt_text = SYSTEM_PROMPT.format(
            now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            servers=servers,
        )

        from ..prompts import PLAYBOOKS, detect_playbook

        active_playbook = state.get("playbook") or detect_playbook(state.get("messages", []))
        if active_playbook and active_playbook in PLAYBOOKS:
            sys_prompt_text += f"\n\n### ACTIVE PLAYBOOK GUIDANCE ({active_playbook.upper()}):\n{PLAYBOOKS[active_playbook]}"

        system = SystemMessage(sys_prompt_text)
        convo = [system, *state["messages"]]

        if iterations >= max_iterations:
            emit("agent_status", message="Step limit reached - writing report with gathered evidence")
            response = await llm.ainvoke([*convo, HumanMessage(FORCE_REPORT)])
            _emit_usage(response)
            return {"messages": [response], "iterations": iterations + 1, "next": "report"}

        if state.get("needs_verification"):
            actions = ", ".join(f"{w['server']}.{w['tool']}({to_json(w['arguments'])})"
                                for w in state.get("executed_writes", [])[-3:])
            convo.append(HumanMessage(f"[CloudOps runtime] {VERIFY_NUDGE.format(actions=actions)}"))

        tools = [s.to_llm_tool() for s in registry.tools.values() if role_can_request(role, s.risk)]
        model = llm.bind_tools(tools) if tools else llm
        emit("agent_thinking", iteration=iterations + 1)
        response: AIMessage = await model.ainvoke(convo)
        _emit_usage(response)

        text = message_text(response).strip()
        update: dict[str, Any] = {"messages": [response], "iterations": iterations + 1}
        if response.tool_calls:
            if text:
                emit("agent_message", text=text, final=False)
            update["next"] = "gate"
        elif state.get("needs_verification") and not state.get("verification_nudged"):
            # The model tried to conclude right after changing infrastructure: force one verification pass.
            emit("agent_status", message="Verification required before concluding")
            update.update({"next": "reason", "verification_nudged": True})
        else:
            update["next"] = "report"
        return update

    return reason


def _emit_usage(response: AIMessage) -> None:
    usage = getattr(response, "usage_metadata", None) or {}
    if usage:
        emit("llm_usage", input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0))


def make_gate_node(registry: MCPToolRegistry):
    async def gate(state: AgentState) -> dict[str, Any]:
        last: AIMessage = state["messages"][-1]
        role = state.get("user_role", "viewer")
        reason_text = message_text(last).strip()[:1000]
        planned: list[PlannedCall] = []
        for tc in last.tool_calls:
            p: PlannedCall = {"id": tc["id"], "qualified_name": tc["name"], "arguments": tc.get("args") or {},
                              "reason": reason_text, "approval_required": False, "approved_by": None}
            spec = registry.get(tc["name"])
            if spec is None:
                p.update(server="?", tool=tc["name"], risk=Risk.HIGH.value, status="unknown",
                         note=f"Tool '{tc['name']}' is not exposed by any connected MCP server")
            else:
                p.update(server=spec.server, tool=spec.name, risk=spec.risk.value)
                try:
                    validate_arguments(spec.input_schema, p["arguments"])
                except InvalidArguments as e:
                    p.update(status="invalid", note=f"Invalid arguments: {e}")
                else:
                    if not role_can_request(role, spec.risk):
                        p.update(status="denied", note=f"Role '{role}' is not permitted to perform write actions")
                    elif requires_approval(spec.risk):
                        p.update(status="awaiting_approval", approval_required=True)
                    else:
                        p.update(status="ready")
            emit("tool_call_planned", call_id=p["id"], server=p["server"], tool=p["tool"],
                 arguments=p["arguments"], risk=p["risk"], status=p["status"],
                 approval_required=p["approval_required"], reason=reason_text, note=p.get("note"))
            planned.append(p)
        return {"planned": planned}

    return gate


def route_after_gate(state: AgentState) -> str:
    return "approval" if any(p["status"] == "awaiting_approval" for p in state.get("planned", [])) else "execute"


def approval_node(state: AgentState) -> dict[str, Any]:
    """Pause the graph until a human approves or rejects the pending write action(s).

    NOTE: LangGraph re-runs this node from the top on resume, so nothing with side effects
    may happen before ``interrupt()``.
    """
    pending = [p for p in state["planned"] if p["status"] == "awaiting_approval"]
    decision = interrupt({
        "kind": "approval_request",
        "run_id": state.get("run_id"),
        "risk": max((p["risk"] for p in pending), key=lambda r: ["low", "medium", "high"].index(r)),
        "actions": [{"call_id": p["id"], "server": p["server"], "tool": p["tool"], "arguments": p["arguments"],
                     "risk": p["risk"], "reason": p["reason"]} for p in pending],
    })
    decision = decision or {}
    approved = bool(decision.get("approved"))
    approver = decision.get("approved_by") or "unknown"
    approver_role = decision.get("approver_role", "viewer")
    comment = decision.get("comment") or ""

    updated: list[PlannedCall] = []
    for p in state["planned"]:
        p = dict(p)  # type: ignore[assignment]
        if p["status"] == "awaiting_approval":
            if approved and role_can_approve(approver_role, Risk(p["risk"])):
                p.update(status="approved", approved_by=approver, note=comment)
            elif approved:
                p.update(status="denied", note=f"Approver role '{approver_role}' cannot approve {p['risk']} risk")
            else:
                p.update(status="rejected", approved_by=approver,
                         note=f"Rejected by {approver}" + (f": {comment}" if comment else ""))
            emit("approval_decision", call_id=p["id"], server=p["server"], tool=p["tool"], status=p["status"],
                 decided_by=approver, comment=comment)
        updated.append(p)  # type: ignore[arg-type]
    return {"planned": updated}


def make_execute_node(registry: MCPToolRegistry):
    async def run_one(p: PlannedCall) -> tuple[PlannedCall, ToolMessage, dict[str, Any] | None]:
        if p["status"] not in ("ready", "approved"):
            emit("tool_call_skipped", call_id=p["id"], server=p["server"], tool=p["tool"], status=p["status"],
                 note=p.get("note"))
            msg = ToolMessage(f"NOT EXECUTED ({p['status']}): {p.get('note', '')}", tool_call_id=p["id"],
                              name=p["qualified_name"], status="error")
            return p, msg, None
        emit("tool_call_started", call_id=p["id"], server=p["server"], tool=p["tool"], arguments=p["arguments"],
             risk=p["risk"])
        res = await registry.call(p["server"], p["tool"], p["arguments"])
        emit("tool_call_finished", call_id=p["id"], server=p["server"], tool=p["tool"], ok=res.ok,
             duration_ms=res.duration_ms, risk=p["risk"], approved_by=p.get("approved_by"),
             arguments=p["arguments"], reason=p.get("reason"),
             result=to_json(res.data, RESULT_EVENT_LIMIT) if res.ok else res.text[:RESULT_EVENT_LIMIT])
        if res.ok:
            content = to_json(compact(res.data), RESULT_LLM_LIMIT)
            msg = ToolMessage(content, tool_call_id=p["id"], name=p["qualified_name"])
        else:
            msg = ToolMessage(f"ERROR: {res.text[:2000]}", tool_call_id=p["id"], name=p["qualified_name"],
                              status="error")
        write = None
        if res.ok and p["risk"] != Risk.READ.value:
            write = {"server": p["server"], "tool": p["tool"], "arguments": p["arguments"],
                     "approved_by": p.get("approved_by"), "result": compact(res.data, max_list=5)}
        return p, msg, write

    async def execute(state: AgentState) -> dict[str, Any]:
        planned = state.get("planned", [])
        # Reads run concurrently; writes run one-by-one, in order, after reads.
        reads = [p for p in planned if p.get("risk") == Risk.READ.value]
        writes = [p for p in planned if p.get("risk") != Risk.READ.value]
        results = list(await asyncio.gather(*(run_one(p) for p in reads)))
        for p in writes:
            results.append(await run_one(p))

        by_id = {p["id"]: msg for p, msg, _ in results}
        messages = [by_id[p["id"]] for p in planned]  # preserve the LLM's tool_call order
        new_writes = [w for _, _, w in results if w]
        read_ok = any(p.get("risk") == Risk.READ.value and p["status"] == "ready" for p in planned)

        update: dict[str, Any] = {"messages": messages, "planned": []}
        if new_writes:
            update.update(executed_writes=[*state.get("executed_writes", []), *new_writes],
                          needs_verification=True, verification_nudged=False)
            emit("verification_pending", actions=[f"{w['server']}.{w['tool']}" for w in new_writes])
        elif state.get("needs_verification") and read_ok:
            update["needs_verification"] = False
            emit("verification_performed")
        return update

    return execute


def make_report_node():
    async def report(state: AgentState) -> dict[str, Any]:
        text = message_text(state["messages"][-1]).strip()
        emit("final_report", report=text, iterations=state.get("iterations", 0),
             actions_taken=state.get("executed_writes", []))
        return {"final_report": text}

    return report


__all__ = [
    "approval_node", "make_discover_node", "make_execute_node", "make_gate_node", "make_reason_node",
    "make_report_node", "route_after_gate",
]
