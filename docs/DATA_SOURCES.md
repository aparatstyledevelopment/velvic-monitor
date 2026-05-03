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

### Verified OK

- **FRED** — Endpoint `https://api.stlouisfed.org/fred/series/observations`
  and series IDs `DCOILBRENTEU`, `DGS10`, `DEXUSEU` confirmed against
  current FRED docs. Free API key (`FRED_API_KEY`) required.

### VERIFY before turning on (still open)

- **Riksbank SWEA** — `/swea/v1/Observations/{series}/{from}/{to}` endpoint
  shape confirmed against search results. Series IDs `SECBREPOEFF`,
  `SEKEURPMI`, `SEKUSDPMI`, `SEKGVB10YC` are the documented IDs but
  haven't been hit live from this repo. Cross-check against the live
  series list at `riksbank.se/en-gb/statistics/...series-for-the-api/`
  before first scheduled run. API limits are 200/min and 30k/week — well
  within budget.

- **MFN** — Per-issuer Atom URL pattern `mfn.se/all/a/{slug}?format=atom`
  is plausible based on observed issuer pages but `?format=atom` is
  undocumented in public search results. Confirm against a known issuer
  (e.g. `mfn.se/all/a/volvo?format=atom`) before turning on the
  `crawl.mfn` beat task. Slug list lives on `Company.mfn_slug`.

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
