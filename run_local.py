"""Local multi-service launcher for CloudOps AI.

Runs the 3 MCP servers (AWS, GitHub, Docker) and the FastAPI backend
with graceful startup, health verification, and shutdown handling.

Usage:
    python run_local.py               # Starts MCP servers + FastAPI backend
    python run_local.py --frontend    # Also starts Next.js frontend (port 3000)
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _venv_python() -> str:
    """Prefer the project's .venv interpreter, where all dependencies are installed."""
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",  # Windows
        ROOT / ".venv" / "bin" / "python",  # Linux / macOS
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable


PYTHON = _venv_python()

# If launched with the system interpreter, re-exec under the venv so imports work everywhere.
if Path(sys.executable).resolve() != Path(PYTHON).resolve() and __name__ == "__main__":
    print(f"[CloudOps] Re-launching with project virtualenv: {PYTHON}")
    sys.exit(subprocess.call([PYTHON, str(Path(__file__).resolve()), *sys.argv[1:]]))

SERVICES = [
    {
        "name": "AWS MCP Server",
        "cmd": [PYTHON, str(ROOT / "mcp-servers" / "aws" / "server.py"), "--transport", "streamable-http", "--port", "8101"],
        "port": 8101,
    },
    {
        "name": "GitHub MCP Server",
        "cmd": [PYTHON, str(ROOT / "mcp-servers" / "github" / "server.py"), "--transport", "streamable-http", "--port", "8102"],
        "port": 8102,
    },
    {
        "name": "Docker MCP Server",
        "cmd": [PYTHON, str(ROOT / "mcp-servers" / "docker" / "server.py"), "--transport", "streamable-http", "--port", "8103"],
        "port": 8103,
    },
    {
        "name": "FastAPI Backend",
        "cmd": [PYTHON, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        "port": 8000,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Start CloudOps AI services locally.")
    parser.add_argument("--frontend", action="store_true", help="Also start Next.js frontend on port 3000")
    args = parser.parse_args()

    services = list(SERVICES)
    if args.frontend:
        npm = shutil.which("npm.cmd") or shutil.which("npm")  # npm is npm.cmd on Windows
        if not npm:
            print("[!] npm not found on PATH - install Node.js 20+ or run without --frontend.")
            sys.exit(1)
        if not (ROOT / "frontend" / "node_modules").exists():
            print("[*] Installing frontend dependencies (npm install)...")
            subprocess.check_call([npm, "install"], cwd=str(ROOT / "frontend"))
        services.append({
            "name": "Next.js Frontend",
            "cmd": [npm, "run", "dev"],
            "cwd": str(ROOT / "frontend"),
            "port": 3000,
        })

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    env = {**os.environ}
    if not env.get("CLOUDOPS_MODE"):
        env["CLOUDOPS_MODE"] = "demo"

    processes: list[subprocess.Popen] = []

    def shutdown(signum=None, frame=None):
        print("\n[CloudOps] Stopping all services...")
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=3)
            except Exception:
                p.kill()
        print("[CloudOps] All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    gh_mode = env.get("GITHUB_MODE") or ("live" if env.get("GITHUB_TOKEN") else env.get("CLOUDOPS_MODE", "demo"))
    aws_mode = env.get("AWS_MODE") or env.get("CLOUDOPS_MODE", "demo")
    docker_mode = env.get("DOCKER_MODE") or env.get("CLOUDOPS_MODE", "demo")

    print("=" * 65)
    print(" CloudOps AI Agent - Local Launcher")
    print(f" Global Mode: {env.get('CLOUDOPS_MODE', 'demo').upper()} | LLM Provider: {env.get('LLM_PROVIDER', 'demo')}")
    print(f" Integrations: GitHub={gh_mode.upper()} | AWS={aws_mode.upper()} | Docker={docker_mode.upper()}")
    print("=" * 65)

    for s in services:
        print(f"[*] Starting {s['name']} (port {s['port']})...")
        cwd = s.get("cwd", str(ROOT))
        p = subprocess.Popen(s["cmd"], cwd=cwd, env=env)
        processes.append(p)
        time.sleep(0.8)

    print("\n" + "=" * 65)
    print(" All services are running!")
    print(" - Backend API:  http://localhost:8000")
    print(" - API Docs:     http://localhost:8000/docs")
    print(" - AWS MCP:      http://localhost:8101/mcp")
    print(" - GitHub MCP:   http://localhost:8102/mcp")
    print(" - Docker MCP:   http://localhost:8103/mcp")
    if args.frontend:
        print(" - Dashboard UI: http://localhost:3000")
    print(" Press Ctrl+C to terminate all services.")
    print("=" * 65 + "\n")

    try:
        while True:
            for p in processes:
                if p.poll() is not None:
                    print(f"[!] Warning: Process {p.pid} terminated unexpectedly with code {p.returncode}")
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
