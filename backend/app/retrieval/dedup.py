"""Merge papers returned by multiple sources into one record per canonical ID.

Canonical ID preference: DOI > PMID > Semantic Scholar paperId > title+year hash.
Each source may key a paper slightly differently (e.g. PubMed uses pmid:..., but
Semantic Scholar/Europe PMC prefer doi:... when available) — `_remap_canonical_id`
normalizes before merging so the same paper from different sources collapses into
one entry instead of duplicating.
"""

from __future__ import annotations

import hashlib
import re

from app.retrieval.models import Paper


def _title_hash(title: str, year: int | None) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", title.lower())
    digest = hashlib.sha1(f"{normalized}:{year or ''}".encode()).hexdigest()[:16]
    return f"titlehash:{digest}"


def _best_canonical_id(paper: Paper) -> str:
    if paper.doi:
        return f"doi:{paper.doi.lower()}"
    if paper.pmid:
        return f"pmid:{paper.pmid}"
    if paper.semantic_scholar_id:
        return f"s2:{paper.semantic_scholar_id}"
    return _title_hash(paper.title, paper.year)


def _merge(a: Paper, b: Paper) -> Paper:
    """Merge b into a, preferring non-empty fields and unioning sources/authors."""
    return Paper(
        canonical_id=a.canonical_id,
        title=a.title or b.title,
        abstract=a.abstract or b.abstract,
        year=a.year or b.year,
        authors=a.authors or b.authors,
        pmid=a.pmid or b.pmid,
        doi=a.doi or b.doi,
        semantic_scholar_id=a.semantic_scholar_id or b.semantic_scholar_id,
        sources=sorted(set(a.sources) | set(b.sources)),
        full_text=a.full_text or b.full_text,
        is_open_access=a.is_open_access or b.is_open_access,
        citation_count=a.citation_count if a.citation_count is not None else b.citation_count,
    )


def dedup_papers(papers: list[Paper]) -> list[Paper]:
    """Collapse papers from multiple sources into one record per canonical work."""
    merged: dict[str, Paper] = {}
    for paper in papers:
        key = _best_canonical_id(paper)
        paper = paper.model_copy(update={"canonical_id": key})
        if key in merged:
            merged[key] = _merge(merged[key], paper)
        else:
            merged[key] = paper
    return list(merged.values())
