# Health/Fitness RAG Chatbot — Implementation Plan

## Context

You want a deployed, portfolio-ready chatbot that answers nuanced health/fitness
questions (e.g. "if I can run a half marathon in 1:30 but smoke a pack a day, what does
that say about my health?") by retrieving real scientific literature and having an LLM
reason across it — not canned answers, and not a fixed pre-built knowledge base, since
the whole point is handling arbitrary novel questions with evidence-backed (if
appropriately caveated) reasoning. The target directory is currently empty, so this is a
from-scratch build.

Key constraints that shape the design:
- **Google Scholar is not usable** — no API, and scraping violates its ToS / gets IPs
  blocked. Replaced with **PubMed/NCBI E-utilities** + **Semantic Scholar API** (both
  free, official) and **Europe PMC** (free, adds open-access full text).
- **Cheapest possible hosting.** GitHub Pages is static-only and can't run backend logic
  or hold API keys, so it's ruled out for anything beyond static asset hosting. The plan
  targets a **$0-fixed-cost stack**: Vercel (frontend), Render free tier (backend),
  Supabase free tier (Postgres + pgvector), Upstash free tier (Redis for rate limiting).
  The only real ongoing cost is small pay-as-you-go Anthropic API usage.
- **Claude Haiku 4.5** for production generation (cheap, fast). You also want to
  experiment with a **self-hosted Ollama + Qwen2.5:9B** model for RAG — this can't run
  on free hosting tiers (no GPU/RAM), so it's built as a local-dev-only alternate
  provider behind a swappable interface, never used in the deployed version.
- **Public-facing** (portfolio/friends), no user accounts, but calls a paid API — needs
  basic per-IP + global rate limiting to bound cost exposure.
- The core hard part isn't lookup, it's **synthesis across a nuanced tradeoff** — the
  pipeline needs to decompose a question into sub-topics (e.g. physiological demands of
  a sub-90-minute half marathon vs. known effects of chronic smoking on lung
  function/VO2max), retrieve literature per sub-topic, and get the model to weigh/engage
  with the tradeoff rather than either refusing (over-hedging) or sounding like
  definitive personal medical advice.

## 0. Model/pricing facts

- Production LLM: **Claude Haiku 4.5** (`claude-haiku-4-5`, resolves to
  `claude-haiku-4-5-20251001`). 200K context, 64K max output. **$1.00/MTok input,
  $5.00/MTok output.** No adaptive-thinking/effort support on Haiku — leave thinking off
  by default.
- Prompt caching (4096-token minimum prefix) is **skipped for v1** — retrieved context
  is mostly unique per request, so it wouldn't pay off yet.
- Estimated cost per query (decomposition ~500in/250out + synthesis ~5000in/1200out):
  **~$0.006–0.01/query** → expected well under $1–3/month at portfolio traffic given the
  rate limits in §6.

## 1. Architecture

**Backend:** Python FastAPI, hand-rolled pipeline (no LangChain/LlamaIndex) — literature
APIs are just HTTP calls, and hand-rolling keeps the codebase transparent and lets the
same code run the Ollama dev path via a provider abstraction.

**Frontend:** Next.js on Vercel free tier — simple chat UI.

**Backend hosting:** Render free tier (no credit card required, unlike Fly.io's
usage-based free allowance). Accepted tradeoff: ~30–60s cold start after idle spin-down
— must be surfaced in the UI, not left looking broken.

**Vector store / literature cache:** Supabase (Postgres + pgvector), free tier (500MB).
Acts as a **growing cache**: once a paper is fetched and embedded, it's reused on future
queries instead of re-fetched/re-embedded. Gotcha: Supabase free projects can auto-pause
after ~1 week fully idle — may need a manual resume before a demo after a dormant period.

**Embeddings:** local, in-process **`fastembed`** (ONNX runtime, not PyTorch) with
**`BAAI/bge-small-en-v1.5`** (384-dim, ~130MB) — keeps the stack genuinely $0 and fits
Render's tight free-tier RAM far better than `sentence-transformers`. Not
biomedical-tuned (accepted tradeoff, see Risks); designed with an escape hatch to swap
in a hosted embeddings API (Voyage AI / OpenAI) behind the same provider-abstraction
pattern if RAM ever becomes a real problem.

**Rate limiting:** Upstash Redis free tier, atomic `INCR`+`EXPIRE` daily counters —
simpler/more correct than hand-rolled Postgres counters, and keeps abuse-protection
separate from the paper cache.

**LLM provider abstraction:** `LLM_PROVIDER=anthropic` (prod, Haiku 4.5) or
`LLM_PROVIDER=ollama` (local dev, Qwen2.5:9B via a plain `httpx` client) — orchestrator
code depends only on an `LLMProvider` interface, never a concrete implementation, so the
Ollama path adds zero deployment complexity.

### Request flow (single question)

```
Browser (Next.js/Vercel)
  --HTTPS POST /api/chat (SSE)-->
FastAPI backend (Render)
  1. Rate-limit check -----------------> Upstash Redis
  2. Decompose question ----------------> Anthropic (Haiku, small call)
  3. Parallel per-sub-topic search ------> PubMed E-utilities / Semantic Scholar / Europe PMC
  4. Dedup + cache check -----------------> Supabase (papers/chunks)
  5. Chunk + embed only new papers -------> local fastembed (in-process)
  6. pgvector similarity search ----------> Supabase Postgres+pgvector
  7. Assemble synthesis prompt, stream ---> Anthropic Haiku (or local Ollama/Qwen if dev)
  <--- streamed tokens + citations back to browser
```

## 2. Repository structure

```
project-root/
  backend/
    app/
      main.py                    # FastAPI app, CORS, startup
      config.py                  # pydantic Settings from env vars
      api/routes_chat.py         # POST /api/chat (SSE), GET /api/health
      api/deps.py                # DI: supabase/redis/llm clients
      pipeline/
        prompts.py                # decomposition + synthesis templates
        decompose.py               # question -> sub-topics (structured output)
        orchestrator.py            # retrieval -> cache -> embed -> search -> synth
        synthesize.py               # final context assembly + streamed call
      retrieval/
        models.py                  # Paper, Chunk, SearchResult, SubTopic
        pubmed.py                  # NCBI E-utilities client
        semantic_scholar.py        # Semantic Scholar Graph API client
        europepmc.py               # Europe PMC client (metadata + OA full text)
        dedup.py                   # canonical-ID merge across sources
      embeddings/
        embedder.py                 # embedding provider abstraction (fastembed default)
        chunking.py                  # abstract/full-text chunking
      vectorstore/
        supabase_client.py
        store.py                    # dedup-upsert + similarity search
        schema.sql                  # papers/chunks tables + pgvector index
      llm/
        base.py                      # LLMProvider protocol
        anthropic_provider.py        # Claude Haiku 4.5 (prod default)
        ollama_provider.py           # Qwen via Ollama (local dev)
        factory.py                    # reads LLM_PROVIDER, returns instance
      ratelimit/limiter.py           # Upstash per-IP + global daily counters
    scripts/
      ingest_cli.py                  # Phase 1 standalone retrieval test
      embed_cli.py                   # Phase 2 chunk+embed+search test
      ask_cli.py                      # Phase 3 full pipeline test, no HTTP
    tests/
    pyproject.toml
    .env.example
    render.yaml
  frontend/
    app/page.tsx, layout.tsx
    components/
      ChatWindow.tsx, MessageBubble.tsx, CitationList.tsx,
      DisclaimerBanner.tsx, ProgressStatus.tsx
    lib/api.ts                       # fetch + SSE-stream parsing
    .env.local.example
    package.json
  docs/ARCHITECTURE.md
  README.md
  .gitignore
```

`.env.example` (backend, names only):
```
ANTHROPIC_API_KEY=
LLM_PROVIDER=anthropic            # anthropic | ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:9b

NCBI_EMAIL=
NCBI_API_KEY=                     # optional: 3 req/sec -> 10 req/sec
SEMANTIC_SCHOLAR_API_KEY=         # optional but recommended

SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=        # server-side only

UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=

RATE_LIMIT_PER_IP_PER_DAY=20
RATE_LIMIT_GLOBAL_PER_DAY=300
MAX_SUBTOPICS=4
MAX_CHUNKS_PER_SUBTOPIC=8
MAX_SYNTHESIS_OUTPUT_TOKENS=1800

EMBEDDING_PROVIDER=fastembed      # fastembed | voyage | openai (escape hatch)
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

CORS_ALLOWED_ORIGINS=https://your-portfolio.vercel.app
ENVIRONMENT=production
```

`.env.local.example` (frontend): `NEXT_PUBLIC_BACKEND_URL=https://your-backend.onrender.com`

## 3. Retrieval + synthesis pipeline

- **Decomposition:** one Haiku call with structured JSON output, breaking the question
  into 2–4 sub-topics (label, focused search-query string, one-line rationale), capped
  by `MAX_SUBTOPICS`.
- **Literature search (parallel per sub-topic):**
  - PubMed: `esearch.fcgi` → `esummary.fcgi`/`efetch.fcgi`, batched PMIDs, always send
    `email`, send `api_key` if configured, exponential backoff on 429s.
  - Semantic Scholar: `/graph/v1/paper/search`. Treated as best-effort/degrade-gracefully
    since its unauthenticated rate limit is the tightest of the three.
  - Europe PMC: metadata search, plus full-text fetch for only the **top 1–2 hits per
    sub-topic** (bounds latency and storage growth).
- **Cross-source dedup:** canonical ID = DOI → PMID → Semantic Scholar `paperId` →
  title+year hash; merge metadata across sources.
- **Cache check against Supabase:** if a paper's canonical ID already exists, reuse its
  chunks/embeddings (skip re-embedding) and bump `last_seen_at`; otherwise insert new
  `papers`/`chunks` rows. This is what makes the vector store a reusable, growing cache.
- **Chunking:** abstracts as ~1 chunk (defensive splitting past ~500 tokens); full text
  in ~300–500 token windows with ~15% overlap, paragraph/sentence-aware.
- **Embedding + similarity search:** batch-embed new chunks only via the embedding
  abstraction (`fastembed`/`bge-small-en-v1.5` default); pgvector `ORDER BY embedding <=>
  query_embedding LIMIT k` per sub-topic (k≈5–8, capped by `MAX_CHUNKS_PER_SUBTOPIC`);
  total chunks fed to synthesis capped ~20–30 to control quality dilution and cost.
- **Synthesis prompt:** system prompt establishes (a) role as an evidence-synthesis tool
  that reasons/weighs across sub-topics rather than listing facts flatly, (b) a citation
  requirement — every substantive claim cites `[PMID:...]` matched to a reference list,
  (c) a **single, precise, non-repeated** framing line establishing this is educational
  reasoning grounded in literature, not personalized medical advice — paired with an
  explicit instruction to still substantively engage with the tradeoff rather than
  deflecting. This precision-over-volume approach to the disclaimer is the main lever
  against both over-hedging and false-definitiveness. Output via `.messages.stream(...)`,
  capped at `MAX_SYNTHESIS_OUTPUT_TOKENS` (~1800), thinking off, no prompt caching in v1.

## 4. Backend API

- **`POST /api/chat`** `{question, session_id?}` → SSE stream via `StreamingResponse`.
  Events: `decomposition` (sub-topics, sent early for UI progress), `sources` (papers as
  found), `token` (streamed synthesis text), `done` (final citation list), `error`.
- **`GET /api/health`** — liveness check.
- Frontend consumes via `fetch` + `ReadableStream` (not `EventSource`, since it needs a
  POST body) with a small SSE-line parser. Backend forwards Claude's tokens as they
  arrive, never buffers the full response.

## 5. Frontend v1 scope

Essential: single-page chat with streaming render; one prominent top-of-page disclaimer
banner (not repeated per message); citations panel per answer (numbered, clickable
PubMed/DOI/Semantic-Scholar links) populated on the `done` event and matched to inline
`[n]` markers; progress states ("Breaking down your question…", "Searching…",
"Synthesizing…") since the pipeline takes 5–15s; explicit cold-start ("waking up the
server, up to a minute") and rate-limit-exceeded states; basic mobile responsiveness.

Nice-to-have (later): markdown+citation hyperlinks, clickable example questions
(including the half-marathon/smoking one), local-only session history, dark mode.

## 6. Rate limiting

Upstash Redis fixed-window daily counters: per-IP (`ratelimit:{ip}:{date}`, default 20/
day) and a global backstop (`ratelimit:global:{date}`, default 300/day), IP from
`X-Forwarded-For`. Independent cost bounds regardless of limiter correctness:
`MAX_SYNTHESIS_OUTPUT_TOKENS`, `MAX_SUBTOPICS`, `MAX_CHUNKS_PER_SUBTOPIC`, input question
length cap (~500 chars), and a hard monthly spend cap/alert set directly in the Anthropic
Console as a second line of defense. CAPTCHA/Turnstile explicitly deferred unless real
abuse occurs.

## 7. Ollama/Qwen local-dev path

`llm/base.py` defines an async `LLMProvider` protocol
(`stream_completion(system, messages, max_tokens) -> AsyncIterator[str]`).
`AnthropicProvider` wraps `anthropic.Anthropic()` (prod default). `OllamaProvider` is
plain `httpx` calls to a local Ollama server, adapting its NDJSON streaming to the same
interface — no heavyweight Ollama client dependency. `llm/factory.py` reads
`LLM_PROVIDER` and returns the right instance; the orchestrator never imports a concrete
provider. Local workflow: `ollama serve` + `ollama pull qwen2.5:9b`, set
`LLM_PROVIDER=ollama`, run the same endpoint locally for direct Haiku-vs-Qwen
comparison. Production Render config always sets `LLM_PROVIDER=anthropic`. Embeddings
stay local (`fastembed`) regardless of which LLM provider is active — a separate axis.

## 8. Deployment & accounts (all $0 fixed cost)

- **Vercel:** connect repo, root dir `frontend/`, set `NEXT_PUBLIC_BACKEND_URL`, deploy on push.
- **Render:** free web service, root dir `backend/`, build `pip install -r
  requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, set all
  backend env vars in dashboard.
- **Supabase:** free project, `create extension if not exists vector;`, run
  `schema.sql`, copy `SUPABASE_URL` + service-role key (server-side only) into Render env.
- **Upstash:** free Redis DB (region near Render), copy REST URL+token into Render env.
- **Anthropic:** Console account, API key, small prepaid credit, set a monthly spend cap/alert.
- **NCBI:** no account required (must send `email` per request); optional free API key
  for higher rate limit.
- **Semantic Scholar:** apply for a free API key **in Phase 1**, not later — the app
  depends on it live per query.
- **Europe PMC:** no account/key needed.

## 9. Build order

0. **Setup** — scaffold backend/frontend skeletons, `/api/health`, git init. Verify:
   `uvicorn` + `next dev` both serve locally.
1. **Retrieval pipeline (standalone)** — `pubmed.py`/`semantic_scholar.py`/
   `europepmc.py`/`dedup.py` as plain async functions + `ingest_cli.py`. Apply for the
   Semantic Scholar key now. Verify: CLI returns sane deduped results for real queries.
2. **Embeddings + Supabase cache** — `schema.sql`, `chunking.py`, `embedder.py`,
   `store.py` with dedup-upsert. Verify: re-ingesting the same topic doesn't duplicate
   rows; similarity search returns topically relevant chunks.
3. **Synthesis + prompting** — `llm/base.py` + `anthropic_provider.py`,
   `decompose.py`, `synthesize.py`, `orchestrator.py`, `ask_cli.py`. Verify: the
   half-marathon/smoking example produces a coherent answer engaging both sides with
   citations and non-repeated, non-preachy framing; test 3–5 varied questions including
   an edge case.
4. **Backend API** — `routes_chat.py` with SSE. Verify: `curl -N` streams tokens
   incrementally, not all at once.
5. **Frontend** — chat UI wired to local backend. Verify: full browser round trip with
   progress states, citations, mobile viewport check.
6. **Rate limiting** — Upstash counters as a FastAPI dependency, 429 handling in UI.
   Verify: temporarily lower the limit, hammer the endpoint, confirm block + reset.
7. **Ollama/Qwen alt-provider** — `ollama_provider.py` + factory switch. Verify: same
   questions run against both providers via env-var flip only; confirm prod config never
   sets `LLM_PROVIDER=ollama`.
8. **Deploy** — push to GitHub, deploy Render then Vercel, wire production Supabase/
   Upstash creds, CORS to the Vercel domain. Verify: full round trip from the live URL
   (different network/device), citation links resolve, rate limiting works live.
9. **Polish** — README with architecture diagram, example questions in the UI, tidied
   error states, disclaimer tone pass, mobile check. Verify: fresh-eyes walkthrough.

## 10. Key risks (flagged, with mitigations already designed in)

- PubMed/NCBI and especially unauthenticated Semantic Scholar rate limits — batch
  requests, backoff, apply for the S2 key early, degrade gracefully per-source.
- Render free-tier cold starts (~30–60s) and 512MB RAM ceiling — surfaced in UI;
  `fastembed`/ONNX chosen specifically over PyTorch to fit the RAM budget, with a
  hosted-embeddings escape hatch behind the provider abstraction if it's still too tight.
- Supabase free-tier auto-pause after ~1 week fully idle — may need a manual resume
  before a demo.
- `bge-small-en-v1.5` isn't biomedical-tuned — accepted relevance tradeoff, mitigated by
  slightly larger top-k plus the synthesis LLM's own relevance weighing; a biomedical
  embedding model is a scoped future upgrade.
- The central *quality* risk is prompt tuning for engagement-without-over-hedging vs.
  false-definitiveness — this needs a few iteration rounds in Phase 3 against edge-case
  questions, not a one-shot prompt.
- Anthropic cost exposure beyond app-level rate limiting — mitigated by an independent
  spend cap set in the Anthropic Console.
- Unbounded Europe PMC full-text ingestion could grow Supabase storage faster than
  abstracts alone — mitigated by only fetching full text for top 1–2 hits per sub-topic.

## Critical files (once building begins)

- `backend/app/pipeline/orchestrator.py` — glues every stage together
- `backend/app/retrieval/{pubmed,semantic_scholar,europepmc}.py` — the three sources
- `backend/app/vectorstore/{schema.sql,store.py}` — the cache/dedup contract
- `backend/app/llm/{base.py,factory.py}` — the Haiku/Ollama provider abstraction
- `backend/app/pipeline/prompts.py` — where hedging-vs-engagement is actually resolved
- `backend/app/api/routes_chat.py` — the SSE contract the frontend depends on
