from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx

from app.config import get_settings
from app.embeddings.chunking import chunk_paper
from app.embeddings.embedder import get_embedder
from app.llm.base import LLMProvider
from app.pipeline.decompose import decompose_question
from app.pipeline.synthesize import assemble_context, stream_synthesis
from app.retrieval import europepmc, pubmed, semantic_scholar
from app.retrieval.dedup import dedup_papers
from app.retrieval.models import Paper, SubTopic
from app.vectorstore.store import (
    ChunkSearchResult,
    get_store_pool,
    insert_chunks_with_embeddings,
    papers_already_cached,
    similarity_search,
    touch_papers,
    upsert_paper,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineEvent:
    type: str  # decomposition | sources | token | done | error
    data: dict[str, Any] = field(default_factory=dict)


async def _search_all_sources(client: httpx.AsyncClient, query: str) -> list[Paper]:
    pubmed_results, s2_results, epmc_results = await asyncio.gather(
        pubmed.search(client, query, retmax=8),
        semantic_scholar.search(client, query, limit=8),
        europepmc.search_with_full_text(client, query, page_size=8, fetch_full_text_for=2),
    )
    return dedup_papers([*pubmed_results, *s2_results, *epmc_results])


async def _retrieve_and_cache_subtopic(
    subtopic: SubTopic, client: httpx.AsyncClient, embedder, pool, k: int
) -> tuple[SubTopic, list[ChunkSearchResult], list[Paper]]:
    papers = await _search_all_sources(client, subtopic.search_query)
    if not papers:
        return subtopic, [], []

    canonical_ids = [p.canonical_id for p in papers]
    cached_ids = await papers_already_cached(pool, canonical_ids)
    new_papers = [p for p in papers if p.canonical_id not in cached_ids]

    if cached_ids:
        await touch_papers(pool, list(cached_ids))

    for paper in new_papers:
        await upsert_paper(pool, paper)
        chunks = chunk_paper(paper)
        if not chunks:
            continue
        embeddings = embedder.embed([c.text for c in chunks])
        await insert_chunks_with_embeddings(pool, chunks, embeddings)

    query_embedding = embedder.embed_query(subtopic.search_query)
    results = await similarity_search(pool, query_embedding, canonical_ids=canonical_ids, k=k)
    return subtopic, results, papers


async def run_pipeline(llm: LLMProvider, question: str) -> AsyncIterator[PipelineEvent]:
    settings = get_settings()

    try:
        subtopics = await decompose_question(llm, question)
    except Exception:
        logger.exception("Decomposition failed for question=%r", question)
        yield PipelineEvent("error", {"message": "Couldn't process the question. Please try rephrasing it."})
        return

    if not subtopics:
        yield PipelineEvent("error", {"message": "Couldn't identify any researchable sub-topics in that question."})
        return

    yield PipelineEvent("decomposition", {"subtopics": [s.model_dump() for s in subtopics]})

    embedder = get_embedder()
    pool = await get_store_pool().get_pool()

    async with httpx.AsyncClient() as client:
        subtopic_task_results = await asyncio.gather(
            *[
                _retrieve_and_cache_subtopic(st, client, embedder, pool, settings.max_chunks_per_subtopic)
                for st in subtopics
            ]
        )

    all_papers: dict[str, Paper] = {}
    subtopic_results: list[tuple[SubTopic, list[ChunkSearchResult]]] = []
    for subtopic, results, papers in subtopic_task_results:
        subtopic_results.append((subtopic, results))
        for p in papers:
            all_papers[p.canonical_id] = p

    yield PipelineEvent(
        "sources",
        {
            "papers": [
                {"title": p.title, "year": p.year, "link": p.link, "sources": p.sources}
                for p in all_papers.values()
            ]
        },
    )

    if not any(results for _, results in subtopic_results):
        yield PipelineEvent("error", {"message": "No relevant literature was found for this question."})
        return

    user_content, citations = assemble_context(question, subtopic_results, all_papers)

    async for token in stream_synthesis(llm, user_content, settings.max_synthesis_output_tokens):
        yield PipelineEvent("token", {"text": token})

    yield PipelineEvent(
        "done",
        {
            "citations": [
                {
                    "key": c.key,
                    "title": c.paper.title,
                    "year": c.paper.year,
                    "link": c.paper.link,
                }
                for c in citations
            ]
        },
    )
