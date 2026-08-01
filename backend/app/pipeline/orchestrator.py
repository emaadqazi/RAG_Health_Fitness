from __future__ import annotations

import asyncio
import logging
import re
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


_CITATION_KEY_RE = re.compile(r"\[(\d+)\]")


def _split_into_subtopic_sections(full_answer: str) -> list[str]:
    """Mirror of the frontend's section splitting (MessageBubble.tsx's
    splitIntoSections) -- split the answer on every "## " header boundary and drop
    the Summary section, returning each remaining section's body text in order.
    Used to determine which citation keys were actually used *within a given
    sub-topic's specific section* of the answer, not just anywhere in the whole text.
    """
    chunks = re.split(r"\n(?=##\s+)", full_answer.strip())
    sections = []
    for chunk in chunks:
        match = re.match(r"^##\s+(.+?)\s*\n([\s\S]*)$", chunk.strip())
        if not match:
            continue
        heading, body = match.group(1).strip(), match.group(2).strip()
        if heading.lower() == "summary" or not body:
            continue
        sections.append(body)
    return sections


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

    full_answer_parts: list[str] = []
    async for token in stream_synthesis(llm, user_content, settings.max_synthesis_output_tokens):
        full_answer_parts.append(token)
        yield PipelineEvent("token", {"text": token})
    full_answer = "".join(full_answer_parts)

    # "cited" here answers the source-transparency question of *why* one paper was
    # surfaced over another for a *given sub-topic*. A naive check -- "is this paper's
    # canonical_id anywhere in the citations list" -- is over-inclusive: assemble_context
    # bundles every chunk of a paper across *all* sub-topics under one shared citation
    # key, so a paper cited via sub-topic A's chunk would also show cited under sub-topic
    # B's unrelated chunk (confirmed live: nearly every entry showed as cited). Checking
    # chunk-text membership in that shared key's excerpts doesn't fix it either -- every
    # candidate chunk shown in a sub-topic's results was, by construction, also fed into
    # that paper's shared excerpts list, so the check reduces back to the same
    # over-inclusive paper-level result (confirmed live: identical output before/after).
    #
    # The only real signal for "did this sub-topic's section of the answer actually use
    # this citation" is the rendered answer text itself: split it into per-sub-topic
    # sections the same way the frontend does (doc 07), and check which citation keys
    # literally appear as "[n]" within *that specific section*, not the whole answer.
    key_by_paper = {c.paper.canonical_id: c.key for c in citations}
    answer_sections = _split_into_subtopic_sections(full_answer)
    section_cited_keys: list[set[int]]
    if len(answer_sections) == len(subtopic_task_results):
        section_cited_keys = [{int(k) for k in _CITATION_KEY_RE.findall(body)} for body in answer_sections]
    else:
        # The model didn't produce exactly one "## " section per sub-topic (e.g. it
        # merged two sub-topics into one section) -- pairing sections to sub-topics
        # positionally would risk mismatching them, so fall back to "cited anywhere in
        # the answer" for all sub-topics rather than attributing a citation to the
        # wrong one.
        logger.warning(
            "Answer section count (%d) != sub-topic count (%d); falling back to whole-answer cited check",
            len(answer_sections),
            len(subtopic_task_results),
        )
        all_keys_used = {int(k) for k in _CITATION_KEY_RE.findall(full_answer)}
        section_cited_keys = [all_keys_used] * len(subtopic_task_results)

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
                    "cited": key_by_paper.get(r.paper_canonical_id) in section_cited_keys[i],
                }
                for r in sorted(sr.results, key=lambda r: r.distance)
                if r.paper_canonical_id in all_papers
            ],
        }
        for i, sr in enumerate(subtopic_task_results)
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
