"""GitHub MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
LOW_RISK = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
HIGH_RISK = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True)


def register(mcp: FastMCP, backend) -> None:
    @mcp.tool(annotations=READ)
    def get_repository_info() -> dict[str, Any]:
        """Get repository name, default branch, stars, and open issues."""
        return backend.get_repository_info()

    @mcp.tool(annotations=READ)
    def get_recent_commits(
        limit: Annotated[int, Field(ge=1, le=50, description="Max commits to return")] = 5,
    ) -> list[dict[str, Any]]:
        """List recent git commits on the default branch (author, timestamp, sha, commit message)."""
        return backend.get_recent_commits(limit)

    @mcp.tool(annotations=READ)
    def get_commit_details(
        commit_sha: Annotated[str, Field(pattern=r"^[0-9a-f]{7,40}$", description="Commit SHA hash")],
    ) -> dict[str, Any]:
        """Inspect specific commit diff stats, changed files, and patch summary."""
        return backend.get_commit_details(commit_sha)

    @mcp.tool(annotations=READ)
    def list_pull_requests(
        state: Annotated[str, Field(description="Pull request state: open, closed, or all")] = "all",
    ) -> list[dict[str, Any]]:
        """List recent pull requests, branches and merge status."""
        return backend.list_pull_requests(state)

    @mcp.tool(annotations=READ)
    def get_pull_request(
        pr_number: Annotated[int, Field(ge=1, description="Pull request number")],
    ) -> dict[str, Any]:
        """Get full details of a specific pull request."""
        return backend.get_pull_request(pr_number)

    @mcp.tool(annotations=READ)
    def get_workflow_runs(
        limit: Annotated[int, Field(ge=1, le=50, description="Number of workflow runs to fetch")] = 5,
    ) -> list[dict[str, Any]]:
        """List recent CI/CD workflow and deployment pipeline runs."""
        return backend.get_workflow_runs(limit)

    @mcp.tool(annotations=READ)
    def get_workflow_status(
        run_id: Annotated[str, Field(description="Workflow run ID")],
    ) -> dict[str, Any]:
        """Check status and conclusion of a specific GitHub Actions workflow run."""
        return backend.get_workflow_status(run_id)

    @mcp.tool(annotations=HIGH_RISK)
    def trigger_workflow(
        workflow_id: Annotated[str, Field(description="Workflow filename or identifier, e.g. deploy.yml")],
        ref: Annotated[str, Field(description="Git branch, tag or commit SHA")] = "main",
    ) -> dict[str, Any]:
        """Trigger a GitHub Actions workflow dispatch. HIGH risk: requires approval."""
        return backend.trigger_workflow(workflow_id, ref)

    @mcp.tool(annotations=HIGH_RISK)
    def rollback_deployment(
        target_commit: Annotated[str, Field(description="Commit SHA or tag to rollback to")],
    ) -> dict[str, Any]:
        """Initiate automated deployment rollback to a known good release commit. HIGH risk: requires approval."""
        return backend.rollback_deployment(target_commit)

    @mcp.tool(annotations=LOW_RISK)
    def create_issue(
        title: Annotated[str, Field(min_length=3, max_length=200, description="Issue title")],
        description: Annotated[str, Field(min_length=1, description="Markdown issue description")],
    ) -> dict[str, Any]:
        """Create a new GitHub tracking issue for an incident or bug."""
        return backend.create_issue(title, description)
