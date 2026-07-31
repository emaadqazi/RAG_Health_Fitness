"""Phase 1 standalone retrieval test script.

Usage: python -m scripts.ingest_cli "VO2max marathon performance"
Searches PubMed + Semantic Scholar + Europe PMC in parallel, dedups across sources,
and prints the merged result set. No DB/embedding dependency -- pure retrieval sanity
check.
"""

from __future__ import annotations

import asyncio
import sys

import httpx

from app.retrieval import europepmc, pubmed, semantic_scholar
from app.retrieval.dedup import dedup_papers


async def run(query: str) -> None:
    async with httpx.AsyncClient() as client:
        pubmed_results, s2_results, epmc_results = await asyncio.gather(
            pubmed.search(client, query, retmax=8),
            semantic_scholar.search(client, query, limit=8),
            europepmc.search_with_full_text(client, query, page_size=8, fetch_full_text_for=2),
        )

    print(f"\nRaw counts -- pubmed={len(pubmed_results)} semantic_scholar={len(s2_results)} europepmc={len(epmc_results)}")

    merged = dedup_papers([*pubmed_results, *s2_results, *epmc_results])
    print(f"Deduped total: {len(merged)}\n")

    for paper in merged:
        print(f"[{paper.canonical_id}] {paper.title} ({paper.year})")
        print(f"  sources={paper.sources} oa={paper.is_open_access} full_text={'yes' if paper.full_text else 'no'}")
        abstract_preview = (paper.abstract or "")[:180].replace("\n", " ")
        print(f"  abstract: {abstract_preview}...")
        print()


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "VO2max marathon performance"
    asyncio.run(run(query))
