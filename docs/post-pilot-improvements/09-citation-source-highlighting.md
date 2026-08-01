# 9. Link citation clicks to a highlighted entry in the Sources tab

## Problem

[02](02-structured-answer-and-citations.md) already shows the excerpt text in a popover
when you click an inline `[n]` citation chip (`CitationChip.tsx`), and
[03](03-source-transparency-view.md) already shows the same underlying data (per
sub-topic, ranked, with a `cited` flag) in the Sources tab
(`SourceTransparencyPanel.tsx`). What's missing is the connective link the user wants:
clicking a citation should let you "backtrack" to *exactly* where that piece of
information sits among the retrieved sources — not just a floating popover disconnected
from the fuller Sources view.

## Direction

Treat this as wiring together two features that already both exist, rather than
building new UI from scratch:

1. Give each entry in `SourceTransparencyPanel.tsx`'s `selected` list a stable DOM id
   derived from its citation key (once [08](08-sources-tab-bugs.md)'s chunk-level
   `cited` fix lands, each selected chunk can carry its own citation `key` when one
   applies — thread that through from the backend's `retrieval_detail` payload).
2. Clicking a `CitationChip` (or a "Show in Sources" affordance inside the existing
   excerpt popover) switches `MessageBubble.tsx`'s `activeTab` to `"sources"` and
   scrolls/highlights the matching entry — a brief background flash or a persistent
   emphasized border (something like a teal outline pulse, respecting
   `prefers-reduced-motion` — no highlight animation for users who've asked for less
   motion, just an instant static emphasis instead) on that specific list item so it's
   unambiguous which one the user backtracked to.
3. This depends on [07](07-tabbed-answer-sections.md)'s tab restructuring landing
   first if the Sources tab also gets split into per-sub-topic tabs — the "switch tab
   + scroll + highlight" logic needs to target the right sub-topic's tab, not just
   scroll within a single long Sources view. Sequence this doc after 07 and 08.

## Feasibility note

The user flagged uncertainty about whether this is even possible — it is, and cheaply:
all the data already exists (citation key ↔ paper ↔ chunk excerpt), this is UI wiring
(shared state + `scrollIntoView` + a highlight class), not a new retrieval/ranking
capability. The harder version — highlighting the exact sentence *within the original
paper itself* (e.g. deep-linking into PubMed with a text fragment) — is not reliably
possible for most sources (PubMed/DOI landing pages don't support arbitrary text-fragment
highlighting, and full-text is only available for a minority of papers). Recommend
scoping this to "highlight the retrieved excerpt in our own Sources view" (fully
achievable) rather than "highlight the sentence on the publisher's site" (not reliably
achievable) — the excerpt text shown *is* the actual passage that informed the answer,
which satisfies the "backtrack the exact information" goal without depending on
external sites cooperating.

## Acceptance

- [ ] Clicking a citation chip (or an action within its popover) switches to the Sources
      tab and visually highlights the specific matching entry.
- [ ] The highlighted entry is unambiguous — same excerpt text as the popover, not just
      "some entry from the right paper."
- [ ] Highlight behavior respects `prefers-reduced-motion` (static emphasis instead of
      an animated pulse/flash for users who've asked for less motion).
- [ ] Works correctly once sub-topic tabs ([07](07-tabbed-answer-sections.md)) exist —
      verify the right sub-topic tab activates, not just the Sources tab in general.
