"""Small, source-backed market intelligence; no second agent orchestration system."""

from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime

from app.core.config import Settings
from app.finance.metrics import build_calculations
from app.modules.intelligence.highlight_cache import HighlightCache
from app.modules.intelligence.industries import IndustryCatalog
from app.modules.intelligence.news import news_feed, summarize_news
from app.modules.intelligence.rss import RSSNewsService
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
        self.rss_collector = RSSNewsService(settings)
        self.highlight_cache = HighlightCache(settings.database_url)

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

    def rss_feed(self, category: str = "ai") -> dict:
        return self.rss_collector.feed(category)

    def rss_refresh(self) -> dict:
        self.rss_collector.schedule(force=True)
        return self.rss_collector.feed(schedule=False)

    def rss_saved_highlights(self, category: str) -> dict:
        self.rss_collector.validate_category(category)
        return self.highlight_cache.get(category)

    def rss_highlights(self, category: str) -> dict:
        self.rss_collector.validate_category(category)
        settings = self.current_settings()
        with closing(self.rss_collector.connect()):
            pass
        fingerprint = self.highlight_cache.fingerprint(category)
        result = self.rss_collector.highlights(category, settings)
        self.highlight_cache.save(category, result, settings.llm_model, fingerprint)
        return result

    def ai_computing_evidence(self, year: int) -> dict:
        """Deterministic industry evidence preview; does not invoke a model."""
        snapshot = self.data.sec_industry_snapshot(year)
        stories = []
        try:
            for category in ("ai", "semi"):
                feed = self.rss_collector.feed(category, schedule=False)
                for item in feed["items"][:5]:
                    stories.append(
                        {
                            "category": category,
                            "headline": item["headline"],
                            "source_name": item["source_name"],
                            "source_url": item["source_url"],
                            "published_at": item["published_at"],
                        }
                    )
        except (OSError, ValueError) as exc:
            snapshot["gaps"].append(f"Cached RSS headlines unavailable ({type(exc).__name__}).")
        snapshot["news"] = sorted(stories, key=lambda item: item["published_at"], reverse=True)[:8]
        if not snapshot["news"]:
            snapshot["gaps"].append("RSS headlines not cached yet; refresh Industry Intelligence news first.")
        return snapshot

    def signals(self) -> dict:
        return self.data.signals()

    def industries(self) -> list[dict]:
        return self.catalog.industries()

    def industry(self, slug: str) -> dict:
        return self.catalog.industry(slug)

    def summarize_news(self) -> dict:
        return summarize_news(self.data, self.current_settings())
