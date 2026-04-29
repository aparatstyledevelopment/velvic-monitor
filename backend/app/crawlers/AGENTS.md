# crawlers/AGENTS.md

Crawlers fetch from external sources and write to Tier-1 raw tables only.

## Pattern

Every crawler subclasses `BaseCrawler` (in `base.py`):

```python
class YahooFinanceCrawler(BaseCrawler):
    name = "yahoo_finance"
    schedule = Schedule(crontab(hour=17, minute=45))
    politeness = PolitenessConfig(min_interval_s=0.5, user_agent=USER_AGENT)

    def fetch_batches(self, window): ...
    def parse(self, batch): ...
    def upsert_raw(self, rows): ...
```

## Discipline

- ONE crawler = ONE source. Don't compose.
- Always preserve `raw_payload` (the original response) in Tier-1.
- Idempotent upsert keyed by source's natural primary key.
- HTTP errors retry with exponential backoff; don't catch business-logic exceptions.
- Always honor `If-Modified-Since` / ETag where the source supports it.
- Never write to Tier-2 or Tier-3 from a crawler. The ingestion layer does that.
- Every crawl creates one `crawl_run` row for observability.
