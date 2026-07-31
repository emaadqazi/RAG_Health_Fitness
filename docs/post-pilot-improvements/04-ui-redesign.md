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

## Acceptance

- [ ] Fresh-eyes visual pass in a browser against both desktop and mobile viewport
      widths.
- [ ] Disclaimer banner, summary callout, citation chips, and source-transparency tab
      (once #1–#3 land) read as one coherent visual system, not bolted-on pieces.
- [ ] No regression to the progress states (`ProgressStatus.tsx`) or error/rate-limit
      states — verify those still read clearly under the new palette.
