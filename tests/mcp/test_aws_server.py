"""AWS MCP server tests - through the MCP protocol, as any MCP client would use it."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_tools_are_discoverable_with_annotations(registry):
    tools = await registry.refresh()
    assert registry.server_status["aws"]["status"] == "connected"
    names = {t.name for t in tools.values()}
    assert {"list_ec2_instances", "get_cpu_metrics", "list_buckets", "get_database_status", "restart_ec2"} <= names
    assert tools["aws__list_ec2_instances"].annotations["readOnlyHint"] is True
    assert tools["aws__restart_ec2"].annotations["destructiveHint"] is True


async def test_list_ec2(registry):
    res = await registry.call("aws", "list_ec2_instances", {})
    assert res.ok
    ids = {i["instance_id"] for i in res.data}
    assert "i-0a1f3c9e7b2d41001" in ids
    running = await registry.call("aws", "list_ec2_instances", {"state": "stopped"})
    assert all(i["state"] == "stopped" for i in running.data)


async def test_cloudwatch_metrics(registry):
    res = await registry.call("aws", "get_cpu_metrics", {"instance_id": "i-0a1f3c9e7b2d41001", "minutes": 30})
    assert res.ok
    assert res.data["metric"] == "CPUUtilization"
    assert res.data["maximum"] > 80          # incident is visible
    assert len(res.data["datapoints"]) == 30
    alarms = await registry.call("aws", "get_recent_alarms", {})
    assert any(a["name"] == "orders-api-p99-latency-high" for a in alarms.data)


async def test_s3_and_rds(registry):
    public = await registry.call("aws", "check_bucket_public_access", {"bucket": "orders-app-static-assets"})
    assert public.data["is_public"] is True
    db = await registry.call("aws", "get_database_status", {"database": "orders-db"})
    assert db.data["status"] == "available"


async def test_server_rejects_invalid_arguments(registry):
    res = await registry.call("aws", "get_cpu_metrics", {"instance_id": "rm -rf /"})
    assert not res.ok
    assert "instance_id" in res.text


async def test_unknown_resource_is_error(registry):
    res = await registry.call("aws", "get_ec2_instance", {"instance_id": "i-0000000000000dead"})
    assert not res.ok
    assert "not found" in res.text
