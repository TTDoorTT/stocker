from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import Settings
from app.data.http import DataUnavailable, ProviderHTTP
from app.data.service import DataService, normalize_symbol, parse_sec_facts
from app.finance.metrics import (
    build_calculations,
    comparable,
    percentage_change,
    price_earnings,
    profit_margin,
    unrealized_pnl,
)


def settings(**kwargs):
    kwargs.setdefault('history_provider', 'alpha_vantage')
    return Settings(_env_file=None, **kwargs)


@pytest.mark.parametrize('raw,expected', [('aapl', 'AAPL'), (' US:msft ', 'MSFT'), ('BRK.B', 'BRK.B')])
def test_normalize(raw, expected):
    assert normalize_symbol(raw) == expected


@pytest.mark.parametrize('symbol', ['TSX:SHOP', 'CA:SHOP', '../AAPL', 'AAPL?key=secret', '', 'ABCDEF'])
def test_invalid_symbols(symbol):
    with pytest.raises(ValueError):
        normalize_symbol(symbol)


def test_fixture_metadata_and_math():
    service = DataService(settings())
    for symbol in ['AAPL', 'MSFT', 'NVDA']:
        stock = service.stock(symbol)
        assert stock.mode == 'fixtures'
        assert stock.quote.fixture
        assert all(e.fixture and e.source_url and e.fetched_at and e.published_at for e in stock.evidence)
        calculations = {c.metric: c for c in build_calculations(stock)}
        assert calculations['profit_margin'].value is not None
        assert calculations['pe_annual'].value is not None
        assert calculations['revenue_yoy'].value is not None
        assert all(c.input_evidence_ids for c in calculations.values())
    apple = service.stock('AAPL')
    assert {c.metric: c.value for c in build_calculations(apple)}['profit_margin'] == pytest.approx(250/1200*100)
    assert len(service.history('NVDA')) == 10
    assert service.news() == []
    assert len(service.overview()) == 2
    assert service.search('apple')[0]['symbol'] == 'AAPL'


def test_no_synthetic_live_fallback_or_missing_keys():
    service = DataService(settings(data_mode='live'))
    stock = service.stock('AAPL')
    assert stock.mode == 'live'
    assert stock.quote is None
    assert not stock.facts
    assert not stock.evidence
    assert stock.gaps
    with pytest.raises(DataUnavailable, match='ALPHA_VANTAGE'):
        service.history('AAPL')
    with pytest.raises(DataUnavailable, match='SEC_USER_AGENT'):
        service.search('AAPL')


def test_denominator_and_currency_rules():
    assert price_earnings(50, 0) is None
    assert price_earnings(50, -2) is None
    assert profit_margin(5, 0) is None
    assert percentage_change(3, -2) is None
    assert unrealized_pnl(10, 20, 25) == 50
    assert unrealized_pnl(10, 20, None) is None
    stock = DataService(settings()).stock('AAPL')
    revenue = next(f for f in stock.facts if f.field == 'revenue')
    profit = next(f for f in stock.facts if f.field == 'net_income')
    assert comparable(revenue, profit)
    assert not comparable(revenue, profit.model_copy(update={'currency': 'CAD'}))
    assert not comparable(revenue, profit.model_copy(update={'period_start': None}))
    assert price_earnings(float('inf'), 2) is None
    assert price_earnings(1e308, 1e-308) is None
    assert percentage_change(1e308, 1e-308) is None
    assert profit_margin(1e308, 1e-308) is None
    assert unrealized_pnl(1e9, 100, 1e308) is None


def test_http_caching_and_host_allowlist():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={'ok': True})

    http = ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler)))
    for _ in range(2):
        assert http.json('https://data.sec.gov/example', interval=0) == {'ok': True}
    assert len(requests) == 1
    with pytest.raises(DataUnavailable, match='not allowed'):
        http.json('http://127.0.0.1/secret')
    with pytest.raises(DataUnavailable, match='not allowed'):
        http.json('https://attacker.example/secret')


def test_provider_error_redacts_keys():
    http = ProviderHTTP(httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(403))))
    with pytest.raises(DataUnavailable) as exc:
        http.json('https://finnhub.io/api/v1/quote', params={'token': 'never-expose-me'}, interval=0)
    assert 'never-expose-me' not in str(exc.value)
    assert '403' in str(exc.value)


