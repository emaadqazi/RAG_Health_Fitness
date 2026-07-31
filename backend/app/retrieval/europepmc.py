"""Europe PMC client: metadata search + open-access full text.

Full text is only fetched for the top-N most relevant hits per sub-topic (bounds
both request latency and Supabase storage growth) — callers pass `fetch_full_text_for`
to control how many.
"""

from __future__ import annotations

import asyncio
import logging
from xml.etree import ElementTree

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.retrieval.models import Paper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
)
async def _get(client: httpx.AsyncClient, path: str, params: dict) -> httpx.Response:
    resp = await client.get(f"{BASE_URL}/{path}", params=params, timeout=15)
    if resp.status_code == 429:
        raise httpx.HTTPStatusError("rate limited", request=resp.request, response=resp)
    resp.raise_for_status()
    return resp


def _to_paper(item: dict) -> Paper:
    doi = item.get("doi")
    pmid = item.get("pmid")
    if doi:
        canonical_id = f"doi:{doi.lower()}"
    elif pmid:
        canonical_id = f"pmid:{pmid}"
    else:
        canonical_id = f"europepmc:{item.get('id')}"

    authors = [a.strip() for a in (item.get("authorString") or "").split(",") if a.strip()]
    year_text = item.get("pubYear")
    year = int(year_text) if year_text and str(year_text).isdigit() else None

    return Paper(
        canonical_id=canonical_id,
        title=item.get("title") or "",
        abstract=item.get("abstractText"),
        year=year,
        authors=authors,
        pmid=pmid,
        doi=doi,
        sources=["europepmc"],
        is_open_access=(item.get("isOpenAccess") == "Y"),
    )


async def search(client: httpx.AsyncClient, query: str, page_size: int = 10) -> list[Paper]:
    params = {"query": query, "format": "json", "resultType": "core", "pageSize": page_size}
    try:
        resp = await _get(client, "search", params)
        data = resp.json()
        results = data.get("resultList", {}).get("result", [])
        return [_to_paper(item) for item in results if item.get("title")]
    except Exception:
        logger.exception("Europe PMC search failed for query=%r", query)
        return []


async def fetch_full_text(client: httpx.AsyncClient, pmcid: str) -> str | None:
    """Fetch OA full text XML for a PMC id (e.g. 'PMC1234567') and return plain text."""
    try:
        resp = await _get(client, f"{pmcid}/fullTextXML", {})
        root = ElementTree.fromstring(resp.content)
        body = root.find(".//body")
        if body is None:
            return None
        text = " ".join("".join(body.itertext()).split())
        return text or None
    except Exception:
        logger.warning("Europe PMC full text fetch failed for pmcid=%r", pmcid, exc_info=True)
        return None


async def search_with_full_text(
    client: httpx.AsyncClient, query: str, page_size: int = 10, fetch_full_text_for: int = 2
) -> list[Paper]:
    """Search, then attach OA full text to the top `fetch_full_text_for` hits only."""
    params = {"query": query, "format": "json", "resultType": "core", "pageSize": page_size}
    try:
        resp = await _get(client, "search", params)
        data = resp.json()
        raw_results = data.get("resultList", {}).get("result", [])
    except Exception:
        logger.exception("Europe PMC search failed for query=%r", query)
        return []

    papers = []
    full_text_budget = fetch_full_text_for
    for item in raw_results:
        if not item.get("title"):
            continue
        paper = _to_paper(item)
        pmcid = item.get("pmcid")
        if full_text_budget > 0 and paper.is_open_access and pmcid:
            full_text = await fetch_full_text(client, pmcid)
            if full_text:
                paper.full_text = full_text
                full_text_budget -= 1
        papers.append(paper)
    return papers


if __name__ == "__main__":

    async def _main() -> None:
        async with httpx.AsyncClient() as client:
            papers = await search_with_full_text(client, "half marathon VO2max physiology", page_size=5)
            for p in papers:
                print(f"- {p.title} ({p.year}) OA={p.is_open_access} full_text={'yes' if p.full_text else 'no'}")

    asyncio.run(_main())
