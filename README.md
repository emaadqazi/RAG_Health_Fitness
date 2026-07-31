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

Under active development. Build phases:

- [x] Phase 0 — Project setup
- [ ] Phase 1 — Retrieval pipeline (PubMed / Semantic Scholar / Europe PMC)
- [ ] Phase 2 — Embeddings + Supabase cache
- [ ] Phase 3 — Synthesis + prompting
- [ ] Phase 4 — Backend API (SSE streaming)
- [ ] Phase 5 — Frontend chat UI
- [ ] Phase 6 — Rate limiting
- [ ] Phase 7 — Ollama/Qwen local-dev alt-provider
- [ ] Phase 8 — Deploy (Vercel + Render + Supabase + Upstash)
- [ ] Phase 9 — Polish / portfolio-readiness

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
