from fastapi import APIRouter, HTTPException

from app.core.config import Settings
from app.db.repository import Repository
from app.finance.metrics import unrealized_pnl
from app.models.api import PositionRequest, SymbolRequest
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.service import DataService
from app.modules.market_data.symbols import normalize_symbol


def create_router(settings: Settings, service: DataService, repository: Repository) -> APIRouter:
    router = APIRouter()

    def symbol(value):
        try:
            return normalize_symbol(value)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @router.get("/api/watchlist")
    def watchlist() -> list[dict[str, str]]:
        return repository.query("SELECT symbol FROM watchlist ORDER BY symbol")

    @router.post("/api/watchlist", status_code=201)
    def add_watchlist(body: SymbolRequest) -> dict[str, str]:
        repository.query("INSERT OR IGNORE INTO watchlist VALUES (?)", (body.symbol,))
        return {"symbol": body.symbol}

    @router.delete("/api/watchlist/{ticker}")
    def delete_watchlist(ticker: str) -> dict[str, bool]:
        repository.query("DELETE FROM watchlist WHERE symbol=?", (symbol(ticker),))
        return {"deleted": True}

    @router.get("/api/positions")
    def positions() -> list[dict]:
        rows = repository.query("SELECT * FROM positions ORDER BY id DESC")
        for row in rows:
            try:
                quote = service.stock(row["symbol"]).quote
                if quote and quote.currency != row["currency"]:
                    quote = None
            except DataUnavailable:
                quote = None
            row.update(
                quote_price=quote.price if quote else None,
                unrealized_pnl=unrealized_pnl(
                    row["shares"], row["average_cost"], quote.price if quote else None
                ),
                mode=settings.data_mode,
                quote=quote.model_dump(mode="json") if quote else None,
            )
        return rows

    @router.post("/api/positions", status_code=201)
    def add_position(body: PositionRequest) -> dict:
        repository.query(
            "INSERT INTO positions(symbol,shares,average_cost,currency) VALUES (?,?,?,?)",
            (body.symbol, body.shares, body.average_cost, body.currency),
        )
        return {"saved": True}

    @router.delete("/api/positions/{position_id}")
    def delete_position(position_id: int) -> dict[str, bool]:
        if position_id <= 0:
            raise HTTPException(422, "Position ID must be positive")
        repository.query("DELETE FROM positions WHERE id=?", (position_id,))
        return {"deleted": True}

    return router
