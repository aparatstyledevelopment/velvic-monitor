from __future__ import annotations

import abc
import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Generic, TypeVar

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.crawlers.models import CrawlRun

T = TypeVar("T")


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(f"start {self.start} after end {self.end}")

    @classmethod
    def trailing(cls, days: int, *, end: date | None = None) -> "DateRange":
        e = end or date.today()
        return cls(start=e - timedelta(days=days), end=e)


@dataclass(frozen=True)
class PolitenessConfig:
    min_interval_s: float = 0.5
    user_agent: str = "VelvicMonitor/0.1 (+https://velvic.example)"
    max_retries: int = 3
    backoff_base_s: float = 1.0


@dataclass
class CrawlReport:
    crawler_name: str
    rows_inserted: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    status: str = "running"
    error: str | None = None


class CrawlerError(Exception):
    """Raised when a crawler cannot complete a run."""


class BaseCrawler(abc.ABC, Generic[T]):
    """Base class for all source crawlers.

    Subclasses implement `fetch_batches`, `parse`, and `upsert_raw`. The base
    class wires politeness, retries, the crawl_run ledger, and structured
    logging.

    Crawlers are PURE writers to Tier-1 raw tables. They never read from
    Tier-2 or Tier-3 and never call the LLM. See crawlers/AGENTS.md.
    """

    name: str
    politeness: PolitenessConfig = PolitenessConfig()

    def __init__(self, *, http_client: httpx.AsyncClient | None = None) -> None:
        self._http = http_client

    # ---------- Lifecycle ----------

    async def crawl(self, session: AsyncSession, window: DateRange) -> CrawlReport:
        report = CrawlReport(crawler_name=self.name)
        run = CrawlRun(
            crawler_name=self.name,
            window_start=datetime.combine(window.start, datetime.min.time(), UTC),
            window_end=datetime.combine(window.end, datetime.min.time(), UTC),
            status="running",
        )
        session.add(run)
        await session.flush()

        try:
            async for batch in self.fetch_batches(window):
                rows = self.parse(batch)
                inserted = await self.upsert_raw(session, rows)
                report.rows_inserted += inserted
            run.status = "ok"
            run.rows_inserted = report.rows_inserted
            run.finished_at = datetime.now(UTC)
            await session.flush()
            report.status = "ok"
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)[:2000]
            run.finished_at = datetime.now(UTC)
            await session.flush()
            report.status = "failed"
            report.error = str(e)
            logger.exception("crawler_failed", crawler=self.name, error=str(e))
            raise CrawlerError(str(e)) from e
        finally:
            report.finished_at = datetime.now(UTC)
            logger.info(
                "crawl_finished",
                crawler=self.name,
                status=report.status,
                rows=report.rows_inserted,
            )
        return report

    # ---------- HTTP helpers ----------

    @asynccontextmanager
    async def http(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._http is not None:
            yield self._http
            return
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0),
            headers={"User-Agent": self.politeness.user_agent},
        )
        try:
            yield client
        finally:
            await client.aclose()

    async def get_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self.politeness.max_retries):
            try:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code in (429, 503):
                    raise httpx.HTTPError(f"transient {resp.status_code}")
                resp.raise_for_status()
                if self.politeness.min_interval_s > 0:
                    await asyncio.sleep(self.politeness.min_interval_s)
                return resp
            except httpx.HTTPError as e:
                last_exc = e
                wait = self.politeness.backoff_base_s * (2**attempt)
                logger.warning(
                    "crawl_retry",
                    crawler=self.name,
                    url=url,
                    attempt=attempt + 1,
                    wait_s=wait,
                    error=str(e),
                )
                await asyncio.sleep(wait)
        assert last_exc is not None
        raise last_exc

    # ---------- Subclass contract ----------

    @abc.abstractmethod
    def fetch_batches(self, window: DateRange) -> AsyncIterator[Any]:
        """Yield raw batches (e.g., HTTP responses, parsed dicts) for the window."""
        raise NotImplementedError

    @abc.abstractmethod
    def parse(self, batch: Any) -> Sequence[T]:
        """Validate and extract typed rows from a batch."""
        raise NotImplementedError

    @abc.abstractmethod
    async def upsert_raw(self, session: AsyncSession, rows: Sequence[T]) -> int:
        """Idempotent upsert into the source's Tier-1 table; return rows touched."""
        raise NotImplementedError
