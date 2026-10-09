"""Agent runs inspection endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth.dependencies import get_current_user
from ..database import get_db
from ..models import AgentRun, User

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("")
async def list_runs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
):
    query = (
        select(AgentRun)
        .options(selectinload(AgentRun.user))
        .order_by(desc(AgentRun.started_at))
        .limit(min(limit, 100))
    )
    result = await db.execute(query)
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "thread_id": r.thread_id,
            "request": r.request,
            "status": r.status,
            "user_email": r.user.email if r.user else "anonymous",
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "error": r.error,
        }
        for r in runs
    ]


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    query = (
        select(AgentRun)
        .options(
            selectinload(AgentRun.user),
            selectinload(AgentRun.tool_calls),
            selectinload(AgentRun.approvals),
        )
        .where(AgentRun.id == run_id)
    )
    result = await db.execute(query)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    return {
        "id": run.id,
        "thread_id": run.thread_id,
        "request": run.request,
        "status": run.status,
        "final_report": run.final_report,
        "error": run.error,
        "user_email": run.user.email if run.user else "anonymous",
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "tool_calls": [
            {
                "id": tc.id,
                "server": tc.server,
                "tool": tc.tool,
                "arguments": tc.arguments,
                "result": tc.result,
                "duration_ms": tc.duration_ms,
                "ok": tc.ok,
                "risk": tc.risk,
                "reason": tc.reason,
                "approved_by": tc.approved_by,
                "timestamp": tc.timestamp.isoformat() if tc.timestamp else None,
            }
            for tc in sorted(run.tool_calls, key=lambda x: x.timestamp or "")
        ],
        "approvals": [
            {
                "id": a.id,
                "server": a.server,
                "tool": a.tool,
                "arguments": a.arguments,
                "risk_level": a.risk_level,
                "status": a.status,
                "reason": a.reason,
                "approved_by": a.approved_by,
                "comment": a.comment,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in run.approvals
        ],
    }
