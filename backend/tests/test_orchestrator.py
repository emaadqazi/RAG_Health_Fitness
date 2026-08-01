from app.pipeline.orchestrator import _split_into_subtopic_sections


def test_splits_on_headers_and_drops_summary():
    text = (
        "## Summary\nThe verdict is X.\n\n"
        "## Cardiovascular effects\nSmoking harms [1] the endothelium.\n\n"
        "## Respiratory effects\nLung function declines [2][3].\n"
    )
    sections = _split_into_subtopic_sections(text)
    assert sections == [
        "Smoking harms [1] the endothelium.",
        "Lung function declines [2][3].",
    ]


def test_no_summary_section_still_splits():
    text = "## Topic A\nBody A [1].\n\n## Topic B\nBody B [2].\n"
    sections = _split_into_subtopic_sections(text)
    assert sections == ["Body A [1].", "Body B [2]."]


def test_empty_body_sections_are_dropped():
    text = "## Summary\nverdict\n\n## Empty topic\n\n## Real topic\nBody [1].\n"
    sections = _split_into_subtopic_sections(text)
    assert sections == ["Body [1]."]


def test_no_headers_returns_empty():
    assert _split_into_subtopic_sections("Just plain text, no headers at all.") == []
