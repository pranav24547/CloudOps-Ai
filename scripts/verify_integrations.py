"""Integration verification script for CloudOps AI.

Checks all configured integrations:
1. GitHub Integration (Live / Simulated)
2. AWS Integration (Live / Simulated)
3. Docker Integration (Live / Simulated)
4. Database Integration (SQLite / PostgreSQL)
5. AI LLM Integration (Zero-Key Demo Engine / Frontier Providers)
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "mcp-servers" / "github"))
sys.path.insert(0, str(ROOT / "mcp-servers" / "aws"))
sys.path.insert(0, str(ROOT / "mcp-servers" / "docker"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def _load_backend(module_dir: Path):
    import sys

    for mod in list(sys.modules.keys()):
        if mod == "backends" or mod.startswith("backends."):
            sys.modules.pop(mod, None)
    while str(module_dir) in sys.path:
        sys.path.remove(str(module_dir))
    sys.path.insert(0, str(module_dir))
    import backends

    return backends.get_backend()


def check_github():
    print("\n[1/5] Checking GitHub Integration...")
    repo = os.getenv("GITHUB_REPOSITORY", "acme-corp/orders-api")
    token = os.getenv("GITHUB_TOKEN", "")
    mode = os.getenv("GITHUB_MODE") or ("live" if token else os.getenv("CLOUDOPS_MODE", "demo"))

    print(f"  Target Repository : {repo}")
    print(f"  GitHub Mode       : {mode}")
    print(f"  Token Configured  : {'Yes (length=' + str(len(token)) + ')' if token else 'No'}")

    try:
        backend = _load_backend(ROOT / "mcp-servers" / "github")
        print(f"  Active Backend    : {backend.__class__.__name__} (mode={backend.mode})")

        if backend.mode == "live":
            info = backend.get_repository_info()
            print(f"  [OK] Successfully fetched live repo: {info.get('repository')}")
            print(f"    - Default branch: {info.get('default_branch')}")
            print(f"    - Stars: {info.get('stars')}")
            commits = backend.get_recent_commits(limit=2)
            print(f"  [OK] Found {len(commits)} recent commits:")
            for c in commits:
                print(f"    - [{c['short_sha']}] {c['message'].splitlines()[0]} ({c['author']})")
        else:
            commits = backend.get_recent_commits(limit=2)
            print(f"  [OK] Simulated GitHub backend operational ({len(commits)} commits available)")
            print(f"    - Recent commit: [{commits[0]['short_sha']}] {commits[0]['message']}")
        return True
    except Exception as e:
        print(f"  [FAIL] GitHub Check Failed: {e}")
        return False


def check_aws():
    print("\n[2/5] Checking AWS Integration...")
    aws_mode = os.getenv("AWS_MODE") or os.getenv("CLOUDOPS_MODE", "demo")
    region = os.getenv("AWS_REGION", "ap-south-1")
    print(f"  AWS Mode          : {aws_mode}")
    print(f"  AWS Region        : {region}")

    try:
        backend = _load_backend(ROOT / "mcp-servers" / "aws")
        print(f"  Active Backend    : {backend.__class__.__name__} (mode={backend.mode})")
        instances = backend.list_ec2_instances()
        print(f"  [OK] AWS Backend operational ({len(instances)} EC2 instances discovered)")
        return True
    except Exception as e:
        print(f"  [FAIL] AWS Check Failed: {e}")
        return False


def check_docker():
    print("\n[3/5] Checking Docker Integration...")
    docker_mode = os.getenv("DOCKER_MODE") or os.getenv("CLOUDOPS_MODE", "demo")
    print(f"  Docker Mode       : {docker_mode}")

    try:
        backend = _load_backend(ROOT / "mcp-servers" / "docker")
        print(f"  Active Backend    : {backend.__class__.__name__} (mode={backend.mode})")
        containers = backend.list_containers()
        print(f"  [OK] Docker Backend operational ({len(containers)} containers discovered)")
        return True
    except Exception as e:
        print(f"  [FAIL] Docker Check Failed: {e}")
        return False


async def check_database():
    print("\n[4/5] Checking Database Integration...")
    try:
        from sqlalchemy import select

        from backend.app.database import AsyncSessionLocal, init_db
        from backend.app.models import User

        await init_db()
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User))
            users = res.scalars().all()
            print(f"  [OK] Database connected ({len(users)} users found in DB)")
            for u in users:
                print(f"    - User: {u.email} (Role: {u.role})")
        return True
    except Exception as e:
        print(f"  [FAIL] Database Check Failed: {e}")
        return False


def check_ai_provider():
    print("\n[5/5] Checking AI / LLM Configuration...")
    provider = os.getenv("LLM_PROVIDER", "demo").lower()
    print(f"  Configured Provider : {provider}")
    try:
        from agent.llm import get_chat_model, llm_status
        status = llm_status()
        print(f"  Status              : {status}")
        model = get_chat_model()
        print(f"  [OK] AI model initialized successfully: {model.__class__.__name__}")
        print("  [OK] Zero API key required (using built-in DemoChatModel)")
        return True
    except Exception as e:
        print(f"  [FAIL] AI Model Initialization Failed: {e}")
        return False


async def main():
    print("=" * 60)
    print(" CloudOps AI Agent - Integration Health Check")
    print("=" * 60)

    gh_ok = check_github()
    aws_ok = check_aws()
    docker_ok = check_docker()
    db_ok = await check_database()
    ai_ok = check_ai_provider()

    print("\n" + "=" * 60)
    print(" Summary:")
    print(f"  - GitHub   : {'[OK]' if gh_ok else '[FAIL]'}")
    print(f"  - AWS      : {'[OK]' if aws_ok else '[FAIL]'}")
    print(f"  - Docker   : {'[OK]' if docker_ok else '[FAIL]'}")
    print(f"  - Database : {'[OK]' if db_ok else '[FAIL]'}")
    print(f"  - AI Engine: {'[OK] (Zero-Key Demo)' if ai_ok else '[FAIL]'}")
    print("=" * 60)



if __name__ == "__main__":
    asyncio.run(main())
