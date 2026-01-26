from __future__ import annotations

import json
from typing import Any, Optional

import redis

from app.core.config import get_settings

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
        return None

    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
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