"""Read-only, evidence-first SEC snapshot for the AI-computing research pilot.

No AI calls, no scraping, no arbitrary user-selected hosts, and no claims
about comprehensive industry coverage. Uses Stocker's existing SEC transport.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from math import isfinite

from app.contracts.industry_sources import sec_filing_source
from app.core.config import Settings
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.sec import SecProvider

PEERS = ("NVDA", "AMD", "INTC", "AVGO", "MU")
METRICS = {
    "research_and_development": ("ResearchAndDevelopmentExpense", "R&D expense"),
    "net_income": ("NetIncomeLoss", "Net income"),
}
FORMS = frozenset({"10-K", "10-Q", "8-K"})
ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
DOCUMENT = re.compile(r"^[A-Za-z0-9_.-]{1,180}$")


def _frame_rows(payload: object, concept: str, year: int, cik_to_symbol: dict[int, str]) -> list[dict]:
    """Retain only peer data with sane units/periods; do not impute absent rows."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise DataUnavailable("SEC XBRL frame has an unexpected structure")
    results: dict[str, dict] = {}
    for row in payload["data"]:
        if not isinstance(row, dict):
            continue
        try:
            cik = int(row["cik"])
            symbol = cik_to_symbol.get(cik)
            value = row["val"]
            start = date.fromisoformat(str(row["start"]))
            end = date.fromisoformat(str(row["end"]))
            if not symbol or isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if not isfinite(value) or not 330 <= (end - start).days <= 390:
                continue
            # Frame assignment is calendar-period based; fiscal end may differ.
            # Do not silently equate it with the company's 2025 fiscal year.
            if abs(end.year - year) > 1:
                continue
            accession = str(row.get("accn", ""))
            results[symbol] = {
                "symbol": symbol,
                "company": str(row.get("entityName") or symbol)[:160],
                "value": value,
                "unit": "USD",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "accession": accession if ACCESSION.fullmatch(accession) else None,
            }
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return sorted(results.values(), key=lambda row: PEERS.index(row["symbol"]))


def _filing_rows(payload: object, symbol: str, cik: int) -> list[dict]:
    if not isinstance(payload, dict):
        raise DataUnavailable("SEC filings have an unexpected structure")
    filings = payload.get("filings", {})
    if not isinstance(filings, dict):
        raise DataUnavailable("SEC filings have an unexpected structure")
    recent = filings.get("recent", {})
    if not isinstance(recent, dict):
        raise DataUnavailable("SEC filings are missing recent submission metadata")
    result = []
    seen_forms = set()
    forms = recent.get("form", [])
    if not isinstance(forms, list):
        raise DataUnavailable("SEC forms have an unexpected structure")
    for index, form in enumerate(forms[:200]):
        if form not in FORMS or form in seen_forms:
            continue
        try:
            accession = recent["accessionNumber"][index]
            document = recent["primaryDocument"][index]
            filed = recent["filingDate"][index]
            date.fromisoformat(filed)
            if not ACCESSION.fullmatch(accession) or not DOCUMENT.fullmatch(document) or ".." in document:
                continue
            seen_forms.add(form)
            result.append(
                {
                    "symbol": symbol,
                    "form": form,
                    "filed": filed,
                    "source_name": "SEC EDGAR submissions",
                    "source_url": (
                        f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                        f"{accession.replace('-', '')}/{document}"
                    ),
                }
            )
            if len(result) == 3:
                break
        except (TypeError, KeyError, IndexError, ValueError):
            continue
    return result


class SECIndustryEvidence:
    """Bounded industry pilot; never accepts raw CIKs or URLs from a browser."""

    def __init__(self, sec: SecProvider, settings: Settings):
        self.sec = sec
        self.settings = settings

    def snapshot(self, year: int, *, industry: str = "ai-computing") -> dict:
        source = sec_filing_source(industry)
        peers = source.peers
        now = datetime.now(UTC)
        if year < 2009 or year >= now.year:
            raise ValueError("Year must be a completed calendar year from 2009 onward")
        result = {
            "industry": industry,
            "year": year,
            "mode": self.settings.data_mode,
            "as_of": now.isoformat(),
            "companies": [],
            "metrics": [],
            "filings": [],
            "gaps": [],
            "coverage": source.limitations,
        }
        if self.settings.data_mode != "live":
            result["gaps"].append(
                "SEC data unavailable in fixture mode; no synthetic industry evidence is created."
            )
            return result

        try:
            headers = self.sec.headers()
            mappings = self.sec.tickers()
        except DataUnavailable as exc:
            result["gaps"].append(str(exc))
            return result

        by_symbol = {row["ticker"].upper(): row for row in mappings}
        cik_to_symbol = {}
        for symbol in peers:
            row = by_symbol.get(symbol)
            if not row:
                result["gaps"].append(f"{symbol}: SEC ticker mapping unavailable.")
                continue
            cik = row["cik_str"]
            if not isinstance(cik, int) or cik <= 0:
                continue
            cik_to_symbol[cik] = symbol
            result["companies"].append({"symbol": symbol, "name": row["title"], "cik": str(cik).zfill(10)})
        if not cik_to_symbol:
            result["gaps"].append("No selected peer identifiers were available from the SEC.")
            return result

        for key, (tag, label) in METRICS.items() if industry == "ai-computing" else ():
            url = f"https://data.sec.gov/api/xbrl/frames/us-gaap/{tag}/USD/CY{year}.json"
            try:
                response = self.sec.http.fetch(url, headers=headers, ttl=86400, interval=0.2)
                rows = _frame_rows(response.data, tag, year, cik_to_symbol)
                result["metrics"].append(
                    {
                        "key": key,
                        "label": label,
                        "concept": f"us-gaap:{tag}",
                        "period": f"CY{year}",
                        "source_name": "SEC EDGAR XBRL Frames",
                        "source_url": url,
                        "fetched_at": response.fetched_at.isoformat(),
                        "cached": response.cached,
                        "rows": rows,
                    }
                )
                if len(rows) < len(cik_to_symbol):
                    missing = [
                        v
                        for v in peers
                        if v in cik_to_symbol.values() and v not in {x["symbol"] for x in rows}
                    ]
                    result["gaps"].append(f"{label}: no comparable frame entry for {', '.join(missing)}.")
            except DataUnavailable as exc:
                result["gaps"].append(f"{label}: {exc}")

        for company in result["companies"]:
            cik = int(company["cik"])
            try:
                response = self.sec.http.fetch(
                    f"https://data.sec.gov/submissions/CIK{cik:010d}.json",
                    headers=headers,
                    ttl=21600,
                    interval=0.2,
                )
                result["filings"].extend(_filing_rows(response.data, company["symbol"], cik))
            except DataUnavailable as exc:
                result["gaps"].append(f"{company['symbol']} filings: {exc}")
        result["filings"] = sorted(result["filings"], key=lambda f: f["filed"], reverse=True)[:15]
        if industry == "semiconductor":
            result["gaps"].append(source.limitations)
        result["gaps"].extend(
            [
                "XBRL Frames can omit peers because their fiscal periods or accounting concepts differ.",
                "An XBRL frame does not establish as-of filing availability; use source filings for historical cutoffs.",
                "The metric tables do not establish supply-chain relationships, market shares, or industry totals.",
                "Filing search here filters recent submissions by form, not full-text document contents.",
            ]
        )
        return result
