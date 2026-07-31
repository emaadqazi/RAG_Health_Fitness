from __future__ import annotations

from pydantic import BaseModel, Field


class Paper(BaseModel):
    """A single paper, merged across whichever sources returned it."""

    canonical_id: str  # doi:... | pmid:... | s2:... | title-hash:...
    title: str
    abstract: str | None = None
    year: int | None = None
    authors: list[str] = Field(default_factory=list)
    pmid: str | None = None
    doi: str | None = None
    semantic_scholar_id: str | None = None
    sources: list[str] = Field(default_factory=list)  # ["pubmed", "semantic_scholar", "europepmc"]
    full_text: str | None = None
    is_open_access: bool = False
    citation_count: int | None = None

    @property
    def link(self) -> str:
        if self.pmid:
            return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"
        if self.doi:
            return f"https://doi.org/{self.doi}"
        if self.semantic_scholar_id:
            return f"https://www.semanticscholar.org/paper/{self.semantic_scholar_id}"
        return ""


class SubTopic(BaseModel):
    label: str
    search_query: str
    rationale: str


class SearchResult(BaseModel):
    subtopic: SubTopic
    papers: list[Paper] = Field(default_factory=list)


class Chunk(BaseModel):
    paper_canonical_id: str
    chunk_index: int
    text: str
    section: str = "abstract"  # abstract | full_text
