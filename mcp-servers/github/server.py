"""GitHub MCP Server."""

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
    format="%(asctime)s %(levelname)s [github-mcp] %(message)s",
)


def build_server(host: str = "127.0.0.1", port: int = 8102) -> FastMCP:
    backend = get_backend()
    mcp = FastMCP(
        "cloudops-github",
        instructions=(
            "GitHub repository, commit, and CI/CD tools for CloudOps. Read tools (commits, PRs, workflows) "
            "are safe. Write tools (trigger_workflow, rollback_deployment) change deployment state and require approval."
        ),
        host=host,
        port=port,
    )

    tools.register(mcp, backend)

    @mcp.resource("github://repository", mime_type="application/json")
    def repository_resource() -> str:
        return json.dumps(backend.get_repository_info())

    logging.getLogger(__name__).info("GitHub MCP server ready (mode=%s, repo=%s)", backend.mode, backend.repo)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="CloudOps GitHub MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default=os.getenv("MCP_TRANSPORT", "streamable-http"),
    )
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8102")))
    args = parser.parse_args()
    build_server(args.host, args.port).run(transport=args.transport)


if __name__ == "__main__":
    main()
