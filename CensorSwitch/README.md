# AgentGate

An agentic rate-limiter / API gateway for LLM traffic. Apps call AgentGate instead of
calling OpenAI/Anthropic directly. AgentGate then checks a semantic cache, enforces
per-key rate limits, routes to the best available provider, and logs everything for
a savings dashboard.

## Request flow

```
client -> POST /v1/chat
            |
            v
      rate limiter  --(blocked)--> 429 response  --> log
            |  (allowed)
            v
      semantic cache --(hit)-----> cached answer  --> log --> response
            |  (miss)
            v
      smart router --> provider (OpenAI / Anthropic) --> log --> response
```

## Project layout

```
app/
  main.py            FastAPI app, the single /v1/chat endpoint (Student A)
  router.py           Provider selection + circuit breaker         (Student A)
  cache.py             Semantic cache (embeddings + similarity)     (Student B)
  rate_limiter.py       Token bucket + abuse detection               (Student C)
  logging_store.py       Request/response logging (SQLite)            (Student D)
  dashboard.py             Aggregated stats endpoint + static page      (Student D)
  providers.py               Thin wrappers around real LLM provider calls
  models.py                    Pydantic request/response schemas
  config.py                      Settings (env vars, thresholds)
  static/dashboard.html          Minimal dashboard UI (chart.js via CDN)
requirements.txt
.env.example
load_test.py            Simulates "QuickCart" traffic for demo data
```

## Each student's starting point

- **Student A (gateway/routing)**: `app/main.py` + `app/router.py`. The `route_request`
  function in `router.py` currently always picks the first healthy provider — swap in
  real health/cost/latency scoring.
- **Student B (cache)**: `app/cache.py`. `SemanticCache.lookup` currently does exact
  string match — replace with real embeddings (sentence-transformers) + FAISS/cosine
  similarity, and tune the similarity threshold.
- **Student C (rate limiting/abuse)**: `app/rate_limiter.py`. `TokenBucket` is a working
  minimal implementation — extend with sliding-window anomaly detection for abuse.
- **Student D (logging/dashboard)**: `app/logging_store.py` + `app/dashboard.py` +
  `app/static/dashboard.html`. Logging writes to SQLite already; the dashboard reads
  aggregates from it. Make the frontend richer (charts, filters).

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # add real API keys if you want live provider calls
uvicorn app.main:app --reload
```

Then either:
- `python load_test.py` to generate demo traffic (cache hits, blocks, provider calls), or
- point your own client at `http://localhost:8000/v1/chat`

Dashboard: `http://localhost:8000/dashboard`

## Notes

- Providers run in "mock mode" by default (no API key needed) so the whole pipeline
  works out of the box for development and demos without spending API credits.
- Everything is in-memory + SQLite for simplicity. Swap the cache for FAISS/pgvector
  and the rate limiter for Redis if you want it to survive restarts / scale up.
