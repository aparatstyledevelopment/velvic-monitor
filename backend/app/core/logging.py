import sys

from loguru import logger

from app.core.config import get_settings


def configure_logging() -> None:
    logger.remove()
    settings = get_settings()
    serialize = settings.env != "local"
    logger.add(
        sys.stdout,
        level="INFO",
        serialize=serialize,
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )


__all__ = ["configure_logging", "logger"]
