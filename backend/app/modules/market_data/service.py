import json

from app.contracts.market import NewsItem, PriceBar, Stock
from app.core.config import ROOT, Settings
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.fixtures import FixtureData
from app.modules.market_data.providers.alpha_vantage import AlphaVantageProvider
from app.modules.market_data.providers.bank_of_canada import valet_signals
from app.modules.market_data.providers.finnhub import FinnhubProvider
from app.modules.market_data.providers.fred import FredProvider
from app.modules.market_data.providers.http import ProviderHTTP
from app.modules.market_data.providers.sec import SecProvider
from app.modules.market_data.providers.yahoo import YFinanceHistory
from app.modules.market_data.symbols import normalize_symbol, symbol_market


class DataService:
    def __init__(self, settings: Settings, http: ProviderHTTP | None = None):
        self.settings = settings
        self.http = http or ProviderHTTP()
        self.fixtures = FixtureData(json.loads((ROOT / "fixtures" / "market.json").read_text()))
        self.yahoo_history = YFinanceHistory()
        self.sec = SecProvider(settings, self.http)
        self.finnhub = FinnhubProvider(settings, self.http)
        self.alpha_vantage = AlphaVantageProvider(settings, self.http)
        self.fred = FredProvider(settings, self.http)

    def search(self, q: str) -> list[dict]:
        q = q.strip().upper()
        if not q:
            return []
        if self.settings.data_mode == "fixtures":
            return self.fixtures.search(q)
        # Exact Canadian listings are accepted without inventing identity/search coverage.
        try:
            candidate = normalize_symbol(q)
        except ValueError:
            candidate = None
        if candidate and symbol_market(candidate) == "CA":
            return [{"symbol": candidate, "name": "Canadian listing — identity and fundamentals unverified"}]
        try:
            return [
                {"symbol": r["ticker"], "name": r["title"]}
                for r in self.sec.tickers()
                if q in r["ticker"].upper() or q in r["title"].upper()
            ][:20]
        except DataUnavailable:
            if not self.settings.finnhub_api_key:
                raise
            return self.finnhub.search(q)

    def stock(self, symbol: str) -> Stock:
        symbol = normalize_symbol(symbol)
        if self.settings.data_mode == "fixtures":
            return self.fixtures.stock(symbol)
        if symbol_market(symbol) == "CA":
            return Stock(
                symbol=symbol,
                name=symbol,
                market="CA",
                currency="CAD",
                mode="live",
                profile="Canadian listing requested; company identity and financial statements unavailable.",
                gaps=[
                    "Canadian listing identity is unverified; symbol entry is not provider confirmation.",
                    "Canadian-only issuer financial statements unavailable: no permitted automated SEDAR+ adapter.",
                    "SEC EDGAR is not used as coverage for Canadian-only issuers.",
                    "Finnhub free-tier Canadian quote entitlement is not verified; quote unavailable.",
                    "Optional yfinance supports daily history for explicit .TO/.V symbols when accessible.",
                    "Licensed analyst consensus unavailable.",
                ],
            )
        stock = Stock(symbol=symbol, name=symbol, mode="live", profile="Company profile unavailable.")
        self.sec.populate(stock, symbol)
        self.finnhub.populate(stock, symbol)
        stock.gaps += [
            "Licensed analyst consensus unavailable.",
            "Annual SEC metrics are not trailing twelve-month metrics.",
        ]
        return stock

    def history(self, symbol: str, range: str = "1y") -> list[PriceBar]:
        symbol = normalize_symbol(symbol)
        if range not in {"1m", "3m", "1y"}:
            raise ValueError(
                "Supported ranges: 1m, 3m, 1y; live compact history is limited to 100 observations"
            )
        if self.settings.data_mode == "fixtures":
            return self.fixtures.history(symbol)
        failures = []
        if self.settings.history_provider in {"auto", "yfinance"}:
            try:
                return self.yahoo_history.history(
                    symbol, range, "CAD" if symbol_market(symbol) == "CA" else "USD"
                )
            except DataUnavailable as exc:
                failures.append(str(exc))
                if self.settings.history_provider == "yfinance":
                    raise
        if symbol_market(symbol) == "CA":
            raise DataUnavailable("Canadian history unavailable; use optional yfinance for .TO/.V listings")
        return self.alpha_vantage.history(symbol, range, failures)

    def overview(self) -> list[Stock]:
        return [self.stock(symbol) for symbol in ["SPY", "QQQ"]]

    def news(self, symbol: str | None = None) -> list[NewsItem]:
        if self.settings.data_mode == "fixtures":
            return []  # no invented headlines
        symbols = [normalize_symbol(symbol)] if symbol else ["AAPL", "MSFT", "NVDA"]
        output = []
        for ticker in symbols:
            stock = self.stock(ticker)
            output.extend(stock.news)
            if self.settings.finnhub_api_key and symbol_market(ticker) == "US":
                self.finnhub.append_news(output, ticker)
        return list({(item.headline, item.source_url): item for item in output}.values())[:60]

    def signals(self) -> dict:
        items = self.fred.signals()
        if self.settings.bank_of_canada_enabled:
            items.extend(valet_signals(self.http, fixtures=self.settings.data_mode == "fixtures"))
        return {
            "mode": self.settings.data_mode,
            "items": items,
            "gaps": ["These indicators describe macro conditions; no investment signals are inferred."],
        }
