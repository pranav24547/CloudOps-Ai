"""Incident management endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, require_role
from ..database import get_db
from ..models import Incident, User

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


class CreateIncidentRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    severity: str = "HIGH"
    service: str = "orders-api"
    root_cause: str | None = None
    run_id: str | None = None


class UpdateIncidentRequest(BaseModel):
    status: str | None = None  # OPEN, INVESTIGATING, MITIGATED, RESOLVED
    root_cause: str | None = None
    resolution: str | None = None


@router.get("")
async def list_incidents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
):
    query = select(Incident).order_by(desc(Incident.created_at))
    if status:
        query = query.where(Incident.status == status)
    result = await db.execute(query.limit(50))
    incidents = result.scalars().all()
    return [
        {
            "id": inc.id,
            "title": inc.title,
            "severity": inc.severity,
            "status": inc.status,
            "service": inc.service,
            "root_cause": inc.root_cause,
            "resolution": inc.resolution,
            "run_id": inc.run_id,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
        }
        for inc in incidents
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_incident(
    req: CreateIncidentRequest,
    current_user: Annotated[User, Depends(require_role("operator", "admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    inc = Incident(
        title=req.title,
        severity=req.severity,
        service=req.service,
        status="OPEN",
        root_cause=req.root_cause,
        run_id=req.run_id,
    )
    db.add(inc)
    await db.commit()
    await db.refresh(inc)
    return {
        "id": inc.id,
        "title": inc.title,
        "severity": inc.severity,
        "status": inc.status,
        "service": inc.service,
        "created_at": inc.created_at.isoformat(),
    }


@router.patch("/{incident_id}")
async def update_incident(
    incident_id: str,
    req: UpdateIncidentRequest,
    current_user: Annotated[User, Depends(require_role("operator", "admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    inc = result.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    if req.status:
        inc.status = req.status
        if req.status == "RESOLVED":
            inc.resolved_at = datetime.now(timezone.utc)
    if req.root_cause is not None:
        inc.root_cause = req.root_cause
    if req.resolution is not None:
        inc.resolution = req.resolution

    await db.commit()
    await db.refresh(inc)
    return {
        "id": inc.id,
        "title": inc.title,
        "status": inc.status,
        "root_cause": inc.root_cause,
        "resolution": inc.resolution,
        "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
    }
