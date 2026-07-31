"""Per-IP + global daily rate limiting.

Fixed-window daily counters via atomic INCR+EXPIRE. Works identically against a
local redis-server (dev) and Upstash's Redis (prod) -- both speak the standard Redis
protocol, so no Upstash-specific client/SDK is needed.

Independent cost bounds (MAX_SUBTOPICS, MAX_CHUNKS_PER_SUBTOPIC,
MAX_SYNTHESIS_OUTPUT_TOKENS, question length cap) exist regardless of this limiter's
correctness -- see config.py and routes_chat.py -- plus a monthly spend cap set
directly in the Anthropic Console as an independent second line of defense.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache

import redis.asyncio as redis

from app.config import get_settings

SECONDS_PER_DAY = 86400


class RateLimitExceeded(Exception):
    def __init__(self, scope: str) -> None:
        self.scope = scope
        super().__init__(f"rate limit exceeded: {scope}")


@lru_cache
def get_redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def _today_key(prefix: str) -> str:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"ratelimit:{prefix}:{today}"


async def _increment_and_check(client: redis.Redis, key: str, limit: int) -> int:
    pipe = client.pipeline()
    pipe.incr(key)
    pipe.expire(key, SECONDS_PER_DAY, nx=True)
    count, _ = await pipe.execute()
    return count


async def check_and_increment(ip: str) -> None:
    settings = get_settings()
    client = get_redis_client()

    global_count = await _increment_and_check(client, _today_key("global"), settings.rate_limit_global_per_day)
    if global_count > settings.rate_limit_global_per_day:
        raise RateLimitExceeded("global")

    per_ip_count = await _increment_and_check(client, _today_key(f"ip:{ip}"), settings.rate_limit_per_ip_per_day)
    if per_ip_count > settings.rate_limit_per_ip_per_day:
        raise RateLimitExceeded("ip")
