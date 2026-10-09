"""Shared state between simulated MCP servers (GitHub, AWS, Docker).

Allows the simulated GitHub deployment rollback to tangibly recover the
simulated AWS infrastructure metrics and CloudWatch alarms.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATE_FILE = Path(__file__).resolve().parent / ".simulated_state.json"


def get_simulated_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def set_simulated_state(updates: dict[str, Any]) -> dict[str, Any]:
    current = get_simulated_state()
    current.update(updates)
    try:
        STATE_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except Exception:
        pass
    return current


def reset_simulated_state() -> None:
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    except Exception:
        pass


def is_rollback_applied() -> bool:
    return bool(get_simulated_state().get("rollback_applied", False))
