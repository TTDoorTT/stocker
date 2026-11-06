"""Real bind-mount/reload regression against an already running fixture stack.

Run with backend/.venv/bin/python scripts/reload_smoke.py; needs native browser extras.
Temporary source edits are always restored. Never runs against live data mode.
"""

import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "tests"))
from browser_smoke import expect, sync_playwright  # noqa: E402

BASE = "http://127.0.0.1:5173"


def health():
    with urlopen(BASE + "/api/health", timeout=3) as response:
        return json.load(response)


def wait_status(value: str):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            if health()["status"] == value:
                return
        except (URLError, TimeoutError):
            pass
        time.sleep(0.2)
    raise AssertionError("Backend source reload was not observed")


@contextmanager
def temporary_edit(relative: str, needle: str, replacement: str):
    path = ROOT / relative
    original = path.read_text()
    if original.count(needle) != 1 or replacement in original:
        raise AssertionError("Probe source does not match expected baseline")
    try:
        path.write_text(original.replace(needle, replacement))
        yield
    finally:
        path.write_text(original)


def main():
    if health()["mode"] != "fixtures":
        raise SystemExit("Refusing source probes against live data mode")
    with temporary_edit("backend/app/main.py", '"status": "ok"', '"status": "reload-probe"'):
        wait_status("reload-probe")
    wait_status("ok")
    print("PASS: backend bind-mount reload and source restoration")
    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(BASE)
            expect(page.get_by_role("heading", name="Market workspace", exact=True)).to_be_visible()
            expect(page.locator(".mode-banner")).to_contain_text("Synthetic sample data")
            with temporary_edit(
                "frontend/src/features/market/pages/HomePage.tsx",
                "Market workspace",
                "Market workspace reload probe",
            ):
                expect(
                    page.get_by_role("heading", name="Market workspace reload probe", exact=True)
                ).to_be_visible(timeout=15000)
                page.wait_for_timeout(500)
            expect(page.get_by_role("heading", name="Market workspace", exact=True)).to_be_visible(
                timeout=15000
            )
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors, errors
        finally:
            browser.close()
    print("PASS: frontend HMR edit/restore, fixture UI, 390px no overflow, zero pageerrors")


if __name__ == "__main__":
    main()
