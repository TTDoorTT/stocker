import re
from datetime import date, datetime
from math import isfinite

from app.contracts.market import Evidence, FinancialFact, NewsItem, Stock
from app.core.config import Settings
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.provenance import evidence_id
from app.modules.market_data.providers.http import ProviderHTTP


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


class SecProvider:
    def __init__(self, settings: Settings, http: ProviderHTTP):
        self.settings = settings
        self.http = http

    def headers(self):
        ua = self.settings.sec_user_agent
        if not ua or not re.search(r"[^\s@]+@[^\s@]+\.[^\s@]+", ua):
            raise DataUnavailable("SEC_USER_AGENT must contain a genuine descriptive name and contact email")
        return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}

    def tickers(self):
        data = self.http.json(
            "https://www.sec.gov/files/company_tickers.json",
            headers=self.headers(),
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

    def populate(self, stock: Stock, symbol: str) -> None:
        try:
            mapping = next((r for r in self.tickers() if r["ticker"].upper() == symbol), None)
            if not mapping:
                stock.gaps.append("SEC company mapping not found; ETFs may not have companyfacts.")
            else:
                cik = str(mapping["cik_str"]).zfill(10)
                url = f"https://data.sec.gov/submissions/CIK{cik}.json"
                response = self.http.fetch(url, headers=self.headers(), ttl=21600, interval=0.2)
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
                    headers=self.headers(),
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
                stock.news = self.filings(symbol, cik, submissions, fetched, cached=response.cached)
                if not stock.facts:
                    stock.gaps.append("No comparable annual SEC facts available.")
        except (DataUnavailable, KeyError, TypeError, ValueError, AttributeError):
            stock.gaps.append(
                "SEC financials unavailable; verify SEC_USER_AGENT, network and ticker mapping."
            )

    def filings(self, symbol, cik, submissions, fetched, *, cached=False):
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
