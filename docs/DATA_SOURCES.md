# Data Sources

Per-source integration specs. Update whenever a source changes.

| Source | Module | Cadence | Auth | Format | ToS |
|---|---|---|---|---|---|
| Yahoo Finance | `yahoo_finance.py` | Nightly 17:45 CET | None | OHLCV | OK for non-commercial; paid mirror later |
| MFN | `mfn.py` | Every 15 min in market hours | None | RSS / Atom | Designed for redistribution |
| Riksbank SWEA | `riksbank.py` | Daily 09:00 CET | None | JSON | Public |
| SCB PXWeb | `scb.py` | Weekly Mon 06:00 CET | None | JSON | Public |
| FRED | `fred.py` | Daily 09:30 CET | API key (free) | JSON | API ToS, free tier |
| ESAP | `esap.py` | Hourly | None | XML | EU regulatory |
| FI Insider | `fi_insider.py` | Hourly | None | CSV/XLSX | Public register |
| FI Short | `fi_short.py` | Daily 16:00 CET | None | CSV/XLSX | Public register |
| Company IR RSS | `company_ir_rss.py` | Hourly per onboarded ticker | None | RSS | Publisher-sanctioned |

## Discipline

- One crawler = one source. No blending in Tier 1.
- Always preserve `raw_payload` verbatim.
- Idempotent upsert keyed by source's natural primary key.
- HTTP errors retry with exponential backoff; do not catch business-logic exceptions.
- Honor `If-Modified-Since` / ETag where the source supports it.
- Every crawl creates one `crawl_run` row for observability.

## ToS posture for v1

Conservative — regulatory primary sources only (MFN, ESAP, Riksbank, SCB,
Yahoo Finance, the company's own IR RSS). No scraping of business press in v1.
Yahoo is acceptable for the pilot phase via `yfinance`; replace with paid feed
(Millistream, Refinitiv) before scaling commercially.

## Per-source detail

Per-source endpoints, schemas, schema-mapping rules, and known issues are in
the blueprint Appendix E. When a source changes (URL pattern, series IDs, auth
flow), update both this file and the blueprint.
