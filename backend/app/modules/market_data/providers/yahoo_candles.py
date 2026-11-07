"""Optional Yahoo OHLCV adapter sharing the existing daily history cache/pacer."""

import time
from collections.abc import Mapping
from datetime import UTC, datetime
from importlib import import_module

from app.contracts.stock_research import CandleBar, CandleSeries, SourceMetadata
from app.core.config import ROOT
from app.modules.market_data.candles import aggregate_bars, select_range
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.yahoo import YFinanceHistory
from app.modules.market_data.symbols import symbol_market

PERIODS = {"1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"}


class YFinanceCandleHistory(YFinanceHistory):
    def candles(self, symbol: str, range_key: str, interval: str, currency: str) -> CandleSeries:
        if range_key not in PERIODS or interval not in {"1d", "1wk", "1mo"}:
            raise ValueError("Unsupported candle range/interval")
        key = ("candles", symbol, range_key, interval, currency)
        with self.lock:
            cached = self.cache.get(key)
            if cached and cached[0] > time.monotonic():
                return cached[1].model_copy(
                    update={"source": cached[1].source.model_copy(update={"cached": True})}, deep=True
                )
            factory = self.ticker_factory
            if factory is None:
                try:
                    yf = import_module("yfinance")
                    yf.set_tz_cache_location(str(ROOT / ".provider-cache" / "yfinance"))
                    factory = yf.Ticker
                except ImportError:
                    raise DataUnavailable(
                        "Optional yfinance dependency absent; install backend[history]"
                    ) from None
            pause = self.interval - (time.monotonic() - self.last)
            if pause > 0:
                time.sleep(pause)
            self.last = time.monotonic()
            try:
                provider_symbol = symbol if symbol.endswith((".TO", ".V")) else symbol.replace(".", "-")
                ticker = factory(provider_symbol)
                frame = ticker.history(
                    period=PERIODS[range_key],
                    interval="1d",
                    auto_adjust=False,
                    actions=False,
                    timeout=self.timeout,
                    raise_errors=True,
                )
                metadata = ticker.history_metadata
                if (
                    not isinstance(metadata, Mapping)
                    or metadata.get("currency") != currency
                    or metadata.get("symbol", "").upper() != provider_symbol
                ):
                    raise DataUnavailable(
                        "Yahoo history identity/currency unavailable or incompatible with listing"
                    )
                fetched_at = datetime.now(UTC)
                bars = []
                for index, row in frame.iterrows():
                    # Reject missing/invalid OHLCV rather than fabricating a valid candle.
                    adjustment = row.get("Adj Close")
                    bars.append(
                        CandleBar(
                            date=index.date(),
                            open=float(row["Open"]),
                            high=float(row["High"]),
                            low=float(row["Low"]),
                            close=float(row["Close"]),
                            volume=int(row["Volume"]) if row.get("Volume") is not None else None,
                            adjusted_close=float(adjustment) if adjustment is not None else None,
                        )
                    )
                bars = select_range(bars, range_key, as_of=fetched_at.date())
                if not bars or len({bar.date for bar in bars}) != len(bars):
                    raise DataUnavailable("Yahoo returned empty or duplicate-dated OHLCV history")
                series = CandleSeries(
                    symbol=symbol,
                    market=symbol_market(symbol),
                    currency=currency,
                    mode="live",
                    range=range_key,
                    interval=interval,
                    price_basis="provider_ohlc",
                    adjustment_note=(
                        "Yahoo auto_adjust=False provider OHLC; Close may reflect splits. "
                        "Adj Close is separate where available; candlestick returns are not total returns."
                    ),
                    source=SourceMetadata(
                        name="Yahoo Finance via yfinance (educational/personal use)",
                        url=f"https://finance.yahoo.com/quote/{provider_symbol}/history/",
                        fetched_at=fetched_at,
                    ),
                    bars=aggregate_bars(bars, interval),
                    gaps=["Unofficial Yahoo history; availability and use rights may change."],
                )
            except DataUnavailable:
                raise
            except Exception:
                raise DataUnavailable(
                    "yfinance OHLCV unavailable; check listing, access and data quality"
                ) from None
            self.cache[key] = (time.monotonic() + self.ttl, series)
            return series.model_copy(deep=True)
