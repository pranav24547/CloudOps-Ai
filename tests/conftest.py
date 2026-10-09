"""Shared pytest fixtures.

Starts real MCP servers (AWS, GitHub, Docker) as subprocesses speaking streamable HTTP,
so all agent and backend tests exercise the genuine Model Context Protocol without mocks.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


@pytest.fixture(scope="session", autouse=True)
def setup_test_env(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("cloudops_test")
    test_db = temp_dir / "test_cloudops.db"
    test_db_url = f"sqlite+aiosqlite:///{test_db.resolve()}"
    os.environ["DATABASE_URL"] = test_db_url
    os.environ["CLOUDOPS_MODE"] = "demo"
    os.environ["GITHUB_MODE"] = "demo"
    os.environ["AWS_MODE"] = "demo"
    os.environ["DOCKER_MODE"] = "demo"
    os.environ["LLM_PROVIDER"] = "demo"
    os.environ["LOG_LEVEL"] = "WARNING"

    try:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        import backend.app.database as db_mod

        db_mod.engine = create_async_engine(test_db_url, future=True)
        db_mod.AsyncSessionLocal = async_sessionmaker(
            bind=db_mod.engine, class_=AsyncSession, expire_on_commit=False
        )
    except Exception:
        pass
    yield


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _run_mcp_server(script_rel_path: str):
    port = _free_port()
    env = {
        **os.environ,
        "CLOUDOPS_MODE": "demo",
        "GITHUB_MODE": "demo",
        "AWS_MODE": "demo",
        "DOCKER_MODE": "demo",
        "LOG_LEVEL": "WARNING",
    }
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / script_rel_path), "--transport", "streamable-http", "--port", str(port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError(f"MCP server {script_rel_path} exited during startup")
            time.sleep(0.2)
    else:
        proc.kill()
        raise RuntimeError(f"MCP server {script_rel_path} did not start within timeout")
    yield f"http://127.0.0.1:{port}/mcp"
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def aws_mcp_url():
    yield from _run_mcp_server("mcp-servers/aws/server.py")


@pytest.fixture(scope="session")
def github_mcp_url():
    yield from _run_mcp_server("mcp-servers/github/server.py")


@pytest.fixture(scope="session")
def docker_mcp_url():
    yield from _run_mcp_server("mcp-servers/docker/server.py")


@pytest.fixture
def registry(aws_mcp_url):
    """Registry with AWS MCP server (backward-compatible with existing tests)."""
    from agent.mcp_client import MCPToolRegistry, ServerConfig

    return MCPToolRegistry([ServerConfig(name="aws", transport="streamable_http", url=aws_mcp_url)])


@pytest.fixture
def multi_mcp_registry(aws_mcp_url, github_mcp_url, docker_mcp_url):
    """Full registry with AWS, GitHub, and Docker MCP servers."""
    from agent.mcp_client import MCPToolRegistry, ServerConfig

    return MCPToolRegistry([
        ServerConfig(name="aws", transport="streamable_http", url=aws_mcp_url),
        ServerConfig(name="github", transport="streamable_http", url=github_mcp_url),
        ServerConfig(name="docker", transport="streamable_http", url=docker_mcp_url),
    ])
