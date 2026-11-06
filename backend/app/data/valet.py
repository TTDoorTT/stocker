"""No-key Bank of Canada Valet observations; dates are not release timestamps."""
from datetime import UTC, date, datetime, timedelta
from math import isfinite

from app.data.http import DataUnavailable

SERIES = (
    {'series_id': 'FXUSDCAD', 'name': 'Canadian dollar per U.S. dollar',
     'unit': 'CAD per USD', 'max_age_days': 10},
    {'series_id': 'V39079', 'name': 'Bank of Canada target overnight rate',
     'unit': 'percent', 'max_age_days': 10},
)


def valet_signals(http, *, fixtures=False):
    items = []
    today = datetime.now(UTC).date()
    for definition in SERIES:
        series = definition['series_id']
        url = f'https://www.bankofcanada.ca/valet/observations/{series}/json'
        item = {'series_id': series, 'name': definition['name'], 'unit': definition['unit'],
                'market': 'CA', 'source_name': 'Bank of Canada Valet', 'source_url': url,
                'observation_date': None, 'value': None, 'published_at': None,
                'fetched_at': None, 'cached': False, 'stale': True, 'status': 'unavailable',
                'observations': [], 'gaps': []}
        if fixtures:
            item['gaps'].append('Fixture mode: live Canadian observations are not requested or fabricated.')
        else:
            try:
                captured = http.fetch(url, params={'start_date': str(today-timedelta(days=120))})
                observations = {}
                for row in captured.data.get('observations', []):
                    try:
                        day = date.fromisoformat(row['d'])
                        raw = row[series]['v']
                        value = float(raw)
                        if isinstance(raw, bool) or not isfinite(value) or day > today:
                            continue
                        observations[str(day)] = {'date': str(day), 'value': value}
                    except (ValueError, TypeError, KeyError):
                        continue
                ordered = sorted(observations.values(), key=lambda row: row['date'])
                if ordered:
                    latest = ordered[-1]
                    item.update(value=latest['value'], observation_date=latest['date'],
                                fetched_at=captured.fetched_at.isoformat(), cached=captured.cached,
                                observations=ordered, status='available',
                                stale=(today-date.fromisoformat(latest['date'])).days > definition['max_age_days'])
                    item['gaps'].append('Observation date is not a publication timestamp; revisions and release lags apply.')
                    if item['stale']:
                        item['gaps'].append('Latest observation exceeds the documented freshness window.')
                else:
                    item['gaps'].append('Valet returned no finite dated observations.')
            except (DataUnavailable, ValueError, TypeError, AttributeError):
                item['gaps'].append('Bank of Canada observations unavailable; check network and provider limits.')
        items.append(item)
    return items
