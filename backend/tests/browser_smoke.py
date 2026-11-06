"""Manual real-browser fixture smoke. Run from project root; not collected by pytest.

Requires project-local playwright and Chromium. Never uses real provider/model keys.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".browser-cache" / "chromium"))
local_libraries = ROOT / ".browser-cache" / "libs" / "extracted" / "usr" / "lib" / "x86_64-linux-gnu"
if local_libraries.is_dir():
    os.environ["LD_LIBRARY_PATH"] = str(local_libraries) + ":" + os.environ.get("LD_LIBRARY_PATH", "")

from playwright.sync_api import expect, sync_playwright  # noqa: E402

BASE = "http://127.0.0.1:5173"


def ready(url, process):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Server exited before ready: {url}")
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            time.sleep(0.2)
    raise TimeoutError(f"Server not ready: {url}")


def main():
    for port in (8000, 5173):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(f"Port {port} is occupied; stop its server before smoke testing")
    cache = ROOT / ".browser-cache"
    cache.mkdir(exist_ok=True)
    screenshots = ROOT / "docs" / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    steps = []
    with tempfile.TemporaryDirectory(prefix="smoke-", dir=cache) as temporary:
        env = os.environ.copy()
        env.update(
            DATA_MODE="fixtures",
            DATABASE_URL=f"sqlite:///{temporary}/smoke.db",
            LLM_MODEL="",
            LLM_API_KEY="",
            FINNHUB_API_KEY="",
            SEC_USER_AGENT="",
            ALPHA_VANTAGE_API_KEY="",
            FRED_API_KEY="",
        )
        logs = [open(Path(temporary) / name, "w+") for name in ("backend.log", "frontend.log")]
        processes = []
        try:
            backend = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                cwd=ROOT / "backend",
                env=env,
                stdout=logs[0],
                stderr=subprocess.STDOUT,
            )
            processes.append(backend)
            frontend = subprocess.Popen(
                ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
                cwd=ROOT / "frontend",
                env=env,
                stdout=logs[1],
                stderr=subprocess.STDOUT,
            )
            processes.append(frontend)
            ready("http://127.0.0.1:8000/api/health", backend)
            ready(BASE, frontend)
            with sync_playwright() as browser_driver:
                browser = browser_driver.chromium.launch(headless=True, args=["--no-sandbox"])
                context = browser.new_context(viewport={"width": 1440, "height": 1000})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(error.stack or str(error)))
                page.set_default_timeout(15000)
                page.goto(BASE)
                expect(page.get_by_role("heading", name="Market workspace")).to_be_visible()
                expect(page.locator(".mode-banner")).to_contain_text("Synthetic sample data")
                expect(page.get_by_text("ETF proxy", exact=True)).to_have_count(2)
                # The cross-origin widget is tested only for a loaded iframe or its explicit fallback.
                try:
                    page.frame_locator('iframe[title="TradingView heatmap sandbox"]').locator(
                        'iframe[title="TradingView U.S. stock heatmap"]'
                    ).wait_for(timeout=12000)
                    heatmap = "official iframe inserted (cross-origin prices not inspected)"
                except Exception:
                    expect(
                        page.get_by_text("The external heatmap could not be confirmed loaded.", exact=False)
                    ).to_be_visible(timeout=12000)
                    heatmap = "explicit external-widget failure state visible"
                page.screenshot(path=str(screenshots / "home-desktop.png"), full_page=True)
                steps.append("Home fixture labels, two ETF proxies and heatmap state: " + heatmap)
                page.get_by_label("Search U.S. and Canadian stocks").fill("AAPL")
                page.locator(".search-results").get_by_role("link").filter(has_text="AAPL").click()
                expect(page.get_by_role("heading", name="Apple Inc.", exact=True)).to_be_visible()
                expect(page.get_by_role("img", name="Closing price history", exact=False)).to_be_visible()
                page.get_by_role("button", name="+ Watchlist", exact=True).click()
                expect(page.get_by_text("AAPL added to watchlist", exact=True)).to_be_visible()
                steps.append("Search opens AAPL stock; sourced synthetic chart and watchlist mutation work")
                page.get_by_label("Stock question").fill("What financial evidence is available?")
                page.get_by_role("button", name="Ask question", exact=True).click()
                expect(page.locator(".chat-answer")).to_contain_text("Synthetic fixture report stage")
                assert (page.request.get(BASE + "/api/research-runs").json()) == []
                steps.append("Chat returns fixture-labeled answer and does not launch research")
                page.get_by_role("button", name="Run Research", exact=False).click()
                page.wait_for_url("**/runs/**")
                run_url = page.url
                expect(page.locator(".page-title h1")).to_have_text("AAPL research")
                expect(page.locator(".stage-card.complete")).to_have_count(6, timeout=20000)
                expect(page.get_by_role("button", name="Download Markdown", exact=False)).to_be_visible()
                expect(page.locator(".event-log")).to_contain_text("run finished")
                run = page.request.get(BASE + "/api/research-runs/" + run_url.rsplit("/", 1)[1]).json()
                assert run["status"] == "incomplete" and len(run["stages"]) == 6 and run["report"]
                with page.expect_download() as pending_download:
                    page.get_by_role("button", name="Download Markdown", exact=False).click()
                download = pending_download.value
                assert download.suggested_filename == f"AAPL-research-{run['run_id']}.md"
                assert Path(download.path()).read_text() == run["report"]
                page.screenshot(path=str(screenshots / "research-desktop.png"), full_page=True)
                steps.append(
                    "Six actual stage completions, saved cited incomplete report and execution events"
                )
                page.get_by_role("navigation").get_by_role(
                    "link", name="Research Records", exact=True
                ).click()
                expect(page.get_by_role("link", name="Open analysis", exact=False)).to_have_count(1)
                page.get_by_role("link", name="Open analysis", exact=False).click()
                expect(page.locator(".page-title h1")).to_have_text("AAPL research")
                steps.append("History reopens saved report and trace")
                backend.terminate()
                backend.wait(timeout=5)
                backend = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8000",
                    ],
                    cwd=ROOT / "backend",
                    env=env,
                    stdout=logs[0],
                    stderr=subprocess.STDOUT,
                )
                processes.append(backend)
                ready("http://127.0.0.1:8000/api/health", backend)
                page.reload()
                expect(page.locator(".stage-card.complete")).to_have_count(6)
                expect(page.get_by_role("button", name="Download Markdown", exact=False)).to_be_visible()
                steps.append("Backend restart preserves and browser reopens identical run/report")
                page.get_by_role("link", name="My Stocks", exact=False).click()
                expect(page.get_by_role("button", name="Remove AAPL from watchlist")).to_be_visible()
                page.get_by_label("Ticker", exact=True).fill("AAPL")
                page.get_by_label("Shares", exact=True).fill("2")
                page.get_by_label("Average cost (USD)", exact=True).fill("100")
                page.get_by_role("button", name="Add position", exact=True).click()
                expect(page.get_by_role("cell", name="$40.00", exact=True)).to_be_visible()
                positions = page.request.get(BASE + "/api/positions").json()
                assert positions[0]["unrealized_pnl"] == 40
                steps.append(
                    "Manual position uses sourced fixture quote: 2 × (120−100) = USD40 unrealized P&L"
                )
                page.get_by_role("link", name="Industry Research", exact=False).click()
                expect(page.locator(".industry-grid > article")).to_have_count(20)
                steps.append("All twenty guided industry templates render")
                page.get_by_role("link", name="Daily Review", exact=False).click()
                expect(page.get_by_role("heading", name="Daily market review")).to_be_visible()
                expect(page.get_by_text("SPY and QQQ ETF proxies; no market-wide breadth")).to_be_visible()
                page.get_by_role("link", name="Industry Intelligence", exact=False).click()
                expect(page.locator(".signal-grid > article")).to_have_count(5)
                expect(page.locator(".signal-grid")).to_contain_text("Unavailable")
                steps.append(
                    "Daily review preserves ETF coverage; five signals honestly unavailable in fixture mode"
                )
                page.get_by_role("link", name="Settings / AI", exact=False).click()
                expect(page.get_by_role("heading", name="Settings / AI", exact=True)).to_be_visible()
                expect(
                    page.get_by_text(
                        "Canada / TSX and TSXV: optional daily history and Bank of Canada macro. Canadian statements and Finnhub quotes are unavailable."
                    )
                ).to_be_visible()
                steps.append("Settings shows partial Canadian coverage and unavailable fundamentals")
                page.set_viewport_size({"width": 390, "height": 844})
                page.goto(BASE)
                expect(page.get_by_role("heading", name="Market workspace")).to_be_visible()
                page.screenshot(path=str(screenshots / "home-mobile.png"), full_page=True)
                width = page.evaluate(
                    "({viewport: innerWidth, document: document.documentElement.scrollWidth})"
                )
                assert width["document"] <= width["viewport"], f"Mobile page overflows: {width}"
                steps.append("Mobile390px viewport has no document horizontal overflow")
                page.route("**/embed-widget-stock-heatmap.js", lambda route: route.abort())
                page.reload()
                expect(
                    page.get_by_text("The external heatmap could not be confirmed loaded.", exact=False)
                ).to_be_visible(timeout=25000)
                expect(page.get_by_role("button", name="Reload heatmap", exact=True)).to_be_visible()
                page.get_by_role("button", name="Reload heatmap", exact=True).click()
                expect(
                    page.get_by_text("The external heatmap could not be confirmed loaded.", exact=False)
                ).to_be_visible(timeout=25000)
                expect(page.get_by_label("Search U.S. and Canadian stocks")).to_be_enabled()
                steps.append("Blocked widget script shows explicit failure/retry; search remains available")
                assert not errors, f"Browser runtime errors: {errors}"
                browser.close()
            print(json.dumps({"status": "passed", "steps": steps, "console_page_errors": errors}, indent=2))
        except Exception:
            for log in logs:
                log.flush()
                log.seek(0)
                print(log.read()[-5000:], file=sys.stderr)
            raise
        finally:
            for process in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            for log in logs:
                log.close()


if __name__ == "__main__":
    main()
