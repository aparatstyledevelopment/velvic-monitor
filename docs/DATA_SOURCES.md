# Data Sources

Per-source integration specs. Update whenever a source changes.

| Source | Module | Cadence | Auth | Format | ToS |
|---|---|---|---|---|---|
| Yahoo Finance | `yahoo_finance.py` | Nightly 17:45 CET | None | OHLCV | OK for non-commercial; paid mirror later |
| MFN | `mfn.py` | DISABLED (free feed retired May 2026) | n/a | n/a | Commercial API only |
| Riksbank SWEA | `riksbank.py` | DISABLED (Azure APIM key required since 2026) | `Ocp-Apim-Subscription-Key` | JSON | Public via key |
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

## Upstream status (Layer 2 audit, May 2026; updated post-Phase-1.5 fixes)

Status after the Phase-1.5 fix-it patch. Items below are sorted by current
state.

### Resolved

- **Yahoo Finance** — Swapped from direct `httpx` calls to the `yfinance`
  library. Yahoo's `/v8/finance/chart/` endpoint returns 403 to plain HTTP
  (TLS-fingerprint detection); yfinance's curl_cffi Chrome impersonation
  bypasses it. Network call now lives in `_yf_history_records`, executed
  via `asyncio.to_thread`. The crawler's `parse()` is unchanged in shape
  (list-of-records in, ParsedBar out) so unit tests still drive it with
  fixtures, no network. Tier-1 isolation (ADR 0005) means the eventual
  swap to a paid feed (Millistream / Refinitiv) stays a Tier-1 + ingestion
  change with zero Engine impact.

- **SCB PXWeb** — Default `table_id` swapped from the bogus `PR0101A1`
  to `KPItotM` (the real monthly CPI 1980=100 table). The `crawl.scb`
  beat task is disabled in `pipeline/schedules.py:DISABLED_CRAWLERS`
  until the operator confirms the active 2020=100 successor table id
  for 2026+ data and re-enables. The crawler can still be invoked
  manually for ad-hoc runs.

- **ESAP** — Beat task disabled in `DISABLED_CRAWLERS`; module docstring
  updated to call out the 2026-07-10 collection start / July 2027 public
  API timeline. Skeleton kept so the BaseCrawler contract is in place
  for the future cutover.

- **MFN** — Free public Atom feed retired in 2026.
  `mfn.se/all/a/{slug}?format=atom` now serves `text/html` regardless of
  the query param, and every alternate path probed (`.atom`, `.rss`,
  `.xml`, `/feed`, `/api/feeds/...`) returns 500. `mfn.se/robots.txt`
  also explicitly disallows `*.xml$ / *.rss$ / *.atom$ / *.json$`,
  including the `sitemap.xml` endpoint that does still serve a custom
  feed format. Beat task disabled in `DISABLED_CRAWLERS`; backfill
  script no longer invokes `MfnCrawler`. Re-enabling requires either
  the commercial MFN API or a redistribution partnership.

### Verified OK

- **FRED** — Endpoint `https://api.stlouisfed.org/fred/series/observations`
  and series IDs `DCOILBRENTEU`, `DGS10`, `DEXUSEU` confirmed against
  current FRED docs. Free API key (`FRED_API_KEY`) required.

- **Riksbank SWEA** — Migrated to Azure API Management; the rates / FX
  read endpoints now require `Ocp-Apim-Subscription-Key`. Without the
  key, requests return 200 with a non-JSON body that crashes
  `resp.json()` (observed in pod May 2026). Crawler now reads the key
  from `Settings.riksbank_subscription_key` and raises a `CrawlerError`
  with operator instructions when missing. Beat task disabled in
  `DISABLED_CRAWLERS`; backfill no longer invokes `RiksbankCrawler`.
  Re-enable: register at developer.api.riksbank.se, set
  `RIKSBANK_SUBSCRIPTION_KEY` in DO secrets, remove from
  `DISABLED_CRAWLERS`, and add the import + `_safe_step` call back to
  `backfill.py`.

### VERIFY before turning on (still open)

- **FI Insider (`marknadssok.fi.se/publiceringsklient/...`)** — Host
  confirmed; the CSV-export URL with `button=export` came from
  reverse-engineering the search UI. Sniff the actual download URL from
  a browser session and confirm column names match `parse()` before
  enabling. Same for **FI Short**
  (`fi.se/sv/vara-register/blankningsregistret/GetAktuellFile/`) — it's
  the URL behind the "download" button on the registry page; confirm the
  CSV header set matches what `parse()` expects.

- **Company IR RSS** — Per-company `ir_rss_url`. Tests use synthetic
  feeds; confirm against the real Datablocks/Cision feeds for each
  onboarded company at admin onboarding time.
