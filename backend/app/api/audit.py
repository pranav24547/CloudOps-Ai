"""Audit trail endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth.dependencies import get_current_user
from ..database import get_db
from ..models import ToolCallRecord, User

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
async def get_audit_trail(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    server: str | None = None,
    risk: str | None = None,
):
    """Returns an immutable auditable ledger of every MCP tool call, arguments, risk, result, and approvals."""
    query = (
        select(ToolCallRecord)
        .options(selectinload(ToolCallRecord.run))
        .order_by(desc(ToolCallRecord.timestamp))
    )
    if server:
        query = query.where(ToolCallRecord.server == server)
    if risk:
        query = query.where(ToolCallRecord.risk == risk)

    result = await db.execute(query.limit(min(limit, 200)))
    records = result.scalars().all()

    return [
        {
            "id": r.id,
            "run_id": r.run_id,
            "user_request": r.run.request if r.run else None,
            "server": r.server,
            "tool": r.tool,
            "arguments": r.arguments,
            "result": r.result,
            "duration_ms": r.duration_ms,
            "ok": r.ok,
            "risk": r.risk,
            "reason": r.reason,
            "approval_required": r.risk != "read",
            "approved_by": r.approved_by,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in records
    ]
