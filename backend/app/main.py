"""FastAPI application entrypoint for CloudOps AI."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agent_service import get_agent
from .api.agent import router as agent_router
from .api.approvals import router as approvals_router
from .api.audit import router as audit_router
from .api.auth import router as auth_router
from .api.incidents import router as incidents_router
from .api.resources import router as resources_router
from .api.runs import router as runs_router
from .database import init_db

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("cloudops-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting CloudOps AI backend...")
    # Initialize database & default seed users
    await init_db()
    log.info("Database initialized with seed users")

    # Expire orphaned pending approvals from prior crashes/restarts
    try:
        from sqlalchemy import update

        from .database import AsyncSessionLocal
        from .models import ApprovalRecord

        async with AsyncSessionLocal() as session:
            await session.execute(
                update(ApprovalRecord)
                .where(ApprovalRecord.status == "pending")
                .values(status="expired", reason="Server restarted while approval was pending")
            )
            await session.commit()
    except Exception as e:
        log.warning("Could not clean up orphaned approvals: %s", e)

    # Refresh MCP tools from configured servers
    agent = get_agent()
    try:
        await agent.registry.refresh()
        log.info(
            "MCP servers refreshed: %s",
            {k: v.get("status") for k, v in agent.registry.server_status.items()},
        )
    except Exception as e:
        log.warning("MCP initial discovery encountered warning: %s", e)

    yield

    log.info("Shutting down CloudOps AI backend")


app = FastAPI(
    title="CloudOps AI Agent API",
    description="Autonomous Cloud Infrastructure & DevOps Assistant powered by Model Context Protocol (MCP)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(runs_router)
app.include_router(incidents_router)
app.include_router(resources_router)
app.include_router(approvals_router)
app.include_router(audit_router)


from fastapi.responses import RedirectResponse


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    agent = get_agent()
    return {
        "status": "ok",
        "service": "cloudops-backend",
        "mcp_servers": agent.registry.server_status,
    }
