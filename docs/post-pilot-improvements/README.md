# Post-pilot improvements

This folder is **Phase 10** — work identified from actually using the app after the
Phase 0–9 pilot build (see [../ARCHITECTURE.md](../ARCHITECTURE.md) for the original
plan), not part of the original scope. Each file below is one issue, written against
the real code paths involved so it's actionable without re-deriving context.

Source of these issues: a real pilot session asking "how much does chronic sleep
deprivation blunt the benefits of strength training?" surfaced formatting, structure,
and transparency gaps in how the answer is presented — not pipeline/retrieval bugs
(those are solid per the live verification in the main README's Status section).

## Round 1 — issues, roughly in the order they compound on each other

1. [Markdown rendering](01-markdown-rendering.md) — answers are markdown but rendered
   as plain text (visible `##`, `**`). Fix this first; it's a prerequisite for #2 reading
   cleanly.
2. [Structured answers + inline source excerpts](02-structured-answer-and-citations.md)
   — answers read as one undifferentiated block instead of summary-then-reasoning, and
   citation markers like `[1]` are dead text instead of linking to the actual excerpt
   that supports the claim.
3. [Source transparency view](03-source-transparency-view.md) — a tab showing what was
   retrieved from where, and why one paper was surfaced over another for a given
   sub-topic (the pipeline already computes this ranking internally; it's just not
   exposed).
4. [UI redesign](04-ui-redesign.md) — generic default-Tailwind chat styling; wants a
   minimalistic, healthcare-friendly look. Sequenced last because #1–#3 change what
   needs to be laid out.

## Round 2 — issues raised after seeing #1–#4 live

Sequencing matters more here than in round 1 — later items depend on earlier ones, noted
inline.

5. [Landing page](05-landing-page.md) — a "Let's begin" entry screen with a 3D visual
   treatment, before dropping into the chat. Independent of the rest of this round.
6. [Buffered response reveal](06-buffered-response-reveal.md) — stop growing the answer
   bubble token-by-token (forces the user to keep scrolling); reveal the complete answer
   once ready instead. Do this before #7 — tab-splitting a still-streaming answer adds
   real complexity that buffering avoids.
7. [Per-sub-topic tabs](07-tabbed-answer-sections.md) — pull each `## `-headed section
   of the answer into its own tab instead of one long scroll, alongside the existing
   Sources tab. Depends on #6.
8. [Sources tab bugs](08-sources-tab-bugs.md) — two confirmed bugs found while
   reproducing a user report: raw HTML entities showing in some paper titles, and the
   "cited in answer" flag being paper-level instead of chunk-level (so it's currently
   showing almost everything as cited). Independent of #6/#7, but do it before #9.
9. [Citation → source highlighting](09-citation-source-highlighting.md) — clicking a
   citation should highlight the matching entry in the Sources tab, not just show a
   disconnected popover. Depends on #7 (tab targeting) and #8 (accurate `cited` data).

## Not in scope here

Deploy (Phase 8) and general polish (Phase 9) from the original plan are unaffected by
this list and can proceed independently — none of these issues block a pilot deploy,
they're about response quality/trust/UX once real users are looking at it.

## Dev-tooling gotcha (found and fixed during this Phase 10 pass)

For a while during this work, the running-app verification kept intermittently failing
in ways that looked like ordinary HMR flakiness from rapid concurrent edits (clicks not
registering, streamed input not updating, dev server occasionally down). It was actually
a real bug, just not in application code: **Turbopack's persistent dev cache (`.next/`)
gets corrupted by rapidly creating and deleting the same route directory** (this repo's
verification pattern used a throwaway `frontend/app/markdown-test/` route, created and
removed several times across #1–#3's manual checks). Once corrupted, the dev server
enters a fatal-panic-and-restart loop (`next.js` log: `Failed to write app endpoint
/markdown-test/page ... no longer exists in task ... (no cell of this type exists)`),
serving fast 200s on `/` the whole time — which is why it read as "flaky" rather than
"broken." **Fix:** `rm -rf frontend/.next` and restart `next dev`. If a future scratch
route is needed for manual verification, prefer a stable name that's created once and
reused, or just delete `.next` after removing a throwaway route, rather than repeatedly
creating/deleting different route paths across a long dev session.
