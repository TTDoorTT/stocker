"""Executable ownership rules, including aliases and package-import forms."""

import ast
import sys
import time
from pathlib import Path

import pytest

from app.contracts.api import PositionRequest, ResearchRequest
from app.core.config import Settings
from app.core.database import Database
from app.modules.market_data.service import DataService
from app.modules.portfolio.repository import PortfolioRepository
from app.modules.portfolio.service import PortfolioService
from app.modules.research.repository import ResearchRepository
from app.modules.research.service import ResearchService

APP = Path(__file__).resolve().parents[1] / "app"
PUBLIC = {
    "market_data": {"service", "symbols", "errors", "provenance"},
    "research": {"service", "errors"},
    "portfolio": {"service"},
    "intelligence": {"service"},
}


def boundary_errors(source: str, module: str) -> list[str]:
    errors = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                errors.append("Use absolute application imports so ownership is explicit")
                continue
            imports = [f"{node.module}.{alias.name}" for alias in node.names]
        else:
            continue
        for imported in imports:
            parts = imported.split(".")
            if module.startswith("app.finance."):
                if not imported.startswith("app.contracts.") and parts[0] not in sys.stdlib_module_names:
                    errors.append(f"Pure finance imports {imported}")
            if module.startswith("app.modules.") and imported.startswith("app.modules."):
                owner = module.split(".")[2]
                target = parts[2]
                if target != owner and (len(parts) < 4 or parts[3] not in PUBLIC.get(target, set())):
                    errors.append(f"{owner} imports private {imported}")
            if module.endswith(".router") and ("repository" in parts or imported.startswith("sqlite3")):
                errors.append(f"Router imports persistence {imported}")
    return errors


def test_application_import_boundaries():
    errors = []
    for path in APP.rglob("*.py"):
        module = "app." + ".".join(path.relative_to(APP).with_suffix("").parts)
        errors.extend(
            f"{path.relative_to(APP)}: {error}" for error in boundary_errors(path.read_text(), module)
        )
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize(
    "source,module",
    [
        ("import app.modules.market_data.providers.sec as sec", "app.modules.research.service"),
        ("from app.modules.market_data import providers", "app.modules.research.service"),
        (
            "def nested():\n from app.modules.research import repository as repo",
            "app.modules.portfolio.service",
        ),
        ("from httpx import Client", "app.finance.metrics"),
        ("from app.core.database import Database", "app.finance.metrics"),
        ("from app.modules.portfolio.repository import PortfolioRepository", "app.modules.portfolio.router"),
    ],
)
def test_checker_rejects_forbidden_imports(source, module):
    assert boundary_errors(source, module)


@pytest.mark.parametrize(
    "source,module",
    [
        ("from app.modules.market_data.service import DataService", "app.modules.research.service"),
        (
            "from app.modules.research.service import summarize_captured_headlines",
            "app.modules.intelligence.news",
        ),
        ("from app.contracts.market import Stock", "app.finance.metrics"),
    ],
)
def test_checker_accepts_public_contracts(source, module):
    assert not boundary_errors(source, module)


def test_public_feature_facades_share_storage_without_http():
    settings = Settings(_env_file=None)
    data = DataService(settings)
    database = Database("sqlite:///:memory:")
    repo = ResearchRepository(database)
    portfolio = PortfolioService(PortfolioRepository(database), data, settings)
    research = ResearchService(repo, data, settings, lambda slug: {})
    try:
        portfolio.add_watchlist("AAPL")
        portfolio.add_position(PositionRequest(symbol="AAPL", shares=2, average_cost=100))
        run = research.start(ResearchRequest(symbol="AAPL"))
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            saved = research.run(run["run_id"])
            if saved["status"] not in {"queued", "running"}:
                break
            time.sleep(0.01)
        assert saved["mode"] == "fixtures" and len(saved["stages"]) == 6 and saved["report"]
        assert research.events(run["run_id"])[-1]["event"] == "run_finished"
        assert portfolio.watchlist() == [{"symbol": "AAPL"}]
        assert portfolio.positions()[0]["unrealized_pnl"] == 40
    finally:
        research.shutdown()
        database.close()
