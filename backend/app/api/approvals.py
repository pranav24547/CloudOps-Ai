"""Human approval management endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent_service import resume_agent_execution
from ..auth.dependencies import get_current_user, require_role
from ..database import get_db
from ..models import AgentRun, ApprovalRecord, User

router = APIRouter(prefix="/api", tags=["approvals"])


class DecisionRequest(BaseModel):
    approved: bool
    comment: str | None = None


@router.get("/approvals")
async def list_approvals(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
):
    query = select(ApprovalRecord).order_by(desc(ApprovalRecord.created_at))
    if status:
        query = query.where(ApprovalRecord.status == status)
    result = await db.execute(query.limit(50))
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "run_id": r.run_id,
            "interrupt_id": r.interrupt_id,
            "server": r.server,
            "tool": r.tool,
            "arguments": r.arguments,
            "risk_level": r.risk_level,
            "status": r.status,
            "reason": r.reason,
            "approved_by": r.approved_by,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        }
        for r in records
    ]


@router.post("/approval/{approval_id}")
async def submit_approval(
    approval_id: str,
    req: DecisionRequest,
    current_user: Annotated[User, Depends(require_role("operator", "admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(ApprovalRecord).where(ApprovalRecord.id == approval_id))
    appr = result.scalar_one_or_none()
    if not appr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    if appr.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval request is already {appr.status}",
        )

    # Get associated run to resume execution
    run_res = await db.execute(select(AgentRun).where(AgentRun.id == appr.run_id))
    run = run_res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated agent run not found")

    decision = {
        "approved": req.approved,
        "approved_by": current_user.email,
        "approver_role": current_user.role,
        "comment": req.comment or "",
    }

    # Stream the resumed execution back
    generator = resume_agent_execution(
        run_id=run.id,
        thread_id=run.thread_id,
        decision=decision,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
