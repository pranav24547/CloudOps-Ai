"""Docker MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
LOW_RISK = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)


def register(mcp: FastMCP, backend) -> None:
    @mcp.tool(annotations=READ)
    def list_containers(
        all_containers: Annotated[bool, Field(description="Show all containers including stopped ones")] = False,
    ) -> list[dict[str, Any]]:
        """List running application containers (names, status, ports, CPU and memory)."""
        return backend.list_containers(all_containers)

    @mcp.tool(annotations=READ)
    def get_container_status(
        container: Annotated[str, Field(description="Container ID or name, e.g. orders-api-prod-1")],
    ) -> dict[str, Any]:
        """Get container runtime status, health state, image tag and restart counter."""
        return backend.get_container_status(container)

    @mcp.tool(annotations=READ)
    def get_container_logs(
        container: Annotated[str, Field(description="Container ID or name")],
        lines: Annotated[int, Field(ge=1, le=500, description="Number of recent log lines")] = 50,
    ) -> dict[str, Any]:
        """Retrieve stdout/stderr logs from a specific container."""
        return backend.get_container_logs(container, lines)

    @mcp.tool(annotations=READ)
    def get_container_stats(
        container: Annotated[str, Field(description="Container ID or name")],
    ) -> dict[str, Any]:
        """Fetch live resource consumption metrics: CPU percentage and memory utilization."""
        return backend.get_container_stats(container)

    @mcp.tool(annotations=LOW_RISK)
    def restart_container(
        container: Annotated[str, Field(description="Container ID or name to restart")],
    ) -> dict[str, Any]:
        """Restart a container. Low-risk write action."""
        return backend.restart_container(container)

    @mcp.tool(annotations=READ)
    def list_images() -> list[dict[str, Any]]:
        """List local docker container images and tags available for deployment."""
        return backend.list_images()
