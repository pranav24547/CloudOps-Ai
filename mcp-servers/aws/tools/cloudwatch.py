"""CloudWatch metrics, logs and alarms tools for the AWS MCP server."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .ec2 import InstanceId

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

Minutes = Annotated[int, Field(ge=5, le=1440, description="Look-back window in minutes")]
Period = Annotated[int, Field(ge=60, le=3600, multiple_of=60, description="Datapoint period in seconds")]
Service = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$", description="Application/service name")]


def register(mcp: FastMCP, backend) -> None:
    @mcp.tool(annotations=READ)
    def get_cpu_metrics(instance_id: InstanceId, minutes: Minutes = 30, period: Period = 60) -> dict[str, Any]:
        """CloudWatch CPUUtilization for an EC2 instance (latest/avg/max + datapoints)."""
        return backend.get_cpu_metrics(instance_id, minutes, period)

    @mcp.tool(annotations=READ)
    def get_memory_metrics(instance_id: InstanceId, minutes: Minutes = 30, period: Period = 60) -> dict[str, Any]:
        """Memory utilisation (CloudWatch Agent mem_used_percent) for an EC2 instance."""
        return backend.get_memory_metrics(instance_id, minutes, period)

    @mcp.tool(annotations=READ)
    def get_network_metrics(instance_id: InstanceId, minutes: Minutes = 30, period: Period = 60) -> dict[str, Any]:
        """NetworkIn / NetworkOut bytes for an EC2 instance."""
        return backend.get_network_metrics(instance_id, minutes, period)

    @mcp.tool(annotations=READ)
    def get_application_metrics(service: Service, minutes: Minutes = 30, period: Period = 60) -> dict[str, Any]:
        """Application-level metrics for a service: p99 latency, request rate and error rate."""
        return backend.get_application_metrics(service, minutes, period)

    @mcp.tool(annotations=READ)
    def get_application_logs(
        service: Service,
        minutes: Minutes = 30,
        filter_pattern: Annotated[str | None, Field(max_length=200, description="Case-insensitive text filter")] = None,
        limit: Annotated[int, Field(ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        """Recent application log events from CloudWatch Logs group /app/<service>."""
        return backend.get_application_logs(service, minutes, filter_pattern, limit)

    @mcp.tool(annotations=READ)
    def get_recent_alarms(
        state: Annotated[Literal["ALARM", "OK", "INSUFFICIENT_DATA"] | None,
                         Field(description="Alarm state filter; null for all")] = "ALARM",
    ) -> list[dict[str, Any]]:
        """CloudWatch alarms (default: those currently in ALARM) with threshold and when they changed state."""
        return backend.get_recent_alarms(state)
