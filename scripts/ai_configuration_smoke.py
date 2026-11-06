"""Manual real-browser AI setup acceptance against an isolated synthetic Compose stack.

First run backend/tests/fixture_model_server.py inside the fixture backend container.
STOCKER_SMOKE_BASE can select alternate published fixture ports. Uses synthetic keys only.
Requires the same native Playwright/Chromium dependencies as browser_smoke.py.
"""

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "tests"))
from browser_smoke import expect, sync_playwright  # noqa: E402

BASE = os.environ.get("STOCKER_SMOKE_BASE", "http://127.0.0.1:5173")


def request(path, method="GET"):
    with urlopen(Request(BASE + "/api" + path, method=method), timeout=5) as response:
        return json.load(response)


def main():
    assert request("/health")["mode"] == "fixtures", "Requires isolated fixture stack"
    assert all(run["mode"] == "fixtures" for run in request("/research-runs"))
    config = request("/settings/ai")
    assert not config["configured"] or config["model_id"].startswith("synthetic-"), (
        "Refusing real AI settings"
    )
    request("/settings/ai", "DELETE")
    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()

        # Alternate fixture ports simulate the supported UI origin without relaxing app policies.
        def allowed_origin(route):
            headers = dict(route.request.headers)
            if route.request.method in {"POST", "DELETE"}:
                headers["origin"] = "http://127.0.0.1:5173"
            response = route.fetch(headers=headers)
            route.fulfill(response=response)

        page.route("**/api/**", allowed_origin)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(BASE + "/research")
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name="Skip AI setup").click()
        expect(dialog).not_to_be_visible()
        expect(page.locator(".mode-banner")).to_contain_text("Synthetic")
        page.reload()
        expect(dialog).to_be_visible()
        dialog.get_by_label("API Base URL").fill("http://127.0.0.1:14000/v1")
        dialog.get_by_label("Model ID").fill("synthetic-ui-model")
        dialog.get_by_label("API Key", exact=True).fill("synthetic-ui-secret")
        dialog.get_by_role("button", name="Test Connection").click()
        expect(dialog.get_by_text("Model responded successfully.", exact=False)).to_be_visible()
        dialog.get_by_role("button", name="Save", exact=True).click()
        expect(dialog).not_to_be_visible()
        assert request("/settings/ai")["model_id"] == "synthetic-ui-model"
        page.goto(BASE + "/settings")
        expect(page.get_by_label("Model ID")).to_have_value("synthetic-ui-model")
        expect(page.get_by_label("API Key", exact=True)).to_have_value("")
        assert "synthetic-ui-secret" not in page.content()
        assert page.evaluate("localStorage.length + sessionStorage.length") == 0
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path="/tmp/stocker-ai-settings-mobile.png", full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.screenshot(path="/tmp/stocker-ai-settings-desktop.png", full_page=True)
        page.get_by_role("button", name="Use environment configuration").click()
        expect(page.get_by_label("Model ID")).to_have_value("")
        assert not request("/settings/ai")["configured"]
        assert not errors, errors
        browser.close()
    print(
        "PASS: real setup/skip/test/save/settings/reset, synthetic mode, secret absence, mobile overflow, zero pageerrors"
    )


if __name__ == "__main__":
    main()
