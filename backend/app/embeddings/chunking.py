"""Chunking for abstracts and full text.

Token sizing uses a lightweight word-count heuristic (words * ~1.3) rather than a
real tokenizer -- acceptable at this scale and avoids an extra dependency.
"""

from __future__ import annotations

import re

from app.retrieval.models import Chunk, Paper

WORDS_PER_TOKEN = 1 / 1.3  # inverse: tokens ~= words * 1.3

ABSTRACT_MAX_TOKENS = 500
FULL_TEXT_CHUNK_TOKENS = 400
FULL_TEXT_OVERLAP_TOKENS = 60


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _word_count(text: str) -> int:
    return len(text.split())


def _tokens_estimate(text: str) -> float:
    return _word_count(text) * 1.3


def chunk_abstract(paper: Paper) -> list[Chunk]:
    if not paper.abstract:
        return []
    if _tokens_estimate(paper.abstract) <= ABSTRACT_MAX_TOKENS:
        return [Chunk(paper_canonical_id=paper.canonical_id, chunk_index=0, text=paper.abstract, section="abstract")]

    # Defensive split for unusually long abstracts, at sentence boundaries.
    sentences = _split_sentences(paper.abstract)
    return _pack_sentences(sentences, paper.canonical_id, section="abstract", max_tokens=ABSTRACT_MAX_TOKENS, overlap_tokens=40)


def chunk_full_text(paper: Paper) -> list[Chunk]:
    if not paper.full_text:
        return []
    # Prefer paragraph boundaries; fall back to sentence boundaries within an
    # over-long paragraph so we never cut mid-sentence.
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", paper.full_text) if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = _split_sentences(paper.full_text)

    return _pack_sentences(
        paragraphs,
        paper.canonical_id,
        section="full_text",
        max_tokens=FULL_TEXT_CHUNK_TOKENS,
        overlap_tokens=FULL_TEXT_OVERLAP_TOKENS,
    )


def _pack_sentences(
    units: list[str], paper_canonical_id: str, section: str, max_tokens: int, overlap_tokens: int
) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0.0
    chunk_index = 0

    for unit in units:
        unit_tokens = _tokens_estimate(unit)
        if current and current_tokens + unit_tokens > max_tokens:
            chunks.append(
                Chunk(paper_canonical_id=paper_canonical_id, chunk_index=chunk_index, text=" ".join(current), section=section)
            )
            chunk_index += 1
            # carry the tail of the previous chunk forward for overlap
            overlap: list[str] = []
            overlap_total = 0.0
            for u in reversed(current):
                t = _tokens_estimate(u)
                if overlap_total + t > overlap_tokens:
                    break
                overlap.insert(0, u)
                overlap_total += t
            current = overlap
            current_tokens = overlap_total

        current.append(unit)
        current_tokens += unit_tokens

    if current:
        chunks.append(
            Chunk(paper_canonical_id=paper_canonical_id, chunk_index=chunk_index, text=" ".join(current), section=section)
        )

    return chunks


def chunk_paper(paper: Paper) -> list[Chunk]:
    """Chunk a paper: full text chunks (if present) plus the abstract as its own chunk."""
    chunks = chunk_abstract(paper)
    full_text_chunks = chunk_full_text(paper)
    # renumber full-text chunks after the abstract chunk(s)
    offset = len(chunks)
    for c in full_text_chunks:
        c.chunk_index += offset
    return chunks + full_text_chunks
