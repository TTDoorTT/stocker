"""Pure OHLCV helpers; the price basis must be explicitly identified by callers."""

from collections import defaultdict
from datetime import date, timedelta

from app.contracts.stock_research import CandleBar
from app.modules.market_data.errors import DataUnavailable

RANGE_DAYS = {"1m": 31, "3m": 93, "6m": 186, "1y": 366, "2y": 732, "5y": 1830}


def select_range(bars: list[CandleBar], range_key: str, *, as_of: date) -> list[CandleBar]:
    if range_key not in RANGE_DAYS:
        raise ValueError("Unsupported candle range")
    lower = as_of - timedelta(days=RANGE_DAYS[range_key])
    selected = [bar for bar in bars if lower <= bar.date <= as_of]
    return sorted(selected, key=lambda bar: bar.date)


def aggregate_bars(bars: list[CandleBar], interval: str) -> list[CandleBar]:
    """Resample *daily* trading observations using calendar weeks/months, never weekends as rows."""
    if interval == "1d":
        return bars
    if interval not in {"1wk", "1mo"}:
        raise ValueError("Unsupported candle interval")
    buckets: dict[tuple[int, int], list[CandleBar]] = defaultdict(list)
    for bar in bars:
        key = (
            (bar.date.isocalendar().year, bar.date.isocalendar().week)
            if interval == "1wk"
            else (
                bar.date.year,
                bar.date.month,
            )
        )
        buckets[key].append(bar)
    output = []
    for group in sorted(buckets.values(), key=lambda group: group[0].date):
        group.sort(key=lambda bar: bar.date)
        volume = sum(bar.volume for bar in group if bar.volume is not None)
        output.append(
            CandleBar(
                date=group[-1].date,
                open=group[0].open,
                high=max(bar.high for bar in group),
                low=min(bar.low for bar in group),
                close=group[-1].close,
                volume=volume if all(bar.volume is not None for bar in group) else None,
                adjusted_close=group[-1].adjusted_close
                if all(bar.adjusted_close is not None for bar in group)
                else None,
            )
        )
    return output


def fixture_candles(*, quote_price: float, range_key: str, interval: str, as_of: date) -> list[CandleBar]:
    """Repeatable and visually explicit fabricated data; no financial API access."""
    if quote_price <= 0:
        raise DataUnavailable("Synthetic quote price is unavailable")
    daily: list[CandleBar] = []
    day = as_of - timedelta(days=RANGE_DAYS["5y"] + 10)
    index = 0
    while day <= as_of:
        if day.weekday() < 5:
            # Smooth but nonconstant synthetic movement, no RNG or local clock dependencies.
            center = quote_price * (0.68 + 0.00025 * index + 0.025 * ((index % 43) / 43))
            open_price = center * (1 + (((index * 7) % 13) - 6) / 1000)
            close_price = center * (1 + (((index * 11) % 17) - 8) / 1000)
            daily.append(
                CandleBar(
                    date=day,
                    open=open_price,
                    high=max(open_price, close_price) * 1.007,
                    low=min(open_price, close_price) * 0.993,
                    close=close_price,
                    volume=100000 + (index * 173) % 500000,
                )
            )
            index += 1
        day += timedelta(days=1)
    return aggregate_bars(select_range(daily, range_key, as_of=as_of), interval)
