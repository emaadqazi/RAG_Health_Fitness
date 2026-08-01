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

## Progress

**Done.** Backend now sends a `citation_key` per selected chunk, set only on the
chunk(s) that actually earned a citation (per doc 08's chunk-level, section-scoped
fix) -- not just "this paper has a key somewhere." Frontend: `CitationChip`'s popover
gained a "Show in Sources" button; clicking it switches to the Sources tab and passes
a `{key, nonce}` request to `SourceTransparencyPanel`, which finds every entry sharing
that key via a `data-citation-key` attribute, scrolls the first into view, and applies
a highlight class (removed-and-re-added to force the animation to restart even on
repeat clicks of the same chip).

One architectural note on the fourth acceptance item below: sub-topic tabs (07) only
ever split the *answer* content, not Sources -- `SourceTransparencyPanel` still renders
every sub-topic's entries in one scrollable panel (that was always the design, see
03/07's own progress notes). So there's no "per-sub-topic Sources tab" to target; the
implementation switches to the one Sources tab and finds the entry within it regardless
of which sub-topic section it's under, which fully satisfies the underlying goal
("backtrack to where this sits among the retrieved sources") without needing tab-of-
tabs logic doc 09 speculated might be necessary.

Live-verified (normal + emulated `prefers-reduced-motion`): clicking a chip's "Show in
Sources" correctly switches tabs and highlights all matching entries with a
screenshot-confirmed teal ring, distinct from the existing cited (green)/uncited
(dimmed) styling. Reduced-motion pass confirmed no animation, same static tint applied
instantly. No console/page errors either run.

## Acceptance

- [x] Clicking a citation chip (or an action within its popover) switches to the Sources
      tab and visually highlights the specific matching entry. — Screenshot-verified
      both motion modes.
- [x] The highlighted entry is unambiguous — same excerpt text as the popover, not just
      "some entry from the right paper." — `citation_key` is only set on the chunk(s)
      whose exact text is part of that citation (chunk-level, per doc 08), so every
      highlighted entry is a genuine match, not just paper-level proximity. One honest
      caveat: the popover itself still previews only the first excerpt (a doc-02
      design choice, unchanged here) even when a citation was earned via multiple
      distinct chunks, all of which get highlighted -- not a mismatch, just worth
      naming.
- [x] Highlight behavior respects `prefers-reduced-motion` (static emphasis instead of
      an animated pulse/flash for users who've asked for less motion). — Verified via
      Playwright's emulated reduced-motion mode: no `.citation-highlight` animation,
      same tint applied instantly, `scrollIntoView` uses `"auto"` not `"smooth"`.
- [x] Works correctly once sub-topic tabs ([07](07-tabbed-answer-sections.md)) exist —
      verify the right sub-topic tab activates, not just the Sources tab in general. —
      See the architectural note above: Sources was never split per-sub-topic, so this
      resolves to "switches to the Sources tab and finds the entry regardless of which
      sub-topic section it's under," which is the actual goal and is verified working.
