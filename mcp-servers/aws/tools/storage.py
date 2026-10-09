"""S3 and RDS read-only tools for the AWS MCP server."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .cloudwatch import Minutes, Period

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

Bucket = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", description="S3 bucket name")]
Database = Annotated[str, Field(pattern=r"^[a-zA-Z][a-zA-Z0-9-]{0,62}$", description="RDS DB instance identifier")]


def register(mcp: FastMCP, backend) -> None:
    # ----------------------------------------------------------------- S3
    @mcp.tool(annotations=READ)
    def list_buckets() -> list[dict[str, Any]]:
        """List S3 buckets with region and creation date."""
        return backend.list_buckets()

    @mcp.tool(annotations=READ)
    def get_bucket_details(bucket: Bucket) -> dict[str, Any]:
        """S3 bucket configuration: versioning, default encryption, size."""
        return backend.get_bucket_details(bucket)

    @mcp.tool(annotations=READ)
    def check_bucket_public_access(bucket: Bucket) -> dict[str, Any]:
        """Evaluate whether an S3 bucket is publicly accessible (Public Access Block, policy, ACL)."""
        return backend.check_bucket_public_access(bucket)

    # ----------------------------------------------------------------- RDS
    @mcp.tool(annotations=READ)
    def list_databases() -> list[dict[str, Any]]:
        """List RDS database instances with engine, class, status and tags."""
        return backend.list_databases()

    @mcp.tool(annotations=READ)
    def get_database_status(database: Database) -> dict[str, Any]:
        """Status and configuration of one RDS instance."""
        return backend.get_database_status(database)

    @mcp.tool(annotations=READ)
    def get_database_metrics(database: Database, minutes: Minutes = 30, period: Period = 60) -> dict[str, Any]:
        """RDS CloudWatch metrics: CPU, read/write latency (ms), connections, read IOPS."""
        return backend.get_database_metrics(database, minutes, period)
