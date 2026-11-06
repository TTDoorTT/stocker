from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.contracts.api import PositionRequest
from app.core.config import Settings
from app.core.database import Database
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.service import DataService
from app.modules.portfolio.repository import PortfolioRepository
from app.modules.portfolio.service import PortfolioService


@pytest.mark.parametrize("provider_unavailable", [False, True])
def test_portfolio_keeps_missing_or_wrong_currency_quote_unavailable(provider_unavailable):
    settings = Settings(_env_file=None)
    storage = Database("sqlite:///:memory:")
    repository = PortfolioRepository(storage)
    repository.add_position(PositionRequest(symbol="RY.TO", shares=2, average_cost=100, currency="CAD"))
    data = Mock(spec=DataService)
    if provider_unavailable:
        data.stock.side_effect = DataUnavailable("Provider unavailable")
    else:
        data.stock.return_value = SimpleNamespace(quote=SimpleNamespace(currency="USD", price=120))
    service = PortfolioService(repository, data, settings)
    row = service.positions()[0]
    assert row["symbol"] == "RY.TO" and row["currency"] == "CAD"
    assert row["quote"] is None and row["quote_price"] is None and row["unrealized_pnl"] is None
    data.stock.assert_called_once_with("RY.TO")
    storage.close()
