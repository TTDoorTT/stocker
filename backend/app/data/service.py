import builtins
import hashlib
import json
import re
from datetime import UTC, date, datetime, timedelta
from math import isfinite

from app.core.config import ROOT, Settings
from app.data.history import YFinanceHistory
from app.data.http import DataUnavailable, ProviderHTTP
from app.models.market import Evidence, FinancialFact, NewsItem, PriceBar, Quote, Stock

DEMO_PATH = ROOT / "fixtures" / "market.json"
FIXTURE_SOURCE = "fixture:market.json (synthetic test data)"


def now() -> datetime:
    return datetime.now(UTC)


def normalize_symbol(symbol: str, market: str | None = None) -> str:
    symbol = symbol.strip().upper()
    prefix = None
    if symbol.startswith(("US:", "CA:")):
        prefix, symbol = symbol.split(":", 1)
    canadian = bool(re.fullmatch(r"[A-Z]{1,5}(?:[.-][A-Z])?\.(?:TO|V)", symbol))
    us = bool(re.fullmatch(r"[A-Z]{1,5}(?:[.-][A-Z])?", symbol)) and not canadian
    actual = "CA" if canadian else "US"
    if not (canadian or us) or (prefix and prefix != actual) or (market is not None and market != actual):
        raise ValueError("Use a U.S. ticker or explicit Canadian .TO (TSX) / .V (TSXV) listing")
    return symbol


def symbol_market(symbol: str) -> str:
    return "CA" if normalize_symbol(symbol).endswith((".TO", ".V")) else "US"


def evidence_id(*parts) -> str:
    return "ev-" + hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]


def _timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_sec_facts(symbol: str, data: dict, fetched_at: datetime, *, cached=False) -> list[FinancialFact]:
    """Annual 10-K contexts only; never combine YTD or quarterly values."""
    concepts = {
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
        "net_income": ["NetIncomeLoss"],
        "eps": ["EarningsPerShareDiluted", "EarningsPerShareBasic"],
        "cashflow": ["NetCashProvidedByUsedInOperatingActivities"],
        "long_term_debt": ["LongTermDebt"],
        "long_term_debt_current": ["LongTermDebtCurrent"],
        "long_term_debt_noncurrent": ["LongTermDebtNoncurrent"],
    }
    facts = []
    if not isinstance(data, dict) or not isinstance(data.get("facts", {}), dict):
        return []
    taxonomy = data.get("facts", {}).get("us-gaap", {})
    if not isinstance(taxonomy, dict):
        return []
    for field, tags in concepts.items():
        # Prefer a reported long-term-debt concept; components remain distinct if it is unavailable.
        if field in {"long_term_debt_current", "long_term_debt_noncurrent"} and any(
            fact.field == "long_term_debt" for fact in facts
        ):
            continue
        is_debt = field.startswith("long_term_debt")
        for tag in tags:
            concept = taxonomy.get(tag, {})
            units = concept.get("units", {}) if isinstance(concept, dict) else {}
            if not isinstance(units, dict):
                continue
            desired_unit = "USD/shares" if field == "eps" else "USD"
            candidates = units.get(desired_unit, [])
            if not isinstance(candidates, list):
                continue
            by_end = {}
            for row in candidates:
                if not isinstance(row, dict):
                    continue
                try:
                    end, filed = date.fromisoformat(row["end"]), date.fromisoformat(row["filed"])
                    start = date.fromisoformat(row["start"]) if row.get("start") else None
                    if row.get("form") != "10-K" or filed > fetched_at.date() or end > fetched_at.date():
                        continue
                    if not is_debt and (not start or not 350 <= (end - start).days <= 380):
                        continue
                    if is_debt and start:
                        continue
                    value = float(row["val"])
                    if isinstance(row["val"], bool) or not isfinite(value):
                        continue
                    # Prefer the latest filed restatement for each original period.
                    if end not in by_end or row["filed"] > by_end[end]["filed"]:
                        by_end[end] = dict(row, val=value)
                except (ValueError, KeyError, TypeError):
                    continue
            if by_end:
                for end, row in sorted(by_end.items(), reverse=True)[:3]:
                    accession = row.get("accn", "")
                    cik = str(data.get("cik", "")).lstrip("0")
                    url = (
                        f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/"
                        if accession and cik
                        else "https://data.sec.gov/"
                    )
                    try:
                        facts.append(
                            FinancialFact(
                                evidence_id=evidence_id(symbol, field, tag, row.get("start"), end, accession),
                                symbol=symbol,
                                field=field,
                                value=row["val"],
                                unit=desired_unit,
                                period=f"{row.get('start', end)}..{end}",
                                period_start=row.get("start"),
                                period_end=end,
                                source_name=f"SEC EDGAR ({tag})",
                                source_url=url,
                                published_at=f"{row['filed']}T00:00:00Z",
                                fetched_at=fetched_at,
                                cached=cached,
                                statement="cashflow"
                                if field == "cashflow"
                                else "balance"
                                if is_debt
                                else "income",
                                fiscal_year=None,
                                filing_fiscal_year=row.get("fy"),
                                fiscal_period="FY",
                            )
                        )
                    except (TypeError, ValueError):
                        continue
                break
    return facts


