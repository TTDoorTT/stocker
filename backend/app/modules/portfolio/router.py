from fastapi import APIRouter, HTTPException

from app.models.api import PositionRequest, SymbolRequest
from app.modules.market_data.symbols import normalize_symbol
from app.modules.portfolio.service import PortfolioService


def create_router(service: PortfolioService) -> APIRouter:
    router = APIRouter()

    def symbol(value):
        try:
            return normalize_symbol(value)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @router.get("/api/watchlist")
    def watchlist() -> list[dict[str, str]]:
        return service.watchlist()

    @router.post("/api/watchlist", status_code=201)
    def add_watchlist(body: SymbolRequest) -> dict[str, str]:
        return service.add_watchlist(body.symbol)

    @router.delete("/api/watchlist/{ticker}")
    def delete_watchlist(ticker: str) -> dict[str, bool]:
        return service.delete_watchlist(symbol(ticker))

    @router.get("/api/positions")
    def positions() -> list[dict]:
        return service.positions()

    @router.post("/api/positions", status_code=201)
    def add_position(body: PositionRequest) -> dict:
        return service.add_position(body)

    @router.delete("/api/positions/{position_id}")
    def delete_position(position_id: int) -> dict[str, bool]:
        if position_id <= 0:
            raise HTTPException(422, "Position ID must be positive")
        return service.delete_position(position_id)

    return router
