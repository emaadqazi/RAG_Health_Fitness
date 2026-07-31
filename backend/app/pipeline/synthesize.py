from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator

from app.llm.base import LLMProvider
from app.pipeline.prompts import SYNTHESIS_SYSTEM_PROMPT
from app.retrieval.models import Paper, SubTopic
from app.vectorstore.store import ChunkSearchResult


@dataclass
class Excerpt:
    text: str
    section: str


@dataclass
class CitationEntry:
    key: int
    paper: Paper
    # A paper can be cited via more than one retrieved chunk (same sub-topic or
    # across sub-topics) -- keep all of them so the frontend can show the specific
    # passage that backs a given claim, not just the paper title/link.
    excerpts: list[Excerpt] = field(default_factory=list)


def assemble_context(
    question: str,
    subtopic_results: list[tuple[SubTopic, list[ChunkSearchResult]]],
    papers: dict[str, Paper],
) -> tuple[str, list[CitationEntry]]:
    """Build the synthesis user-turn content and the ordered citation list.

    Citation numbers are assigned in order of first appearance across sub-topics so
    they read naturally top-to-bottom in the final answer.
    """
    citation_by_paper: dict[str, CitationEntry] = {}
    next_key = 1
    sections: list[str] = [f"Question: {question}\n"]

    for subtopic, results in subtopic_results:
        if not results:
            continue
        lines = [f"## {subtopic.label}\n({subtopic.rationale})"]
        for r in results:
            paper = papers.get(r.paper_canonical_id)
            if paper is None:
                continue
            if paper.canonical_id not in citation_by_paper:
                citation_by_paper[paper.canonical_id] = CitationEntry(key=next_key, paper=paper)
                next_key += 1
            entry = citation_by_paper[paper.canonical_id]
            if not any(e.text == r.text for e in entry.excerpts):
                entry.excerpts.append(Excerpt(text=r.text, section=r.section))
            lines.append(f"[{entry.key}] {paper.title} ({paper.year or 'n.d.'}): {r.text}")
        sections.append("\n".join(lines))

    user_content = "\n\n".join(sections)
    citations = sorted(citation_by_paper.values(), key=lambda c: c.key)
    return user_content, citations


async def stream_synthesis(llm: LLMProvider, user_content: str, max_tokens: int) -> AsyncIterator[str]:
    async for token in llm.stream_complete(
        system=SYNTHESIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        max_tokens=max_tokens,
    ):
        yield token
