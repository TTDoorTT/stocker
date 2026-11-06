"""Small, source-backed market intelligence; no second agent orchestration system."""

import json
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

from app.core.config import ROOT
from app.finance.metrics import build_calculations
from app.modules.market_data.errors import DataUnavailable


def now():
    return datetime.now(UTC)


class IntelligenceService:
    def __init__(self, data, settings):
        self.data = data
        self.settings = settings
        self.templates = json.loads((ROOT / "fixtures" / "industries.json").read_text())

    def daily_review(self) -> dict:
        proxies = []
        for stock in self.data.overview():
            returns = next((c for c in build_calculations(stock) if c.metric == "daily_return"), None)
            proxies.append(
                {
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "quote": stock.quote.model_dump(mode="json") if stock.quote else None,
                    "daily_return_pct": returns.value if returns else None,
                    "calculation": returns.model_dump(mode="json") if returns else None,
                    "gaps": stock.gaps,
                }
            )
        news = self.news()
        return {
            "mode": self.settings.data_mode,
            "as_of": now().isoformat(),
            "proxies": proxies,
            "news": news["items"],
            "coverage": "SPY and QQQ ETF proxies; no market-wide breadth",
            "session": "Market session is not inferred; use individual quote timestamps.",
            "gaps": [
                "ETF prices are not index levels.",
                "Market breadth, sector coverage and volume unavailable.",
                "No whole-market conclusions can be drawn from these two ETF proxies.",
            ]
            + news["gaps"],
        }

    def news(self) -> dict:
        gaps = []
        try:
            items = self.data.news()
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
        if self.settings.data_mode == "fixtures":
            gaps.append("Fixture mode provides no invented headlines or AI summaries.")
        else:
            gaps.append(
                "Coverage is limited to configured sources and AAPL/MSFT/NVDA; no social sentiment feed."
            )
        return {
            "mode": self.settings.data_mode,
            "items": ordered[:60],
            "fetched_at": now().isoformat(),
            "gaps": gaps,
        }

    def signals(self) -> dict:
        return self.data.signals()

    def industries(self) -> list[dict]:
        common = [
            "Guided research template, not a verified sector analysis.",
            "Company examples must be verified against current filings; one stock does not represent a sector.",
            "Industry capacity, pricing, market-share and demand datasets are not integrated.",
            "Canadian history/macro support is partial; Canadian company fundamentals remain unavailable.",
        ]
        return [dict(template, gaps=common.copy()) for template in self.templates]

    def industry(self, slug: str) -> dict:
        for template in self.industries():
            if template["slug"] == slug:
                return template
        raise KeyError("Industry template not found")
