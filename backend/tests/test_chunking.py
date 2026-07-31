from app.embeddings.chunking import chunk_paper
from app.retrieval.models import Paper


def test_short_abstract_is_a_single_chunk():
    paper = Paper(canonical_id="pmid:1", title="T", abstract="A short abstract about VO2max.", sources=["pubmed"])
    chunks = chunk_paper(paper)
    assert len(chunks) == 1
    assert chunks[0].section == "abstract"
    assert chunks[0].chunk_index == 0


def test_no_abstract_or_full_text_produces_no_chunks():
    paper = Paper(canonical_id="pmid:1", title="T", sources=["pubmed"])
    assert chunk_paper(paper) == []


def test_long_full_text_splits_into_multiple_overlapping_chunks():
    paragraph = "Exercise physiology sentence about lung function and VO2max. " * 30
    full_text = "\n\n".join([paragraph] * 5)
    paper = Paper(canonical_id="pmid:1", title="T", abstract="Short abstract.", full_text=full_text, sources=["europepmc"])
    chunks = chunk_paper(paper)
    # 1 abstract chunk + multiple full-text chunks, indices contiguous
    assert chunks[0].section == "abstract"
    full_text_chunks = [c for c in chunks if c.section == "full_text"]
    assert len(full_text_chunks) > 1
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunk_index_unique_per_paper():
    paper = Paper(
        canonical_id="pmid:1",
        title="T",
        abstract="Abstract text here.",
        full_text="Paragraph one.\n\nParagraph two.\n\nParagraph three.",
        sources=["europepmc"],
    )
    chunks = chunk_paper(paper)
    assert len({c.chunk_index for c in chunks}) == len(chunks)
