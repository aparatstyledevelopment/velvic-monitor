from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import auth, briefings, chat, health
from app.core.cache import close_redis
from app.core.config import get_settings
from app.core.errors import AppError, to_http
from app.core.logging import configure_logging, logger


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("startup", env=get_settings().env)
    try:
        yield
    finally:
        await close_redis()
        logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Velvic Monitor API",
        version=settings.engine_version,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        http = to_http(exc)
        return JSONResponse(status_code=http.status_code, content=http.detail)

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(briefings.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")

    return app


app = create_app()
