"""Source crawlers. Importing this package populates the registry."""
from app.crawlers import (  # noqa: F401
    company_ir_rss,
    esap,
    fi_insider,
    fi_short,
    fred,
    mfn,
    riksbank,
    scb,
    yahoo_finance,
)
from app.crawlers.base import BaseCrawler, CrawlerError, DateRange, PolitenessConfig
from app.crawlers.registry import all_names, build, register

__all__ = [
    "BaseCrawler",
    "CrawlerError",
    "DateRange",
    "PolitenessConfig",
    "all_names",
    "build",
    "register",
]
