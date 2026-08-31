import json
import logging
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import get_settings


logger = logging.getLogger(__name__)
_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis | None:
    settings = get_settings()
    if not settings.redis_url:
        return None

    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_client


async def get_json(key: str) -> Any | None:
    client = get_redis_client()
    if client is None:
        return None

    try:
        value = await client.get(key)
    except (OSError, RedisError) as error:
        logger.warning('Redis cache read failed for %s: %s', key, error)
        return None

    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        logger.warning(
            'Redis cache contains invalid JSON for %s: %s',
            key,
            error,
        )
        return None


async def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    client = get_redis_client()
    if client is None:
        return

    try:
        await client.set(
            key,
            json.dumps(value, ensure_ascii=False),
            ex=ttl_seconds,
        )
    except (OSError, RedisError) as error:
        logger.warning('Redis cache write failed for %s: %s', key, error)


async def delete_key(key: str) -> None:
    client = get_redis_client()
    if client is None:
        return

    try:
        await client.delete(key)
    except (OSError, RedisError) as error:
        logger.warning('Redis cache delete failed for %s: %s', key, error)


async def close_redis() -> None:
    global _redis_client
    if _redis_client is None:
        return

    await _redis_client.aclose()
    _redis_client = None
