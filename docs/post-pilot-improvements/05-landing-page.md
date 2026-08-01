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

## Progress

**Done.** `AppShell.tsx` (client-side state toggle, no new route) renders
`LandingPage.tsx` first, handing off into the untouched `ChatWindow` empty state on
"Let's begin". Kept the doc 04 palette exactly; identity comes from a slow ECG/pulse-
line SVG drift + heartbeat icon, not new colors. "Cool 3D UI" is a CSS-only mouse-
follow `rotateX/rotateY` tilt on the card (`perspective` + CSS custom properties) --
no new dependency. Both motion effects respect `prefers-reduced-motion` two ways: the
JS tilt listener is never attached when reduced motion is preferred (via
`useSyncExternalStore`, after an eslint rule caught an initial `setState`-in-effect
version), plus a CSS `@media (prefers-reduced-motion: reduce)` rule as a second line
of defense on the SVG/icon animations.

Live-verified with real Playwright screenshots (installed `playwright` + chromium
myself this cycle to close the "I can't see a browser" gap) across desktop, mobile,
and a reduced-motion-emulated run: "Let's begin" clickable within ~600ms every time
(no meaningful delay), clean handoff into the chat empty state with no duplicated
disclaimer/example questions, zero console/page errors.

## Acceptance

- [x] A real landing view appears before the chat, with a "Let's begin" (or equivalent)
      action that transitions into the existing chat empty-state. — Screenshot-verified.
- [x] Visually reads as one identity with the rest of the app (same palette/type system
      as doc 04), not a bolted-on separate design. — Same teal/stone/warm-off-white
      system, no new colors introduced.
- [x] The 3D/motion element respects `prefers-reduced-motion` and doesn't meaningfully
      delay time-to-first-interaction for a user who just wants to start asking
      questions. — ~600ms to interactive across all three screenshot runs; reduced-
      motion run confirmed no animation attached.
- [x] Fresh-eyes check on both desktop and mobile viewport widths. — Both
      screenshot-verified; layout holds at 390px width.
