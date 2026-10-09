"""Tests for DemoChatModel and zero-credential fallback behavior."""

import pytest
from langchain_core.messages import HumanMessage

from agent.agent import CloudOpsAgent
from agent.llm import DemoChatModel, llm_status


def test_demo_chat_model_status(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "demo")
    status = llm_status()
    assert status["configured"] is True
    assert status["provider"] == "demo"


@pytest.mark.asyncio
async def test_demo_chat_model_incident_flow():
    model = DemoChatModel()

    # Turn 0: User reports latency
    res0 = await model.ainvoke([HumanMessage("Orders API latency spiked! Can you check?")])
    assert len(res0.tool_calls) == 2
    assert res0.tool_calls[0]["name"] == "aws__get_recent_alarms"
    assert res0.tool_calls[1]["name"] == "aws__get_application_metrics"


@pytest.mark.asyncio
async def test_demo_chat_model_resource_queries():
    model = DemoChatModel()

    # EC2 query
    res_ec2 = await model.ainvoke([HumanMessage("Show active EC2 instances")])
    assert len(res_ec2.tool_calls) == 1
    assert res_ec2.tool_calls[0]["name"] == "aws__list_ec2_instances"

    # Docker query
    res_docker = await model.ainvoke([HumanMessage("List docker containers")])
    assert len(res_docker.tool_calls) == 1
    assert res_docker.tool_calls[0]["name"] == "docker__list_containers"


@pytest.mark.asyncio
async def test_agent_with_demo_model_e2e(multi_mcp_registry):
    agent = CloudOpsAgent(registry=multi_mcp_registry, llm=DemoChatModel())
    events = []
    async for ev in agent.run(
        thread_id="test-demo-thread",
        run_id="test-demo-run",
        message="Investigate high latency in orders-api",
        user_role="operator",
    ):
        events.append(ev)

    # Must require approval before high risk rollback
    approval_events = [e for e in events if e["type"] == "approval_required"]
    assert len(approval_events) > 0
    assert approval_events[0]["risk"] == "high"

