"""Agent chat endpoint with SSE streaming."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..agent_service import stream_agent_execution
from ..auth.dependencies import get_current_user
from ..models import User

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = None


@router.post("/chat")
async def chat(
    req: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Initiates an autonomous agent investigation or action workflow with real-time SSE event streaming."""
    generator = stream_agent_execution(
        message=req.message,
        user=current_user,
        thread_id=req.thread_id,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
