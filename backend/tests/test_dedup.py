from app.retrieval.dedup import dedup_papers
from app.retrieval.models import Paper


def test_dedup_merges_by_doi_across_sources():
    a = Paper(canonical_id="pmid:1", title="Same paper", doi="10.1/x", pmid="1", sources=["pubmed"])
    b = Paper(
        canonical_id="s2:abc",
        title="Same paper",
        doi="10.1/X",  # different case, should still match
        abstract="from semantic scholar",
        sources=["semantic_scholar"],
    )
    merged = dedup_papers([a, b])
    assert len(merged) == 1
    assert merged[0].abstract == "from semantic scholar"
    assert set(merged[0].sources) == {"pubmed", "semantic_scholar"}


def test_dedup_keeps_distinct_papers_separate():
    a = Paper(canonical_id="pmid:1", title="Paper A", pmid="1", sources=["pubmed"])
    b = Paper(canonical_id="pmid:2", title="Paper B", pmid="2", sources=["pubmed"])
    merged = dedup_papers([a, b])
    assert len(merged) == 2


def test_dedup_falls_back_to_title_hash_when_no_ids():
    a = Paper(canonical_id="x", title="A Paper With No IDs", year=2020, sources=["europepmc"])
    b = Paper(canonical_id="y", title="a paper with no ids", year=2020, sources=["europepmc"])
    merged = dedup_papers([a, b])
    assert len(merged) == 1
