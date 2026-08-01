# Health/Fitness RAG Chatbot

A chatbot that answers nuanced health/fitness questions by retrieving real biomedical
literature (PubMed, Semantic Scholar, Europe PMC) at query time and having an LLM
(Claude Haiku 4.5, or a local Ollama model in dev) synthesize a reasoned, cited answer.

**This is not medical advice.** It's an educational tool that reasons over published
research to illustrate tradeoffs (e.g. "if I can run a half marathon in 1:30 but smoke a
pack a day, what does that say about my health?") — take answers as a starting point for
further reading, not a diagnosis or personal recommendation.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design and build plan, and
[docs/post-pilot-improvements/](docs/post-pilot-improvements/) for issues identified from
actually using the app (markdown rendering, answer structure, source transparency, UI).

## Status

Build phases:

- [x] Phase 0 — Project setup
- [x] Phase 1 — Retrieval pipeline (PubMed / Semantic Scholar / Europe PMC) — live-tested:
      `ingest_cli.py` returns real deduped PubMed/Europe PMC results; Semantic Scholar
      degrades gracefully on its (expected) unauthenticated rate limit
- [x] Phase 2 — Embeddings + Supabase cache — live-tested against local Postgres+pgvector:
      re-running `embed_cli.py` on the same query embedded 0 new chunks the second time
      (dedup-upsert cache contract holds) and similarity search returned on-topic chunks
- [x] Phase 3 — Synthesis + prompting — live-tested against the **real production model**
      (Claude Haiku 4.5, real `ANTHROPIC_API_KEY`) on the plan's flagship verify case
      (half-marathon/smoking tradeoff): produced a coherent, well-cited answer that
      directly engages the tradeoff (explains fitness and smoking harm as largely
      independent pathways, cites 15 sources, single non-repeated disclaimer up front,
      no over-hedging or refusal). This resolves the gap from the previous check —
      earlier local-only Ollama/Qwen testing had drifted off-topic on this exact
      question; switching to the real model plus the `MAX_SYNTHESIS_OUTPUT_TOKENS`
      1800→2400 bump (the old cap was cutting Haiku off mid-sentence) fixed it. Only 1
      of the plan's suggested 3–5 varied test questions has been run against the real
      model so far (plus 1 against Ollama) — broader coverage is still worth doing before
      calling prompt-tuning fully settled, but the hard case passes.
- [x] Phase 4 — Backend API (SSE streaming) — live-tested: `curl -N` against a locally
      running server showed `decomposition` → `sources` → individually-arriving `token`
      events over several seconds, not one buffered response
- [x] Phase 5 — Frontend chat UI — live browser round-trip verified via Playwright
      (installed locally for this) across many real Claude Haiku 4.5 runs: progress
      states, citation rendering, and mobile viewport all confirmed working (see
      Phase 10 below for the fuller UI build-out since this was first checked)
- [x] Phase 6 — Rate limiting — live-tested against local Redis: requests 1–3 allowed,
      4th+ blocked with `RateLimitExceeded`, under a temporarily-lowered limit per the
      plan's own verify method
- [x] Phase 7 — Ollama/Qwen local-dev alt-provider — live-tested: full pipeline runs
      end-to-end via `LLM_PROVIDER=ollama`; `render.yaml` hardcodes
      `LLM_PROVIDER=anthropic` for prod
- [ ] Phase 8 — Deploy (Vercel + Render + Supabase + Upstash) — blocked on accounts only
      you can create, see below
- [ ] Phase 9 — Polish / portfolio-readiness
- [x] Phase 10 — Post-pilot improvements (see
      [docs/post-pilot-improvements/](docs/post-pilot-improvements/)) — all 9 items
      implemented and live-verified: markdown rendering, structured summary + clickable
      citation excerpts, source-transparency tab, healthcare-friendly redesign, a
      "Let's begin" landing page, buffered (non-growing) answer reveal, per-sub-topic
      answer tabs, two real bugs found and fixed (escaped HTML in titles, an
      over-inclusive "cited" flag), and citation-click-to-highlighted-source linking

## What's needed to deploy

Phases 0–4, 6, and 7 are code-complete and independently verified locally (see checklist
above for exactly what was tested), including a real Claude Haiku 4.5 answer on the
flagship question. Phase 5's live browser round-trip is the only fully open item, plus
broader multi-question coverage on Phase 3 — both are plain iteration work, not blocked
on anything external. Separately, what's left requires accounts/credentials only you can
create:

1. **Anthropic API key** — already set locally and validated end-to-end against Claude
   Haiku 4.5. Still needs to be set as a Render env var for the deployed backend, with a
   monthly spend cap/alert in the Anthropic Console.
2. **Supabase project** (supabase.com, free tier) — run `backend/app/vectorstore/schema.sql`
   against it, then use its Postgres connection string as `DATABASE_URL`.
3. **Upstash Redis database** (upstash.com, free tier) — use its Redis connection
   string as `REDIS_URL`.
4. **Semantic Scholar API key** (semanticscholar.org/product/api, free, manually
   approved) — optional but recommended; the app degrades gracefully without it.
5. **Render account** (render.com) — deploy `backend/` via the included `render.yaml`
   Blueprint, then fill in the secret env vars it references.
6. **Vercel account** (vercel.com) — deploy `frontend/` with root directory `frontend`,
   set `NEXT_PUBLIC_BACKEND_URL` to the live Render URL.

## Local development

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```
