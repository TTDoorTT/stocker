from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.data.service import DataService, normalize_symbol, symbol_market
from app.models.market import PriceBar, Stock


def create_router(service: DataService) -> APIRouter:
    router = APIRouter()

    def symbol(value):
        try:
            return normalize_symbol(value)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @router.get("/api/stocks/search")
    def search(q: str = Query(min_length=1, max_length=80)) -> list[dict[str, str]]:
        return service.search(q)

    @router.get("/api/markets/overview", response_model=list[Stock])
    def overview():
        return service.overview()

    @router.get("/api/stocks/{ticker}", response_model=Stock)
    def stock(ticker: str, market: Literal["US", "CA"] | None = None):
        ticker = symbol(ticker)
        if market and market != symbol_market(ticker):
            raise HTTPException(422, "Market does not match the explicit listing symbol")
        return service.stock(ticker)

    @router.get("/api/stocks/{ticker}/history", response_model=list[PriceBar])
    def history(ticker: str, range: Literal["1m", "3m", "1y"] = "1y"):
        return service.history(symbol(ticker), range)

    return router
