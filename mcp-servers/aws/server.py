"""CloudOps AWS MCP Server.

Exposes AWS observability and (approval-gated) control operations as MCP tools.
Every tool carries MCP ``ToolAnnotations`` (readOnlyHint / destructiveHint) so a
client can classify risk without hard-coding knowledge of this server.

Run:
    python server.py                          # streamable HTTP on :8101/mcp
    python server.py --transport stdio        # stdio (for local MCP clients / tests)

Environment:
    CLOUDOPS_MODE   demo (default, simulated AWS) | live (boto3 + AWS credential chain)
    AWS_REGION      region for live mode
    MCP_HOST/MCP_PORT  bind address for HTTP transport
"""

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

from backends import get_backend  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
from tools import cloudwatch, ec2, storage  # noqa: E402

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), stream=sys.stderr,
                    format="%(asctime)s %(levelname)s [aws-mcp] %(message)s")


def build_server(host: str = "127.0.0.1", port: int = 8101) -> FastMCP:
    backend = get_backend()
    mcp = FastMCP(
        "cloudops-aws",
        instructions=(
            "AWS infrastructure tools for CloudOps. Read tools (EC2, CloudWatch metrics/logs/alarms, S3, RDS) "
            "are safe. Tools without readOnlyHint change infrastructure and must only be called after "
            "explicit human approval."
        ),
        host=host,
        port=port,
    )

    ec2.register(mcp, backend)
    cloudwatch.register(mcp, backend)
    storage.register(mcp, backend)

    @mcp.resource("aws://environment", mime_type="application/json")
    def environment() -> str:
        """Which AWS backend this server is connected to."""
        return json.dumps({"mode": backend.mode, "region": backend.region})

    logging.getLogger(__name__).info("AWS MCP server ready (mode=%s, region=%s)", backend.mode, backend.region)
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="CloudOps AWS MCP server")
    parser.add_argument("--transport", choices=["stdio", "streamable-http", "sse"],
                        default=os.getenv("MCP_TRANSPORT", "streamable-http"))
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8101")))
    args = parser.parse_args()
    build_server(args.host, args.port).run(transport=args.transport)


if __name__ == "__main__":
    main()
