# 5. Landing page with a "Let's begin" entry point

## Problem

The app currently drops straight into the chat view (`frontend/app/page.tsx` →
`DisclaimerBanner` + `ChatWindow`, with `ChatWindow`'s own empty-state showing the
disclaimer, a prompt line, and the three example-question pills). The ask is a real
landing page before that — a "Let's begin" moment — with a "cool 3D UI" and a bit more
of a health/fitness identity layered onto the current palette, which the user likes and
wants kept (warm off-white/near-black background, teal accent, `stone` neutrals — see
[04](04-ui-redesign.md)).

## Direction

- **New route/state**, not a redesign of the chat: add a landing view that renders
  before `ChatWindow` — either a separate `/` splash with a "Let's begin" button that
  navigates into the chat, or a client-side state toggle in `page.tsx` (simpler, avoids
  a real route change / no real need for the URL to differ). Prefer the state-toggle
  approach unless there's a reason to want the landing page independently linkable.
- **Keep the palette**, extend the *identity*: same teal/`stone`/warm-off-white system
  from doc 04, not a new color scheme. "Health and fitness kick" should come from
  motif/iconography/motion, not new colors — e.g. a subtle heartbeat-line or
  pulse-rhythm motif tying "biomedical literature" (the research vibe already present)
  to "fitness" (the domain), rather than generic gym/dumbbell clichés.
- **"Cool 3D UI":** the brief calls for genuine visual craft here — this is the one
  place in the app that's an entry-moment, not a utility screen, so it's fair to spend
  more design budget than the chat/tab views got. A few concrete directions worth
  considering (pick one, don't stack all of them):
  - A CSS 3D transform (`perspective`, `rotateX/Y`, subtle parallax on mouse/scroll) on
    a card or headline — cheap, no new dependency, respects `prefers-reduced-motion`.
  - A lightweight WebGL/Canvas ambient background (e.g. a slowly drifting particle
    field suggesting a pulse/heartbeat waveform, or an abstract DNA-helix-adjacent
    line pattern) behind the "Let's begin" CTA — avoid anything that reads as a stock
    Spline/Three.js hero template; keep it subtle and slow, not a flashy centerpiece.
  - Whichever direction: respect `prefers-reduced-motion`, keep it performant (this is
    a portfolio chat app, not a 3D showcase — the animation should support the "Let's
    begin" moment, not dominate it), and make sure it doesn't block/delay actually
    starting a chat for a user who just wants to ask a question.
- **The "Let's begin" action** should hand off cleanly into the existing `ChatWindow`
  empty state (disclaimer + example questions) — no need to duplicate the disclaimer or
  example questions on the landing page itself; keep the landing page focused on the
  single CTA plus a short framing line (what the tool is, in one sentence).

## Acceptance

- [ ] A real landing view appears before the chat, with a "Let's begin" (or equivalent)
      action that transitions into the existing chat empty-state.
- [ ] Visually reads as one identity with the rest of the app (same palette/type system
      as doc 04), not a bolted-on separate design.
- [ ] The 3D/motion element respects `prefers-reduced-motion` and doesn't meaningfully
      delay time-to-first-interaction for a user who just wants to start asking
      questions.
- [ ] Fresh-eyes check on both desktop and mobile viewport widths.
