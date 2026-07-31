"""Local Ollama provider (e.g. Qwen2.5:9b) -- dev/experimentation only, never used
in the production deploy (Render always sets LLM_PROVIDER=anthropic). Plain httpx
calls against a local Ollama server; no extra client dependency needed.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from app.config import get_settings


class OllamaProvider:
    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.ollama_model

    async def stream_complete(
        self, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": True,
            "think": False,
            "options": {"num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    content = data.get("message", {}).get("content")
                    if content:
                        yield content
                    if data.get("done"):
                        break

    async def complete_json(self, system: str, user: str, json_schema: dict, max_tokens: int) -> dict:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "format": json_schema,
            # Thinking models (e.g. Qwen3.5) can burn the whole token budget on
            # chain-of-thought before ever emitting the JSON content -- disable it for
            # structured-output calls where we just need the final answer.
            "think": False,
            "options": {"num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data.get("message", {}).get("content", "{}")
        return json.loads(content)
