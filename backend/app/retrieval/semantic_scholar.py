"""Semantic Scholar Graph API client.

Unauthenticated access has the tightest rate limit of the three literature sources
(observed to 429 even on light/single-call testing) — treated as best-effort:
callers should degrade gracefully (skip S2 for a sub-topic) rather than fail the
whole request if this source is unavailable.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.retrieval.models import Paper
from app.retrieval.text_utils import clean_title

logger = logging.getLogger(__name__)

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,abstract,year,externalIds,citationCount,authors"

# Per Semantic Scholar's own docs, an individual API key is capped at 1 request/sec
# across all endpoints. The orchestrator fires one search per sub-topic concurrently
# (asyncio.gather), so without this throttle, 2+ sub-topics can still 429 each other
# even with a key configured -- this serializes S2 calls process-wide to stay under it.
_rate_lock = asyncio.Lock()
_last_call_monotonic = 0.0
_MIN_INTERVAL_SECONDS = 1.1


async def _throttle() -> None:
    global _last_call_monotonic
    async with _rate_lock:
        loop = asyncio.get_event_loop()
        wait = _last_call_monotonic + _MIN_INTERVAL_SECONDS - loop.time()
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call_monotonic = loop.time()


@retry(
    reraise=True,
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=6),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
)
async def _get(client: httpx.AsyncClient, params: dict) -> httpx.Response:
    settings = get_settings()
    headers = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key
    await _throttle()
    resp = await client.get(f"{BASE_URL}/paper/search", params=params, headers=headers, timeout=15)
    if resp.status_code == 429:
        raise httpx.HTTPStatusError("rate limited", request=resp.request, response=resp)
    resp.raise_for_status()
    return resp


def _to_paper(item: dict) -> Paper:
    external_ids = item.get("externalIds") or {}
    authors = [a.get("name", "") for a in (item.get("authors") or []) if a.get("name")]
    doi = external_ids.get("DOI")
    pmid = external_ids.get("PubMed")
    s2_id = item.get("paperId")

    if doi:
        canonical_id = f"doi:{doi.lower()}"
    elif pmid:
        canonical_id = f"pmid:{pmid}"
    else:
        canonical_id = f"s2:{s2_id}"

    return Paper(
        canonical_id=canonical_id,
        title=clean_title(item.get("title")),
        abstract=item.get("abstract"),
        year=item.get("year"),
        authors=authors,
        pmid=str(pmid) if pmid else None,
        doi=doi,
        semantic_scholar_id=s2_id,
        sources=["semantic_scholar"],
        citation_count=item.get("citationCount"),
    )


async def search(client: httpx.AsyncClient, query: str, limit: int = 10) -> list[Paper]:
    params = {"query": query, "limit": limit, "fields": FIELDS}
    try:
        resp = await _get(client, params)
        data = resp.json()
        return [_to_paper(item) for item in data.get("data", []) if item.get("title")]
    except Exception:
        logger.warning("Semantic Scholar search degraded/unavailable for query=%r", query, exc_info=True)
        return []


if __name__ == "__main__":

    async def _main() -> None:
        async with httpx.AsyncClient() as client:
            papers = await search(client, "chronic smoking lung function", limit=5)
            for p in papers:
                print(f"- {p.title} ({p.year}) canonical={p.canonical_id}")

    asyncio.run(_main())
