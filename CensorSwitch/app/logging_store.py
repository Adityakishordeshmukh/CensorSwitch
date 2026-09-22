"""
Student D: logging + audit trail.

Writes every request to SQLite. dashboard.py reads aggregates from this table.
Extend with: pagination for a "search past requests" view, export to CSV, and
per-user cost breakdown.
"""

import time
import aiosqlite

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY,
    api_key TEXT,
    prompt TEXT,
    provider TEXT,
    cached INTEGER,
    blocked INTEGER,
    latency_ms REAL,
    cost_usd REAL,
    timestamp REAL
);
"""


async def init_db():
    async with aiosqlite.connect(settings.log_db_path) as db:
        await db.execute(_SCHEMA)
        await db.commit()


async def log_request(
    request_id: str,
    api_key: str,
    prompt: str,
    provider: str,
    cached: bool,
    blocked: bool,
    latency_ms: float,
    cost_usd: float,
):
    async with aiosqlite.connect(settings.log_db_path) as db:
        await db.execute(
            """INSERT INTO requests
               (request_id, api_key, prompt, provider, cached, blocked, latency_ms, cost_usd, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request_id,
                api_key,
                prompt[:500],  # truncate for storage
                provider,
                int(cached),
                int(blocked),
                latency_ms,
                cost_usd,
                time.time(),
            ),
        )
        await db.commit()


async def get_dashboard_stats() -> dict:
    async with aiosqlite.connect(settings.log_db_path) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM requests")).fetchone())[0]
        cached = (await (await db.execute("SELECT COUNT(*) FROM requests WHERE cached=1")).fetchone())[0]
        blocked = (await (await db.execute("SELECT COUNT(*) FROM requests WHERE blocked=1")).fetchone())[0]
        cost_row = await (await db.execute("SELECT SUM(cost_usd) FROM requests WHERE cached=0")).fetchone()
        cost_spent = cost_row[0] or 0.0

        # Estimated savings: what cached requests would have cost had they hit a provider
        avg_cost_row = await (
            await db.execute("SELECT AVG(cost_usd) FROM requests WHERE cached=0 AND cost_usd > 0")
        ).fetchone()
        avg_cost = avg_cost_row[0] or 0.0
        cost_saved = cached * avg_cost

        by_provider_rows = await (
            await db.execute(
                "SELECT provider, COUNT(*) FROM requests WHERE cached=0 AND blocked=0 GROUP BY provider"
            )
        ).fetchall()

        return {
            "total_requests": total,
            "cache_hits": cached,
            "cache_hit_rate": (cached / total) if total else 0.0,
            "blocked_requests": blocked,
            "cost_spent_usd": round(cost_spent, 4),
            "cost_saved_usd": round(cost_saved, 4),
            "requests_by_provider": dict(by_provider_rows),
        }
