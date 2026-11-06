"""All company values in this module are synthetic; external HTTP is mocked."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import Settings
from app.core.database import Repository
from app.main import create_app
from app.models.api import PositionRequest
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.bank_of_canada import valet_signals
from app.modules.market_data.providers.http import ProviderHTTP
from app.modules.market_data.providers.yahoo import YFinanceHistory
from app.modules.market_data.service import DataService
from app.modules.market_data.symbols import normalize_symbol, symbol_market
from app.orchestrator.engine import new_run


@pytest.mark.parametrize(
    "raw,expected", [("ca:ry.to", "RY.TO"), ("SHOP.TO", "SHOP.TO"), ("TSU.V", "TSU.V"), ("BRK.B", "BRK.B")]
)
def test_explicit_listing_normalization(raw, expected):
    assert normalize_symbol(raw) == expected
    assert symbol_market(expected) == ("CA" if expected.endswith((".TO", ".V")) else "US")


@pytest.mark.parametrize("raw", ["US:SHOP.TO", "CA:SHOP", "CA:AAPL", "RY.TO?secret=x", "../RY.TO"])
def test_ambiguous_or_unsafe_listings_rejected(raw):
    with pytest.raises(ValueError):
        normalize_symbol(raw)


def test_canadian_stock_does_not_leak_into_sec_or_assume_finnhub_coverage():
    settings = Settings(_env_file=None, data_mode="live", finnhub_api_key="synthetic-key")

    def reject(request):
        pytest.fail("Canadian-only company must not be fetched as a U.S. issuer")

    service = DataService(settings, ProviderHTTP(httpx.Client(transport=httpx.MockTransport(reject))))
    stock = service.stock("RY.TO")
    assert (stock.market, stock.currency) == ("CA", "CAD")
    assert stock.quote is None and stock.facts == [] and stock.evidence == []
    assert any("SEDAR+" in gap for gap in stock.gaps)
    assert service.search("CA:RY.TO")[0]["symbol"] == "RY.TO"
    assert new_run("RY.TO", settings)["market"] == "CA"


def test_position_currency_must_match_listing():
    assert PositionRequest(symbol="RY.TO", shares=1, average_cost=100, currency="CAD").currency == "CAD"
    with pytest.raises(ValueError):
        PositionRequest(symbol="RY.TO", shares=1, average_cost=100, currency="USD")
    with pytest.raises(ValueError):
        PositionRequest(symbol="AAPL", shares=1, average_cost=100, currency="CAD")


def fake_ticker_factory(calls, currency="CAD", value=100.0):
    class Ticker:
        history_metadata = {"currency": currency, "symbol": "RY.TO"}

        def history(self, **kwargs):
            calls.append(kwargs)
            day = datetime.now(UTC) - timedelta(days=1)
            return SimpleNamespace(iterrows=lambda: iter([(day, {"Close": value})]))

    return lambda symbol: Ticker()


def test_yfinance_history_preserves_currency_source_timestamp_and_cache():
    calls = []
    provider = YFinanceHistory(fake_ticker_factory(calls))
    first = provider.history("RY.TO", "1y", "CAD")
    second = provider.history("RY.TO", "1y", "CAD")
    assert len(calls) == 1
    assert calls[0]["timeout"] == 15 and calls[0]["auto_adjust"] is False
    assert first[0].currency == "CAD" and not first[0].fixture
    assert second[0].cached and second[0].fetched_at == first[0].fetched_at
    assert first[0].source_url.endswith("RY.TO/history/")
    second[0].close = 200
    assert provider.history("RY.TO", "1y", "CAD")[0].close == 100


@pytest.mark.parametrize("currency,value", [("USD", 100), ("CAD", float("nan")), ("CAD", -1)])
def test_yfinance_currency_and_invalid_values_do_not_produce_bars(currency, value):
    provider = YFinanceHistory(fake_ticker_factory([], currency, value))
    with pytest.raises(DataUnavailable):
        provider.history("RY.TO", "1y", "CAD")
    assert not provider.cache


def test_yfinance_expired_cache_failure_has_no_stale_fallback():
    provider = YFinanceHistory(fake_ticker_factory([]))
    provider.history("RY.TO", "1y", "CAD")
    provider.cache[("RY.TO", "1y", "CAD")] = (0, provider.cache[("RY.TO", "1y", "CAD")][1])
    provider.interval = 0

    def fail(symbol):
        raise RuntimeError("secret provider body")

    provider.ticker_factory = fail
    with pytest.raises(DataUnavailable) as error:
        provider.history("RY.TO", "1y", "CAD")
    assert "secret" not in str(error.value)


def test_auto_history_falls_back_to_explicit_alpha_source_after_yahoo_failure():
    today = str(datetime.now(UTC).date() - timedelta(days=1))
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"Time Series (Daily)": {today: {"4. close": "100"}}})
    )
    service = DataService(
        Settings(_env_file=None, data_mode="live", alpha_vantage_api_key="synthetic-key"),
        ProviderHTTP(httpx.Client(transport=transport)),
    )

    def fail(*args):
        raise DataUnavailable("Yahoo temporarily unavailable")

    service.yahoo_history.history = fail
    bars = service.history("AAPL")
    assert bars[0].source_name.startswith("Alpha Vantage") and bars[0].currency == "USD"


def test_valet_actual_format_missing_values_and_cached_capture():
    requests = []
    day = str(datetime.now(UTC).date() - timedelta(days=1))

    def handler(request):
        requests.append(request)
        series = request.url.path.split("/")[-2]
        return httpx.Response(
            200,
            json={
                "observations": [
                    {"d": day, series: {"v": "1.25"}},
                    {"d": "bad", series: {"v": "NaN"}},
                    {"d": "2999-01-01", series: {"v": "9"}},
                    {"d": day, series: {}},
                ]
            },
        )

    provider = ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler)))
    first, second = valet_signals(provider), valet_signals(provider)
    assert len(requests) == 2
    for a, b in zip(first, second, strict=True):
        assert a["value"] == 1.25 and a["market"] == "CA"
        assert a["published_at"] is None and not a["stale"]
        assert b["cached"] and a["fetched_at"] == b["fetched_at"]
        assert len(a["observations"]) == 1


def test_valet_unavailable_and_fixture_modes_are_honest():
    provider = ProviderHTTP(httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(403))))
    for rows in [valet_signals(provider), valet_signals(provider, fixtures=True)]:
        assert all(row["value"] is None and row["status"] == "unavailable" and row["gaps"] for row in rows)


def test_canadian_api_routes_and_positions_share_existing_storage():
    from fastapi.testclient import TestClient

    settings = Settings(_env_file=None, data_mode="live")
    repo = Repository("sqlite:///:memory:")
    try:
        with TestClient(create_app(settings, repo=repo)) as client:
            response = client.get("/api/stocks/RY.TO?market=CA")
            assert response.status_code == 200 and response.json()["currency"] == "CAD"
            assert client.get("/api/stocks/RY.TO?market=US").status_code == 422
            assert client.post("/api/watchlist", json={"symbol": "CA:RY.TO"}).status_code == 201
            assert (
                client.post(
                    "/api/positions",
                    json={"symbol": "RY.TO", "shares": 2, "average_cost": 100, "currency": "CAD"},
                ).status_code
                == 201
            )
            position = client.get("/api/positions").json()[0]
            assert position["unrealized_pnl"] is None and position["quote_price"] is None
    finally:
        repo.close()


def test_yfinance_current_mapping_metadata_is_supported():
    from collections import UserDict

    factory = fake_ticker_factory([])

    def mapped(symbol):
        ticker = factory(symbol)
        ticker.history_metadata = UserDict(ticker.history_metadata)
        return ticker

    assert YFinanceHistory(mapped).history("RY.TO", "1m", "CAD")[0].currency == "CAD"


def test_alpha_local_daily_budget_counts_only_network_calls_and_resets(monkeypatch):
    clock = [100000.0]
    monkeypatch.setattr("app.modules.market_data.providers.http.time.monotonic", lambda: clock[0])
    monkeypatch.setattr(
        "app.modules.market_data.providers.http.time.sleep",
        lambda seconds: clock.__setitem__(0, clock[0] + seconds),
    )
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    provider = ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler)))
    url = "https://www.alphavantage.co/query"
    provider.fetch(url, params={"symbol": "AAPL"})
    assert provider.fetch(url, params={"symbol": "AAPL"}).cached
    for n in range(24):
        provider.fetch(url, params={"symbol": str(n)})
    with pytest.raises(DataUnavailable, match="daily request budget"):
        provider.fetch(url, params={"symbol": "EXTRA"})
    assert len(requests) == 25
    clock[0] += 86401
    provider.fetch(url, params={"symbol": "EXTRA"})
    assert len(requests) == 26


def test_soft_provider_errors_are_not_cached_as_financial_data():
    provider = ProviderHTTP(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"Information": "synthetic secret in provider text"})
            )
        )
    )
    with pytest.raises(DataUnavailable) as error:
        provider.fetch("https://www.alphavantage.co/query")
    assert "synthetic secret" not in str(error.value)
    assert provider.cache == {}


def test_missing_optional_history_dependency_does_not_prevent_startup(monkeypatch):
    def absent(name):
        raise ImportError(name)

    monkeypatch.setattr("app.modules.market_data.providers.yahoo.import_module", absent)
    service = DataService(Settings(_env_file=None, data_mode="live"))
    assert service.stock("AAPL").facts == []
    with pytest.raises(DataUnavailable, match="Optional yfinance dependency absent"):
        service.history("AAPL")
