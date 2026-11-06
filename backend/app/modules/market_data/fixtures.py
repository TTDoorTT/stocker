import builtins
from datetime import UTC, date, datetime, timedelta

from app.contracts.market import Evidence, FinancialFact, PriceBar, Quote, Stock
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.provenance import evidence_id

FIXTURE_SOURCE = "fixture:market.json (synthetic test data)"


def _timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def now() -> datetime:
    return datetime.now(UTC)


class FixtureData:
    def __init__(self, demo: dict):
        self.demo = demo

    def stock(self, symbol):
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

    def history(self, symbol: str) -> list[PriceBar]:
        stock = self.stock(symbol)

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

    def search(self, q: str) -> list[dict[str, str]]:
        return [
            {"symbol": symbol, "name": data["name"]}
            for symbol, data in self.demo["companies"].items()
            if q in symbol or q in data["name"].upper()
        ][:20]
