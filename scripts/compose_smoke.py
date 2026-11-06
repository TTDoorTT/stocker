"""Credential-free fixture API/persistence acceptance through the real Vite proxy.

Usage: python scripts/compose_smoke.py seed|verify /tmp/stockscope-smoke.json
Run only against the explicitly isolated fixture Compose project on port 5173.
"""

import argparse
import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

BASE = os.environ.get("STOCKER_SMOKE_BASE", "http://127.0.0.1:5173")


def request(path: str, body: dict | None = None):
    message = Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(message, timeout=5) as response:
        return json.load(response)


def snapshot(run_id: str) -> dict:
    fields = ("id", "symbol", "shares", "average_cost", "currency", "quote_price", "unrealized_pnl", "mode")
    return {
        "ai": request("/api/settings/ai"),
        "watchlist": request("/api/watchlist"),
        "positions": [{key: row[key] for key in fields} for row in request("/api/positions")],
        "run": request(f"/api/research-runs/{run_id}"),
        "events": request(f"/api/research-runs/{run_id}/events"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("seed", "verify"))
    parser.add_argument("state", type=Path)
    args = parser.parse_args()
    health = request("/api/health")
    if health["mode"] != "fixtures" or health["model_id"] != "fixture-stub":
        raise SystemExit("Refusing mutations: target is not the synthetic fixture stack")
    if any(run["mode"] != "fixtures" for run in request("/api/research-runs")):
        raise SystemExit("Refusing mutations: target contains live research history")
    if args.phase == "seed":
        assert request("/api/stocks/search?q=AAPL")[0]["symbol"] == "AAPL"
        assert request("/api/stocks/AAPL")["quote"]["fixture"]
        request("/api/watchlist", {"symbol": "AAPL"})
        request("/api/positions", {"symbol": "AAPL", "shares": 2, "average_cost": 100})
        run_id = request("/api/research-runs", {"symbol": "AAPL"})["run_id"]
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            saved = request(f"/api/research-runs/{run_id}")
            events = request(f"/api/research-runs/{run_id}/events")
            if (
                saved["status"] not in {"queued", "running"}
                and events
                and events[-1]["event"] == "run_finished"
            ):
                break
            time.sleep(0.1)
        assert saved["status"] == "incomplete" and len(saved["stages"]) == 6 and saved["report"]
        # Synthetic credential only: prove private settings survive container recreation.
        configured = request(
            "/api/settings/ai",
            {
                "base_url": "http://127.0.0.1:14000/v1",
                "model_id": "synthetic-persistence-model",
                "api_key": "synthetic-persistence-key",
            },
        )
        assert configured["source"] == "saved" and configured["has_api_key"]
        assert "synthetic-persistence-key" not in json.dumps(configured)
        assert request("/api/health")["mode"] == "fixtures"
        state = snapshot(run_id)
        assert state["positions"][0]["unrealized_pnl"] == 40
        os.umask(0o077)
        args.state.write_text(json.dumps(state, sort_keys=True) + "\n")
        print("PASS: fixture health, proxy/search, position, six stages, saved report/events")
    else:
        expected = json.loads(args.state.read_text())
        assert snapshot(expected["run"]["run_id"]) == expected
        print(
            "PASS: AI settings/watchlist/positions/full run/report/events identical after container recreation"
        )


if __name__ == "__main__":
    main()
