from datetime import UTC, date, datetime, timedelta
from math import isfinite

from app.core.config import Settings
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.http import ProviderHTTP

SIGNALS = (
    {"series_id": "DGS10", "name": "U.S. 10-year Treasury yield", "unit": "percent", "max_age_days": 10},
    {"series_id": "FEDFUNDS", "name": "Effective federal funds rate", "unit": "percent", "max_age_days": 65},
    {
        "series_id": "DCOILWTICO",
        "name": "WTI crude oil spot price",
        "unit": "USD per barrel",
        "max_age_days": 10,
    },
)


def now():
    return datetime.now(UTC)


class FredProvider:
    def __init__(self, settings: Settings, http: ProviderHTTP):
        self.settings = settings
        self.http = http

    def signals(self) -> list[dict]:
        items = []

        fetched = now()

        for definition in SIGNALS:
            series_id = definition["series_id"]
            item = {
                "series_id": series_id,
                "name": definition["name"],
                "unit": definition["unit"],
                "source_name": "FRED, Federal Reserve Bank of St. Louis",
                "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
                "observation_date": None,
                "value": None,
                "published_at": None,
                "fetched_at": None,
                "stale": True,
                "status": "unavailable",
                "observations": [],
                "gaps": [],
            }
            item["cached"] = False
            if self.settings.data_mode == "fixtures":
                item["gaps"].append(
                    "Fixture mode: live macroeconomic observations are not requested or fabricated."
                )
            elif not self.settings.fred_api_key:
                item["gaps"].append("FRED_API_KEY is not configured; observations unavailable.")
            else:
                try:
                    captured = self.http.fetch(
                        "https://api.stlouisfed.org/fred/series/observations",
                        params={
                            "series_id": series_id,
                            "api_key": self.settings.fred_api_key,
                            "file_type": "json",
                            "sort_order": "desc",
                            "limit": 40,
                            "observation_start": str(fetched.date() - timedelta(days=365)),
                        },
                        ttl=21600,
                        interval=0.6,
                    )
                    response = captured.data
                    observations = []
                    for row in response.get("observations", []):
                        try:
                            observation_date = date.fromisoformat(row["date"])
                            value = float(row["value"])
                            if not isfinite(value) or observation_date > fetched.date():
                                continue
                            observations.append({"date": str(observation_date), "value": value})
                        except (KeyError, ValueError, TypeError):
                            continue
                    observations.sort(key=lambda row: row["date"])
                    if observations:
                        latest = observations[-1]
                        stale = (fetched.date() - date.fromisoformat(latest["date"])).days > definition[
                            "max_age_days"
                        ]
                        item.update(
                            observation_date=latest["date"],
                            value=latest["value"],
                            fetched_at=captured.fetched_at.isoformat(),
                            cached=captured.cached,
                            status="available",
                            stale=stale,
                            observations=observations,
                        )
                        item["gaps"].append(
                            "Observation date is not a publication timestamp; revisions and release lags apply."
                        )
                        if stale:
                            item["gaps"].append("Latest observation exceeds the documented freshness window.")
                    else:
                        item["gaps"].append("FRED returned no finite, dated observations.")
                except (DataUnavailable, ValueError, TypeError, AttributeError):
                    item["gaps"].append(
                        "FRED request unavailable; check credentials, network and provider limits."
                    )
            items.append(item)

        return items
