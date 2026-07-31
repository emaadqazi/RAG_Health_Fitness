"""LLM provider abstraction.

The orchestrator/pipeline code depends only on this Protocol, never on a concrete
provider -- that's what lets `LLM_PROVIDER=ollama` (local Qwen experimentation) swap
in for `LLM_PROVIDER=anthropic` (Claude Haiku 4.5, production default) via a single
env var, with zero code branching in the pipeline itself.
"""

from __future__ import annotations

from typing import AsyncIterator, Protocol


class LLMProvider(Protocol):
    async def stream_complete(
        self, system: str, messages: list[dict[str, str]], max_tokens: int
    ) -> AsyncIterator[str]:
        """Yield text deltas as they arrive."""
        ...

    async def complete_json(self, system: str, user: str, json_schema: dict, max_tokens: int) -> dict:
        """Return a dict conforming to json_schema (best-effort on providers without
        native structured-output support)."""
        ...
