"""Portfolio persistence using the existing schema and storage transaction lock."""

from app.contracts.api import PositionRequest
from app.core.database import Database


class PortfolioRepository:
    def __init__(self, storage: Database):
        self.storage = storage

    def watchlist(self) -> list[dict[str, str]]:
        return self.storage.query("SELECT symbol FROM watchlist ORDER BY symbol")

    def add_watchlist(self, symbol: str) -> None:
        self.storage.query("INSERT OR IGNORE INTO watchlist VALUES (?)", (symbol,))

    def delete_watchlist(self, symbol: str) -> None:
        self.storage.query("DELETE FROM watchlist WHERE symbol=?", (symbol,))

    def positions(self) -> list[dict]:
        return self.storage.query("SELECT * FROM positions ORDER BY id DESC")

    def add_position(self, body: PositionRequest) -> None:
        self.storage.query(
            "INSERT INTO positions(symbol,shares,average_cost,currency) VALUES (?,?,?,?)",
            (body.symbol, body.shares, body.average_cost, body.currency),
        )

    def delete_position(self, position_id: int) -> None:
        self.storage.query("DELETE FROM positions WHERE id=?", (position_id,))
