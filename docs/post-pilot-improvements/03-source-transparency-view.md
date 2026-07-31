# 3. Source transparency view

## Problem

The user wants to see, per question: which of the three literature APIs (PubMed,
Semantic Scholar, Europe PMC) actually returned results, how many candidates came back
per sub-topic, and — the specific ask — *why* one paper was surfaced in the final answer
over another for a given sub-topic. Not a diagram, more like a structured/filterable
view of the retrieval process. Currently the app shows only the final deduped paper list
with no ranking or provenance.

## What's already available

The pipeline already computes exactly this, it's just not exposed past the current
`sources` SSE event:

- `backend/app/pipeline/orchestrator.py::_retrieve_and_cache_subtopic()` calls
  `similarity_search()` per sub-topic and gets back `ChunkSearchResult` objects with a
  `distance` field (pgvector cosine distance — **this *is* the ranking** used to decide
  which chunks/papers make it into the synthesis context, via `MAX_CHUNKS_PER_SUBTOPIC`
  in `config.py`). Lower distance = more relevant = more likely to be selected.
- Each `Paper` already carries a `sources: list[str]` field (e.g. `["pubmed",
  "europepmc"]`) from the cross-source dedup in `backend/app/retrieval/dedup.py` — so
  which API(s) surfaced a given paper is already known.
- The current `sources` event in `orchestrator.py` flattens all of this into one
  undifferentiated `papers` list across every sub-topic, with no distance/ranking and no
  per-sub-topic grouping — that's the gap.

## Proposed changes

**Backend:** enrich (or add alongside) the `sources` event with per-sub-topic structure,
something like:

```json
{
  "subtopics": [
    {
      "label": "Smoking's effects on cardiovascular function and aerobic capacity",
      "search_query": "smoking tobacco cardiovascular effects aerobic fitness VO2 max",
      "candidates_by_source": {"pubmed": 8, "semantic_scholar": 6, "europepmc": 8},
      "selected": [
        {"title": "...", "link": "...", "distance": 0.178, "section": "abstract", "cited": true},
        {"title": "...", "link": "...", "distance": 0.241, "section": "full_text", "cited": false}
      ]
    }
  ]
}
```

`cited` = whether that chunk's paper ended up with a citation key in the final `done`
event (cross-reference against the citation list) — this is what answers "why article 1
over article 2": it was closer in embedding space to the sub-topic query, and/or it's
one of the top-`MAX_CHUNKS_PER_SUBTOPIC` results while the other wasn't.

**Frontend:** a second tab/panel next to the chat (not a separate page — keep it
attached to the current answer) showing:
- One section per sub-topic, with a small breakdown of how many candidates came from
  each of the 3 APIs.
- The selected/ranked chunks for that sub-topic, ordered by relevance (lowest distance
  first), visually marking which ones made it into the actual answer (`cited: true`) vs.
  were retrieved but not used.

This is explicitly *not* meant to be a chart/diagram per the ask — a clean list/table
view grouped by sub-topic is enough; revisit as a visual only if a table ends up feeling
insufficient once it's built.

## Acceptance

- [ ] Tab shows real per-sub-topic candidate counts broken down by source API for an
      actual question.
- [ ] Tab shows the actual relevance ranking (distance) used to select the top-k chunks,
      not just the final flat list.
- [ ] Cited vs. retrieved-but-unused papers are visually distinguishable.
