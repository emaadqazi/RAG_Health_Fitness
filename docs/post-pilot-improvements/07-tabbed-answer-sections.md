# 7. Per-sub-topic tabs instead of one long scrolling answer

## Problem

The synthesis prompt (`backend/app/pipeline/prompts.py`) already structures every
answer as `## Summary` followed by one `## `-headed section per sub-topic (e.g. for a
creatine question: "Creatine metabolism and urinary excretion", "Acute vs. chronic
effects", etc. — see the real subtopic labels already flowing through the
`decomposition` SSE event). Right now `MessageBubble.tsx` renders all of that as one
continuous scroll under the Summary callout. The user wants each sub-topic section
pulled into its own tab instead of one long page of paragraphs — the Summary stays
up top (that part's working well, keep it as-is), the detail underneath becomes
navigable rather than a wall of text.

## What's already available

- `decomposition` event gives sub-topic `label`s up front, before the answer even
  starts streaming.
- The synthesis prompt already emits one `## <label>` markdown header per sub-topic in
  the answer body (matching those same labels) — see `prompts.py`'s "Structure:..."
  instruction. So the section boundaries already exist in the text; they just need to
  be parsed out into tabs instead of rendered as sequential headers.
- `MessageBubble.tsx` already has a working tab-pair pattern to extend (`Answer` /
  `Sources`, from [03](03-source-transparency-view.md)) — `TAB_BUTTON_BASE/ACTIVE/INACTIVE`
  and the `activeTab` state — this is the same UI primitive, just with more tabs and
  driven by parsed section names instead of a fixed pair.

## Direction

- **Parsing:** split `message.text` (after pulling out the `## Summary` block, which
  already happens in `splitSummarySection()`) into segments on each `## ` header,
  keeping the header text as the tab label and the following markdown as that tab's
  content. This is the same kind of regex/split `splitSummarySection()` already does,
  generalized to split on *every* `## ` boundary rather than just the first one.
- **Streaming interaction with [06](06-buffered-response-reveal.md):** if 06 lands
  first (buffer full text, reveal on `done`), section-splitting only needs to run once
  on the complete text — simpler. If tabs need to work before 06 lands, splitting
  mid-stream on a not-yet-closed section is possible but adds real complexity (a
  partially-streamed final section) — recommend sequencing 06 before this one for
  exactly that reason.
- **Tab bar:** replace the current fixed `Answer` / `Sources` pair with
  `[Sub-topic 1] [Sub-topic 2] ... [Sub-topic N] [Sources]` — Summary stays visible
  above the tab bar regardless of which tab is active (it's the one thing the user
  explicitly said is working well and should stay put). Keep sub-topic labels
  reasonably short in the tab bar even if the underlying `label` is a full sentence —
  truncate with an ellipsis + full text on hover/title attribute if needed, since
  labels like "Creatine supplementation and kidney function biomarkers" are long.
- **Default active tab:** first sub-topic, not Sources (Sources should still require an
  explicit click, consistent with current behavior).

## Acceptance

- [ ] A real multi-sub-topic answer shows one tab per sub-topic (matching the actual
      `## ` headers in the answer), not one long scroll.
- [ ] Summary callout remains visible/pinned above the tabs regardless of active tab.
- [ ] Sources tab still works alongside the new sub-topic tabs.
- [ ] Tab labels stay legible (truncation/ellipsis) even for long sub-topic labels —
      check against a real long label, not a short placeholder.
- [ ] Mobile viewport check — a horizontal row of 4–5 tabs needs to not overflow badly
      on a narrow screen (horizontal scroll on the tab bar itself is an acceptable
      fallback, just make sure it's usable, not broken).
