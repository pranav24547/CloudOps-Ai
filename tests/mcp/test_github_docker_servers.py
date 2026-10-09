"""MCP tests for GitHub and Docker servers."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_github_mcp_tools(multi_mcp_registry):
    tools = await multi_mcp_registry.refresh()
    assert multi_mcp_registry.server_status["github"]["status"] == "connected"
    assert "github__get_recent_commits" in tools
    assert "github__trigger_workflow" in tools
    assert "github__rollback_deployment" in tools

    # Test commit listing
    res = await multi_mcp_registry.call("github", "get_recent_commits", {"limit": 3})
    assert res.ok
    assert len(res.data) > 0
    assert any("9f3c2ab" in c["short_sha"] for c in res.data)

    # Test commit details
    detail = await multi_mcp_registry.call("github", "get_commit_details", {"commit_sha": "9f3c2ab"})
    assert detail.ok
    assert "patch_summary" in detail.data

    # Test workflow runs
    wf = await multi_mcp_registry.call("github", "get_workflow_runs", {"limit": 10})
    assert wf.ok
    assert any(r["run_id"] == "184" for r in wf.data)


async def test_docker_mcp_tools(multi_mcp_registry):
    tools = await multi_mcp_registry.refresh()
    assert multi_mcp_registry.server_status["docker"]["status"] == "connected"
    assert "docker__list_containers" in tools
    assert "docker__restart_container" in tools

    # List containers
    res = await multi_mcp_registry.call("docker", "list_containers", {})
    assert res.ok
    containers = res.data
    assert len(containers) >= 2
    orders_c = next(c for c in containers if "orders" in c["name"])

    # Container stats
    stats = await multi_mcp_registry.call("docker", "get_container_stats", {"container": orders_c["name"]})
    assert stats.ok
    assert "cpu_percent" in stats.data

    # Container logs
    logs = await multi_mcp_registry.call("docker", "get_container_logs", {"container": orders_c["name"], "lines": 10})
    assert logs.ok
    assert len(logs.data["lines"]) > 0

    # Restart container
    restart = await multi_mcp_registry.call("docker", "restart_container", {"container": orders_c["name"]})
    assert restart.ok
    assert restart.data["status"] == "restarted"
