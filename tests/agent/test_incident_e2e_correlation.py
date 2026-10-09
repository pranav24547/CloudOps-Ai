"""End-to-end Multi-MCP Incident Investigation and Remediation Workflow.

Implements the centerpiece demo workflow specified in Section 13 & 37:
1. User reports latency spike.
2. Agent queries AWS CloudWatch alarms, metrics, and application logs.
3. Agent queries AWS RDS metrics (database latency increased 340%).
4. Agent queries GitHub recent deployments and commits (deployment #184 13 mins ago with slow query).
5. Agent correlates timestamps across AWS and GitHub: identifies root cause with high confidence.
6. Agent proposes rollback action -> Gated by HITL approval.
7. Human operator approves.
8. Agent executes rollback through GitHub MCP.
9. Agent performs post-action verification using AWS CloudWatch.
10. Agent outputs complete auditable incident analysis report.
"""

import pytest

from agent.agent import CloudOpsAgent
from tests.fakes import ScriptedChatModel, call, say

pytestmark = pytest.mark.asyncio


async def test_full_incident_investigation_and_rollback_workflow(multi_mcp_registry):
    """Full autonomous investigation and remediation correlating AWS, GitHub, and Docker MCP tools."""
    llm = ScriptedChatModel(steps=[
        # Turn 1: Start investigation by checking alarms and application latency
        say(
            "Starting incident investigation. Checking CloudWatch alarms and application metrics for orders-api.",
            call("aws__get_recent_alarms", state="ALARM"),
            call("aws__get_application_metrics", service="orders-api", minutes=20),
        ),
        # Turn 2: Inspect application logs and RDS database metrics
        say(
            "P99 latency is 2.8s and latency alarms are firing. Checking application logs and database performance.",
            call("aws__get_application_logs", service="orders-api", minutes=20, limit=20),
            call("aws__get_database_metrics", database="orders-db", minutes=20),
        ),
        # Turn 3: Database read latency spiked and logs show DB pool timeouts. Check recent deployments in GitHub.
        say(
            "Application logs show database timeouts and RDS read latency spiked 340%. Checking recent CI/CD deployments and commits in GitHub.",
            call("github__get_workflow_runs", limit=3),
            call("github__get_recent_commits", limit=3),
        ),
        # Turn 4: Deployment #184 with commit 9f3c2ab deployed right before the incident started. Inspect commit details.
        say(
            "Deployment #184 finished 13 minutes ago for commit 9f3c2ab. Inspecting commit diff details.",
            call("github__get_commit_details", commit_sha="9f3c2ab"),
        ),
        # Turn 5: Root cause confirmed: commit 9f3c2ab added un-indexed query. Propose rollback deployment #184 to commit 8c1d5fa.
        say(
            "Root cause identified: commit 9f3c2ab in deployment #184 introduced an un-indexed JOIN query causing database connection pool exhaustion. "
            "I recommend an immediate rollback to previous stable commit 8c1d5fa.",
            call("github__rollback_deployment", target_commit="8c1d5fa"),
        ),
        # Turn 6: After human approval and rollback execution: agent MUST verify before writing final report!
        say(
            "Rollback initiated. Now verifying application health and alarm status.",
            call("aws__get_application_metrics", service="orders-api", minutes=5),
            call("aws__get_recent_alarms", state=None),
        ),
        # Turn 7: Final incident report
        say(
            "## INCIDENT ANALYSIS & RESOLUTION REPORT\n"
            "**Severity:** HIGH\n"
            "**Status:** RESOLVED\n"
            "**Summary:** Production API latency increased from 220ms to 2.8s due to inefficient query in deployment #184.\n"
            "### Findings\n"
            "- EC2 CPU at 91%, Memory at 84%\n"
            "- RDS read latency spiked by 340%\n"
            "- Application logs confirm DB pool exhaustion and 504 timeouts\n"
            "- GitHub Actions run #184 deployed commit 9f3c2ab 13 minutes prior to alarm\n"
            "### Root Cause\n"
            "Commit 9f3c2ab added customer order history query without supporting index.\n"
            "**Confidence:** 92%\n"
            "### Actions Taken & Verification\n"
            "1. Approved and executed rollback to commit 8c1d5fa via GitHub MCP.\n"
            "2. Verified application latency and instance health returned to nominal baseline."
        ),
    ])

    agent = CloudOpsAgent(registry=multi_mcp_registry, llm=llm)
    thread_id = "inc-thread-101"
    run_id = "inc-run-101"

    # Step 1: Run agent until it pauses for human approval
    events_phase1 = []
    async for ev in agent.run(
        thread_id=thread_id,
        run_id=run_id,
        message="Production API latency suddenly increased. Find out what happened and fix it if possible.",
        user_role="operator",
    ):
        events_phase1.append(ev)

    # Must have discovered tools across all 3 servers
    discovered_ev = next(e for e in events_phase1 if e["type"] == "tools_discovered")
    assert "aws" in discovered_ev["servers"]
    assert "github" in discovered_ev["servers"]
    assert "docker" in discovered_ev["servers"]

    # Verify tool calls were executed across AWS and GitHub
    executed_tools = [e["tool"] for e in events_phase1 if e["type"] == "tool_call_finished"]
    assert "get_recent_alarms" in executed_tools
    assert "get_application_logs" in executed_tools
    assert "get_database_metrics" in executed_tools
    assert "get_workflow_runs" in executed_tools
    assert "get_commit_details" in executed_tools

    # Must require approval for rollback_deployment
    approval_req = next((e for e in events_phase1 if e["type"] == "approval_required"), None)
    assert approval_req is not None
    assert any(a["tool"] == "rollback_deployment" for a in approval_req["actions"])
    assert approval_req["risk"] == "high"

    # Step 2: Human Operator approves the rollback action
    events_phase2 = []
    async for ev in agent.resume(
        thread_id=thread_id,
        decision={
            "approved": True,
            "approved_by": "oncall-lead@acme.com",
            "approver_role": "operator",
            "comment": "Approved rollback to 8c1d5fa",
        },
    ):
        events_phase2.append(ev)

    event_types_p2 = [e["type"] for e in events_phase2]
    assert "approval_decision" in event_types_p2
    assert "tool_call_finished" in event_types_p2  # rollback executed
    assert "final_report" in event_types_p2
    assert "run_completed" in event_types_p2

    # Verify rollback was actually called on GitHub server
    rollback_res = next(e for e in events_phase2 if e["type"] == "tool_call_finished" and e["tool"] == "rollback_deployment")
    assert rollback_res["ok"] is True
    assert rollback_res["approved_by"] == "oncall-lead@acme.com"

    # Verify report contents
    report_ev = next(e for e in events_phase2 if e["type"] == "final_report")
    assert "INCIDENT ANALYSIS & RESOLUTION REPORT" in report_ev["report"]
    assert "deployment #184" in report_ev["report"]
    assert "9f3c2ab" in report_ev["report"]
