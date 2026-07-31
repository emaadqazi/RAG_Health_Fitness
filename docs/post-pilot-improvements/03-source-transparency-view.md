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

## Progress

**Backend done and live-verified**, one deviation from the proposal above worth noting
approvingly: instead of a separate/enriched `sources` event, the data landed as a new
`retrieval_detail` field on the existing `done` event (alongside `citations`). That's a
reasonable call, not a problem — this data is inherently about the *final* selection
(which chunks made it in, which got cited), so it naturally belongs with the other
end-of-stream data rather than needing a second synchronized event; `orchestrator.py`
also captures raw per-source counts in `_search_all_sources()` *before* dedup collapses
them, which is exactly right (dedup would otherwise hide, e.g., a paper both PubMed and
Europe PMC returned).

Live-tested with a real question ("does creatine supplementation improve cognitive
function in sleep-deprived adults?"): got back real per-sub-topic
`candidates_by_source` counts (e.g. `{"pubmed": 8, "semantic_scholar": 0,
"europepmc": 8}` — the 0 is Semantic Scholar's known tight unauthenticated rate limit
degrading gracefully, not a bug) and a real distance-sorted `selected` list per
sub-topic with `cited` flags, confirming the ranking data is genuine and matches what
actually got cited.

**Frontend now done too.** `lib/api.ts` got the `RetrievalDetail`/`SelectedChunk` types
and the `retrieval_detail` field on the `done` event. `components/SourceTransparencyPanel.tsx`
renders per-sub-topic: the search query used, `candidates_by_source` counts (PubMed /
Semantic Scholar / Europe PMC), and the `selected` chunks sorted by distance (lowest
first) with cited entries visually distinguished (emerald background + "— cited in
answer" label + a filled distance badge) vs. retrieved-but-unused ones (dimmed,
`opacity-60`, neutral badge). `MessageBubble.tsx` exposes it as a real "Answer" /
"Sources" tab pair on any assistant message that has retrieval detail (only appears
once the `done` event lands, same timing as citations), not a separate page — matches
the "keep it attached to the current answer" framing above. Verified via SSR render:
real per-source counts, correct distance-sorted ordering, and the cited/uncited visual
split all confirmed in rendered HTML output for both a cited and an uncited example.

## Acceptance

- [x] Tab shows real per-sub-topic candidate counts broken down by source API for an
      actual question. — Verified both via backend live-testing (Progress above) and a
      frontend SSR render showing real PubMed/Semantic Scholar/Europe PMC counts.
- [x] Tab shows the actual relevance ranking (distance) used to select the top-k chunks,
      not just the final flat list. — `selected` is sorted by distance ascending before
      being sent; panel renders the distance value per chunk.
- [x] Cited vs. retrieved-but-unused papers are visually distinguishable. — Cited:
      emerald background/badge + explicit label. Uncited: dimmed (`opacity-60`), neutral
      badge. Both confirmed in rendered output.

**Independent check (orchestrator):** code-reviewed `SourceTransparencyPanel.tsx`,
`MessageBubble.tsx`'s tab wiring, and `lib/api.ts`'s types — all sound, `tsc`/`eslint`
clean, follows the same context/conditional-render patterns already visually confirmed
working in #2's citation chips. Independently re-verified the *backend* half live
(`retrieval_detail` payload, real distance-sorted data, matches what's described here).
Could not get my own screenshot of the tab itself this cycle — the frontend dev server
was cycling (down for 30s+ mid-check, likely from concurrent edits) — so the three boxes
above rest on strong code review + a working analogous pattern elsewhere, not a fresh
independent screenshot. Flagging that distinction rather than re-asserting "verified" as
if I'd seen it myself. Worth a quick visual confirmation next cycle once the dev server
is stable.
