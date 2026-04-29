"""Celery beat schedule for the EOD pipeline.

Times are Europe/Stockholm; celery_app sets the timezone.
"""
from __future__ import annotations

from celery.schedules import crontab

BEAT_SCHEDULE = {
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
