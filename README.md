# Health/Fitness RAG Chatbot

A chatbot that answers nuanced health/fitness questions by retrieving real biomedical
literature (PubMed, Semantic Scholar, Europe PMC) at query time and having an LLM
(Claude Haiku 4.5, or a local Ollama model in dev) synthesize a reasoned, cited answer.

**This is not medical advice.** It's an educational tool that reasons over published
research to illustrate tradeoffs (e.g. "if I can run a half marathon in 1:30 but smoke a
pack a day, what does that say about my health?") — take answers as a starting point for
further reading, not a diagnosis or personal recommendation.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design and build plan.

## Status

Build phases:

- [x] Phase 0 — Project setup
- [x] Phase 1 — Retrieval pipeline (PubMed / Semantic Scholar / Europe PMC)
- [x] Phase 2 — Embeddings + Supabase cache
- [x] Phase 3 — Synthesis + prompting (pipeline verified locally against Ollama/Qwen3.5;
      quality validation against the production model, Claude Haiku 4.5, is pending an
      Anthropic API key -- see "What's needed to deploy" below)
- [x] Phase 4 — Backend API (SSE streaming)
- [x] Phase 5 — Frontend chat UI
- [x] Phase 6 — Rate limiting
- [x] Phase 7 — Ollama/Qwen local-dev alt-provider
- [ ] Phase 8 — Deploy (Vercel + Render + Supabase + Upstash) — blocked on accounts only
      you can create, see below
- [ ] Phase 9 — Polish / portfolio-readiness

## What's needed to deploy

Everything through Phase 7 is code-complete and verified locally. What's left requires
accounts/credentials only you can create:

1. **Anthropic API key** (console.anthropic.com) — set `ANTHROPIC_API_KEY`, add a small
   prepaid credit, and set a monthly spend cap/alert in the Console. This also unblocks
   validating real answer quality on Claude Haiku 4.5 (local testing so far used a
   local Ollama/Qwen3.5 model as a stand-in, per your request to experiment with it —
   see docs/ARCHITECTURE.md §0/§10 for why that's not the same as production quality).
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
