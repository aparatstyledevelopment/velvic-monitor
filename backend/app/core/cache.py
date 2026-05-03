from redis.asyncio import Redis, from_url

from app.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        # redis-py's `from_url` is untyped upstream as of 5.0.x.
        _redis = from_url(  # type: ignore[no-untyped-call]
            get_settings().redis_url, decode_responses=True
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
