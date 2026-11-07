import json
from datetime import date

from app.contracts.market import NewsItem, PriceBar, Stock
from app.contracts.stock_research import (
    CandleSeries,
    EarningsResponse,
    FinancialTrendsResponse,
    SourceMetadata,
)
from app.core.config import ROOT, Settings
from app.modules.market_data.candles import fixture_candles
from app.modules.market_data.earnings import fetch_earnings, fixture_earnings, unavailable
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.filing_excerpt import filing_excerpts
from app.modules.market_data.fixtures import FixtureData
from app.modules.market_data.industry_sec import SECIndustryEvidence
from app.modules.market_data.providers.alpha_candles import AlphaVantageCandles
from app.modules.market_data.providers.alpha_vantage import AlphaVantageProvider
from app.modules.market_data.providers.bank_of_canada import valet_signals
from app.modules.market_data.providers.finnhub import FinnhubProvider
from app.modules.market_data.providers.fred import FredProvider
from app.modules.market_data.providers.http import ProviderHTTP
from app.modules.market_data.providers.sec import SecProvider
from app.modules.market_data.providers.yahoo_candles import YFinanceCandleHistory
from app.modules.market_data.quarterly import (
    fetch_sec_financial_trends,
    fixture_financial_trends,
    no_coverage,
)
from app.modules.market_data.symbols import normalize_symbol, symbol_market


class DataService:
    def __init__(self, settings: Settings, http: ProviderHTTP | None = None):
        self.settings = settings
        self.http = http or ProviderHTTP()
        self.fixtures = FixtureData(json.loads((ROOT / "fixtures" / "market.json").read_text()))
        # Subclass of the previous provider: retains the exact legacy .history contract.
        self.yahoo_history = YFinanceCandleHistory()
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

    def candles(self, symbol: str, range_key: str = "1y", interval: str = "1d") -> CandleSeries:
        """New read-only OHLCV endpoint; no changes to the original history endpoint."""
        symbol = normalize_symbol(symbol)
        if range_key not in {"1m", "3m", "6m", "1y", "2y", "5y"}:
            raise ValueError("Unsupported candle range")
        if interval not in {"1d", "1wk", "1mo"}:
            raise ValueError("Unsupported candle interval")
        if self.settings.data_mode == "fixtures":
            stock = self.fixtures.stock(symbol)
            as_of = date.fromisoformat(self.fixtures.demo["as_of"][:10])
            return CandleSeries(
                symbol=symbol,
                market="US",
                currency="USD",
                mode="fixtures",
                range=range_key,
                interval=interval,
                price_basis="provider_ohlc",
                adjustment_note="Invented synthetic OHLCV; not historical prices or returns.",
                source=SourceMetadata(
                    name="Stocker synthetic offline fixture",
                    url="https://github.com/TTDoorTT/stocker/blob/main/fixtures/market.json",
                    fetched_at=stock.quote.fetched_at,
                    fixture=True,
                ),
                bars=fixture_candles(
                    quote_price=stock.quote.price, range_key=range_key, interval=interval, as_of=as_of
                ),
                gaps=["Entire price series is synthetic and cannot be used as real market evidence."],
            )
        currency = "CAD" if symbol_market(symbol) == "CA" else "USD"
        if self.settings.history_provider in {"auto", "yfinance"}:
            try:
                return self.yahoo_history.candles(symbol, range_key, interval, currency)
            except DataUnavailable:
                if self.settings.history_provider == "yfinance":
                    raise
        if symbol_market(symbol) == "CA":
            raise DataUnavailable("Canadian candles require available optional yfinance history")
        return AlphaVantageCandles(self.alpha_vantage).candles(symbol, range_key, interval)

    def financial_trends(self, symbol: str) -> FinancialTrendsResponse:
        """Quarterly evidence independent of annual research calculations."""
        symbol = normalize_symbol(symbol)
        if self.settings.data_mode == "fixtures":
            return fixture_financial_trends(symbol, self.fixtures.demo["companies"])
        if symbol_market(symbol) == "CA":
            return no_coverage(
                symbol,
                "CA",
                "live",
                "Canadian quarterly fundamentals unavailable; no licensed issuer feed or SEDAR+ scraper is configured.",
            )
        return fetch_sec_financial_trends(symbol, self.sec)

    def earnings(self, symbol: str) -> EarningsResponse:
        """Dated earnings records and scheduled dates; no AI or SEC-date inference."""
        symbol = normalize_symbol(symbol)
        if self.settings.data_mode == "fixtures":
            return fixture_earnings(symbol, self.fixtures.demo["companies"])
        if symbol_market(symbol) == "CA":
            return unavailable(symbol, "CA", "Canadian earnings calendar access is not licensed or verified.")
        return fetch_earnings(symbol, self.finnhub)

    def overview(self) -> list[Stock]:
        return [self.stock(symbol) for symbol in ["SPY", "QQQ"]]

    def news(self, symbol: str | None = None) -> list[NewsItem]:
        if self.settings.data_mode == "fixtures":
            return []
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

    def sec_industry_snapshot(self, year: int) -> dict:
        """Expose SEC industry evidence through the market-data service."""
        return SECIndustryEvidence(self.sec, self.settings).snapshot(year)

    def sec_filing_excerpts(self, year: int) -> dict:
        """Fetch bounded, matched SEC filing text without invoking an AI model."""
        return filing_excerpts(self.sec, self.sec_industry_snapshot(year))
