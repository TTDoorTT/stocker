"""Pure, deterministic quarterly metric arithmetic; no provider or model calls."""

import hashlib

from app.contracts.stock_research import FinancialPeriod, TTMValue

ADDITIVE_METRICS = ("revenue", "net_income", "gross_profit", "operating_cash_flow")
ALL_METRICS = (*ADDITIVE_METRICS, "diluted_eps")
UNITS = {
    "revenue": "USD",
    "net_income": "USD",
    "gross_profit": "USD",
    "operating_cash_flow": "USD",
    "diluted_eps": "USD/shares",
}


def calculation_id(operation: str, references: list[str]) -> str:
    """Stable ID identifies exact inputs and operation, not any mutable display position."""
    blob = "\x1f".join([operation, *references])
    return "calc-" + hashlib.sha256(blob.encode()).hexdigest()[:20]


def trailing_twelve_months(periods: list[FinancialPeriod]) -> dict[str, TTMValue]:
    """Only sum the four *latest*, consecutive, standalone fiscal quarters.

    The latest period is never silently skipped to manufacture an outdated TTM.
    EPS is deliberately excluded: summing separately weighted quarterly EPS is
    not an audited trailing diluted EPS figure.
    """
    latest = sorted(
        (p for p in periods if p.period_kind == "standalone_quarter" and p.fiscal_quarter),
        key=lambda p: (p.fiscal_year, int(p.fiscal_quarter[1])),
        reverse=True,
    )[:4]
    result: dict[str, TTMValue] = {}
    for metric in ALL_METRICS:
        unit = UNITS[metric]
        reason = None
        if metric == "diluted_eps":
            reason = (
                "TTM diluted EPS is not the simple sum of four differently weighted quarterly EPS values."
            )
        elif len(latest) != 4:
            reason = "Four recent standalone fiscal quarters are required."
        else:
            numbers = [p.fiscal_year * 4 + int(p.fiscal_quarter[1]) - 1 for p in latest]
            if any(numbers[i] - numbers[i + 1] != 1 for i in range(3)):
                reason = "The four most recent fiscal quarters are not consecutive."
            elif any(
                (observation := p.metrics.get(metric)) is None
                or observation.value is None
                or observation.unit != unit
                for p in latest
            ):
                reason = f"One or more of the latest four quarters lack comparable {metric} observations."
        if reason:
            result[metric] = TTMValue(status="unavailable", value=None, unit=unit, reason=reason)
        else:
            refs = [p.period_id for p in latest]
            result[metric] = TTMValue(
                status="available",
                value=sum(p.metrics[metric].value for p in latest),
                unit=unit,
                input_period_ids=refs,
                calculation_id=calculation_id("ttm:" + metric, refs),
            )
    return result
