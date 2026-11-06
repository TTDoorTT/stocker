"""Small, source-backed market intelligence; no second agent orchestration system."""
import json
from datetime import UTC, date, datetime, timedelta
from math import isfinite
from urllib.parse import urlsplit, urlunsplit

from app.core.config import ROOT
from app.data.http import DataUnavailable
from app.data.valet import valet_signals
from app.finance.metrics import build_calculations

SIGNALS = (
    {'series_id': 'DGS10', 'name': 'U.S. 10-year Treasury yield', 'unit': 'percent', 'max_age_days': 10},
    {'series_id': 'FEDFUNDS', 'name': 'Effective federal funds rate', 'unit': 'percent', 'max_age_days': 65},
    {'series_id': 'DCOILWTICO', 'name': 'WTI crude oil spot price', 'unit': 'USD per barrel', 'max_age_days': 10},
)


def now():
    return datetime.now(UTC)


class IntelligenceService:
    def __init__(self, data, settings):
        self.data = data
        self.settings = settings
        self.templates = json.loads((ROOT / 'fixtures' / 'industries.json').read_text())

    def daily_review(self) -> dict:
        proxies = []
        for stock in self.data.overview():
            returns = next((c for c in build_calculations(stock) if c.metric == 'daily_return'), None)
            proxies.append({'symbol': stock.symbol, 'name': stock.name,
                            'quote': stock.quote.model_dump(mode='json') if stock.quote else None,
                            'daily_return_pct': returns.value if returns else None,
                            'calculation': returns.model_dump(mode='json') if returns else None,
                            'gaps': stock.gaps})
        news = self.news()
        return {'mode': self.settings.data_mode, 'as_of': now().isoformat(), 'proxies': proxies,
                'news': news['items'], 'coverage': 'SPY and QQQ ETF proxies; no market-wide breadth',
                'session': 'Market session is not inferred; use individual quote timestamps.',
                'gaps': ['ETF prices are not index levels.', 'Market breadth, sector coverage and volume unavailable.',
                         'No whole-market conclusions can be drawn from these two ETF proxies.'] + news['gaps']}

    def news(self) -> dict:
        gaps = []
        try:
            items = self.data.news()
        except (DataUnavailable, ValueError):
            items = []
            gaps.append('News provider unavailable; verify configuration, access and network.')
        deduped = {}
        for item in items:
            parts = urlsplit(item.source_url)
            url = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ''))
            key = (' '.join(item.headline.casefold().split()), url)
            if key not in deduped:
                deduped[key] = item.model_dump(mode='json')
        ordered = sorted(deduped.values(), key=lambda row: row['published_at'], reverse=True)
        if not ordered:
            gaps.append('No sourced company/industry headlines or filings are available.')
        if self.settings.data_mode == 'fixtures':
            gaps.append('Fixture mode provides no invented headlines or AI summaries.')
        else:
            gaps.append('Coverage is limited to configured sources and AAPL/MSFT/NVDA; no social sentiment feed.')
        return {'mode': self.settings.data_mode, 'items': ordered[:60],
                'fetched_at': now().isoformat(), 'gaps': gaps}

    def signals(self) -> dict:
        items = []
        fetched = now()
        for definition in SIGNALS:
            series_id = definition['series_id']
            item = {'series_id': series_id, 'name': definition['name'], 'unit': definition['unit'],
                    'source_name': 'FRED, Federal Reserve Bank of St. Louis',
                    'source_url': f'https://fred.stlouisfed.org/series/{series_id}',
                    'observation_date': None, 'value': None, 'published_at': None,
                    'fetched_at': None, 'stale': True, 'status': 'unavailable', 'observations': [], 'gaps': []}
            item['cached'] = False
            if self.settings.data_mode == 'fixtures':
                item['gaps'].append('Fixture mode: live macroeconomic observations are not requested or fabricated.')
            elif not self.settings.fred_api_key:
                item['gaps'].append('FRED_API_KEY is not configured; observations unavailable.')
            else:
                try:
                    captured = self.data.http.fetch('https://api.stlouisfed.org/fred/series/observations',
                        params={'series_id': series_id, 'api_key': self.settings.fred_api_key, 'file_type': 'json',
                                'sort_order': 'desc', 'limit': 40,
                                'observation_start': str(fetched.date()-timedelta(days=365))},
                        ttl=21600, interval=0.6)
                    response = captured.data
                    observations = []
                    for row in response.get('observations', []):
                        try:
                            observation_date = date.fromisoformat(row['date'])
                            value = float(row['value'])
                            if not isfinite(value) or observation_date > fetched.date():
                                continue
                            observations.append({'date': str(observation_date), 'value': value})
                        except (KeyError, ValueError, TypeError):
                            continue
                    observations.sort(key=lambda row: row['date'])
                    if observations:
                        latest = observations[-1]
                        stale = (fetched.date()-date.fromisoformat(latest['date'])).days > definition['max_age_days']
                        item.update(observation_date=latest['date'], value=latest['value'],
                                    fetched_at=captured.fetched_at.isoformat(), cached=captured.cached,
                                    status='available', stale=stale, observations=observations)
                        item['gaps'].append('Observation date is not a publication timestamp; revisions and release lags apply.')
                        if stale:
                            item['gaps'].append('Latest observation exceeds the documented freshness window.')
                    else:
                        item['gaps'].append('FRED returned no finite, dated observations.')
                except (DataUnavailable, ValueError, TypeError, AttributeError):
                    item['gaps'].append('FRED request unavailable; check credentials, network and provider limits.')
            items.append(item)
        if self.settings.bank_of_canada_enabled:
            items.extend(valet_signals(self.data.http, fixtures=self.settings.data_mode == 'fixtures'))
        return {'mode': self.settings.data_mode, 'items': items,
                'gaps': ['These indicators describe macro conditions; no investment signals are inferred.']}

    def industries(self) -> list[dict]:
        common = ['Guided research template, not a verified sector analysis.',
                  'Company examples must be verified against current filings; one stock does not represent a sector.',
                  'Industry capacity, pricing, market-share and demand datasets are not integrated.',
                  'Canadian history/macro support is partial; Canadian company fundamentals remain unavailable.']
        return [dict(template, gaps=common.copy()) for template in self.templates]

    def industry(self, slug: str) -> dict:
        for template in self.industries():
            if template['slug'] == slug:
                return template
        raise KeyError('Industry template not found')
