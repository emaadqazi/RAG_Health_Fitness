from __future__ import annotations

from app.config import get_settings
from app.llm.base import LLMProvider
from app.pipeline.prompts import DECOMPOSITION_JSON_SCHEMA, DECOMPOSITION_SYSTEM_PROMPT
from app.retrieval.models import SubTopic


async def decompose_question(llm: LLMProvider, question: str) -> list[SubTopic]:
    settings = get_settings()
    result = await llm.complete_json(
        system=DECOMPOSITION_SYSTEM_PROMPT,
        user=question,
        json_schema=DECOMPOSITION_JSON_SCHEMA,
        max_tokens=800,
    )
    subtopics = [SubTopic(**item) for item in result.get("subtopics", [])]
    return subtopics[: settings.max_subtopics]
