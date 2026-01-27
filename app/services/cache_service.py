from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional, Sequence

import redis

from app.core.config import get_settings
from app.core.metrics import increment_cache_hit, increment_cache_miss

_settings = get_settings()
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(_settings.redis_url, decode_responses=True)
    return _redis_client


def get_recommendation_cache_key(user_id: int, strategy: str, limit: int) -> str:
    return f"recai:recs:{strategy}:user:{user_id}:limit:{limit}"


def get_cached_recommendations(user_id: int, strategy: str, limit: int) -> Any | None:
    try:
        client = get_redis_client()
        key = get_recommendation_cache_key(user_id, strategy, limit)
        raw = client.get(key)
    except redis.exceptions.RedisError:
        increment_cache_miss()
        return None

    if not raw:
        increment_cache_miss()
        return None
    try:
        increment_cache_hit()
        return json.loads(raw)
    except json.JSONDecodeError:
        increment_cache_miss()
        return None


def set_cached_recommendations(
    user_id: int,
    strategy: str,
    limit: int,
    data: Any,
    ttl_seconds: int = 600,
) -> None:
    try:
        client = get_redis_client()
        key = get_recommendation_cache_key(user_id, strategy, limit)
        client.setex(key, ttl_seconds, json.dumps(data))
    except redis.exceptions.RedisError:
        # Cache failures should not fail the request path.
        return


def update_popularity_and_trending_counters(
    item_id: int,
    genres: Optional[Sequence[str]] = None,
    weight: float = 1.0,
    ts: Optional[datetime] = None,
) -> None:
    """Best-effort updates of Redis counters for popular / trending items.

    - Global popularity: ZINCRBY on recai:popular:global
    - Per-genre popularity: ZINCRBY on recai:popular:genre:{genre}
    - Trending: simple time-bucketed sorted set per hour
    """
    try:
        client = get_redis_client()
    except redis.exceptions.RedisError:
        return

    try:
        client.zincrby("recai:popular:global", weight, str(item_id))

        for genre in genres or []:
            client.zincrby(f"recai:popular:genre:{genre.lower()}", weight, str(item_id))

        ts = ts or datetime.utcnow()
        bucket = ts.strftime("%Y%m%d%H")
        trending_key = f"recai:trending:{bucket}"
        client.zincrby(trending_key, weight, str(item_id))
        # Let trending buckets expire after 24 hours to approximate decay.
        client.expire(trending_key, 60 * 60 * 24)
    except redis.exceptions.RedisError:
        # Metrics are best-effort only.
        return