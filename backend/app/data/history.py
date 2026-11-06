"""Optional Yahoo/yfinance daily history, separate from quote/fundamental providers.

No Yahoo data is used unless selected (or installed in auto mode). No credentials,
proxy configuration, cookies or other user-wide configuration are loaded by us.
"""

import threading
import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from importlib import import_module

from app.core.config import ROOT
from app.data.http import DataUnavailable
from app.models.market import PriceBar


class YFinanceHistory:
    ttl = 3600
    interval = 2.0
    timeout = 15

    def __init__(self, ticker_factory=None):
        self.ticker_factory = ticker_factory
        self.cache = {}
        self.lock = threading.RLock()
        self.last = 0.0

    def history(self, symbol, range, currency):
        key = (symbol, range, currency)
        with self.lock:
            cached = self.cache.get(key)
            if cached and cached[0] > time.monotonic():
                return [bar.model_copy(update={"cached": True}, deep=True) for bar in cached[1]]
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
                # Yahoo uses '-' for U.S. share classes, '.TO'/'.V' for Canadian exchanges.
                provider_symbol = symbol if symbol.endswith((".TO", ".V")) else symbol.replace(".", "-")
                ticker = factory(provider_symbol)
                frame = ticker.history(
                    period={"1m": "1mo", "3m": "3mo", "1y": "1y"}[range],
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
                        "Yahoo history identity/currency unavailable or incompatible with selected listing"
                    )
                fetched = datetime.now(UTC)
                lower = fetched.date() - timedelta(days={"1m": 31, "3m": 93, "1y": 366}[range])
                bars = []
                for index, row in frame.iterrows():
                    day = index.date()
                    if not lower <= day <= fetched.date():
                        continue
                    bars.append(
                        PriceBar(
                            date=day,
                            close=float(row["Close"]),
                            currency=currency,
                            source_name="Yahoo Finance via yfinance (educational/personal use)",
                            source_url=f"https://finance.yahoo.com/quote/{symbol}/history/",
                            fetched_at=fetched,
                            adjusted=False,
                            limitations=[
                                "Unofficial Yahoo access; availability and terms may change.",
                                "auto_adjust=False Close; not a total-return series.",
                            ],
                        )
                    )
                bars.sort(key=lambda bar: bar.date)
                if not bars:
                    raise DataUnavailable("Yahoo returned no valid daily history")
            except DataUnavailable:
                raise
            except Exception:
                # Third-party failures may contain request details; never expose their text.
                raise DataUnavailable(
                    "yfinance history unavailable; check symbol, access, limits and network"
                ) from None
            self.cache[key] = (time.monotonic() + self.ttl, bars)
            return [bar.model_copy(deep=True) for bar in bars]
