from app.contracts.api import PositionRequest
from app.core.config import Settings
from app.finance.metrics import unrealized_pnl
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.service import DataService
from app.modules.portfolio.repository import PortfolioRepository


class PortfolioService:
    def __init__(self, repository: PortfolioRepository, data: DataService, settings: Settings):
        self.repository = repository
        self.data = data
        self.settings = settings

    def watchlist(self) -> list[dict[str, str]]:
        return self.repository.watchlist()

    def add_watchlist(self, symbol: str) -> dict[str, str]:
        self.repository.add_watchlist(symbol)
        return {"symbol": symbol}

    def delete_watchlist(self, symbol: str) -> dict[str, bool]:
        self.repository.delete_watchlist(symbol)
        return {"deleted": True}

    def positions(self) -> list[dict]:
        rows = self.repository.positions()
        for row in rows:
            try:
                quote = self.data.stock(row["symbol"]).quote
                if quote and quote.currency != row["currency"]:
                    quote = None
            except DataUnavailable:
                quote = None
            row.update(
                quote_price=quote.price if quote else None,
                unrealized_pnl=unrealized_pnl(
                    row["shares"], row["average_cost"], quote.price if quote else None
                ),
                mode=self.settings.data_mode,
                quote=quote.model_dump(mode="json") if quote else None,
            )
        return rows

    def add_position(self, body: PositionRequest) -> dict:
        self.repository.add_position(body)
        return {"saved": True}

    def delete_position(self, position_id: int) -> dict[str, bool]:
        self.repository.delete_position(position_id)
        return {"deleted": True}
