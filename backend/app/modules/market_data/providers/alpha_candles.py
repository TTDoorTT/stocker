"""US Alpha Vantage compact daily OHLCV fallback. Never claims full-year coverage."""

from datetime import UTC, date, datetime

from app.contracts.stock_research import CandleBar, CandleSeries, SourceMetadata
from app.modules.market_data.candles import aggregate_bars, select_range
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.alpha_vantage import AlphaVantageProvider


class AlphaVantageCandles:
    def __init__(self, provider: AlphaVantageProvider):
        self.provider = provider

    def candles(self, symbol: str, range_key: str, interval: str) -> CandleSeries:
        if not self.provider.settings.alpha_vantage_api_key:
            raise DataUnavailable("Optional ALPHA_VANTAGE_API_KEY absent; candle data unavailable")
        if range_key in {"2y", "5y"}:
            raise DataUnavailable("Alpha Vantage compact feed does not provide 2- or 5-year daily history")
        response = self.provider.http.fetch(
            "https://www.alphavantage.co/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "apikey": self.provider.settings.alpha_vantage_api_key,
            },
            ttl=86400,
            interval=3,
        )
        series = response.data.get("Time Series (Daily)") if isinstance(response.data, dict) else None
        if not isinstance(series, dict) or not series:
            raise DataUnavailable("Alpha Vantage daily OHLCV unavailable")
        try:
            bars = []
            for day, row in series.items():
                bars.append(
                    CandleBar(
                        date=date.fromisoformat(day),
                        open=float(row["1. open"]),
                        high=float(row["2. high"]),
                        low=float(row["3. low"]),
                        close=float(row["4. close"]),
                        volume=int(row["5. volume"]) if "5. volume" in row else None,
                    )
                )
            bars = select_range(bars, range_key, as_of=datetime.now(UTC).date())
            if not bars or len({bar.date for bar in bars}) != len(bars):
                raise DataUnavailable("Alpha Vantage returned empty or duplicate-dated OHLCV history")
            result = CandleSeries(
                symbol=symbol,
                market="US",
                currency="USD",
                mode="live",
                range=range_key,
                interval=interval,
                price_basis="provider_ohlc",
                adjustment_note="Alpha Vantage raw daily OHLCV compact feed; no adjusted-close or total-return claim.",
                source=SourceMetadata(
                    name="Alpha Vantage (compact daily, at most 100 observations)",
                    url="https://www.alphavantage.co/documentation/#daily",
                    fetched_at=response.fetched_at,
                    cached=response.cached,
                ),
                bars=aggregate_bars(bars, interval),
                gaps=[
                    "Compact history is limited to up to 100 daily observations, even for longer requested ranges."
                ],
            )
            return result
        except DataUnavailable:
            raise
        except (ValueError, TypeError, KeyError, OverflowError):
            raise DataUnavailable("Alpha Vantage OHLCV failed structural validation") from None
