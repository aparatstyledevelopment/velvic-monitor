from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis
from app.core.config import get_settings
from app.core.db import get_session
from app.core.logging import logger

router = APIRouter(tags=["health"])


_DEFAULT_REDIS_URL = "redis://localhost:6379/0"


@router.get("/health", status_code=status.HTTP_200_OK)
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    redis_status = "skipped"
    if get_settings().redis_url != _DEFAULT_REDIS_URL:
        try:
            redis = get_redis()
            await redis.ping()
            redis_status = "ok"
        except Exception as e:  # noqa: BLE001
            logger.warning("redis_health_failed", error=str(e))
            redis_status = "degraded"
    return {"status": "ok", "redis": redis_status}
