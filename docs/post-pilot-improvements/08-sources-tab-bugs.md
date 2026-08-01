# 8. Sources tab bugs (reported: "not fully showing")

## Context

User-reported bug, with a screenshot that didn't come through in the conversation this
was dictated in. Rather than block on that image, I (the orchestrator) reproduced the
Sources tab live against the running app (`SourceTransparencyPanel.tsx`, real question:
"Does creatine supplementation affect kidney function in healthy adults?") and found two
concrete, confirmed issues. Neither is a full page-clipping/truncation bug in a desktop
headless-browser render — if what the user saw was specifically a visual cutoff (e.g. on
mobile, or a specific browser), get the actual screenshot and compare against what's
below; it may be a third, separate issue.

## Confirmed issue A: raw HTML entities showing in paper titles

Some paper titles contain literal escaped HTML, e.g. a real title rendered in the panel
as:

> The &lt;i&gt;Comrades Marathon&lt;/i&gt;: a narrative review of physiological
> responses and health implications in the world's oldest ultra-marathon.

instead of *The Comrades Marathon: a narrative review...* — the source metadata
(PubMed/Europe PMC/Semantic Scholar) includes markup (here `<i>...</i>` for italicizing
a race name) in the title field, and it's being displayed as escaped literal text
instead of being stripped or rendered. This is likely double-escaping: the title string
probably already contains literal `<i>` tags from the source API, gets HTML-escaped
somewhere (React does this by default for plain text interpolation, which is correct
behavior for *untrusted* text), and the result is visible `&lt;i&gt;` rather than either
plain "Comrades Marathon" (tags stripped) or actually-italicized text (tags rendered
safely). This likely affects `frontend/components/SourceTransparencyPanel.tsx` and
`CitationList.tsx`/`CitationChip.tsx` equally, since they all render `title` directly —
worth checking `backend/app/retrieval/{pubmed,europepmc,semantic_scholar}.py`'s title
parsing too, since stripping embedded markup at ingestion time (plain-text titles in the
`Paper` model) is probably the more correct fix than a frontend rendering workaround —
it'd fix this everywhere titles are shown, not just in one component.

## Confirmed issue B: "cited in answer" is over-inclusive (paper-level, not chunk-level)

In the live test, essentially *every* entry across every sub-topic showed the green
"— cited in answer" label — including entries that read as tangential to the actual
question (e.g. a blood-flow-restriction-training paper showing as cited on a creatine/
kidney-function question). Root cause, in `backend/app/pipeline/orchestrator.py`:

```python
cited_canonical_ids = {c.paper.canonical_id for c in citations}
...
"cited": r.paper_canonical_id in cited_canonical_ids,
```

`cited_canonical_ids` is a set of **paper** IDs, not **chunk** IDs. If a paper got cited
via *any* chunk from *any* sub-topic, every chunk of that paper across *every*
sub-topic's `selected` list shows as cited — even a chunk that was retrieved for a
different sub-topic and never actually informed the part of the answer it's listed
under. This defeats the actual point of the feature (showing *why this specific chunk,
for this specific sub-topic*, did or didn't make it into the answer).

**Fix:** `synthesize.py`'s `CitationEntry.excerpts` already tracks the exact chunk
texts used per citation (see [02](02-structured-answer-and-citations.md)) — check
chunk-level membership instead of paper-level: a `ChunkSearchResult` should show
`cited: true` only if its specific `text` appears in that citation's `excerpts` list
(match by `(paper_canonical_id, text)`, not just `paper_canonical_id`).

## Acceptance

- [ ] Paper titles render clean (no visible `&lt;`/`&gt;` or raw markup) everywhere a
      title is shown — Sources tab, citation chips, bottom citation list.
- [ ] "Cited in answer" reflects chunk-level truth: a chunk only shows as cited if that
      specific excerpt was actually used in the synthesis context for a citation,
      not just "this paper got cited somewhere." Verify by checking a paper that
      appears in two different sub-topics' candidate lists but was only actually cited
      via one of them — it should show cited in one sub-topic's list, not both.
- [ ] Get the user's actual screenshot/repro and confirm whether there's a separate
      visual clipping/truncation bug beyond A and B above (possibly mobile-specific or
      browser-specific) — if so, add it here as issue C.
