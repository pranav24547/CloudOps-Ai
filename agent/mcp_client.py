"""MCP client layer.

The agent never imports AWS/GitHub/Docker code. It only knows a list of MCP
server endpoints. At runtime it connects to each server, *discovers* the tools
it exposes (``tools/list``), and invokes them with ``tools/call``. Adding a new
server (e.g. GitHub MCP) is a configuration change, not an agent code change.

Configuration (``MCP_SERVERS`` env var, JSON)::

    {
      "aws":    {"transport": "streamable_http", "url": "http://localhost:8101/mcp"},
      "local":  {"transport": "stdio", "command": "python", "args": ["server.py", "--transport", "stdio"]}
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from .policy import Risk, classify_tool

log = logging.getLogger(__name__)

DEFAULT_SERVERS = {
    "aws": {"transport": "streamable_http", "url": os.getenv("AWS_MCP_URL", "http://127.0.0.1:8101/mcp")},
    "github": {"transport": "streamable_http", "url": os.getenv("GITHUB_MCP_URL", "http://127.0.0.1:8102/mcp")},
    "docker": {"transport": "streamable_http", "url": os.getenv("DOCKER_MCP_URL", "http://127.0.0.1:8103/mcp")},
}
SEPARATOR = "__"  # qualified tool name = "<server>__<tool>" (LLM-safe characters only)


@dataclass
class ServerConfig:
    name: str
    transport: str
    url: str | None = None
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    cwd: str | None = None

    @classmethod
    def from_dict(cls, name: str, d: dict[str, Any]) -> "ServerConfig":
        return cls(name=name, transport=d.get("transport", "streamable_http"), url=d.get("url"),
                   command=d.get("command"), args=list(d.get("args", [])), env=d.get("env"), cwd=d.get("cwd"))


def load_server_configs(raw: str | None = None) -> list[ServerConfig]:
    raw = raw if raw is not None else os.getenv("MCP_SERVERS")
    data = json.loads(raw) if raw else DEFAULT_SERVERS
    return [ServerConfig.from_dict(name, cfg) for name, cfg in data.items()]


@dataclass
class ToolSpec:
    server: str
    name: str
    description: str
    input_schema: dict[str, Any]
    annotations: dict[str, Any]
    risk: Risk

    @property
    def qualified_name(self) -> str:
        return f"{self.server}{SEPARATOR}{self.name}"

    @property
    def is_write(self) -> bool:
        return self.risk != Risk.READ

    def to_llm_tool(self) -> dict[str, Any]:
        note = "" if self.risk == Risk.READ else f" [WRITE action, risk={self.risk.value}; needs human approval]"
        return {
            "type": "function",
            "function": {
                "name": self.qualified_name,
                "description": f"[{self.server} MCP] {self.description}{note}"[:1024],
                "parameters": self.input_schema or {"type": "object", "properties": {}},
            },
        }

    def to_public(self) -> dict[str, Any]:
        return {"server": self.server, "name": self.name, "qualified_name": self.qualified_name,
                "description": self.description, "risk": self.risk.value, "annotations": self.annotations,
                "input_schema": self.input_schema}


@dataclass
class ToolResult:
    ok: bool
    data: Any
    text: str
    duration_ms: int


class MCPError(RuntimeError):
    pass


class MCPToolRegistry:
    """Discovers and calls tools across many MCP servers."""

    def __init__(self, servers: list[ServerConfig] | None = None, call_timeout: float = 45.0) -> None:
        self.servers = {s.name: s for s in (servers if servers is not None else load_server_configs())}
        self.call_timeout = call_timeout
        self._tools: dict[str, ToolSpec] = {}
        self.server_status: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self.call_count = 0

    # ------------------------------------------------------------ sessions
    @asynccontextmanager
    async def session(self, server: str) -> AsyncIterator[ClientSession]:
        cfg = self.servers.get(server)
        if cfg is None:
            raise MCPError(f"Unknown MCP server '{server}'")
        if cfg.transport == "stdio":
            params = StdioServerParameters(command=cfg.command or "python", args=cfg.args,
                                           env={**os.environ, **(cfg.env or {})}, cwd=cfg.cwd)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as s:
                    await s.initialize()
                    yield s
        elif cfg.transport in ("streamable_http", "http"):
            async with streamable_http_client(cfg.url) as (read, write, _):
                async with ClientSession(read, write) as s:
                    await s.initialize()
                    yield s
        else:
            raise MCPError(f"Unsupported transport '{cfg.transport}' for server '{server}'")

    # ------------------------------------------------------------ discovery
    async def refresh(self) -> dict[str, ToolSpec]:
        """(Re)discover tools from every configured server. Unreachable servers are reported, not fatal."""
        async with self._lock:
            tools: dict[str, ToolSpec] = {}
            for name in self.servers:
                started = time.perf_counter()
                try:
                    async with self.session(name) as s:
                        listed = await asyncio.wait_for(s.list_tools(), timeout=self.call_timeout)
                    for t in listed.tools:
                        ann = t.annotations.model_dump(exclude_none=True) if t.annotations else {}
                        spec = ToolSpec(server=name, name=t.name, description=t.description or "",
                                        input_schema=t.inputSchema or {}, annotations=ann,
                                        risk=classify_tool(name, t.name, ann))
                        tools[spec.qualified_name] = spec
                    self.server_status[name] = {"status": "connected", "tools": len(listed.tools),
                                                "latency_ms": int((time.perf_counter() - started) * 1000)}
                except Exception as e:  # noqa: BLE001
                    log.warning("MCP server %s unavailable: %s", name, e)
                    self.server_status[name] = {"status": "unavailable", "error": _err(e), "tools": 0}
            self._tools = tools
            return tools

    async def ensure_tools(self) -> dict[str, ToolSpec]:
        if not self._tools:
            await self.refresh()
        return self._tools

    @property
    def tools(self) -> dict[str, ToolSpec]:
        return self._tools

    def get(self, qualified_name: str) -> ToolSpec | None:
        return self._tools.get(qualified_name)

    def find(self, server: str, tool: str) -> ToolSpec | None:
        return self._tools.get(f"{server}{SEPARATOR}{tool}")

    # ------------------------------------------------------------ invocation
    async def call(self, server: str, tool: str, arguments: dict[str, Any]) -> ToolResult:
        started = time.perf_counter()
        self.call_count += 1
        try:
            async with self.session(server) as s:
                res = await asyncio.wait_for(s.call_tool(tool, arguments), timeout=self.call_timeout)
        except Exception as e:  # noqa: BLE001
            return ToolResult(False, None, f"MCP call failed: {_err(e)}", _ms(started))
        text = "\n".join(getattr(c, "text", "") for c in res.content if getattr(c, "type", "") == "text")
        data: Any = res.structuredContent
        if isinstance(data, dict) and set(data) == {"result"}:
            data = data["result"]  # FastMCP wraps non-object return values
        if data is None and text:
            try:
                data = json.loads(text)
            except ValueError:
                data = text
        return ToolResult(not res.isError, data, text, _ms(started))

    async def call_qualified(self, qualified_name: str, arguments: dict[str, Any]) -> ToolResult:
        server, _, tool = qualified_name.partition(SEPARATOR)
        return await self.call(server, tool, arguments)


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _err(e: BaseException) -> str:
    # anyio/TaskGroup errors wrap the useful exception
    if isinstance(e, BaseExceptionGroup) and e.exceptions:
        return _err(e.exceptions[0])
    return f"{type(e).__name__}: {e}"
