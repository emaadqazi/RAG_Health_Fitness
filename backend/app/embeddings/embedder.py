"""Embedding provider abstraction.

Default is local `fastembed` (ONNX runtime, not PyTorch) so the deployed backend has
zero per-call embedding cost and a small memory footprint. `EMBEDDING_PROVIDER` is an
escape hatch: if Render's free-tier RAM ever can't fit fastembed comfortably under
load, swap to a hosted embeddings API (Voyage AI / OpenAI) behind this same interface
without touching any caller code.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from app.config import get_settings


class Embedder(Protocol):
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    dimensions = 384

    def __init__(self, model_name: str) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [vec.tolist() for vec in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embedding_provider == "fastembed":
        return FastEmbedEmbedder(settings.embedding_model)
    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER={settings.embedding_provider!r}. "
        "Add a new Embedder implementation in app/embeddings/embedder.py to support it."
    )
