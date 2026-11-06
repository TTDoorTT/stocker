"""Fixed-host JSON transport with per-provider throttle, TTL and bounded retry."""
import copy
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

POLICIES = {
    'www.sec.gov': {'interval': 0.2, 'ttl': 21600},
    'data.sec.gov': {'interval': 0.2, 'ttl': 21600},
    'finnhub.io': {'interval': 1.1, 'ttl': 60},
    'www.alphavantage.co': {'interval': 3, 'ttl': 86400, 'daily_limit': 25},
    'api.stlouisfed.org': {'interval': 0.6, 'ttl': 21600},
    'www.bankofcanada.ca': {'interval': 1, 'ttl': 21600},
}
ALLOWED_HOSTS = set(POLICIES)


class DataUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class ProviderResponse:
    data: dict | list
    fetched_at: datetime
    cached: bool


class ProviderHTTP:
    def __init__(self, client=None):
        self.client = client or httpx.Client(timeout=15, follow_redirects=False)
        self.cache = {}
        self.last = {}
        self.requests = {}
        self.lock = threading.RLock()

    def json(self, url, *, params=None, headers=None, ttl=None, interval=None):
        return self.fetch(url, params=params, headers=headers, ttl=ttl, interval=interval).data

    def fetch(self, url, *, params=None, headers=None, ttl=None, interval=None) -> ProviderResponse:
        """Return metadata with this exact response, including on concurrent cache reads."""
        host = urlparse(url).hostname
        if urlparse(url).scheme != 'https' or host not in ALLOWED_HOSTS:
            raise DataUnavailable('Provider URL not allowed')
        policy = POLICIES[host]
        ttl = policy['ttl'] if ttl is None else ttl
        interval = policy['interval'] if interval is None else max(interval, policy['interval'])
        key = (url, tuple(sorted((params or {}).items())))
        # Serialize provider requests/cache mutations to enforce a shared local rate limit.
        with self.lock:
            cached = self.cache.get(key)
            if cached and cached[0] > time.monotonic():
                return ProviderResponse(copy.deepcopy(cached[1]), cached[2], True)
            for attempt in range(3):
                budget = self.requests.setdefault(host, deque())
                while budget and budget[0] <= time.monotonic() - 86400:
                    budget.popleft()
                if policy.get('daily_limit') and len(budget) >= policy['daily_limit']:
                    raise DataUnavailable(f'{host}: local daily request budget exhausted')
                pause = interval - (time.monotonic() - self.last.get(host, 0))
                if pause > 0:
                    time.sleep(pause)
                self.last[host] = time.monotonic()
                if policy.get('daily_limit'):
                    budget.append(self.last[host])
                try:
                    response = self.client.get(url, params=params, headers=headers)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        if attempt < 2:
                            time.sleep(0.5 * (2 ** attempt))
                            continue
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, (list, dict)):
                        raise DataUnavailable('Provider returned unexpected JSON')
                    if isinstance(data, dict) and any(
                            name in data for name in ('Error Message', 'Note', 'Information', 'error')):
                        raise DataUnavailable(f'{host}: provider returned an access/limit error')
                    fetched_at = datetime.now(UTC)
                    self.cache[key] = (time.monotonic() + ttl, data, fetched_at)
                    return ProviderResponse(copy.deepcopy(data), fetched_at, False)
                except (httpx.HTTPError, ValueError) as exc:
                    # Never surface request URLs (provider keys can appear in query strings).
                    if isinstance(exc, httpx.HTTPStatusError):
                        raise DataUnavailable(f'{host}: HTTP {exc.response.status_code}; check access/limits') from None
                    if isinstance(exc, DataUnavailable):
                        raise
                    if attempt == 2:
                        raise DataUnavailable(f'{host}: unavailable or invalid response') from None
            raise DataUnavailable(f'{host}: retry budget exhausted')
