"""EC2 tools for the AWS MCP server."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

InstanceId = Annotated[str, Field(pattern=r"^i-[0-9a-f]{8,17}$", description="EC2 instance id, e.g. i-0abc123...")]

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
# Reboot/start are disruptive but recoverable; stop takes a workload offline.
DISRUPTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True)


def register(mcp: FastMCP, backend) -> None:
    @mcp.tool(annotations=READ)
    def list_ec2_instances(
        state: Annotated[
            Literal["pending", "running", "stopping", "stopped", "shutting-down", "terminated"] | None,
            Field(description="Optional instance-state filter"),
        ] = None,
    ) -> list[dict[str, Any]]:
        """List EC2 instances with name, type, state, IPs and tags (e.g. App, Env)."""
        return backend.list_ec2_instances(state)

    @mcp.tool(annotations=READ)
    def get_ec2_instance(instance_id: InstanceId) -> dict[str, Any]:
        """Get detailed configuration of one EC2 instance (security groups, VPC, IAM profile, launch time)."""
        return backend.get_ec2_instance(instance_id)

    @mcp.tool(annotations=READ)
    def get_ec2_status(instance_id: InstanceId) -> dict[str, Any]:
        """Get runtime state and system/instance status checks of an EC2 instance."""
        return backend.get_ec2_status(instance_id)

    @mcp.tool(annotations=DISRUPTIVE)
    def restart_ec2(instance_id: InstanceId) -> dict[str, Any]:
        """Reboot a running EC2 instance. Disruptive: requires human approval."""
        return backend.restart_ec2(instance_id)

    @mcp.tool(annotations=DISRUPTIVE)
    def start_ec2(instance_id: InstanceId) -> dict[str, Any]:
        """Start a stopped EC2 instance. Requires human approval."""
        return backend.start_ec2(instance_id)

    @mcp.tool(annotations=DISRUPTIVE)
    def stop_ec2(instance_id: InstanceId) -> dict[str, Any]:
        """Stop a running EC2 instance (takes the workload offline). HIGH risk: requires human approval."""
        return backend.stop_ec2(instance_id)
