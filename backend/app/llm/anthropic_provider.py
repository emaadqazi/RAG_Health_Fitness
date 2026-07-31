from __future__ import annotations

from typing import AsyncIterator

import anthropic

from app.config import get_settings


class AnthropicProvider:
    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = model or settings.anthropic_model

    async def stream_complete(
        self, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def complete_json(self, system: str, user: str, json_schema: dict, max_tokens: int) -> dict:
        response = await self._client.messages.create(
            model=self._model,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=max_tokens,
            tools=[
                {
                    "name": "submit_structured_output",
                    "description": "Submit the structured result.",
                    "input_schema": json_schema,
                }
            ],
            tool_choice={"type": "tool", "name": "submit_structured_output"},
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input
        raise RuntimeError("Anthropic response contained no tool_use block for structured output")
