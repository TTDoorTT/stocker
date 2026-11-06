import re
from datetime import UTC, date, datetime, timedelta

from app.contracts.market import Evidence, NewsItem, Quote, Stock
from app.core.config import Settings
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.provenance import evidence_id
from app.modules.market_data.providers.http import ProviderHTTP


def now() -> datetime:
    return datetime.now(UTC)


class FinnhubProvider:
    def __init__(self, settings: Settings, http: ProviderHTTP):
        self.settings = settings
        self.http = http

    def populate(self, stock: Stock, symbol: str) -> None:
        try:
            if not self.settings.finnhub_api_key:
                raise DataUnavailable("FINNHUB_API_KEY not configured; quote unavailable")
            url = "https://finnhub.io/api/v1/quote"
            response = self.http.fetch(
                url, params={"symbol": symbol, "token": self.settings.finnhub_api_key}, ttl=60
            )
            quote = response.data
            if not isinstance(quote, dict):
                raise DataUnavailable("Quote provider returned an invalid object")
            if not quote.get("c") or not quote.get("t"):
                raise DataUnavailable("Quote unavailable for this symbol/plan")
            if any(isinstance(quote.get(field), bool) for field in ("c", "pc", "t")):
                raise DataUnavailable("Quote provider returned nonfinancial numeric values")
            timestamp = datetime.fromtimestamp(quote["t"], UTC)
            if timestamp > now() + timedelta(minutes=5):
                raise DataUnavailable("Quote timestamp is in the future")
            stock.quote = Quote(
                price=quote["c"],
                previous_close=quote.get("pc") or None,
                timestamp=timestamp,
                source_name="Finnhub",
                source_url="https://finnhub.io/docs/api/quote",
                stale=(now() - timestamp).total_seconds() > 86400,
                delayed=True,
                evidence_id=evidence_id(symbol, "price", quote["t"]),
                fetched_at=response.fetched_at,
                cached=response.cached,
            )
            for field, value in [
                ("price", stock.quote.price),
                ("previous_close", stock.quote.previous_close),
            ]:
                if value is not None:
                    stock.evidence.append(
                        Evidence(
                            evidence_id=evidence_id(symbol, field, quote["t"]),
                            symbol=symbol,
                            field=field,
                            value=value,
                            unit="USD",
                            period=str(timestamp.date()),
                            source_name="Finnhub",
                            source_url="https://finnhub.io/docs/api/quote",
                            published_at=timestamp,
                            fetched_at=response.fetched_at,
                            cached=response.cached,
                            stale=stock.quote.stale,
                        )
                    )
        except (DataUnavailable, ValueError, TypeError, OverflowError, OSError):
            stock.gaps.append("Quote unavailable; verify FINNHUB_API_KEY, symbol and plan entitlement.")

    def search(self, q: str) -> list[dict]:
        data = self.http.json(
            "https://finnhub.io/api/v1/search",
            params={"q": q, "token": self.settings.finnhub_api_key},
            ttl=3600,
        )

        if not isinstance(data, dict) or not isinstance(data.get("result", []), list):
            raise DataUnavailable("Search provider returned an invalid result")

        return [
            {"symbol": row["symbol"], "name": row.get("description", "")}
            for row in data.get("result", [])
            if isinstance(row, dict)
            if re.fullmatch(r"[A-Z]{1,5}(?:[.-][A-Z])?", row.get("symbol", ""))
        ][:20]

    def append_news(self, output: list[NewsItem], ticker: str) -> None:
        try:
            response = self.http.fetch(
                "https://finnhub.io/api/v1/company-news",
                params={
                    "symbol": ticker,
                    "from": str(date.today() - timedelta(days=7)),
                    "to": str(date.today()),
                    "token": self.settings.finnhub_api_key,
                },
                ttl=900,
            )
            items = response.data
            for item in items[:20] if isinstance(items, list) else []:
                if not str(item.get("url", "")).startswith("https://"):
                    continue
                output.append(
                    NewsItem(
                        headline=item["headline"][:500],
                        source_name=item.get("source", "Finnhub"),
                        source_url=item["url"],
                        published_at=datetime.fromtimestamp(item["datetime"], UTC),
                        fetched_at=response.fetched_at,
                        cached=response.cached,
                        symbols=[ticker],
                    )
                )
        except (
            DataUnavailable,
            KeyError,
            ValueError,
            TypeError,
            OverflowError,
            OSError,
            AttributeError,
        ):
            pass
