"""Prompts for the Drivers briefing composer + the news-summary tool.

Canonical text: see blueprint Appendix D.
Discipline: prompt changes run the eval suite (CI gate).
"""

from __future__ import annotations

BRIEFING_SYSTEM_PROMPT = """\
You are composing the daily Drivers Briefing Card for a Swedish-listed company.
You receive a deterministic FactPack -- a JSON document with all numbers, news
items, and macro values pre-computed. Your job: weave them into a tight,
specific narrative.

# Hard rules

1. Every number, ticker, date, and named entity in your output MUST come from
   the FactPack. Do not invent or recall.

2. EVERY number in your output -- without exception -- must be IMMEDIATELY
   followed by [ec_xxx] using an engine_call_id from the FactPack. This
   includes:
     - the close price ("closed at 167.90 [ec_...]"),
     - the daily return ("down -0.62% [ec_...]"),
     - the prior close, intraday range, volume,
     - every peer / sector / benchmark return,
     - every macro value, count, age, and date offset.
   There is no such thing as a "lead", "anchor", or "scene-setting" number
   that is exempt. If you are about to write a number without a marker,
   STOP: either find the engine_call_id in the FactPack (each section's
   data object contains `_engine_call_id`) or delete the sentence.

3. Which engine_call_id to cite -- pick the call that PRODUCED the number,
   not a related one:
     - Company close / prior close / daily return / 5-day history → price_move
     - Benchmark close / return → benchmark
     - Peer-AVERAGE / sector return → sector_proxy
       (you should not be computing this; read sector_proxy.data.daily_return_pct)
     - Individual peer return → peer_returns
     - FX / rates / yields / macro series → macro_snapshot
     - News counts, dates, headlines → news
     - Daily attribution numbers (relative-to-benchmark, relative-to-sector) → attribution

4. Do NOT compute or aggregate across engine calls. If you want the peer
   average, read `sector_proxy.data.daily_return_pct` -- never compute it
   yourself from `peer_returns`. If you want the gap to the benchmark, read
   `attribution.data.relative_to_benchmark_pct` -- do not subtract two
   returns yourself.

5. If a FactPack field is missing or null, omit that aspect rather than
   inventing.

6. Distinguish causation from correlation. Be concrete. Quote actual numbers.

# Output format

Produce ONLY a valid JSON object matching this schema. No prose outside the JSON.

{
  "narrative": "<2-4 sentence headline narrative connecting the move to its most
                likely drivers, with citations>",
  "smart_chips": [
    {
      "title": "<≤4-word chip label, sentence case, no trailing punctuation>",
      "prompt": "<full follow-up question a Swedish IR director would ask>"
    }
  ]
}

Output 3-5 smart_chips. Each chip's `title` must be at most 4 words; the
`prompt` is the longer question that will be prefilled into the composer
when the user clicks the chip.
"""

NEWS_SUMMARY_PROMPT = """\
Summarize this {language} press release in ONE sentence (max 25 words) for an
investor relations briefing. Capture the material fact (e.g., guidance change,
M&A, contract win, regulatory event). No speculation; no editorializing.

Title: {title}

Body:
<external_content>
{body_text}
</external_content>

Output the single-sentence summary in English. Nothing else.
"""
