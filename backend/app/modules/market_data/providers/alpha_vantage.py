from datetime import UTC, date, datetime, timedelta

from app.contracts.market import PriceBar
from app.core.config import Settings
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.http import ProviderHTTP


def now() -> datetime:
    return datetime.now(UTC)


class AlphaVantageProvider:
    def __init__(self, settings: Settings, http: ProviderHTTP):
        self.settings = settings
        self.http = http

    def history(self, symbol: str, range: str, failures: list[str]) -> list[PriceBar]:
        if not self.settings.alpha_vantage_api_key:
            raise DataUnavailable(
                "; ".join(failures + ["Optional ALPHA_VANTAGE_API_KEY absent; history unavailable"])
            )

        response = self.http.fetch(
            "https://www.alphavantage.co/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "apikey": self.settings.alpha_vantage_api_key,
            },
            ttl=86400,
            interval=3,
        )

        data = response.data

        series = data.get("Time Series (Daily)") if isinstance(data, dict) else None

        if not isinstance(series, dict) or not series:
            raise DataUnavailable("Daily history unavailable: provider limit, symbol or entitlement")

        fetched = response.fetched_at

        today = now().date()

        lower = today - timedelta(days={"1m": 31, "3m": 93, "1y": 366}[range])

        try:
            bars = []
            for day, row in sorted(series.items()):
                observation = date.fromisoformat(day)
                if observation > today:
                    raise ValueError("Future historical price date")
                if observation >= lower:
                    bars.append(
                        PriceBar(
                            date=day,
                            close=float(row["4. close"]),
                            source_name="Alpha Vantage (raw daily; 100 points max)",
                            source_url="https://www.alphavantage.co/documentation/#daily",
                            fetched_at=fetched,
                            cached=response.cached,
                        )
                    )
            return bars
        except (TypeError, ValueError, KeyError, OverflowError):
            raise DataUnavailable("Daily history unavailable: invalid dated price observations") from None
