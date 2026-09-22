"""
Student A: gateway core.

The single /v1/chat endpoint is the pipeline: rate limit -> cache -> route -> log.
This is the "glue" file -- once all four modules work individually, this is where
you wire them together and this is what QuickCart would actually call.
"""

import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.models import ChatRequest, ChatResponse
from app.rate_limiter import rate_limiter
from app.cache import semantic_cache
from app.router import router as smart_router
from app.providers import estimate_cost
from app.logging_store import init_db, log_request
from app.dashboard import router as dashboard_router

app = FastAPI(title="AgentGate", version="0.1.0")
app.include_router(dashboard_router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    request_id = str(uuid.uuid4())
    start = time.time()

    # 1. Rate limit
    if not rate_limiter.allow(req.api_key):
        await log_request(
            request_id, req.api_key, req.prompt, provider="none",
            cached=False, blocked=True, latency_ms=0, cost_usd=0,
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # 2. Semantic cache
    hit = semantic_cache.lookup(req.prompt)
    if hit:
        latency_ms = (time.time() - start) * 1000
        await log_request(
            request_id, req.api_key, req.prompt, provider=hit.provider,
            cached=True, blocked=False, latency_ms=latency_ms, cost_usd=0,
        )
        return ChatResponse(
            request_id=request_id, answer=hit.answer, provider=hit.provider,
            cached=True, latency_ms=latency_ms,
        )

    # 3. Route to a provider
    try:
        provider, answer, provider_latency_ms = await smart_router.route(
            req.prompt, preferred=req.preferred_provider
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"All providers failed: {e}")

    semantic_cache.store(req.prompt, answer, provider)
    cost = estimate_cost(provider, req.prompt, answer)
    total_latency_ms = (time.time() - start) * 1000

    # 4. Log
    await log_request(
        request_id, req.api_key, req.prompt, provider=provider,
        cached=False, blocked=False, latency_ms=total_latency_ms, cost_usd=cost,
    )

    return ChatResponse(
        request_id=request_id, answer=answer, provider=provider,
        cached=False, latency_ms=total_latency_ms,
    )


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "providers": smart_router.health_snapshot()})
