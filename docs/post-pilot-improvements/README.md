# Post-pilot improvements

This folder is **Phase 10** — work identified from actually using the app after the
Phase 0–9 pilot build (see [../ARCHITECTURE.md](../ARCHITECTURE.md) for the original
plan), not part of the original scope. Each file below is one issue, written against
the real code paths involved so it's actionable without re-deriving context.

Source of these issues: a real pilot session asking "how much does chronic sleep
deprivation blunt the benefits of strength training?" surfaced formatting, structure,
and transparency gaps in how the answer is presented — not pipeline/retrieval bugs
(those are solid per the live verification in the main README's Status section).

## Issues, roughly in the order they compound on each other

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

## Not in scope here

Deploy (Phase 8) and general polish (Phase 9) from the original plan are unaffected by
this list and can proceed independently — none of these four issues block a pilot
deploy, they're about response quality/trust once real users are looking at it.
