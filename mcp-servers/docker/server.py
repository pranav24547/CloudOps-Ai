"""Docker MCP Server."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tools
from backends import get_backend
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s [docker-mcp] %(message)s",
)


def build_server(host: str = "127.0.0.1", port: int = 8103) -> FastMCP:
    backend = get_backend()
    mcp = FastMCP(
        "cloudops-docker",
        instructions=(
            "Docker container management and observability tools for CloudOps. "
            "Read tools (list_containers, logs, stats) are safe. "
            "restart_container is a low-risk write action."
        ),
        host=host,
        port=port,
    )

    tools.register(mcp, backend)

    @mcp.resource("docker://containers", mime_type="application/json")
    def containers_resource() -> str:
        return json.dumps(backend.list_containers())

    logging.getLogger(__name__).info("Docker MCP server ready (mode=%s)", backend.mode)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="CloudOps Docker MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default=os.getenv("MCP_TRANSPORT", "streamable-http"),
    )
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8103")))
    args = parser.parse_args()
    build_server(args.host, args.port).run(transport=args.transport)


if __name__ == "__main__":
    main()
