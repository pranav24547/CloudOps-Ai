"""Small helpers shared by graph nodes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import BaseMessage


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit(event_type: str, **data: Any) -> None:
    """Send a custom event to whoever is streaming the graph (backend → SSE → UI timeline)."""
    try:
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
    except Exception:  # noqa: BLE001 - not running inside a streaming graph
        return
    writer({"type": event_type, "ts": now_iso(), **data})


def message_text(msg: BaseMessage) -> str:
    content = msg.content
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def compact(value: Any, max_list: int = 12, max_str: int = 600, depth: int = 0) -> Any:
    """Shrink tool results for the LLM context: downsample long series, trim long strings."""
    if depth > 6:
        return "…"
    if isinstance(value, dict):
        return {k: compact(v, max_list, max_str, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        if len(value) > max_list:
            step = len(value) / max_list
            sampled = [value[int(i * step)] for i in range(max_list - 1)] + [value[-1]]
            return [compact(v, max_list, max_str, depth + 1) for v in sampled] + [
                f"(downsampled from {len(value)} items)"
            ]
        return [compact(v, max_list, max_str, depth + 1) for v in value]
    if isinstance(value, str) and len(value) > max_str:
        return value[:max_str] + "…"
    return value


def to_json(value: Any, limit: int | None = None) -> str:
    text = json.dumps(value, default=str, ensure_ascii=False)
    if limit and len(text) > limit:
        return text[:limit] + "…(truncated)"
    return text
