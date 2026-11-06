> Historical record imported from `docs/BROWSER_SMOKE.md` at `f8d3cbc`. Current workflow and file locations are in the [progress guide](README.md); old execution steps and branch policies below are historical context.

**Historical artifact — reconciled 2026-11-06.** The measured browser results and earlier missing vision credential below are preserved. Browser/pixel checks were not rerun for cleanup; later recorded live acceptance is separate from the older credential blockers. Current status: [validation](../docs/VALIDATION.md).

---

# Real-browser smoke verification

Status: **passed**, 2026-11-06. `backend/.venv/bin/python backend/tests/browser_smoke.py` exited0 using Playwright1.64.1 and project-local Chromium156. The test runs actual Vite/FastAPI servers on loopback with an isolated temporary SQLite database and explicit synthetic fixture mode. It does not use provider or model credentials. Server processes terminate in a finally block; port checks confirmed8000/5173 were free afterward.

## Repeatable command

```bash
backend/.venv/bin/python -m pip install -e 'backend[browser]'
PLAYWRIGHT_BROWSERS_PATH="$PWD/.browser-cache/chromium" backend/.venv/bin/python -m playwright install chromium
backend/.venv/bin/python backend/tests/browser_smoke.py
```

The smoke script requires ports8000 and5173 free. Playwright is an optional browser-check dependency, not a runtime requirement. This minimal Ubuntu environment lacked libnspr4/libnss3/libasound2. To keep setup entirely within the project, those packages were downloaded with `apt-get download libnspr4 libnss3 libasound2t64` in `.browser-cache/libs`, then extracted using `dpkg-deb -x` into `.browser-cache/libs/extracted`. The script recognizes the local `usr/lib/x86_64-linux-gnu` directory. No global package installation or user configuration was changed.

## Passing checks

- Actual frontend/API startup and health200.
- Fixture banner and SPY/QQQ ETF proxy labels.
- Nested official TradingView iframe insertion inside the isolated opaque-origin wrapper. Cross-origin visualization pixels/prices are not inspected or used as agent evidence.
- Search AAPL, stock identity, synthetic price chart and watchlist add.
- Fixture chat answer; research history remains empty until explicit Run Research action.
- Six persisted completed stages, cited report, honest incomplete overall status and execution trace.
- History reopens the saved report; actual backend restart preserves the same run/report and six stages.
- Manual AAPL position: two shares at average costUSD100 and synthetic quoteUSD120 yields USD40 unrealized P&L.
- All20 guided industry templates, daily ETF coverage, five honestly unavailable FRED/Valet descriptors and Settings/partial Canadian coverage.
- 390px mobile viewport has no document horizontal overflow (DOM measurement).
- Intentionally blocked widget script produces an explicit failure message and working retry control; stock search stays enabled.
- **Zero browser runtime pageerrors** across the final complete flow, including navigation, restart and widget failure/retry.

## Problems found and resolved

The first attempt could not launch Chromium because shared libraries were missing; project-local package extraction resolved that environment issue. Two early attempts stopped on overly broad smoke-test locators (duplicate Records links and duplicate report/page headings); selectors were narrowed.

A subsequent real-browser run found actual TradingView `_replaceScript` errors when React StrictMode/unmount cleanup removed a script container before its async execution. The frontend isolated the official script in an iframe. Its initial allow-scripts-only sandbox then triggered TradingView cookie-access SecurityErrors. The final opaque-origin data-URL wrapper with compatible sandbox settings eliminated both error classes. The final smoke command passed after these fixes, including an intentional network-failure/retry test.

## Screenshot artifacts and perception limit

- [Desktop home](../docs/screenshots/home-desktop.png)
- [Research report and trace](../docs/screenshots/research-desktop.png)
- [Mobile home](../docs/screenshots/home-mobile.png)

Required `vision-analyze` inspection was attempted but failed: `NVIDIA_API_KEY is not set`. No personal credentials were auto-loaded. Visual appearance or overlap has therefore not been asserted from these images. Browser DOM assertions, horizontal-overflow measurement, runtime-error checks and screenshot creation are the verified evidence. Live financial/model behavior remains separate credential-blocked acceptance work.
