"""Backend API tests: authentication, RBAC, resources, incidents, audit, and agent streaming."""

import pytest
from httpx import ASGITransport, AsyncClient

from agent.agent import CloudOpsAgent
from backend.app.agent_service import set_agent
from backend.app.database import init_db
from backend.app.main import app
from tests.fakes import ScriptedChatModel, call, say

pytestmark = pytest.mark.asyncio


async def prepare_backend(registry):
    await init_db()
    agent = CloudOpsAgent(registry=registry)
    set_agent(agent)


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


async def test_auth_login_and_me(registry):
    await prepare_backend(registry)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Admin login
        token = await get_token(client, "admin@cloudops.ai", "admin123")
        res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "admin@cloudops.ai"
        assert data["role"] == "admin"

        # Invalid login
        bad = await client.post("/api/auth/login", json={"email": "admin@cloudops.ai", "password": "wrong"})
        assert bad.status_code == 401

        # Unauthenticated request
        unauth = await client.get("/api/auth/me")
        assert unauth.status_code == 401


async def test_rbac_permissions(registry):
    await prepare_backend(registry)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        viewer_token = await get_token(client, "viewer@cloudops.ai", "viewer123")
        operator_token = await get_token(client, "operator@cloudops.ai", "operator123")

        # Viewer cannot create an incident
        res_viewer = await client.post(
            "/api/incidents",
            json={"title": "Unauthorized incident", "severity": "LOW"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res_viewer.status_code == 403

        # Operator can create an incident
        res_op = await client.post(
            "/api/incidents",
            json={"title": "High latency on orders-api", "severity": "HIGH", "service": "orders-api"},
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert res_op.status_code == 201
        inc_id = res_op.json()["id"]

        # Operator can update incident
        patch_res = await client.patch(
            f"/api/incidents/{inc_id}",
            json={"status": "INVESTIGATING", "root_cause": "Database query latency regression"},
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "INVESTIGATING"


async def test_resources_and_metrics_via_mcp(registry):
    await prepare_backend(registry)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await get_token(client, "viewer@cloudops.ai", "viewer123")

        # Resources endpoint (queries MCP)
        res = await client.get("/api/resources", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert len(data["instances"]) > 0
        assert len(data["databases"]) > 0
        assert len(data["buckets"]) > 0

        # Metrics endpoint
        metrics_res = await client.get("/api/metrics", headers={"Authorization": f"Bearer {token}"})
        assert metrics_res.status_code == 200
        metrics = metrics_res.json()
        assert "agent" in metrics
        assert "incidents" in metrics


async def test_agent_chat_streaming(registry):
    await init_db()
    # Set scripted LLM into agent
    llm = ScriptedChatModel(steps=[
        say("Checking EC2 instances to see status.", call("aws__list_ec2_instances", state="running")),
        say("## Status Overview\n**Severity:** INFO\nAll instances running normally."),
    ])
    agent = CloudOpsAgent(registry=registry, llm=llm)
    set_agent(agent)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await get_token(client, "operator@cloudops.ai", "operator123")
        res = await client.post(
            "/api/agent/chat",
            json={"message": "Show active EC2 instances"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        body = res.text
        assert "tool_call_started" in body
        assert "final_report" in body

        # Verify audit endpoint captured the run and tool calls
        audit_res = await client.get("/api/audit", headers={"Authorization": f"Bearer {token}"})
        assert audit_res.status_code == 200
        audit_records = audit_res.json()
        assert len(audit_records) > 0
        assert any(r["tool"] == "list_ec2_instances" for r in audit_records)


async def test_approval_flow_and_id_matching(multi_mcp_registry):
    await init_db()
    llm = ScriptedChatModel(steps=[
        say("Proposing rollback.", call("github__rollback_deployment", target_commit="8c1d5fa")),
        say("Rollback completed."),
    ])
    agent = CloudOpsAgent(registry=multi_mcp_registry, llm=llm)
    set_agent(agent)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await get_token(client, "operator@cloudops.ai", "operator123")
        chat_res = await client.post(
            "/api/agent/chat",
            json={"message": "Rollback the bad deployment"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert chat_res.status_code == 200

        # Fetch pending approvals
        appr_res = await client.get("/api/approvals?status=pending", headers={"Authorization": f"Bearer {token}"})
        assert appr_res.status_code == 200
        approvals = appr_res.json()
        assert len(approvals) > 0
        appr_id = approvals[0]["id"]

        # Approve using specific approval ID
        decision_res = await client.post(
            f"/api/approval/{appr_id}",
            json={"approved": True, "comment": "Approved fix"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert decision_res.status_code == 200
        assert "text/event-stream" in decision_res.headers["content-type"]
