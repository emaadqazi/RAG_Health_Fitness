# 2. Structured summary-first answers + inline source excerpts

## Problem

Two related issues from a real pilot answer (question: "how much does chronic sleep
deprivation blunt the benefits of strength training?"):

**A. No summary/abstract.** The answer reads like a chatbot transcript — it launches
straight into detailed reasoning per sub-topic. There's no short, skimmable verdict up
top the way a human-written brief would lead with an abstract before the body.

**B. Citation markers are dead text.** The answer contains lines like:

> "The most direct effect is impairment of the anabolic machinery itself. Sleep
> deprivation disrupts the hormonal signaling pathways that translate mechanical
> training stimulus into muscle growth [1]."

`[1]` is currently just a plain-text bracket (see `assemble_context()` in
`backend/app/pipeline/synthesize.py`, which builds `[key] title (year): excerpt` blocks
as *input* context to the LLM). The user has to scroll to the bottom `CitationList` and
match the number by hand — and even then, the bottom list only shows the paper's
title/link, not the specific sentence/excerpt that actually backs *that* claim. The
ask is: clicking `[1]` should show the actual passage from the paper that supports it
("highlight that piece of paper").

## What's already available (the good news)

The backend already computes the exact excerpt used per citation — it's just discarded
before reaching the frontend:

- `backend/app/pipeline/synthesize.py::assemble_context()` builds `CitationEntry(key,
  paper)` from `ChunkSearchResult.text` (the actual chunk text, per
  `backend/app/vectorstore/store.py`'s `ChunkSearchResult` — `text`, `section`,
  `paper_canonical_id`, `distance`) — but only keeps `paper`, dropping which chunk(s)
  the LLM was actually shown.
- `backend/app/pipeline/orchestrator.py`'s final `done` event only sends
  `key/title/year/link` per citation — no excerpt text.

## Proposed changes

**Backend:**
1. Extend `CitationEntry` in `synthesize.py` to also carry the list of chunk excerpts
   used for that paper (a paper can be cited via more than one retrieved chunk across
   sub-topics — keep all of them, frontend can pick "best"/first or show all).
2. In `orchestrator.py`'s `done` event, include an `excerpts` field per citation:
   `[{"text": ..., "section": "abstract" | "full_text"}, ...]`.
3. In `prompts.py`'s `SYNTHESIS_SYSTEM_PROMPT`, add an explicit instruction to open with
   a short (2–4 sentence) `## Summary` section stating the direct answer/verdict in
   plain language, *before* the per-sub-topic reasoning sections it already produces
   (the "Structure: excerpts grouped under `## ` sub-topic headers" instruction already
   there stays — this just adds one more required leading section).

**Frontend:**
1. Post-process the rendered markdown to turn inline `[n]` markers into clickable
   citation chips (small superscript-style buttons), not plain text — e.g. a
   remark/rehype text transform, or a regex pass over `message.text` before handing it
   to `react-markdown` that swaps `[n]` for a custom `<CitationChip n={n} />`-friendly
   token.
2. Clicking/tapping a chip opens a small popover/inline panel showing that citation's
   excerpt text (from the new `excerpts` field) and a link to the source. This is the
   "highlight that piece of paper" ask — showing the actual sentence(s), not just
   linking out to PubMed and leaving the user to search the abstract themselves.
3. Keep the bottom `CitationList` as the full reference list (still useful as a
   scannable "everything cited" summary) — the chips are additive, not a replacement.
4. Render the new `## Summary` section visually distinct from the rest (e.g. a bordered
   callout box at the top of the message) so it reads as "the abstract," not just
   another paragraph.

## Acceptance

- [ ] A real answer shows a clearly distinct summary block before the detailed
      reasoning sections.
- [ ] Clicking an inline `[n]` marker shows the specific excerpt text that supports that
      claim, not just the paper title/link.
- [ ] The bottom source list still works as a full reference list.
- [ ] Re-run the flagship half-marathon/smoking question and the sleep-deprivation
      question from this doc to confirm both read clearly with the new structure.
