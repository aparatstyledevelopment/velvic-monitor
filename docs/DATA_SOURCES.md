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

## Known upstream issues (Layer 2 research, May 2026)

These are the verified deltas between blueprint placeholders and what the
real upstreams currently look like. Each becomes a Phase-1.5 fix-it ticket
before backfill is run for real.

### Yahoo Finance — BLOCKER

`https://query2.finance.yahoo.com/v8/finance/chart/{symbol}` returns **403**
to plain HTTP clients. yfinance bypasses this with `curl_cffi` impersonating
Chrome (TLS fingerprint matters, not just headers). Three remediation paths:

1. **Swap to the `yfinance` Python library** (handles impersonation +
   crumb/cookie dance). Cleanest, ships in a few hours.
2. **Adopt `curl_cffi` directly** in our crawler. Same idea, more code.
3. **Switch to a paid feed** (Millistream / Refinitiv / Polygon). The
   long-term plan per ADR 0002; can wait until pre-LOI.

For the demo backfill, option (1) is enough. Tier-1 isolation means the
Engine doesn't notice.

### Riksbank SWEA — VERIFY before backfill

The series IDs in `riksbank.py` (`SECBREPOEFF`, `SEKEURPMI`, `SEKUSDPMI`,
`SEKGVB10YC`) need a manual cross-check against
`https://www.riksbank.se/en-gb/statistics/interest-rates-and-exchange-rates/retrieving-interest-rates-and-exchange-rates-via-api/series-for-the-api/`.
The `/swea/v1/Observations/{series}/{from}/{to}` endpoint shape is correct.
Note: the API ToS allows 200 calls/min and 30k/week — comfortable for our
cadence.

### SCB PXWeb — BROKEN

The `table_id = "PR0101A1"` in `scb.py` is not a real SCB table. Real CPI
tables go through paths like `START__PR__PR0101__PR0101A/KPItotM` or
`SnabbStatPR0101`. The base URL `https://api.scb.se/OV0104/v1/doris/en/ssd`
is correct; the table-id resolution needs fixing.

Also: the `KPItotM` 1980=100 series stops updating after Dec 2025; from
2026 the rebased 2020=100 series at `KPI2020COICOPAR` is the active one.
Fix when first running backfill against real SCB.

### FRED — OK

`https://api.stlouisfed.org/fred/series/observations` and series IDs
`DCOILBRENTEU`, `DGS10`, `DEXUSEU` all check out against current docs.
Free API key required. Endpoint shape and response shape match the parser.

### MFN — VERIFY

`https://mfn.se/all/a/{slug}?format=atom` is the documented per-issuer feed
URL pattern. Issuer slugs (e.g., `volvo`, `atlas-copco`, `sandvik`) are
hand-curated and live on the `Company.mfn_slug` column. Confirm the
`?format=atom` query param actually returns atom (vs HTML); the seed
already maps the five demo tickers' slugs.

### ESAP — NOT YET LIVE

ESAP's collection start date is **10 July 2026**; public API access lands
**July 2027**. The crawler is a structural skeleton today; the URL,
auth scheme, and response shape are placeholders that will be replaced
when ESMA publishes the v1 API spec. Disable the `crawl.esap` beat task
until then.

### FI Insider — VERIFY

`https://marknadssok.fi.se/publiceringsklient/en-GB/Search/Search` with
`button=export` is undocumented; FI publishes the search UI but not a
stable API. The CSV download URL needs sniffing from the live UI before
backfill.

### FI Short — VERIFY

`https://www.fi.se/sv/vara-register/blankningsregistret/GetAktuellFile/`
is the URL the FI page hits when you click "download". Verify the CSV
column names (Swedish-locale headers) match what `parse()` expects.
