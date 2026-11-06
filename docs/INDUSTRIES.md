# Guided industry research

The 20 topics in `fixtures/industries.json` independently adapt the topic selection of Vibe Research's `desktop/src/verticals/finance/data/sectors.json` at commit `84c141b86b5e7540b29f5f4cd5457dc0ebd6052e`. Prompts are newly written in English for U.S. research and global supply chains. China-specific substitution and trading assumptions have been removed. The source's verification flags are not inherited.

Each topic is a research guide, not a claim that sector capacity, market share or demand data is integrated. Company symbols are starting points for verification against filings. Running one company does not establish an industry-wide finding. Canada is planned for fundamentals and is not enabled through these templates.

Two initial walkthroughs reuse the shared research pipeline: AI computing → NVDA, and AI applications → MSFT. The fixture tests select these topics and execute six stages against clearly synthetic company evidence. These demonstrate workflow and persistence, not sourced sector conclusions or live model acceptance. With a configured model, run the same representative cases and inspect whether requested segment evidence exists; absent data must remain a gap.

No extra sector orchestration service is introduced. All topics are navigable; topics without a representative symbol remain guided prompts for a user-selected U.S. company. There is no claim of autonomous multi-company industry coverage.

## Macro indicators

The intelligence module requests three FRED observation series only when live mode and `FRED_API_KEY` are configured: DGS10 (daily Treasury yield, percent), FEDFUNDS (monthly effective federal funds rate, percent), and DCOILWTICO (daily WTI spot price, USD per barrel). FRED links and observation dates accompany every value. Publication timestamps are explicitly unavailable; revisions and release lags apply. Missing observations (`.`), nonfinite values and future observations are excluded. A trend is drawn only from actual returned observations. Freshness thresholds are 10 calendar days for daily series and 65 for the monthly rate; thresholds describe retrieval warnings, not market-session knowledge.

Fixture mode intentionally has no synthetic news or macro values. Daily review uses SPY/QQQ as labeled ETF proxies, never literal index levels. Breadth, sector performance and aggregate volume remain unavailable because the integrated universe does not support those claims.

## Source acknowledgment

Vibe Research is MIT-licensed, copyright (c) 2026 simonlin1212. Its topic concepts inspired the selection; no OpenStock implementation was reused.

MIT License

Copyright (c) 2026 simonlin1212

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