def test_sec_annual_context_filter_and_restatements():
    rows = [
        {'start': '2023-01-01', 'end': '2023-12-31', 'val': 100, 'filed': '2024-02-01',
         'form': '10-K', 'fy': 2023, 'accn': '00001-24-001'},
        {'start': '2023-01-01', 'end': '2023-12-31', 'val': 110, 'filed': '2025-02-01',
         'form': '10-K', 'fy': 2024, 'accn': '00001-25-001'},
        {'start': '2024-01-01', 'end': '2024-03-31', 'val': 25, 'filed': '2024-05-01', 'form': '10-Q'},
        {'start': '2024-01-01', 'end': '2024-09-30', 'val': 75, 'filed': '2025-02-01', 'form': '10-K'},
        {'start': '2024-01-01', 'end': '2024-12-31', 'val': 150, 'filed': '2030-02-01', 'form': '10-K'},
    ]
    source = {'cik': 1, 'facts': {'us-gaap': {'Revenues': {'units': {'USD': rows}}}}}
    facts = parse_sec_facts('AAPL', source, datetime(2025, 3, 1, tzinfo=UTC))
    assert len(facts) == 1
    assert facts[0].value == 110
    assert facts[0].period == '2023-01-01..2023-12-31'
    assert facts[0].fiscal_year is None  # Restated comparative is not filing FY2024.
    assert facts[0].filing_fiscal_year == 2024
    assert '0000125001' in facts[0].source_url


def test_live_mocked_sec_quote_history():
    def handler(request):
        path = request.url.path
        if 'company_tickers' in path:
            data = {'0': {'ticker': 'AAPL', 'title': 'Apple', 'cik_str': 320193}}
        elif 'submissions' in path:
            data = {'name': 'Apple Inc.', 'sicDescription': 'Electronic Computers', 'filings': {'recent': {}}}
        elif 'companyfacts' in path:
            data = {'facts': {'us-gaap': {'Revenues': {'units': {'USD': [
                {'start':'2023-10-01', 'end':'2024-09-30', 'val':1234, 'filed':'2024-11-01',
                 'form':'10-K', 'fy':2024, 'accn':'0000320193-24-000001'}]}}}}}
        elif path.endswith('quote'):
            data = {'c': 200, 'pc': 198, 't': int(datetime.now(UTC).timestamp())}
        else:
            data = {'Time Series (Daily)': {str(datetime.now(UTC).date()): {'4. close':'200'}}}
        return httpx.Response(200, json=data)
    service = DataService(settings(data_mode='live', sec_user_agent='Test research test@example.org',
        finnhub_api_key='test', alpha_vantage_api_key='test'),
        ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler))))
    stock = service.stock('AAPL')
    assert stock.name == 'Apple Inc.'
    assert stock.quote.price == 200
    assert stock.facts[0].value == 1234
    assert not any(e.fixture for e in stock.evidence)
    identity = next(e for e in stock.evidence if e.field == 'company_name')
    assert identity.published_at is None
    assert identity.fetched_at is not None
    assert 'publication timestamp' in identity.missing_reason
    assert stock.facts[0].fiscal_year is None
    assert stock.facts[0].filing_fiscal_year == 2024
    assert len(service.history('AAPL')) == 1


@pytest.mark.parametrize('include_reported', [False, True])
def test_debt_components_are_named_and_never_misrepresented_as_total(include_reported):
    def concept(value):
        return {'units': {'USD': [{'end': '2024-09-30', 'val': value,
                                  'filed': '2024-11-01', 'form': '10-K', 'fy': 2024}]}}
    tags = {'LongTermDebtCurrent': concept(20), 'LongTermDebtNoncurrent': concept(80)}
    if include_reported:
        tags['LongTermDebt'] = concept(100)
    source = {'cik': 1, 'facts': {'us-gaap': tags}}
    facts = parse_sec_facts('AAPL', source, datetime(2025, 3, 1, tzinfo=UTC))
    fields = {fact.field: fact for fact in facts}
    assert 'debt' not in fields
    assert all(fact.statement == 'balance' and fact.period_start is None for fact in facts)
    if include_reported:
        assert set(fields) == {'long_term_debt'}
        assert fields['long_term_debt'].value == 100
        assert 'LongTermDebt)' in fields['long_term_debt'].source_name
    else:
        assert set(fields) == {'long_term_debt_current', 'long_term_debt_noncurrent'}
        assert fields['long_term_debt_current'].value == 20
        assert fields['long_term_debt_noncurrent'].value == 80
        assert all(fact.value != 100 for fact in facts)


