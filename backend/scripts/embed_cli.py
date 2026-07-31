"""Phase 2 test script: ingest -> chunk -> embed -> upsert -> similarity search.

Usage: python -m scripts.embed_cli "chronic smoking lung function VO2max"

Verifies the cache/dedup contract: re-running the same query a second time should
not duplicate rows (papers already present are only "touched", not re-embedded).
"""

from __future__ import annotations

import asyncio
import sys

import httpx

from app.embeddings.chunking import chunk_paper
from app.embeddings.embedder import get_embedder
from app.retrieval import europepmc, pubmed, semantic_scholar
from app.retrieval.dedup import dedup_papers
from app.vectorstore.store import (
    get_store_pool,
    insert_chunks_with_embeddings,
    papers_already_cached,
    similarity_search,
    touch_papers,
    upsert_paper,
)


async def run(query: str) -> None:
    async with httpx.AsyncClient() as client:
        pubmed_results, s2_results, epmc_results = await asyncio.gather(
            pubmed.search(client, query, retmax=6),
            semantic_scholar.search(client, query, limit=6),
            europepmc.search_with_full_text(client, query, page_size=6, fetch_full_text_for=1),
        )
    papers = dedup_papers([*pubmed_results, *s2_results, *epmc_results])
    print(f"Retrieved {len(papers)} deduped papers for query={query!r}")

    pool = await get_store_pool().get_pool()

    cached_ids = await papers_already_cached(pool, [p.canonical_id for p in papers])
    new_papers = [p for p in papers if p.canonical_id not in cached_ids]
    print(f"Already cached: {len(cached_ids)} | New: {len(new_papers)}")

    if cached_ids:
        await touch_papers(pool, list(cached_ids))

    embedder = get_embedder()
    total_new_chunks = 0
    for paper in new_papers:
        await upsert_paper(pool, paper)
        chunks = chunk_paper(paper)
        if not chunks:
            continue
        embeddings = embedder.embed([c.text for c in chunks])
        await insert_chunks_with_embeddings(pool, chunks, embeddings)
        total_new_chunks += len(chunks)
    print(f"Embedded {total_new_chunks} new chunks")

    query_embedding = embedder.embed_query(query)
    results = await similarity_search(pool, query_embedding, canonical_ids=[p.canonical_id for p in papers], k=5)
    print(f"\nTop {len(results)} similar chunks for the query:")
    for r in results:
        print(f"  [{r.distance:.4f}] ({r.section}) {r.text[:150]}...")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "VO2max marathon performance"
    asyncio.run(run(query))
