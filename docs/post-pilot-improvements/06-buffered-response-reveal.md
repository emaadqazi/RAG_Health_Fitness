# 6. Don't force-scroll while the answer is streaming in

## Problem

Right now `frontend/components/ChatWindow.tsx`'s `ask()` appends each SSE `token` event
directly into `message.text` as it arrives (see the `event.type === "token"` branch),
so the assistant bubble grows continuously while the page's natural scroll-follow
behavior keeps chasing it. The user has to keep scrolling to track it, and wants the
answer to appear once it's actually ready rather than growing under them.

## Direction (recommended default — see tradeoff below)

**Keep the backend exactly as-is.** The SSE pipeline
(`backend/app/api/routes_chat.py` / `backend/app/pipeline/orchestrator.py`) streaming
`decomposition` → `sources` → `token`s → `done` is still the right backend shape —
this is a frontend *reveal* change, not a backend architecture change, so it doesn't
touch the retrieval/synthesis pipeline at all.

**On the frontend:** keep consuming the stream token-by-token (so progress states —
"Breaking down your question…", "Searching…", "Synthesizing…" via
`ProgressStatus.tsx` — still update live and the cold-start hint still works), but stop
writing each token into the *rendered* `message.text` as it arrives. Instead, accumulate
tokens into a buffer, and only commit the full text to render once the `done` event
lands (same moment `citations`/`retrievalDetail` already arrive). Concretely: keep a
`streamingBuffer` ref/state separate from `message.text`, append tokens to it silently,
and on `done` set `message.text = streamingBuffer` in the same update that sets
citations — so the whole answer (markdown, Summary callout, citation chips, tabs from
[07](07-tabbed-answer-sections.md)) appears fully formed in one commit, no growing
bubble, no scroll-chasing.

Keep the progress-state indicator visible and *changing* for the whole wait (already
mostly true) so the user still gets feedback that something's happening — the change is
purely "don't reveal partial text," not "give no feedback at all." Consider updating the
final progress-stage label to something like "Writing your answer…" once tokens start
arriving but before `done`, so the wait doesn't feel dead during the (sometimes 30–60s+)
synthesis stretch.

## Tradeoff worth being explicit about

This trades the "watching Claude think in real time" streaming feel for a calmer,
scroll-stable reveal. That's a legitimate product choice (the user asked for it
directly), but flagging it because it's a real behavior change, not just a bug fix — if
it ends up feeling like a long dead wait without enough progress feedback, the fix is
better progress-state messaging (see above), not reverting to token-by-token reveal.

## Acceptance

- [ ] Progress states still update live while waiting (decomposing → searching →
      synthesizing), so the wait doesn't look frozen.
- [ ] The assistant bubble does not grow/repaint incrementally during synthesis — it
      appears complete (summary + tabs + citations) in one commit once ready.
- [ ] No more forced auto-scroll-chasing during an active question — verify by asking a
      question and confirming the page doesn't jump/grow under the user while waiting.
- [ ] `error` events (mid-stream failures) still surface correctly even though text
      isn't being progressively revealed — verify an error case still shows the error
      message, not a silently-abandoned buffer.
