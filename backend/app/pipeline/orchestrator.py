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


async def _search_all_sources(client: httpx.AsyncClient, query: str) -> tuple[list[Paper], dict[str, int]]:
    pubmed_results, s2_results, epmc_results = await asyncio.gather(
        pubmed.search(client, query, retmax=8),
        semantic_scholar.search(client, query, limit=8),
        europepmc.search_with_full_text(client, query, page_size=8, fetch_full_text_for=2),
    )
    # Raw per-source counts, captured before cross-source dedup collapses them into one
    # list -- this is what the source-transparency view shows as "how many candidates
    # came back from each API" for a given sub-topic.
    candidates_by_source = {
        "pubmed": len(pubmed_results),
        "semantic_scholar": len(s2_results),
        "europepmc": len(epmc_results),
    }
    return dedup_papers([*pubmed_results, *s2_results, *epmc_results]), candidates_by_source


@dataclass
class SubtopicRetrieval:
    subtopic: SubTopic
    results: list[ChunkSearchResult]
    papers: list[Paper]
    candidates_by_source: dict[str, int]


async def _retrieve_and_cache_subtopic(subtopic: SubTopic, client: httpx.AsyncClient, embedder, pool, k: int) -> SubtopicRetrieval:
    papers, candidates_by_source = await _search_all_sources(client, subtopic.search_query)
    if not papers:
        return SubtopicRetrieval(subtopic, [], [], candidates_by_source)

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
    return SubtopicRetrieval(subtopic, results, papers, candidates_by_source)


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
    for sr in subtopic_task_results:
        subtopic_results.append((sr.subtopic, sr.results))
        for p in sr.papers:
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

    # "cited" here answers the source-transparency question of *why* one paper was
    # surfaced over another for a sub-topic: it's whichever chunks were closest in
    # embedding space (lowest `distance`) and therefore made it into the top-k fed to
    # the synthesis LLM, cross-referenced against which of those papers the LLM actually
    # cited in its answer.
    cited_canonical_ids = {c.paper.canonical_id for c in citations}
    retrieval_detail = [
        {
            "label": sr.subtopic.label,
            "search_query": sr.subtopic.search_query,
            "candidates_by_source": sr.candidates_by_source,
            "selected": [
                {
                    "title": all_papers[r.paper_canonical_id].title,
                    "link": all_papers[r.paper_canonical_id].link,
                    "distance": r.distance,
                    "section": r.section,
                    "cited": r.paper_canonical_id in cited_canonical_ids,
                }
                for r in sorted(sr.results, key=lambda r: r.distance)
                if r.paper_canonical_id in all_papers
            ],
        }
        for sr in subtopic_task_results
    ]

    yield PipelineEvent(
        "done",
        {
            "citations": [
                {
                    "key": c.key,
                    "title": c.paper.title,
                    "year": c.paper.year,
                    "link": c.paper.link,
                    "excerpts": [{"text": e.text, "section": e.section} for e in c.excerpts],
                }
                for c in citations
            ],
            "retrieval_detail": retrieval_detail,
        },
    )
