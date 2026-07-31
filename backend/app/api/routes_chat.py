from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm.factory import get_llm_provider
from app.pipeline.orchestrator import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str | None = None


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def _event_stream(question: str) -> AsyncIterator[str]:
    llm = get_llm_provider()
    try:
        async for event in run_pipeline(llm, question):
            yield _sse(event.type, event.data)
    except Exception:
        logger.exception("Unhandled pipeline error for question=%r", question)
        yield _sse("error", {"message": "Something went wrong processing that question. Please try again."})


@router.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    settings = get_settings()
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty")
    if len(question) > settings.max_question_length:
        raise HTTPException(
            status_code=400, detail=f"question must be at most {settings.max_question_length} characters"
        )

    return StreamingResponse(
        _event_stream(question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
