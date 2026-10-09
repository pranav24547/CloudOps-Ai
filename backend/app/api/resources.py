"""Infrastructure resources and observability metrics endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent_service import get_agent
from ..auth.dependencies import get_current_user
from ..database import get_db
from ..models import AgentRun, ApprovalRecord, Incident, ToolCallRecord, User

router = APIRouter(prefix="/api", tags=["resources"])


@router.get("/resources")
async def get_resources(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Retrieves live infrastructure status across EC2, RDS, S3, and CloudWatch Alarms through the real MCP client."""
    agent = get_agent()
    registry = agent.registry

    # Execute MCP read tools
    ec2_res = await registry.call("aws", "list_ec2_instances", {})
    rds_res = await registry.call("aws", "list_databases", {})
    s3_res = await registry.call("aws", "list_buckets", {})
    alarms_res = await registry.call("aws", "get_recent_alarms", {})

    instances = ec2_res.data if ec2_res.ok else []
    databases = rds_res.data if rds_res.ok else []
    buckets = s3_res.data if s3_res.ok else []
    alarms = alarms_res.data if alarms_res.ok else []

    return {
        "instances": instances,
        "databases": databases,
        "buckets": buckets,
        "alarms": alarms,
        "mcp_servers": registry.server_status,
    }


@router.get("/metrics")
async def get_metrics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Observability metrics tracking agent execution, MCP calls, approvals and infrastructure health."""
    agent = get_agent()
    registry = agent.registry

    # Query DB stats
    total_runs = (await db.execute(select(func.count(AgentRun.id)))).scalar() or 0
    successful_runs = (
        await db.execute(select(func.count(AgentRun.id)).where(AgentRun.status == "completed"))
    ).scalar() or 0
    failed_runs = (
        await db.execute(select(func.count(AgentRun.id)).where(AgentRun.status == "failed"))
    ).scalar() or 0

    total_tool_calls = (await db.execute(select(func.count(ToolCallRecord.id)))).scalar() or 0
    total_approvals = (await db.execute(select(func.count(ApprovalRecord.id)))).scalar() or 0
    pending_approvals = (
        await db.execute(select(func.count(ApprovalRecord.id)).where(ApprovalRecord.status == "pending"))
    ).scalar() or 0

    open_incidents = (
        await db.execute(select(func.count(Incident.id)).where(Incident.status.in_(["OPEN", "INVESTIGATING"])))
    ).scalar() or 0
    resolved_incidents = (
        await db.execute(select(func.count(Incident.id)).where(Incident.status == "RESOLVED"))
    ).scalar() or 0

    # Application metrics for orders-api from MCP
    app_metrics = await registry.call("aws", "get_application_metrics", {"service": "orders-api", "minutes": 15})

    return {
        "agent": {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "total_tool_calls": total_tool_calls,
            "total_approvals": total_approvals,
            "pending_approvals": pending_approvals,
            "connected_servers": len([s for s, st in registry.server_status.items() if st.get("status") == "connected"]),
        },
        "incidents": {
            "open": open_incidents,
            "resolved": resolved_incidents,
        },
        "application_telemetry": app_metrics.data if app_metrics.ok else None,
    }