def test_cached_stock_and_history_preserve_original_network_fetch_time(monkeypatch):
    requests = []
    today = str(datetime.now(UTC).date())

    def handler(request):
        requests.append(request.url.path)
        path = request.url.path
        if 'company_tickers' in path:
            payload = {'0': {'ticker': 'AAPL', 'title': 'Apple', 'cik_str': 320193}}
        elif 'submissions' in path:
            payload = {'name': 'Apple Inc.', 'sicDescription': 'Electronic Computers', 'filings': {'recent': {
                'form': ['10-K'], 'accessionNumber': ['0000320193-24-000001'],
                'primaryDocument': ['annual.htm'], 'filingDate': ['2024-11-01']}}}
        elif 'companyfacts' in path:
            payload = {'facts': {'us-gaap': {'Revenues': {'units': {'USD': [
                {'start': '2023-10-01', 'end': '2024-09-30', 'val': 1234,
                 'filed': '2024-11-01', 'form': '10-K', 'fy': 2024}]}}}}}
        elif path.endswith('quote'):
            payload = {'c': 200, 'pc': 198, 't': int(datetime.now(UTC).timestamp())}
        else:
            payload = {'Time Series (Daily)': {today: {'4. close': '200'}}}
        return httpx.Response(200, json=payload)

    monkeypatch.setattr('app.data.http.time.sleep', lambda delay: None)
    service = DataService(settings(data_mode='live', sec_user_agent='Test research test@example.org',
        finnhub_api_key='test', alpha_vantage_api_key='test'),
        ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler))))
    first, first_bars = service.stock('AAPL'), service.history('AAPL')
    second, second_bars = service.stock('AAPL'), service.history('AAPL')
    assert len(requests) == 5  # ticker, identity, facts, quote, history: one network request each
    assert not first.quote.cached and second.quote.cached
    assert first.quote.fetched_at == second.quote.fetched_at
    assert all(not item.cached for item in first.evidence + first.news + first_bars)
    assert all(item.cached for item in second.evidence + second.news + second_bars)
    assert [item.fetched_at for item in first.evidence] == [item.fetched_at for item in second.evidence]
    assert first.news[0].fetched_at == second.news[0].fetched_at
    assert first_bars[0].fetched_at == second_bars[0].fetched_at
    classification = next(item for item in second.evidence if item.field == 'industry_classification')
    assert classification.value == 'Electronic Computers'
    assert classification.published_at is None


def test_concurrent_cache_calls_return_independent_metadata_and_payloads():
    from concurrent.futures import ThreadPoolExecutor

    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={'rows': [1]})

    provider = ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler)))
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: provider.fetch('https://data.sec.gov/example', interval=0), range(4)))
    assert len(requests) == 1
    assert sum(response.cached for response in responses) == 3
    assert len({response.fetched_at for response in responses}) == 1
    responses[0].data['rows'].append(2)
    assert all(response.data == {'rows': [1]} for response in responses[1:])


@pytest.mark.parametrize('invalid', ['NaN', 'Infinity', True, None])
def test_sec_rejects_nonfinite_or_nonfinancial_numeric_values(invalid):
    payload = {'facts': {'us-gaap': {'Revenues': {'units': {'USD': [
        {'start': '2023-01-01', 'end': '2023-12-31', 'val': invalid,
         'filed': '2024-02-01', 'form': '10-K'}]}}}}}
    assert parse_sec_facts('AAPL', payload, datetime(2025, 1, 1, tzinfo=UTC)) == []


@pytest.mark.parametrize('quote', [[1], {'c': 5, 'pc': 4, 't': 1e100},
                                   {'c': 'Infinity', 'pc': 4, 't': 1700000000}])
def test_invalid_live_quote_is_unavailable_without_fallback(quote):
    provider = ProviderHTTP(httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=quote))))
    stock = DataService(settings(data_mode='live', finnhub_api_key='test'), provider).stock('AAPL')
    assert stock.quote is None
    assert not stock.evidence
    assert any('Quote unavailable' in gap for gap in stock.gaps)


@pytest.mark.parametrize('series', [{str(datetime.now(UTC).date()): {'4. close': 'NaN'}},
                                    {'bad-date': {'4. close': '200'}},
                                    {str(datetime.now(UTC).date()): None}, [200]])
def test_invalid_live_history_returns_honest_unavailable(series):
    provider = ProviderHTTP(httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, json={'Time Series (Daily)': series}))))
    service = DataService(settings(data_mode='live', alpha_vantage_api_key='test'), provider)
    with pytest.raises(DataUnavailable, match='history unavailable'):
        service.history('AAPL')


def test_expired_cache_does_not_silently_serve_stale_data_on_provider_failure(monkeypatch):
    responses = iter([httpx.Response(200, json={'value': 1}), httpx.Response(503),
                      httpx.Response(503), httpx.Response(503)])
    monkeypatch.setattr('app.data.http.time.sleep', lambda delay: None)
    provider = ProviderHTTP(httpx.Client(transport=httpx.MockTransport(lambda request: next(responses))))
    assert provider.fetch('https://data.sec.gov/example', ttl=-1, interval=0).data == {'value': 1}
    with pytest.raises(DataUnavailable, match='503'):
        provider.fetch('https://data.sec.gov/example', interval=0)
