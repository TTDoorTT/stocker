"""Phase 1 candle tests use synthetic input only and never contact live providers."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.contracts.stock_research import CandleBar, CandleSeries
from app.core.config import Settings
from app.main import create_app
from app.modules.market_data.candles import aggregate_bars
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.yahoo_candles import YFinanceCandleHistory


def bar(day, open_, high, low, close, volume):
    return CandleBar(date=day, open=open_, high=high, low=low, close=close, volume=volume)


def test_weekly_monthly_aggregation_retains_open_close_extremes_and_volume():
    input_bars = [
        bar(date(2025, 1, 3), 100, 103, 98, 102, 1000),
        bar(date(2025, 1, 6), 110, 115, 109, 113, 1500),
        bar(date(2025, 1, 7), 113, 114, 105, 106, 900),
    ]
    weekly = aggregate_bars(input_bars, "1wk")
    assert [x.date for x in weekly] == [date(2025, 1, 3), date(2025, 1, 7)]
    assert (weekly[1].open, weekly[1].close, weekly[1].high, weekly[1].low) == (110, 106, 115, 105)
    assert weekly[1].volume == 2400
    monthly = aggregate_bars(input_bars, "1mo")
    assert len(monthly) == 1 and monthly[0].volume == 3400
    assert monthly[0].open == 100 and monthly[0].close == 106


def test_missing_volume_does_not_become_zero():
    rows = [bar(date(2025, 1, 6), 10, 12, 9, 11, None), bar(date(2025, 1, 7), 11, 12, 10, 11, 100)]
    assert aggregate_bars(rows, "1wk")[0].volume is None


def test_fixture_candles_and_legacy_history(tmp_path):
    settings = Settings(_env_file=None, data_mode="fixtures", database_url=f"sqlite:///{tmp_path}/chart.db")
    with TestClient(create_app(settings)) as client:
        old = client.get("/api/stocks/AAPL/history?range=1y")
        assert old.status_code == 200 and isinstance(old.json(), list)
        assert "open" not in old.json()[0]
        first = client.get("/api/stocks/AAPL/candles?range=1y&interval=1d")
        assert first.status_code == 200, first.text
        series = CandleSeries.model_validate(first.json())
        assert series.mode == "fixtures" and series.source.fixture
        assert "fixtures/market.json" in str(series.source.url)
        assert series.market == "US" and series.currency == "USD"
        assert len(series.bars) > 200
        assert all(x.high >= max(x.open, x.close, x.low) for x in series.bars)
        assert len({x.date for x in series.bars}) == len(series.bars)
        assert all(x.volume is not None for x in series.bars)
        assert client.get("/api/stocks/AAPL/candles?range=bad").status_code == 422
        assert client.get("/api/stocks/AAPL/candles?interval=3m").status_code == 422
        assert client.get("/api/stocks/RY.TO/candles").status_code == 503
        assert client.get("/api/stocks/CA:AAPL/candles").status_code == 422
        assert client.get("/api/stocks/AAPL/candles?market=CA").status_code == 422
        month = client.get("/api/stocks/AAPL/candles?range=1y&interval=1mo").json()
        week = client.get("/api/stocks/AAPL/candles?range=1y&interval=1wk").json()
        assert len(month["bars"]) < len(week["bars"]) < len(series.bars)
        long = client.get("/api/stocks/AAPL/candles?range=5y").json()
        assert 1200 <= len(long["bars"]) <= 1400
        assert len(long["bars"]) > len(series.bars)


def fake_ticker(calls, *, currency="USD", symbol="AAPL", bad=False):
    class Ticker:
        history_metadata = {"currency": currency, "symbol": symbol}

        def history(self, **kwargs):
            calls.append(kwargs)
            yesterday = datetime.now(UTC) - timedelta(days=2)
            earlier = yesterday - timedelta(days=1)
            return SimpleNamespace(
                iterrows=lambda: iter(
                    [
                        (
                            earlier,
                            {"Open": 10, "High": 12, "Low": 9, "Close": 11, "Volume": 100, "Adj Close": 10.8},
                        ),
                        (
                            yesterday,
                            {
                                "Open": 11,
                                "High": 13,
                                "Low": 10,
                                "Close": 12 if not bad else 99,
                                "Volume": 150,
                                "Adj Close": 11.8,
                            },
                        ),
                    ]
                )
            )

    return lambda requested: Ticker()


def test_yfinance_source_currency_cache_and_original_history_not_modified():
    calls = []
    adapter = YFinanceCandleHistory(fake_ticker(calls))
    one = adapter.candles("AAPL", "1y", "1d", "USD")
    two = adapter.candles("AAPL", "1y", "1d", "USD")
    assert one.market == "US" and not one.source.cached
    assert two.source.cached and one.source.fetched_at == two.source.fetched_at
    assert len(calls) == 1
    assert calls[0]["interval"] == "1d" and calls[0]["auto_adjust"] is False
    assert one.bars[0].adjusted_close == 10.8
    assert one.price_basis == "provider_ohlc"
    two.bars[0].open = 999
    assert adapter.candles("AAPL", "1y", "1d", "USD").bars[0].open == 10
    # Existing legacy .history remains inherited and separately cached.
    adapter.history("AAPL", "1y", "USD")
    assert len(calls) == 2


def test_yfinance_rejects_incompatible_listing_and_invalid_bars():
    with pytest.raises(DataUnavailable, match="currency"):
        YFinanceCandleHistory(fake_ticker([], currency="CAD")).candles("AAPL", "1y", "1d", "USD")
    with pytest.raises(DataUnavailable, match="OHLCV unavailable"):
        YFinanceCandleHistory(fake_ticker([], bad=True)).candles("AAPL", "1y", "1d", "USD")


def test_live_mode_never_returns_fixture_when_no_history_provider(tmp_path):
    settings = Settings(
        _env_file=None,
        data_mode="live",
        history_provider="alpha_vantage",
        database_url=f"sqlite:///{tmp_path}/live.db",
    )
    with TestClient(create_app(settings)) as client:
        result = client.get("/api/stocks/AAPL/candles")
        assert result.status_code == 503
        assert "fixture" not in result.text.lower()


def test_alpha_vantage_compact_volume_and_adjustment_label():
    from app.modules.market_data.providers.alpha_candles import AlphaVantageCandles

    today = datetime.now(UTC).date() - timedelta(days=1)
    payload = {
        "Time Series (Daily)": {
            today.isoformat(): {
                "1. open": "98",
                "2. high": "105",
                "3. low": "97",
                "4. close": "103",
                "5. volume": "12345",
            }
        }
    }

    class DummyHTTP:
        def fetch(self, url, **kwargs):
            assert url.startswith("https://www.alphavantage.co/")
            assert kwargs["params"]["outputsize"] == "compact"
            return SimpleNamespace(data=payload, fetched_at=datetime.now(UTC), cached=False)

    provider = SimpleNamespace(
        settings=SimpleNamespace(alpha_vantage_api_key="synthetic-test-key"), http=DummyHTTP()
    )
    series = AlphaVantageCandles(provider).candles("AAPL", "1m", "1d")
    assert series.bars[0].volume == 12345
    assert series.bars[0].adjusted_close is None
    assert series.mode == "live" and not series.source.fixture
    assert "compact" in series.source.name.lower()
    with pytest.raises(DataUnavailable, match="2- or 5-year"):
        AlphaVantageCandles(provider).candles("AAPL", "5y", "1d")


def test_weekly_aggregation_uses_iso_week_at_year_boundary():
    rows = [
        bar(date(2024, 12, 30), 10, 12, 9, 11, 50),
        bar(date(2025, 1, 2), 11, 13, 10, 12, 30),
    ]
    result = aggregate_bars(rows, "1wk")
    assert len(result) == 1
    assert result[0].date == date(2025, 1, 2)
    assert result[0].open == 10 and result[0].close == 12
    assert result[0].volume == 80
