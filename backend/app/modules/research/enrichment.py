"""Additive quarterly/TTM and earnings evidence capture for six-stage research runs.

Preserves strict separation between SEC GAAP statements and vendor-reported
adjusted earnings calendars. Missing or incompatible data becomes explicit gaps
without failing the core research workflow or inventing facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.contracts.market import Calculation, Evidence
from app.contracts.stock_research import EarningsResponse, FinancialTrendsResponse
from app.modules.market_data.provenance import evidence_id


@dataclass
class ResearchEnrichment:
    evidence: list[dict] = field(default_factory=list)
    calculations: list[dict] = field(default_factory=list)
    quarterly_summary: dict | None = None
    earnings_summary: dict | None = None
    gaps: list[str] = field(default_factory=list)


def _merge_quarterly(trends: FinancialTrendsResponse, symbol: str, result: ResearchEnrichment) -> None:
    result.gaps.extend(trends.gaps)
    standalone = [p for p in trends.periods if p.period_kind == "standalone_quarter"]
    if not standalone:
        return
    standalone.sort(key=lambda p: p.period_end, reverse=True)
    ttm_period_ids = {
        pid for ttm in trends.ttm.values() if ttm.status == "available" for pid in ttm.input_period_ids
    }
    by_id = {p.period_id: p for p in standalone}
    selected_ids: list[str] = []
    for period in standalone[:4]:
        if period.period_id not in selected_ids:
            selected_ids.append(period.period_id)
    for pid in ttm_period_ids:
        if pid in by_id and pid not in selected_ids:
            selected_ids.append(pid)
    selected = sorted((by_id[pid] for pid in selected_ids), key=lambda p: p.period_end, reverse=True)

    period_metric_refs: dict[tuple[str, str], str] = {}
    quarterly_ev_ids: list[str] = []
    for period in selected:
        published = datetime.fromisoformat(f"{period.filed_on.isoformat()}T00:00:00+00:00")
        period_label = (
            f"{period.period_id} ({period.period_start.isoformat()}..{period.period_end.isoformat()})"
        )
        for metric_name, mv in period.metrics.items():
            if mv.status == "unavailable" or mv.value is None:
                continue
            ev_id = evidence_id("quarterly", symbol, period.period_id, metric_name, mv.value, mv.unit)
            ev = Evidence(
                evidence_id=ev_id,
                symbol=symbol,
                market=trends.market,
                field=f"quarterly_{metric_name}",
                value=mv.value,
                unit=mv.unit,
                currency=trends.currency,
                period=period_label,
                period_start=period.period_start,
                period_end=period.period_end,
                source_name=period.source.name,
                source_url=str(period.source.url),
                published_at=published,
                fetched_at=period.source.fetched_at,
                fixture=period.source.fixture,
                cached=period.source.cached,
                missing_reason=(
                    "Derived standalone quarter from comparable SEC filings."
                    if mv.status == "derived"
                    else None
                ),
            )
            result.evidence.append(ev.model_dump(mode="json"))
            period_metric_refs[(period.period_id, metric_name)] = ev_id
            quarterly_ev_ids.append(ev_id)

    ttm_calc_ids: list[str] = []
    for metric_name, ttm in trends.ttm.items():
        if ttm.status != "available" or ttm.value is None or not ttm.calculation_id:
            continue
        refs = [
            period_metric_refs[(pid, metric_name)]
            for pid in ttm.input_period_ids
            if (pid, metric_name) in period_metric_refs
        ]
        if len(refs) != 4:
            continue
        calc = Calculation(
            calculation_id=ttm.calculation_id,
            metric=f"ttm_{metric_name}",
            value=ttm.value,
            unit=ttm.unit,
            input_evidence_ids=refs,
            inputs={
                "periods": ", ".join(ttm.input_period_ids),
                "currency": trends.currency,
                "basis": "SEC GAAP standalone quarters",
            },
        )
        result.calculations.append(calc.model_dump(mode="json"))
        ttm_calc_ids.append(ttm.calculation_id)

    if quarterly_ev_ids or ttm_calc_ids:
        result.quarterly_summary = {
            "currency": trends.currency,
            "quarters_captured": [p.period_id for p in selected],
            "evidence_ids": quarterly_ev_ids,
            "ttm_calculation_ids": ttm_calc_ids,
            "note": (
                "SEC GAAP standalone quarters and derived TTM where four consecutive quarters exist; "
                "separate from annual SEC facts and vendor adjusted earnings."
            ),
        }


def _merge_earnings(report: EarningsResponse, symbol: str, result: ResearchEnrichment) -> None:
    result.gaps.extend(report.gaps)
    earnings_ev_ids: list[str] = []

    upcoming = report.upcoming
    if upcoming is not None:
        upcoming_period = (
            f"FY{upcoming.fiscal_year}{upcoming.fiscal_quarter}"
            if upcoming.fiscal_year and upcoming.fiscal_quarter
            else upcoming.scheduled_date.isoformat()
        )
        sched_id = evidence_id(
            "earnings", symbol, "upcoming", upcoming.scheduled_date.isoformat(), upcoming.date_status
        )
        sched_ev = Evidence(
            evidence_id=sched_id,
            symbol=symbol,
            market=report.market,
            field="upcoming_earnings",
            value=(
                f"Scheduled {upcoming.date_status} earnings release on "
                f"{upcoming.scheduled_date.isoformat()} ({upcoming.timing})"
            ),
            unit="text",
            currency=None,
            period=upcoming_period,
            source_name=upcoming.source.name,
            source_url=str(upcoming.source.url),
            published_at=upcoming.source.published_at,
            fetched_at=upcoming.source.fetched_at,
            fixture=upcoming.source.fixture,
            cached=upcoming.source.cached,
            missing_reason="Vendor calendar date; release timestamp may be unconfirmed.",
        )
        result.evidence.append(sched_ev.model_dump(mode="json"))
        earnings_ev_ids.append(sched_id)

        if upcoming.eps_estimate is not None:
            est_id = evidence_id(
                "earnings", symbol, "upcoming_eps_estimate", upcoming_period, upcoming.eps_estimate
            )
            est_ev = Evidence(
                evidence_id=est_id,
                symbol=symbol,
                market=report.market,
                field="vendor_upcoming_eps_estimate",
                value=upcoming.eps_estimate,
                unit=f"{report.currency}/shares",
                currency=report.currency,
                period=upcoming_period,
                source_name=upcoming.source.name,
                source_url=str(upcoming.source.url),
                published_at=upcoming.source.published_at,
                fetched_at=upcoming.source.fetched_at,
                fixture=upcoming.source.fixture,
                cached=upcoming.source.cached,
                missing_reason=(
                    f"Vendor calendar estimate ({upcoming.eps_estimate_basis or 'unlabeled'}); "
                    "not licensed analyst consensus."
                ),
            )
            result.evidence.append(est_ev.model_dump(mode="json"))
            earnings_ev_ids.append(est_id)

    recent_history = sorted(report.history, key=lambda r: r.reported_on, reverse=True)[:4]
    for record in recent_history:
        period_label = f"FY{record.fiscal_year}{record.fiscal_quarter}"
        published = datetime.fromisoformat(f"{record.reported_on.isoformat()}T00:00:00+00:00")
        entries = [
            (
                "vendor_earnings_actual_eps",
                record.actual_eps,
                f"{report.currency}/shares",
                report.currency,
                f"Vendor reported EPS ({record.actual_basis}); do not mix with SEC GAAP diluted EPS.",
            ),
            (
                "vendor_earnings_estimate_eps",
                record.estimate_eps,
                f"{report.currency}/shares",
                report.currency,
                f"Vendor calendar estimate ({record.estimate_basis}); not licensed analyst consensus.",
            ),
            (
                "vendor_earnings_eps_surprise_pct",
                record.surprise_pct,
                "%",
                None,
                f"Vendor EPS surprise ({record.actual_basis}); not licensed analyst consensus.",
            ),
        ]
        for field_name, value, unit, currency, note in entries:
            if value is None:
                continue
            ev_id = evidence_id("earnings", symbol, record.event_id, field_name, value, unit)
            ev = Evidence(
                evidence_id=ev_id,
                symbol=symbol,
                market=report.market,
                field=field_name,
                value=value,
                unit=unit,
                currency=currency,
                period=period_label,
                source_name=record.source.name,
                source_url=str(record.source.url),
                published_at=published,
                fetched_at=record.source.fetched_at,
                fixture=record.source.fixture,
                cached=record.source.cached,
                missing_reason=note,
            )
            result.evidence.append(ev.model_dump(mode="json"))
            earnings_ev_ids.append(ev_id)

    if earnings_ev_ids:
        result.earnings_summary = {
            "currency": report.currency,
            "upcoming_date": upcoming.scheduled_date.isoformat() if upcoming else None,
            "history_periods": [f"FY{r.fiscal_year}{r.fiscal_quarter}" for r in recent_history],
            "evidence_ids": earnings_ev_ids,
            "note": (
                "Vendor earnings calendar records (typically adjusted/non-GAAP); "
                "not licensed analyst consensus and separate from SEC GAAP diluted EPS."
            ),
        }


def capture_supplementary_research_inputs(data, symbol: str, run_mode: str) -> ResearchEnrichment:
    """Best-effort capture of quarterly/TTM trends and earnings records for research runs."""
    result = ResearchEnrichment()

    if hasattr(data, "financial_trends"):
        try:
            trends = data.financial_trends(symbol)
            if isinstance(trends, FinancialTrendsResponse):
                if trends.mode != run_mode:
                    result.gaps.append("Quarterly financial trends mode mismatch; excluded from run.")
                else:
                    _merge_quarterly(trends, symbol, result)
        except Exception:
            result.gaps.append("Quarterly financial trends unavailable during research capture.")

    if hasattr(data, "earnings"):
        try:
            report = data.earnings(symbol)
            if isinstance(report, EarningsResponse):
                if report.mode != run_mode:
                    result.gaps.append("Earnings calendar mode mismatch; excluded from run.")
                else:
                    _merge_earnings(report, symbol, result)
        except Exception:
            result.gaps.append("Earnings preview and history unavailable during research capture.")

    return result
