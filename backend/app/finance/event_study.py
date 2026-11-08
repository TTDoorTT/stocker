"""Deterministic post-earnings-date drift versus SPY (not initial earnings reaction).

Day zero is the FIRST common trading session STRICTLY AFTER the vendor
reported earnings date. All paths are measured from that session's adjusted
close, so the earnings-day jump is deliberately excluded. An event's date is
not treated as a verified first-public earnings release timestamp.
"""

from __future__ import annotations

from datetime import date
from statistics import mean, median

from app.contracts.stock_research import (
    CandleSeries,
    EventsResponse,
    EventStudyResponse,
    EventStudySummary,
    EventWindow,
)

PRE_DAYS = 5
POST_DAYS = 20
MIN_SAMPLE = 8


def empty_study(events: EventsResponse, reason: str) -> EventStudyResponse:
    return EventStudyResponse(
        symbol=events.symbol,
        market=events.market,
        currency=events.currency,
        mode=events.mode,
        benchmark_symbol="SPY",
        eligible_event_count=0,
        events=[
            EventWindow(event_id=event.event_id, eligible=False, exclusion_reason=reason)
            for event in events.events
        ],
        summary=None,
        sources=events.sources,
        gaps=[*events.gaps, reason],
    )


def _close_map(series: CandleSeries) -> dict[date, float]:
    # Never substitute the provider's unadjusted OHLC close for adjusted close.
    return {
        bar.date: bar.adjusted_close
        for bar in series.bars
        if bar.adjusted_close is not None and bar.adjusted_close > 0
    }


def _path(
    stock: dict[date, float], spy: dict[date, float], dates: list[date], index: int
) -> dict[str, float] | None:
    base = dates[index]
    stock_base, spy_base = stock.get(base), spy.get(base)
    if stock_base is None or spy_base is None:
        return None
    output: dict[str, float] = {}
    for day in range(-PRE_DAYS, POST_DAYS + 1):
        d = dates[index + day]
        s, b = stock.get(d), spy.get(d)
        if s is None or b is None:
            return None
        # Both legs are compounded close-to-close returns from same day-zero.
        output[str(day)] = 100 * ((s / stock_base - 1) - (b / spy_base - 1))
    return output


def calculate_event_study(
    events: EventsResponse,
    stock: CandleSeries,
    benchmark: CandleSeries,
    *,
    as_of: date,
) -> EventStudyResponse:
    """Produce one result per source event and summary only for >=8 eligible events.

    The benchmark's daily sessions define the calendar. Missing even one stock
    trading session disqualifies that event rather than compressing its window.
    Duplicate and overlapping 26-session windows are not double counted.
    """
    if (
        events.market != "US"
        or stock.symbol != events.symbol
        or benchmark.symbol != "SPY"
        or events.mode != stock.mode
        or stock.mode != benchmark.mode
        or stock.interval != "1d"
        or benchmark.interval != "1d"
        or stock.currency != "USD"
        or benchmark.currency != "USD"
    ):
        raise ValueError("Incompatible listing, mode, currency, benchmark, or candle interval")

    stock_close = _close_map(stock)
    spy_close = _close_map(benchmark)
    # Reference the SPY market calendar, excluding future sessions.
    spy_dates = sorted(bar.date for bar in benchmark.bars if bar.date <= as_of)
    spy_dates = sorted(set(spy_dates))
    rows: list[EventWindow] = []
    used_ranges: list[tuple[int, int]] = []
    for event in sorted(events.events, key=lambda e: (e.event_date, e.event_id)):
        reason = None
        index = next((i for i, d in enumerate(spy_dates) if d > event.event_date), None)
        if event.event_date >= as_of:
            reason = "Event is not in the completed historical period."
        elif index is None:
            reason = "No post-date benchmark session."
        elif index < PRE_DAYS or index + POST_DAYS >= len(spy_dates):
            reason = "Incomplete -5/+20 trading-session window."
        elif any(lo <= index + POST_DAYS and index - PRE_DAYS <= hi for lo, hi in used_ranges):
            reason = "Overlapping event window; excluded from aggregate."

        values = None
        if reason is None:
            values = _path(stock_close, spy_close, spy_dates, index)
            if values is None:
                reason = "Adjusted close or a full stock/benchmark trading session is missing."
        if reason is not None:
            rows.append(EventWindow(event_id=event.event_id, eligible=False, exclusion_reason=reason))
            continue
        used_ranges.append((index - PRE_DAYS, index + POST_DAYS))
        rows.append(
            EventWindow(
                event_id=event.event_id,
                day_zero=spy_dates[index],
                eligible=True,
                excess_returns=values,
            )
        )

    eligible = [row for row in rows if row.eligible]
    summary = None
    if len(eligible) >= MIN_SAMPLE:
        summary = [
            EventStudySummary(
                horizon=f"+{horizon}",
                eligible_n=len(eligible),
                mean_excess_return=mean(row.excess_returns[str(horizon)] for row in eligible),
                median_excess_return=median(row.excess_returns[str(horizon)] for row in eligible),
                positive_share=sum(row.excess_returns[str(horizon)] > 0 for row in eligible) / len(eligible),
            )
            for horizon in (1, 5, 20)
        ]
    return EventStudyResponse(
        symbol=events.symbol,
        market="US",
        currency="USD",
        mode=events.mode,
        benchmark_symbol="SPY",
        eligible_event_count=len(eligible),
        events=rows,
        summary=summary,
        sources=[*events.sources, stock.source, benchmark.source],
        gaps=[
            *events.gaps,
            "This measures post-date drift, NOT the immediate earnings reaction or causal impact.",
            "Day zero is the FIRST trading session after the vendor-reported date; returns start at its CLOSE.",
            "The release timestamp and exact after-hours status are not verified.",
            "Uses adjusted closes for both stock and SPY. Excess return is compounded stock return minus compounded SPY return in percentage points.",
            "No aggregate summary is displayed unless eight eligible non-overlapping complete events exist.",
            *(["Insufficient eligible observations for aggregate statistics."] if summary is None else []),
        ],
    )
