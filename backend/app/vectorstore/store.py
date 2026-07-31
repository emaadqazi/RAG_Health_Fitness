"""Postgres+pgvector cache/store.

Works identically against a local Postgres+pgvector instance (dev, via DATABASE_URL)
and Supabase's Postgres (prod, same DATABASE_URL pointed at Supabase's connection
string) -- there is no Supabase-specific code here, just standard asyncpg+pgvector.

This is what turns the vector store into a reusable, growing literature cache: a
paper already present (by canonical_id) is never re-embedded, only its
`last_seen_at` is bumped.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import asyncpg
from pgvector.asyncpg import register_vector

from app.config import get_settings
from app.retrieval.models import Chunk, Paper


async def _init_connection(conn: asyncpg.Connection) -> None:
    await register_vector(conn)


class VectorStorePool:
    _pool: asyncpg.Pool | None = None

    async def get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            settings = get_settings()
            self._pool = await asyncpg.create_pool(
                settings.database_url, init=_init_connection, min_size=1, max_size=5
            )
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


@lru_cache
def get_store_pool() -> VectorStorePool:
    return VectorStorePool()


async def papers_already_cached(pool: asyncpg.Pool, canonical_ids: list[str]) -> set[str]:
    if not canonical_ids:
        return set()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "select canonical_id from papers where canonical_id = any($1::text[])", canonical_ids
        )
    return {r["canonical_id"] for r in rows}


async def touch_papers(pool: asyncpg.Pool, canonical_ids: list[str]) -> None:
    if not canonical_ids:
        return
    async with pool.acquire() as conn:
        await conn.execute(
            "update papers set last_seen_at = now() where canonical_id = any($1::text[])", canonical_ids
        )


async def upsert_paper(pool: asyncpg.Pool, paper: Paper) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into papers (
                canonical_id, title, abstract, year, authors, pmid, doi,
                semantic_scholar_id, sources, is_open_access, citation_count, link
            ) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            on conflict (canonical_id) do update set
                last_seen_at = now(),
                abstract = coalesce(papers.abstract, excluded.abstract),
                sources = (select array(select distinct unnest(papers.sources || excluded.sources)))
            """,
            paper.canonical_id,
            paper.title,
            paper.abstract,
            paper.year,
            paper.authors,
            paper.pmid,
            paper.doi,
            paper.semantic_scholar_id,
            paper.sources,
            paper.is_open_access,
            paper.citation_count,
            paper.link,
        )


async def insert_chunks_with_embeddings(pool: asyncpg.Pool, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    if not chunks:
        return
    rows = [
        (c.paper_canonical_id, c.chunk_index, c.section, c.text, emb) for c, emb in zip(chunks, embeddings, strict=True)
    ]
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            insert into chunks (paper_canonical_id, chunk_index, section, text, embedding)
            values ($1,$2,$3,$4,$5)
            on conflict (paper_canonical_id, chunk_index) do nothing
            """,
            rows,
        )


@dataclass
class ChunkSearchResult:
    text: str
    section: str
    paper_canonical_id: str
    distance: float


async def similarity_search(
    pool: asyncpg.Pool, query_embedding: list[float], canonical_ids: list[str] | None, k: int
) -> list[ChunkSearchResult]:
    """Search chunks by cosine distance, optionally restricted to a set of papers
    (used to keep a sub-topic's retrieval scoped to the papers just fetched for it,
    rather than the entire growing cache)."""
    async with pool.acquire() as conn:
        if canonical_ids is not None:
            rows = await conn.fetch(
                """
                select text, section, paper_canonical_id, embedding <=> $1 as distance
                from chunks
                where paper_canonical_id = any($2::text[])
                order by embedding <=> $1
                limit $3
                """,
                query_embedding,
                canonical_ids,
                k,
            )
        else:
            rows = await conn.fetch(
                """
                select text, section, paper_canonical_id, embedding <=> $1 as distance
                from chunks
                order by embedding <=> $1
                limit $2
                """,
                query_embedding,
                k,
            )
    return [
        ChunkSearchResult(text=r["text"], section=r["section"], paper_canonical_id=r["paper_canonical_id"], distance=r["distance"])
        for r in rows
    ]


async def get_papers_by_ids(pool: asyncpg.Pool, canonical_ids: list[str]) -> dict[str, Paper]:
    if not canonical_ids:
        return {}
    async with pool.acquire() as conn:
        rows = await conn.fetch("select * from papers where canonical_id = any($1::text[])", canonical_ids)
    result = {}
    for r in rows:
        result[r["canonical_id"]] = Paper(
            canonical_id=r["canonical_id"],
            title=r["title"],
            abstract=r["abstract"],
            year=r["year"],
            authors=list(r["authors"] or []),
            pmid=r["pmid"],
            doi=r["doi"],
            semantic_scholar_id=r["semantic_scholar_id"],
            sources=list(r["sources"] or []),
            is_open_access=r["is_open_access"],
            citation_count=r["citation_count"],
        )
    return result