class DataService:
    def __init__(self, settings: Settings, http: ProviderHTTP | None = None):
        self.settings = settings
        self.http = http or ProviderHTTP()
        self.demo = json.loads(DEMO_PATH.read_text())
        self.yahoo_history = YFinanceHistory()

    def _sec_headers(self):
        ua = self.settings.sec_user_agent
        if not ua or not re.search(r"[^\s@]+@[^\s@]+\.[^\s@]+", ua):
            raise DataUnavailable("SEC_USER_AGENT must contain a genuine descriptive name and contact email")
        return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}

    def _tickers(self):
        data = self.http.json(
            "https://www.sec.gov/files/company_tickers.json",
            headers=self._sec_headers(),
            ttl=86400,
            interval=0.2,
        )
        if not isinstance(data, dict):
            raise DataUnavailable("SEC ticker mapping returned an invalid object")
        return [
            row
            for row in data.values()
            if isinstance(row, dict)
            and isinstance(row.get("ticker"), str)
            and isinstance(row.get("title"), str)
            and isinstance(row.get("cik_str"), int)
        ]

    def search(self, q: str) -> list[dict]:
        q = q.strip().upper()
        if not q:
            return []
        if self.settings.data_mode == "fixtures":
            return [
                {"symbol": s, "name": d["name"]}
                for s, d in self.demo["companies"].items()
                if q in s or q in d["name"].upper()
            ][:20]
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
                for r in self._tickers()
                if q in r["ticker"].upper() or q in r["title"].upper()
            ][:20]
        except DataUnavailable:
            if not self.settings.finnhub_api_key:
                raise
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

    def _fixture_stock(self, symbol):
        data = self.demo["companies"].get(symbol)
        if not data:
            raise DataUnavailable("No fixture exists for this symbol; use AAPL, MSFT, NVDA, SPY or QQQ")
        timestamp = _timestamp(self.demo["as_of"])
        fetched = now()
        evidence = []
        for field in ["price", "previous_close"]:
            evidence.append(
                Evidence(
                    evidence_id=evidence_id("fixture", symbol, field),
                    symbol=symbol,
                    field=field,
                    value=data[field],
                    unit="USD",
                    period="synthetic quote",
                    source_name="Synthetic offline fixture — not market data",
                    source_url=FIXTURE_SOURCE,
                    published_at=timestamp,
                    fetched_at=fetched,
                    fixture=True,
                    stale=True,
                )
            )
        identity = Evidence(
            evidence_id=evidence_id("fixture", symbol, "identity"),
            symbol=symbol,
            field="company_name",
            value=data["name"],
            unit="text",
            currency=None,
            period="synthetic identity",
            source_name="Synthetic offline fixture",
            source_url=FIXTURE_SOURCE,
            published_at=timestamp,
            fetched_at=fetched,
            fixture=True,
        )
        evidence.append(identity)
        facts = []
        for field in ["revenue", "net_income", "eps", "cashflow", "debt"]:
            for index, value in enumerate(data.get(field, [])):
                year = 2023 + index
                end = date.fromisoformat(f"{year}-{data['fiscal_end']}")
                start = end.replace(year=year - 1) + timedelta(days=1)
                facts.append(
                    FinancialFact(
                        evidence_id=evidence_id("fixture", symbol, field, year),
                        symbol=symbol,
                        field=field,
                        value=value,
                        unit="USD/shares" if field == "eps" else "USD",
                        period=f"FY{year} (synthetic)",
                        period_start=start if field != "debt" else None,
                        period_end=end,
                        source_name="Synthetic offline fixture — invented financials",
                        source_url=FIXTURE_SOURCE,
                        published_at=timestamp,
                        fetched_at=fetched,
                        fixture=True,
                        fiscal_year=year,
                        statement="cashflow"
                        if field == "cashflow"
                        else "balance"
                        if field == "debt"
                        else "income",
                    )
                )
        return Stock(
            symbol=symbol,
            name=data["name"],
            mode="fixtures",
            profile="Synthetic demonstration context. No business assertions have been retrieved from a live source.",
            quote=Quote(
                price=data["price"],
                previous_close=data["previous_close"],
                timestamp=timestamp,
                source_name="Synthetic offline fixture",
                source_url=FIXTURE_SOURCE,
                stale=True,
                delayed=True,
                evidence_id=evidence[0].evidence_id,
                fixture=True,
                fetched_at=fetched,
            ),
            facts=facts,
            evidence=evidence + facts,
            gaps=[
                "Synthetic fixture values; not financial facts.",
                "Licensed analyst consensus is unavailable.",
            ],
        )

    def stock(self, symbol: str) -> Stock:
        symbol = normalize_symbol(symbol)
        if self.settings.data_mode == "fixtures":
            return self._fixture_stock(symbol)
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
        try:
            mapping = next((r for r in self._tickers() if r["ticker"].upper() == symbol), None)
            if not mapping:
                stock.gaps.append("SEC company mapping not found; ETFs may not have companyfacts.")
            else:
                cik = str(mapping["cik_str"]).zfill(10)
                url = f"https://data.sec.gov/submissions/CIK{cik}.json"
                response = self.http.fetch(url, headers=self._sec_headers(), ttl=21600, interval=0.2)
                submissions, fetched = response.data, response.fetched_at
                if not isinstance(submissions, dict):
                    raise DataUnavailable("SEC submissions returned an invalid object")
                name = submissions.get("name", mapping["title"])
                if not isinstance(name, str) or not name.strip():
                    raise DataUnavailable("SEC company name is unavailable")
                stock.name = name
                sic = submissions.get("sicDescription")
                if not isinstance(sic, str) or not sic:
                    sic = "Industry unavailable"
                stock.profile = f"{stock.name}. SEC industry classification: {sic}."
                stock.evidence.append(
                    Evidence(
                        evidence_id=evidence_id(symbol, "identity", fetched.date()),
                        symbol=symbol,
                        field="company_name",
                        value=stock.name,
                        unit="text",
                        currency=None,
                        period="current SEC submissions",
                        source_name="SEC EDGAR submissions",
                        source_url=url,
                        published_at=None,
                        fetched_at=fetched,
                        cached=response.cached,
                        missing_reason="Identity publication timestamp is unavailable in SEC submissions.",
                    )
                )
                if isinstance(submissions.get("sicDescription"), str) and submissions["sicDescription"]:
                    stock.evidence.append(
                        Evidence(
                            evidence_id=evidence_id(symbol, "industry_classification", fetched.date()),
                            symbol=symbol,
                            field="industry_classification",
                            value=submissions["sicDescription"],
                            unit="text",
                            currency=None,
                            period="current SEC submissions",
                            source_name="SEC EDGAR submissions",
                            source_url=url,
                            published_at=None,
                            fetched_at=fetched,
                            cached=response.cached,
                            missing_reason="Industry-classification publication timestamp is unavailable.",
                        )
                    )
                stock.gaps.append(
                    "SEC identity publication timestamp is unavailable; retrieval time is separate."
                )
                facts_response = self.http.fetch(
                    f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                    headers=self._sec_headers(),
                    ttl=21600,
                    interval=0.2,
                )
                stock.facts = parse_sec_facts(
                    symbol, facts_response.data, facts_response.fetched_at, cached=facts_response.cached
                )
                stock.evidence.extend(stock.facts)
                if stock.facts:
                    stock.gaps.append(
                        "SEC companyfacts fy identifies the filing fiscal year; fact fiscal-year labels "
                        "are unavailable, so exact start/end dates are used."
                    )
                if any(fact.field.startswith("long_term_debt") for fact in stock.facts):
                    stock.gaps.append(
                        "Long-term debt follows the named SEC concept; current/noncurrent components "
                        "are not summed and no total-debt coverage is claimed."
                    )
                stock.news = self._filings(symbol, cik, submissions, fetched, cached=response.cached)
                if not stock.facts:
                    stock.gaps.append("No comparable annual SEC facts available.")
        except (DataUnavailable, KeyError, TypeError, ValueError, AttributeError):
            stock.gaps.append(
                "SEC financials unavailable; verify SEC_USER_AGENT, network and ticker mapping."
            )
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
        stock.gaps += [
            "Licensed analyst consensus unavailable.",
            "Annual SEC metrics are not trailing twelve-month metrics.",
        ]
        return stock

    def _filings(self, symbol, cik, submissions, fetched, *, cached=False):
        recent = submissions.get("filings", {}).get("recent", {})
        output = []
        for i, form in enumerate(recent.get("form", [])[:50]):
            if form not in {"10-K", "10-Q", "8-K"}:
                continue
            try:
                acc = recent["accessionNumber"][i].replace("-", "")
                document = recent["primaryDocument"][i]
                if "/" in document or ".." in document:
                    continue
                output.append(
                    NewsItem(
                        headline=f"{symbol} SEC {form} filing",
                        source_name="SEC EDGAR",
                        source_url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{document}",
                        published_at=f"{recent['filingDate'][i]}T00:00:00Z",
                        fetched_at=fetched,
                        cached=cached,
                        symbols=[symbol],
                    )
                )
            except (KeyError, IndexError, ValueError):
                continue
        return output[:10]

    def history(self, symbol: str, range: str = "1y") -> list[PriceBar]:
        symbol = normalize_symbol(symbol)
        if range not in {"1m", "3m", "1y"}:
            raise ValueError(
                "Supported ranges: 1m, 3m, 1y; live compact history is limited to 100 observations"
            )
        if self.settings.data_mode == "fixtures":
            stock = self._fixture_stock(symbol)
            return [
                PriceBar(
                    date=date(2025, 1, 6) + timedelta(days=i),
                    close=stock.quote.price * (0.95 + i * 0.005),
                    source_name="Synthetic offline fixture — invented price bars",
                    source_url=FIXTURE_SOURCE,
                    fetched_at=now(),
                    fixture=True,
                )
                for i in builtins.range(10)
            ]
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
        return list({(item.headline, item.source_url): item for item in output}.values())[:60]
