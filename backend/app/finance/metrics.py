"""Deterministic calculations. Inputs retain evidence, fiscal periods, units and currencies."""

import hashlib
import json
from datetime import date
from math import isfinite

from app.contracts.market import Calculation, FinancialFact, Stock


def percentage_change(current: float, previous: float) -> float | None:
    if not all(isfinite(v) for v in [current, previous]) or previous <= 0:
        return None
    result = (current / previous - 1) * 100
    return result if isfinite(result) else None


def profit_margin(profit: float, revenue: float) -> float | None:
    if not all(isfinite(v) for v in [profit, revenue]) or revenue <= 0:
        return None
    result = profit / revenue * 100
    return result if isfinite(result) else None


def price_earnings(price: float, eps: float) -> float | None:
    if not all(isfinite(v) for v in [price, eps]) or price <= 0 or eps <= 0:
        return None
    result = price / eps
    return result if isfinite(result) else None


def unrealized_pnl(shares: float, average_cost: float, price: float | None) -> float | None:
    if price is None or not all(isfinite(v) for v in [shares, average_cost, price]):
        return None
    if shares < 0 or average_cost < 0 or price <= 0:
        return None
    result = shares * (price - average_cost)
    return result if isfinite(result) else None


def comparable(a: FinancialFact, b: FinancialFact, *, same_period=True) -> bool:
    if a.currency != b.currency or a.unit != b.unit:
        return False
    if not a.period_start or not b.period_start or not a.period_end or not b.period_end:
        return False
    duration_a = (a.period_end - a.period_start).days
    duration_b = (b.period_end - b.period_start).days
    if abs(duration_a - duration_b) > 8:
        return False
    if same_period:
        return a.period_start == b.period_start and a.period_end == b.period_end
    return 350 <= (a.period_end - b.period_end).days <= 380


def _calculation(metric, value, unit, refs, inputs, reason=None):
    payload = json.dumps([metric, refs, inputs], sort_keys=True, default=str)
    return Calculation(
        calculation_id="calc-" + hashlib.sha256(payload.encode()).hexdigest()[:16],
        metric=metric,
        value=value,
        unit=unit,
        input_evidence_ids=refs,
        inputs=inputs,
        reason=reason,
    )


def build_calculations(stock: Stock) -> list[Calculation]:
    result = []
    by_field = {}
    for fact in stock.facts:
        if isinstance(fact.value, (float, int)):
            by_field.setdefault(fact.field, []).append(fact)
    for facts in by_field.values():
        facts.sort(key=lambda f: f.period_end or date.min, reverse=True)
    for field, metric in [("revenue", "revenue_yoy"), ("eps", "eps_growth")]:
        facts = by_field.get(field, [])
        if len(facts) >= 2:
            current, previous = facts[:2]
            valid = comparable(current, previous, same_period=False)
            value = percentage_change(current.value, previous.value) if valid else None
            result.append(
                _calculation(
                    metric,
                    value,
                    "%",
                    [current.evidence_id, previous.evidence_id],
                    {
                        "current": current.value,
                        "previous": previous.value,
                        "current_period": current.period,
                        "previous_period": previous.period,
                        "currency": current.currency,
                    },
                    None
                    if value is not None
                    else "Incomparable fiscal periods/currency or nonpositive denominator",
                )
            )
    revenues, profits = by_field.get("revenue", []), by_field.get("net_income", [])
    if revenues and profits:
        revenue, profit = revenues[0], profits[0]
        valid = comparable(revenue, profit)
        value = profit_margin(profit.value, revenue.value) if valid else None
        result.append(
            _calculation(
                "profit_margin",
                value,
                "%",
                [profit.evidence_id, revenue.evidence_id],
                {
                    "net_income": profit.value,
                    "revenue": revenue.value,
                    "period": revenue.period,
                    "currency": revenue.currency,
                },
                None if value is not None else "Period/unit/currency mismatch",
            )
        )
    cashflows, capexes = by_field.get("cashflow", []), by_field.get("capex", [])
    if cashflows and capexes:
        ocf, capex = cashflows[0], capexes[0]
        valid = comparable(ocf, capex) and capex.value >= 0
        fcf_value = (ocf.value - capex.value) if valid and isfinite(ocf.value - capex.value) else None
        result.append(
            _calculation(
                "free_cash_flow",
                fcf_value,
                ocf.unit,
                [ocf.evidence_id, capex.evidence_id],
                {
                    "operating_cash_flow": ocf.value,
                    "capex": capex.value,
                    "period": ocf.period,
                    "currency": ocf.currency,
                },
                None if fcf_value is not None else "Period/unit/currency mismatch or invalid CapEx",
            )
        )
    curr_assets, curr_liab = by_field.get("current_assets", []), by_field.get("current_liabilities", [])
    if curr_assets and curr_liab:
        ca, cl = curr_assets[0], curr_liab[0]
        same_snapshot = (
            ca.period_end is not None
            and ca.period_end == cl.period_end
            and ca.currency == cl.currency
            and ca.unit == cl.unit
            and cl.value > 0
        )
        cr_value = (ca.value / cl.value) if same_snapshot and isfinite(ca.value / cl.value) else None
        result.append(
            _calculation(
                "current_ratio",
                cr_value,
                "ratio",
                [ca.evidence_id, cl.evidence_id],
                {
                    "current_assets": ca.value,
                    "current_liabilities": cl.value,
                    "period": ca.period,
                    "currency": ca.currency,
                },
                None
                if cr_value is not None
                else "Snapshot date/currency mismatch or nonpositive liabilities",
            )
        )
    debts, equities = by_field.get("long_term_debt", []), by_field.get("stockholders_equity", [])
    if debts and equities:
        debt, equity = debts[0], equities[0]
        same_snapshot = (
            debt.period_end is not None
            and debt.period_end == equity.period_end
            and debt.currency == equity.currency
            and debt.unit == equity.unit
            and equity.value > 0
        )
        dte_value = (
            (debt.value / equity.value) if same_snapshot and isfinite(debt.value / equity.value) else None
        )
        result.append(
            _calculation(
                "debt_to_equity",
                dte_value,
                "ratio",
                [debt.evidence_id, equity.evidence_id],
                {
                    "long_term_debt": debt.value,
                    "stockholders_equity": equity.value,
                    "period": debt.period,
                    "currency": debt.currency,
                },
                None if dte_value is not None else "Snapshot date/currency mismatch or nonpositive equity",
            )
        )
    eps_facts = by_field.get("eps", [])
    if stock.quote and eps_facts:
        eps, quote = eps_facts[0], stock.quote
        compatible = eps.currency == quote.currency and eps.unit == f"{quote.currency}/shares"
        value = price_earnings(quote.price, eps.value) if compatible else None
        result.append(
            _calculation(
                "pe_annual",
                value,
                "ratio",
                [quote.evidence_id, eps.evidence_id],
                {
                    "price": quote.price,
                    "annual_eps": eps.value,
                    "eps_period": eps.period,
                    "currency": quote.currency,
                },
                None if value is not None else "EPS nonpositive or incompatible currency/unit",
            )
        )
    if stock.quote and stock.quote.previous_close:
        quote = stock.quote
        value = percentage_change(quote.price, quote.previous_close)
        previous = next((e for e in stock.evidence if e.field == "previous_close"), None)
        refs = [quote.evidence_id] + ([previous.evidence_id] if previous else [])
        result.append(
            _calculation(
                "daily_return",
                value,
                "%",
                refs,
                {"price": quote.price, "previous_close": quote.previous_close},
                None if value is not None else "Previous close is not meaningful",
            )
        )
    return result
