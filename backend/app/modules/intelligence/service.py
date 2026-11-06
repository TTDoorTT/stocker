"""Small, source-backed market intelligence; no second agent orchestration system."""

from collections.abc import Callable
from datetime import UTC, datetime

from app.core.config import Settings
from app.finance.metrics import build_calculations
from app.modules.intelligence.industries import IndustryCatalog
from app.modules.intelligence.news import news_feed, summarize_news
from app.modules.market_data.service import DataService


def now():
    return datetime.now(UTC)


class IntelligenceService:
    def __init__(
        self, data: DataService, settings: Settings, current_settings: Callable[[], Settings] | None = None
    ):
        self.data = data
        self.settings = settings
        self.current_settings = current_settings or (lambda: self.settings)
        self.catalog = IndustryCatalog()

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
        return news_feed(self.data, self.settings)

    def signals(self) -> dict:
        return self.data.signals()

    def industries(self) -> list[dict]:
        return self.catalog.industries()

    def industry(self, slug: str) -> dict:
        return self.catalog.industry(slug)

    def summarize_news(self) -> dict:
        return summarize_news(self.data, self.current_settings())
