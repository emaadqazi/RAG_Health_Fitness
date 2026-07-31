# 1. Render markdown instead of showing raw text

## Problem

`frontend/components/MessageBubble.tsx` renders the streamed answer as plain text:

```tsx
{message.text && <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.text}</p>}
```

But the synthesis system prompt (`backend/app/pipeline/prompts.py`) explicitly asks the
model to structure its answer with markdown headers and emphasis (see the real pilot
output in [02](02-structured-answer-and-citations.md) — `## Smoking's effects on...`,
`**your health trajectory**`, etc.). Users see literal `##` and `**` characters instead
of formatted headers/bold text.

## Fix

- Add `react-markdown` + `remark-gfm` (for tables/strikethrough if the model ever uses
  them) to `frontend/package.json`.
- Replace the raw `<p>` in `MessageBubble.tsx` with `<ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>`.
- Streaming safety: `message.text` is the accumulating string as tokens arrive
  (see `ChatWindow.tsx`'s event loop over `streamChat`) — react-markdown re-parses on
  every render, which is fine at chat-turn scale (one message, a few KB of text), no
  incremental-parser complexity needed.
- Style the rendered output with either `@tailwindcss/typography`'s `prose` class
  (customized to match [04](04-ui-redesign.md)'s palette) or hand-rolled Tailwind
  overrides for `h2`, `strong`, `ul`/`ol`, `p` — plain `prose` defaults will look
  generic/too-large inside a chat bubble, so this needs a pass either way.
- Do **not** let markdown rendering interpret the citation markers `[1]`, `[2]` as
  markdown link syntax by accident — they're plain brackets today, not `[text](url)`,
  so standard markdown parsers should leave them alone, but verify once #2's inline
  citation-chip work lands (that will intentionally turn them into custom elements).

## Acceptance

- [ ] A real streamed answer shows actual `<h2>`/`<strong>`/`<ul>` elements, not literal
      `#`/`*` characters, verified in a browser (not just unit-tested).
- [ ] Headers/bold/lists are legible inside the chat-bubble width (not oversized —
      tune `prose-sm` or custom sizing).
- [ ] No layout break mid-stream while markdown is still incomplete (e.g. an unclosed
      `**` while tokens are still arriving) — check visually during an active stream,
      not just on the final message.
