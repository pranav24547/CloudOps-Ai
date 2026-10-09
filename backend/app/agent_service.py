"""Agent runtime service for FastAPI.

Coordinates streaming responses to HTTP clients while simultaneously recording
audit trails (AgentRuns, ToolCalls, Approvals) in the database.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from sqlalchemy import select

from agent.agent import CloudOpsAgent
from agent.mcp_client import MCPToolRegistry

from . import database as db
from .models import AgentRun, ApprovalRecord, ToolCallRecord, User

log = logging.getLogger(__name__)

_agent_instance: CloudOpsAgent | None = None


def get_agent() -> CloudOpsAgent:
    global _agent_instance
    if _agent_instance is None:
        registry = MCPToolRegistry()
        _agent_instance = CloudOpsAgent(registry=registry)
    return _agent_instance


def set_agent(agent: CloudOpsAgent) -> None:
    global _agent_instance
    _agent_instance = agent


async def stream_agent_execution(
    message: str,
    user: User,
    thread_id: str | None = None,
    playbook: str | None = None,
) -> AsyncGenerator[str, None]:
    """Streams SSE formatted events to the client while persisting audit records in DB."""
    agent = get_agent()
    thread_id = thread_id or f"th_{uuid.uuid4().hex[:12]}"
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    # Create run in DB
    async with db.AsyncSessionLocal() as session:
        run = AgentRun(
            id=run_id,
            thread_id=thread_id,
            user_id=user.id,
            request=message,
            status="running",
        )
        session.add(run)
        await session.commit()

    try:
        async for ev in agent.run(
            thread_id=thread_id,
            run_id=run_id,
            message=message,
            user_role=user.role,
            playbook=playbook,
        ):
            # Save relevant events to DB and augment with DB IDs
            await _handle_event_persistence(run_id, ev)

            # Yield SSE format
            yield f"data: {json.dumps(ev)}\n\n"

    except Exception as e:
        log.exception("Error executing agent")
        err_msg = f"{type(e).__name__}: {e}"
        async with db.AsyncSessionLocal() as session:
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            r = result.scalar_one_or_none()
            if r:
                r.status = "failed"
                r.error = err_msg
                r.completed_at = datetime.now(timezone.utc)
                await session.commit()
        yield f"data: {json.dumps({'type': 'run_failed', 'error': err_msg})}\n\n"


async def resume_agent_execution(
    run_id: str,
    thread_id: str,
    decision: dict[str, Any],
) -> AsyncGenerator[str, None]:
    agent = get_agent()

    # Update run status
    async with db.AsyncSessionLocal() as session:
        result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
        r = result.scalar_one_or_none()
        if r:
            r.status = "running"
            await session.commit()

    try:
        async for ev in agent.resume(
            thread_id=thread_id,
            decision=decision,
        ):
            await _handle_event_persistence(run_id, ev)
            yield f"data: {json.dumps(ev)}\n\n"
    except Exception as e:
        log.exception("Error resuming agent")
        err_msg = f"{type(e).__name__}: {e}"
        async with db.AsyncSessionLocal() as session:
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            r = result.scalar_one_or_none()
            if r:
                r.status = "failed"
                r.error = err_msg
                r.completed_at = datetime.now(timezone.utc)
                await session.commit()
        yield f"data: {json.dumps({'type': 'run_failed', 'error': err_msg})}\n\n"


async def _handle_event_persistence(run_id: str, ev: dict[str, Any]) -> None:
    etype = ev.get("type")
    async with db.AsyncSessionLocal() as session:
        if etype == "tool_call_finished":
            record = ToolCallRecord(
                id=ev.get("call_id") or f"tc_{uuid.uuid4().hex[:10]}",
                run_id=run_id,
                server=ev.get("server", ""),
                tool=ev.get("tool", ""),
                arguments=ev.get("arguments", {}),
                result=str(ev.get("result", ""))[:4000],
                duration_ms=ev.get("duration_ms", 0),
                ok=ev.get("ok", True),
                risk=ev.get("risk", "read"),
                reason=ev.get("reason"),
                approved_by=ev.get("approved_by"),
            )
            session.add(record)
            await session.commit()

        elif etype == "approval_required":
            interrupt_id = ev.get("interrupt_id")
            first_id = None
            for act in ev.get("actions", []):
                appr_id = f"appr_{uuid.uuid4().hex[:12]}"
                act["approval_id"] = appr_id
                if not first_id:
                    first_id = appr_id
                appr = ApprovalRecord(
                    id=appr_id,
                    run_id=run_id,
                    interrupt_id=interrupt_id,
                    server=act.get("server", ""),
                    tool=act.get("tool", ""),
                    arguments=act.get("arguments", {}),
                    risk_level=act.get("risk", "medium"),
                    status="pending",
                    reason=act.get("reason"),
                )
                session.add(appr)
            if first_id and "approval_id" not in ev:
                ev["approval_id"] = first_id
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            r = result.scalar_one_or_none()
            if r:
                r.status = "waiting_approval"
            await session.commit()

        elif etype == "approval_decision":
            appr_id = ev.get("approval_id")
            tool = ev.get("tool")
            status = ev.get("status")
            decided_by = ev.get("decided_by")
            if appr_id:
                result = await session.execute(
                    select(ApprovalRecord).where(ApprovalRecord.id == appr_id)
                )
            else:
                result = await session.execute(
                    select(ApprovalRecord)
                    .where(ApprovalRecord.run_id == run_id, ApprovalRecord.tool == tool, ApprovalRecord.status == "pending")
                    .order_by(ApprovalRecord.created_at.asc())
                )
            appr = result.scalars().first()
            if appr:
                appr.status = status
                appr.approved_by = decided_by
                appr.comment = ev.get("comment")
                appr.decided_at = datetime.now(timezone.utc)
                await session.commit()

        elif etype == "run_completed":
            result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
            r = result.scalar_one_or_none()
            if r:
                r.status = "completed"
                r.final_report = ev.get("report")
                r.completed_at = datetime.now(timezone.utc)
                await session.commit()

