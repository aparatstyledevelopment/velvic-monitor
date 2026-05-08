"""Celery beat schedule for the EOD pipeline.

Times are Europe/Stockholm; celery_app sets the timezone.

Crawlers gated to the DISABLED_CRAWLERS set are NOT registered in beat
even though their tasks still exist (and can be invoked manually for
ad-hoc runs or backfill). Use this list to park sources whose upstream
endpoints are not yet stable.
"""

from __future__ import annotations

from celery.schedules import crontab

# Sources whose endpoints are not currently stable enough to run on a
# schedule. Each must be re-enabled deliberately, after the operator has
# confirmed the upstream URL/series/CSV-shape against live docs.
#
# Why each is disabled (May 2026):
# - "esap": ESMA's European Single Access Point starts collecting data
#   2026-07-10 and the public read API isn't expected until July 2027.
#   The crawler skeleton stays in `crawlers/` so the contract is in place
#   but running it now would just generate empty crawl_run rows.
# - "scb": the Layer-2 audit (docs/DATA_SOURCES.md) showed the CPI
#   table id needs swapping to the 2020=100 successor before the run
#   produces meaningful data.
# - "mfn": the free public Atom feed at `mfn.se/all/a/{slug}?format=atom`
#   was retired in 2026; the URL now serves text/html and every alternate
#   path (.atom/.rss/.xml/feed/api) is either 500 or robots-disallowed
#   per `mfn.se/robots.txt` (`Disallow: *.xml$`, `*.rss$`, `*.atom$`,
#   `*.json$`). Re-enabling requires either the commercial API or a
#   partnership; both are out of scope for v1.
# - "riksbank": SWEA migrated to Azure APIM and now requires an
#   `Ocp-Apim-Subscription-Key` header even for the rates / FX read
#   endpoints. Without the key, requests return 200 with a non-JSON body
#   that crashes `resp.json()`. Re-enable by registering at
#   developer.api.riksbank.se, setting RIKSBANK_SUBSCRIPTION_KEY in DO
#   secrets, and removing "riksbank" from this set.
DISABLED_CRAWLERS: frozenset[str] = frozenset({"esap", "scb", "mfn", "riksbank"})

_FULL_SCHEDULE: dict[str, dict[str, object]] = {
    "yahoo-nightly": {
        "task": "crawl.yahoo",
        "schedule": crontab(hour=17, minute=45),
    },
    "mfn-15min-market": {
        "task": "crawl.mfn",
        # every 15 minutes during the trading window
        "schedule": crontab(minute="*/15", hour="8-19"),
    },
    "riksbank-daily": {
        "task": "crawl.riksbank",
        "schedule": crontab(hour=9, minute=0),
    },
    "scb-weekly": {
        "task": "crawl.scb",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),
    },
    "fred-daily": {
        "task": "crawl.fred",
        "schedule": crontab(hour=9, minute=30),
    },
    "esap-hourly": {
        "task": "crawl.esap",
        "schedule": crontab(minute=10),
    },
    "fi-insider-hourly": {
        "task": "crawl.fi_insider",
        "schedule": crontab(minute=20),
    },
    "fi-short-daily": {
        "task": "crawl.fi_short",
        "schedule": crontab(hour=16, minute=15),
    },
    "ir-rss-hourly": {
        "task": "crawl.ir_rss",
        "schedule": crontab(minute=25),
    },
    "ingest-all-evening": {
        "task": "ingest.all",
        "schedule": crontab(hour=18, minute=15),
    },
    "briefings-eod": {
        "task": "briefing.generate_for_all_tickers",
        "schedule": crontab(hour=18, minute=45),
    },
}


def _crawler_name_from_task(task_name: object) -> str | None:
    if not isinstance(task_name, str) or not task_name.startswith("crawl."):
        return None
    return task_name.split(".", 1)[1]


BEAT_SCHEDULE: dict[str, dict[str, object]] = {
    name: spec
    for name, spec in _FULL_SCHEDULE.items()
    if _crawler_name_from_task(spec.get("task")) not in DISABLED_CRAWLERS
}
