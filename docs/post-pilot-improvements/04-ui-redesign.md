# 4. Minimalistic, healthcare-friendly UI

## Problem

The current UI (`frontend/components/ChatWindow.tsx`, `MessageBubble.tsx`,
`DisclaimerBanner.tsx`, `ProgressStatus.tsx`, `frontend/app/globals.css`) is functional
but generic default-Tailwind chat styling (zinc-scale bubbles, no real palette or type
hierarchy). The ask is a more minimalistic, "healthcare-friendly" look — calm,
trustworthy, clinical-adjacent, not a typical dark chatbot skin.

Sequenced last on purpose: #1 (markdown rendering) and #2 (summary block + citation
chips) change what actually needs to be laid out — headers, a distinct summary callout,
inline citation chips, an excerpt popover — so a visual pass before those land would
likely need redoing.

## Direction

- **Palette:** soft, desaturated blues/teals + off-white/warm-gray background rather
  than the current pure zinc scale; reserve saturated red strictly for real error/
  rate-limit states so it stays meaningful when it appears (see `MessageBubble.tsx`'s
  `message.error` handling and the 429 path in `frontend/lib/api.ts`).
- **Typography:** clear hierarchy now that headers/bold are real elements (post-#1) —
  the summary callout (post-#2) and `## ` sub-topic headers need distinct, legible
  sizing, not chat-bubble-cramped text.
- **Disclaimer banner:** keep it prominent (it's load-bearing per
  `docs/ARCHITECTURE.md` §5 — "one prominent top-of-page disclaimer banner, not repeated
  per message") but restyle away from anything alarm-toned; it should read as
  informative, not a warning label.
- **Layout:** generous whitespace, mobile-first single column (already the structural
  approach per `page.tsx`), room for the new source-transparency tab (#3) without
  crowding the chat.
- **Scope check:** this is a portfolio project (per `docs/ARCHITECTURE.md`'s framing,
  not a funded product) — the goal is "looks intentional and trustworthy," a focused
  component-level restyle of the existing five components plus `globals.css` theme
  tokens, not a from-scratch design system.

## Progress

**Root cause found for the "can't get a clean live verification" problem** across this
whole Phase 10 pass: not app instability, a corrupted Turbopack dev cache — see
[../post-pilot-improvements/README.md](README.md#dev-tooling-gotcha-found-and-fixed-during-this-phase-10-pass).
Fixed (`rm -rf frontend/.next` + restart); basic interactivity (typing, button
enable/disable state) confirmed working again. Full answer+tab render screenshot still
pending one more clean pass — see note at the bottom of Acceptance below.

**In progress, most of it landed this cycle.** A real palette shift, not a token
relabeling: `globals.css` background moved from pure `#ffffff`/`#0a0a0a` to a warm
off-white `#faf9f7` / warm near-black `#16191a` (a chosen neutral with warmth, not a
generic default), neutrals across components moved from `zinc` to `stone` (pairs with
the warm background), and a single **teal** accent now threads consistently through:
the disclaimer banner (recolored from alarm-toned amber to teal, plus a small circular
"i" info glyph — reads as informative rather than a warning, exactly the brief), the
progress-status pulse dot, the example-question hover state, the chat input's
focus ring, the submit button, markdown links/blockquotes, the Answer/Sources tab
underline, the Summary callout (unified from its earlier one-off sky blue), citation
chips + their excerpt popover, and the bottom citation list. `page.tsx` also now reads
background/foreground from the CSS custom-property tokens instead of a hardcoded
`bg-zinc-50 dark:bg-black` that had drifted out of sync with the token system — a real
bug fix bundled into the redesign pass, not just styling. `tsc`/`eslint` clean throughout.

**Update: `SourceTransparencyPanel.tsx` landed too**, closing the gap noted above —
`zinc` → `stone`, links recolored to `teal`, and correctly *kept* `emerald` for the
"cited in answer" semantic state rather than folding it into the teal accent (semantic
color should stay distinct from the brand accent so it keeps meaning something — good
instinct). Every component is now on one consistent palette.

**Not yet done at all:** no mobile-viewport check, no fresh-eyes pass confirming the
disclaimer/summary/chips/tab system reads as coherent together in a live browser (vs.
my code-level review here), and error/rate-limit states haven't been re-checked under
the new palette (error text is still plain `text-red-600` — that's correct per the
brief's "reserve saturated red strictly for real error states," just unverified live).

## Acceptance

- [ ] Fresh-eyes visual pass in a browser against both desktop and mobile viewport
      widths. — Not done; only code-reviewed so far, and the dev server was too unstable
      (cycling/down) to get a fresh screenshot this check.
- [ ] Disclaimer banner, summary callout, citation chips, and source-transparency tab
      (once #1–#3 land) read as one coherent visual system, not bolted-on pieces. —
      Everything but `SourceTransparencyPanel.tsx` is on the unified teal/stone system
      now (code-level); that one file still needs the same pass, then a live check.
- [ ] No regression to the progress states (`ProgressStatus.tsx`) or error/rate-limit
      states — verify those still read clearly under the new palette. — Not verified
      live yet; `ProgressStatus.tsx`'s dot is now teal (intentional), error text
      untouched (correct per the brief) — both need eyes-on confirmation, not just
      code review.
