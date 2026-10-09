"""LLM provider factory. Provider is chosen with ``LLM_PROVIDER`` (anthropic | openai | gemini | demo)."""

from __future__ import annotations

import os
import uuid
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4.1",
    "gemini": "gemini-2.5-flash",
    "demo": "cloudops-demo-engine",
}
KEY_VARS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GOOGLE_API_KEY"}


class LLMNotConfigured(RuntimeError):
    pass


def _tool_call(name: str, **args: Any) -> dict[str, Any]:
    return {"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:10]}", "type": "tool_call"}


class DemoChatModel(BaseChatModel):
    """Zero-credential simulated LLM for realistic demo walkthroughs.

    Correlates across AWS, GitHub, and Docker MCP tools deterministically
    when investigating operational latency and outages.
    """

    _bound_tools: list[list[str]] = PrivateAttr(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "demo"

    def bind_tools(self, tools, **kwargs):  # type: ignore[override]
        self._bound_tools.append([t["function"]["name"] for t in tools])
        return self

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        user_prompt = ""
        for m in messages:
            if isinstance(m, HumanMessage):
                user_prompt = str(m.content).lower()
                break

        ai_msgs = [m for m in messages if isinstance(m, AIMessage)]
        turn = len(ai_msgs)

        # Check if this is the latency / incident investigation scenario
        is_incident = any(
            k in user_prompt
            for k in (
                "latency",
                "slow",
                "incident",
                "investigate",
                "orders",
                "alarm",
                "error",
                "outage",
                "p99",
                "fix",
                "pool",
            )
        )

        if is_incident:
            if turn == 0:
                msg = AIMessage(
                    content="Starting incident investigation. Checking CloudWatch alarms and application metrics for orders-api.",
                    tool_calls=[
                        _tool_call("aws__get_recent_alarms", state="ALARM"),
                        _tool_call("aws__get_application_metrics", service="orders-api", minutes=20),
                    ],
                )
            elif turn == 1:
                msg = AIMessage(
                    content="P99 latency is elevated and latency alarms are firing. Checking application logs and database performance.",
                    tool_calls=[
                        _tool_call("aws__get_application_logs", service="orders-api", minutes=20, limit=20),
                        _tool_call("aws__get_database_metrics", database="orders-db", minutes=20),
                    ],
                )
            elif turn == 2:
                msg = AIMessage(
                    content="Application logs show database timeouts and RDS read latency spiked. Checking recent CI/CD deployments and commits in GitHub.",
                    tool_calls=[
                        _tool_call("github__get_workflow_runs", limit=3),
                        _tool_call("github__get_recent_commits", limit=3),
                    ],
                )
            elif turn == 3:
                msg = AIMessage(
                    content="Deployment #184 finished 13 minutes ago for candidate commit. Inspecting commit diff details.",
                    tool_calls=[
                        _tool_call("github__get_commit_details", commit_sha="9f3c2ab"),
                    ],
                )
            elif turn == 4:
                msg = AIMessage(
                    content=(
                        "Root cause identified: commit 9f3c2ab in deployment #184 introduced an un-indexed JOIN query "
                        "causing database connection pool exhaustion. I recommend an immediate rollback to previous stable commit 8c1d5fa."
                    ),
                    tool_calls=[
                        _tool_call("github__rollback_deployment", target_commit="8c1d5fa"),
                    ],
                )
            elif turn == 5:
                # Post-approval verification
                msg = AIMessage(
                    content="Rollback initiated. Now verifying application health and alarm status.",
                    tool_calls=[
                        _tool_call("aws__get_application_metrics", service="orders-api", minutes=5),
                        _tool_call("aws__get_recent_alarms", state=None),
                    ],
                )
            else:
                tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
                has_errors = any("error" in str(m.content).lower() for m in tool_messages[-2:])
                status = "RESOLVED" if not has_errors else "FAILED"
                verification_note = (
                    "Verified application latency returned to nominal baseline and all CloudWatch alarms cleared."
                    if not has_errors
                    else "Verification probe detected residual errors or alarms."
                )

                msg = AIMessage(
                    content=(
                        "## INCIDENT ANALYSIS & RESOLUTION REPORT\n"
                        "**Severity:** HIGH\n"
                        f"**Status:** {status}\n"
                        "**Summary:** Production API latency increased due to inefficient query in deployment #184.\n\n"
                        "### Findings\n"
                        "- Elevated P99 latency and RDS read latency detected\n"
                        "- Application logs confirm connection pool exhaustion and gateway timeouts\n"
                        "- GitHub Actions deployment #184 preceded the incident onset\n\n"
                        "### Root Cause\n"
                        "Commit 9f3c2ab added customer order history query without supporting index.\n"
                        "**Confidence:** 92%\n\n"
                        "### Actions Taken & Verification\n"
                        "1. Executed rollback to commit 8c1d5fa via GitHub MCP.\n"
                        f"2. {verification_note}"
                    )
                )
        elif any(k in user_prompt for k in ("ec2", "instance", "server", "vm")):
            if turn == 0:
                msg = AIMessage(
                    content="Checking EC2 instances to see status.",
                    tool_calls=[_tool_call("aws__list_ec2_instances")],
                )
            else:
                msg = AIMessage(
                    content="## EC2 Status Overview\n**Severity:** INFO\nAll instances are running normally with nominal metrics."
                )
        elif any(k in user_prompt for k in ("docker", "container")):
            if turn == 0:
                msg = AIMessage(
                    content="Checking Docker containers.",
                    tool_calls=[_tool_call("docker__list_containers")],
                )
            else:
                msg = AIMessage(
                    content="## Docker Container Status\n**Severity:** INFO\nAll containers are healthy and operational."
                )
        elif any(k in user_prompt for k in ("security", "audit", "s3", "bucket")):
            if turn == 0:
                msg = AIMessage(
                    content="Running security audit on S3 buckets.",
                    tool_calls=[_tool_call("aws__list_buckets")],
                )
            else:
                msg = AIMessage(
                    content="## Security Audit Report\n**Severity:** LOW\nPublic Access Block is active across all sensitive artifact buckets."
                )
        else:
            msg = AIMessage(
                content=(
                    "Hello! I am CloudOps AI Assistant. I can help investigate infrastructure latency, "
                    "analyze CloudWatch alarms, audit S3/EC2, or inspect GitHub deployments and Docker containers.\n\n"
                    "Try asking: *'Investigate why production latency spiked and fix it.'*"
                )
            )

        return ChatResult(generations=[ChatGeneration(message=msg)])


def llm_status() -> dict[str, object]:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "demo":
        return {"provider": "demo", "model": "cloudops-demo-engine", "configured": True}
    key_var = KEY_VARS.get(provider, "")
    has_key = bool(os.getenv(key_var, ""))
    return {
        "provider": provider,
        "model": os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(provider),
        "configured": has_key,
    }


def get_chat_model() -> BaseChatModel:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "demo":
        print("\n" + "=" * 60)
        print(" [CloudOps LLM] Running in DEMO mode with deterministic scripted demo engine.")
        print("=" * 60 + "\n")
        return DemoChatModel()

    key_var = KEY_VARS.get(provider)
    if not key_var or not os.getenv(key_var):
        raise LLMNotConfigured(
            f"{key_var or 'API key'} is not set (LLM_PROVIDER={provider}). "
            "Configure your API key in .env or set LLM_PROVIDER=demo for the zero-key demo engine."
        )

    model = os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(provider)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model or "gemini-2.5-flash", temperature=0, max_retries=3)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model or "claude-sonnet-4-5", temperature=0, max_tokens=4096, max_retries=3)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model or "gpt-4.1", temperature=0, max_retries=3)

    raise LLMNotConfigured(f"Unsupported LLM_PROVIDER: {provider}")

