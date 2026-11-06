"""Explicit, on-demand summaries of retrieved headlines, never invented article contents."""

from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

from app.contracts.market import Evidence
from app.core.config import Settings
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.provenance import evidence_id
from app.modules.market_data.service import DataService
from app.modules.market_data.symbols import normalize_symbol
from app.modules.research.errors import ModelError
from app.modules.research.service import summarize_captured_headlines


def summarize_news(data: DataService, settings: Settings, symbol: str | None = None) -> dict:
    if settings.data_mode != "live":
        raise ModelError("AI headline summaries require live data mode; fixture summaries are unavailable")
    if not settings.llm_model:
        raise ModelError("LLM_MODEL is not configured; AI headline summary is unavailable")
    requested_symbol = normalize_symbol(symbol) if symbol else None
    news = data.news(requested_symbol)
    evidence = []
    seen = set()
    for item in news:
        if item.fixture or not item.source_url.startswith("https://") or not item.headline.strip():
            continue
        key = (item.headline.casefold().strip(), item.source_url)
        if key in seen:
            continue
        seen.add(key)
        # These are source headlines, not verified financial values or full article extracts.
        record = Evidence(
            evidence_id=evidence_id("headline", item.source_url, item.headline, item.published_at),
            symbol=requested_symbol or (item.symbols[0] if item.symbols else "US"),
            field="headline",
            value=item.headline[:500],
            unit="text",
            currency=None,
            period=str(item.published_at.date()),
            source_name=item.source_name,
            source_url=item.source_url,
            published_at=item.published_at,
            fetched_at=item.fetched_at,
            cached=item.cached,
        )
        evidence.append(record.model_dump(mode="json"))
        if len(evidence) == 12:
            break
    if not evidence:
        raise DataUnavailable("No sourced live headlines are available to summarize")
    gaps = [
        "Headline-only summary: full article contents are not retrieved or verified.",
        "Coverage is limited to the captured sources and dates; no social sentiment is inferred.",
        "Reported headlines may contain allegations or forward-looking statements, not established facts.",
    ]
    payload = {
        "symbol": requested_symbol or "US",
        "mode": "live",
        "profile": "Retrieved headlines only.",
        "evidence": evidence,
        "facts": [],
        "news": [record["value"] for record in evidence],
        "gaps": gaps,
    }
    return summarize_captured_headlines(payload, evidence, gaps, settings)


def now():
    return datetime.now(UTC)


def news_feed(data: DataService, settings: Settings) -> dict:
    gaps = []
    try:
        items = data.news()
    except (DataUnavailable, ValueError):
        items = []
        gaps.append("News provider unavailable; verify configuration, access and network.")
    deduped = {}
    for item in items:
        parts = urlsplit(item.source_url)
        url = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
        key = (" ".join(item.headline.casefold().split()), url)
        if key not in deduped:
            deduped[key] = item.model_dump(mode="json")
    ordered = sorted(deduped.values(), key=lambda row: row["published_at"], reverse=True)
    if not ordered:
        gaps.append("No sourced company/industry headlines or filings are available.")
    if settings.data_mode == "fixtures":
        gaps.append("Fixture mode provides no invented headlines or AI summaries.")
    else:
        gaps.append("Coverage is limited to configured sources and AAPL/MSFT/NVDA; no social sentiment feed.")
    return {
        "mode": settings.data_mode,
        "items": ordered[:60],
        "fetched_at": now().isoformat(),
        "gaps": gaps,
    }
