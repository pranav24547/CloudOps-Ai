"""Database engine, async session factory, and initialization helpers."""

from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base, Incident, User


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        # Normalize postgres:// to postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    # Fallback to local SQLite for non-docker development
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "cloudops.db"))
    return f"sqlite+aiosqlite:///{db_path}"


engine = create_async_engine(
    get_database_url(),
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    from .auth.security import get_password_hash

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default users if they don't exist
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        res = await session.execute(select(User).limit(1))
        if res.scalar_one_or_none() is None:
            default_users = [
                User(
                    id="usr_admin",
                    email="admin@cloudops.ai",
                    name="Admin User",
                    hashed_password=get_password_hash("admin123"),
                    role="admin",
                ),
                User(
                    id="usr_operator",
                    email="operator@cloudops.ai",
                    name="Site Reliability Engineer",
                    hashed_password=get_password_hash("operator123"),
                    role="operator",
                ),
                User(
                    id="usr_viewer",
                    email="viewer@cloudops.ai",
                    name="Viewer ReadOnly",
                    hashed_password=get_password_hash("viewer123"),
                    role="viewer",
                ),
            ]
            session.add_all(default_users)

            # Seed demo active incident
            default_incident = Incident(
                id="inc_active_01",
                title="orders-api high latency spike",
                severity="HIGH",
                status="INVESTIGATING",
                service="orders-api",
                root_cause="Under investigation by CloudOps Agent",
            )
            session.add(default_incident)
            await session.commit()
