"""NCBI E-utilities client (PubMed).

Usage policy: every request must include a contact `email`. Without an API key the
rate limit is 3 req/sec; with one it's 10 req/sec. We batch esummary/efetch calls by
comma-joined PMID list rather than one request per paper.
"""

from __future__ import annotations

import asyncio
import logging
from xml.etree import ElementTree

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.retrieval.models import Paper

logger = logging.getLogger(__name__)

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedError(Exception):
    pass


def _common_params() -> dict:
    settings = get_settings()
    params: dict = {}
    if settings.ncbi_email:
        params["email"] = settings.ncbi_email
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    return params


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


async def search_pmids(client: httpx.AsyncClient, query: str, retmax: int = 10) -> list[str]:
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
        "sort": "relevance",
        **_common_params(),
    }
    resp = await _get(client, "esearch.fcgi", params)
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def _text(elem: ElementTree.Element | None) -> str:
    if elem is None:
        return ""
    return "".join(elem.itertext()).strip()


def _parse_pubmed_article(article_elem: ElementTree.Element) -> Paper | None:
    medline = article_elem.find("MedlineCitation")
    if medline is None:
        return None
    pmid_elem = medline.find("PMID")
    pmid = _text(pmid_elem)
    if not pmid:
        return None

    article = medline.find("Article")
    if article is None:
        return None

    title = _text(article.find("ArticleTitle"))

    abstract_parts = []
    abstract_elem = article.find("Abstract")
    if abstract_elem is not None:
        for ab_text in abstract_elem.findall("AbstractText"):
            label = ab_text.get("Label")
            part = _text(ab_text)
            abstract_parts.append(f"{label}: {part}" if label else part)
    abstract = "\n".join(p for p in abstract_parts if p) or None

    year = None
    pub_date = article.find("Journal/JournalIssue/PubDate")
    if pub_date is not None:
        year_text = _text(pub_date.find("Year"))
        if year_text.isdigit():
            year = int(year_text)
        elif (medline_date := _text(pub_date.find("MedlineDate"))) and medline_date[:4].isdigit():
            year = int(medline_date[:4])

    authors = []
    author_list = article.find("AuthorList")
    if author_list is not None:
        for author in author_list.findall("Author"):
            last = _text(author.find("LastName"))
            fore = _text(author.find("ForeName"))
            name = f"{fore} {last}".strip() if (last or fore) else _text(author.find("CollectiveName"))
            if name:
                authors.append(name)

    doi = None
    for article_id in article_elem.findall("PubmedData/ArticleIdList/ArticleId"):
        if article_id.get("IdType") == "doi":
            doi = _text(article_id)

    return Paper(
        canonical_id=f"pmid:{pmid}",
        title=title,
        abstract=abstract,
        year=year,
        authors=authors,
        pmid=pmid,
        doi=doi,
        sources=["pubmed"],
    )


async def fetch_papers(client: httpx.AsyncClient, pmids: list[str]) -> list[Paper]:
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
        **_common_params(),
    }
    resp = await _get(client, "efetch.fcgi", params)
    root = ElementTree.fromstring(resp.content)
    papers = []
    for article_elem in root.findall("PubmedArticle"):
        paper = _parse_pubmed_article(article_elem)
        if paper is not None:
            papers.append(paper)
    return papers


async def search(client: httpx.AsyncClient, query: str, retmax: int = 10) -> list[Paper]:
    """Search PubMed and return fully-populated papers (title + abstract)."""
    try:
        pmids = await search_pmids(client, query, retmax=retmax)
        if not pmids:
            return []
        return await fetch_papers(client, pmids)
    except Exception:
        logger.exception("PubMed search failed for query=%r", query)
        return []


if __name__ == "__main__":

    async def _main() -> None:
        async with httpx.AsyncClient() as client:
            papers = await search(client, "VO2max marathon performance", retmax=5)
            for p in papers:
                print(f"- [{p.pmid}] {p.title} ({p.year})")
                print(f"  abstract: {(p.abstract or '')[:150]}...")

    asyncio.run(_main())
