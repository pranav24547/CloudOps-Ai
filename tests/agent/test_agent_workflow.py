"""LangGraph agent workflow tests.

Exercises the real graph and real MCP server using the ScriptedChatModel test double,
verifying:
- Multi-step dynamic tool calling
- Human-in-the-loop approval gating (interrupt / resume)
- Role-based authorization
- Post-remediation verification
"""

import pytest

from agent.agent import CloudOpsAgent
from tests.fakes import ScriptedChatModel, call, say

pytestmark = pytest.mark.asyncio


async def test_agent_investigation_workflow(registry):
    """Simulates an investigation: agent checks alarms -> finds orders-api latency -> reads metrics -> produces report."""
    llm = ScriptedChatModel(steps=[
        say("I should check recent alarms first.", call("aws__get_recent_alarms", state="ALARM")),
        say("Found latency alarm on orders-api. Let's check CPU and application metrics.",
            call("aws__get_cpu_metrics", instance_id="i-0a1f3c9e7b2d41001", minutes=15),
            call("aws__get_application_metrics", service="orders-api", minutes=15)),
        say("## Incident Report\n**Severity:** HIGH\n**Summary:** orders-api p99 latency spiked.\n"
            "### Findings\n- CPU at 91%\n- p99 latency increased to 2.8s\n"
            "### Likely Root Cause\nDatabase query latency.\n**Confidence:** 85%\n"
            "### Recommended Actions\n1. Check RDS queries"),
    ])

    agent = CloudOpsAgent(registry=registry, llm=llm)
    events = []
    async for ev in agent.run(thread_id="test-inv-1", run_id="run-1",
                             message="Why is the orders API slow?", user_role="viewer"):
        events.append(ev)

    event_types = [e["type"] for e in events]
    assert "tools_discovered" in event_types
    assert "tool_call_started" in event_types
    assert "tool_call_finished" in event_types
    assert "final_report" in event_types
    assert "run_completed" in event_types

    report_ev = next(e for e in events if e["type"] == "final_report")
    assert "Incident Report" in report_ev["report"]


async def test_agent_approval_gated_write(registry):
    """Verifies that an infrastructure modification (restart_ec2) pauses for human approval,

    and upon approval executes and requires verification.
    """
    llm = ScriptedChatModel(steps=[
        say("CPU is critical on i-0a1f3c9e7b2d41001. I recommend rebooting it.",
            call("aws__restart_ec2", instance_id="i-0a1f3c9e7b2d41001")),
        # Step after reboot: verification step
        say("Reboot executed. Let me check the instance status check to verify.",
            call("aws__get_ec2_status", instance_id="i-0a1f3c9e7b2d41001")),
        say("## Remediation Complete\n**Severity:** MEDIUM\nInstance rebooted and verified online."),
    ])

    agent = CloudOpsAgent(registry=registry, llm=llm)
    events_run = []
    async for ev in agent.run(thread_id="test-appr-1", run_id="run-2",
                             message="Restart instance i-0a1f3c9e7b2d41001", user_role="operator"):
        events_run.append(ev)

    # Must produce approval_required interrupt
    approval_ev = next((e for e in events_run if e["type"] == "approval_required"), None)
    assert approval_ev is not None
    assert approval_ev["risk"] in ("medium", "high")
    assert any(a["tool"] == "restart_ec2" for a in approval_ev["actions"])

    # Resume with approval
    events_resume = []
    async for ev in agent.resume(thread_id="test-appr-1",
                                decision={"approved": True, "approved_by": "lead-sre", "approver_role": "operator"}):
        events_resume.append(ev)

    resume_types = [e["type"] for e in events_resume]
    assert "approval_decision" in resume_types
    assert "tool_call_finished" in resume_types
    assert "run_completed" in resume_types


async def test_agent_approval_rejected(registry):
    """Verifies that when a human rejects an action, it is skipped and reported."""
    llm = ScriptedChatModel(steps=[
        say("I recommend stopping instance i-0a1f3c9e7b2d41001.",
            call("aws__stop_ec2", instance_id="i-0a1f3c9e7b2d41001")),
        say("## Action Cancelled\n**Severity:** LOW\nAction was not approved by human operator."),
    ])

    agent = CloudOpsAgent(registry=registry, llm=llm)
    events_run = []
    async for ev in agent.run(thread_id="test-appr-2", run_id="run-3",
                             message="Stop instance i-0a1f3c9e7b2d41001", user_role="operator"):
        events_run.append(ev)

    assert any(e["type"] == "approval_required" for e in events_run)

    # Resume with rejection
    events_resume = []
    async for ev in agent.resume(thread_id="test-appr-2",
                                decision={"approved": False, "approved_by": "lead-sre",
                                          "approver_role": "operator", "comment": "Do not stop during peak hours"}):
        events_resume.append(ev)

    # Verify tool was skipped, not executed
    skipped_ev = next(e for e in events_resume if e["type"] == "tool_call_skipped")
    assert skipped_ev["status"] == "rejected"


async def test_viewer_role_cannot_request_write(registry):
    """A viewer role is unauthorized to initiate write actions."""
    llm = ScriptedChatModel(steps=[
        say("Attempting to restart instance.",
            call("aws__restart_ec2", instance_id="i-0a1f3c9e7b2d41001")),
        say("## Denied\n**Severity:** INFO\nOperation not permitted for viewer."),
    ])

    agent = CloudOpsAgent(registry=registry, llm=llm)
    events = []
    async for ev in agent.run(thread_id="test-viewer-1", run_id="run-4",
                             message="Restart i-0a1f3c9e7b2d41001", user_role="viewer"):
        events.append(ev)

    planned = next(e for e in events if e["type"] == "tool_call_planned")
    assert planned["status"] == "denied"
    assert not any(e["type"] == "approval_required" for e in events)
