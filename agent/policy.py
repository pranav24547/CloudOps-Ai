"""Security policy: risk classification, RBAC and argument validation.

Risk is derived from the MCP ``ToolAnnotations`` a server publishes, but the
client never *trusts* a server to lower risk: explicit overrides here win, and
any tool that is not explicitly read-only is treated as a write. Unknown write
tools default to HIGH risk.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

import jsonschema


class Risk(str, Enum):
    READ = "read"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Role(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


# Explicit, reviewed classifications ("<server>.<tool>"). These override server hints.
RISK_OVERRIDES: dict[str, Risk] = {
    "aws.restart_ec2": Risk.MEDIUM,
    "aws.start_ec2": Risk.MEDIUM,
    "aws.stop_ec2": Risk.HIGH,
    "docker.restart_container": Risk.LOW,
    "github.create_issue": Risk.LOW,
    "github.trigger_workflow": Risk.HIGH,
}


def classify_tool(server: str, tool: str, annotations: dict[str, Any] | None) -> Risk:
    key = f"{server}.{tool}"
    if key in RISK_OVERRIDES:
        return RISK_OVERRIDES[key]
    ann = annotations or {}
    if ann.get("readOnlyHint") is True:
        return Risk.READ
    if ann.get("destructiveHint") is False:
        return Risk.LOW
    return Risk.HIGH  # MCP default: destructiveHint=true when not read-only


def auto_approve_low_risk() -> bool:
    return os.getenv("AUTO_APPROVE_LOW_RISK", "false").lower() in {"1", "true", "yes"}


def requires_approval(risk: Risk) -> bool:
    if risk == Risk.READ:
        return False
    if risk == Risk.LOW:
        return not auto_approve_low_risk()
    return True  # MEDIUM / HIGH always need a human


def role_can_request(role: str, risk: Risk) -> bool:
    """Can a user with ``role`` start a run that *proposes* this action?"""
    if risk == Risk.READ:
        return True
    return role in (Role.OPERATOR.value, Role.ADMIN.value)


def role_can_approve(role: str, risk: Risk) -> bool:
    """Can a user with ``role`` approve an action of this risk level?"""
    if role == Role.ADMIN.value:
        return True
    if role == Role.OPERATOR.value:
        return risk in (Risk.LOW, Risk.MEDIUM, Risk.HIGH)
    return False


class InvalidArguments(ValueError):
    pass


def validate_arguments(schema: dict[str, Any], arguments: Any) -> None:
    """Validate tool arguments against the MCP tool's JSON schema before anything executes."""
    if not isinstance(arguments, dict):
        raise InvalidArguments("Tool arguments must be a JSON object")
    try:
        jsonschema.validate(arguments, schema or {"type": "object"})
    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.absolute_path) or "(root)"
        raise InvalidArguments(f"{path}: {e.message}") from e
