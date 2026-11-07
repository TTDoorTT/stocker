from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.contracts.market import PriceBar, Stock
from app.contracts.stock_research import CandleSeries, EarningsResponse, FinancialTrendsResponse
from app.modules.market_data.service import DataService
from app.modules.market_data.symbols import normalize_symbol, symbol_market


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

    @router.get("/api/stocks/{ticker}/candles", response_model=CandleSeries)
    def candles(
        ticker: str,
        range: Literal["1m", "3m", "6m", "1y", "2y", "5y"] = "1y",
        interval: Literal["1d", "1wk", "1mo"] = "1d",
        market: Literal["US", "CA"] | None = None,
    ):
        ticker = symbol(ticker)
        if market and market != symbol_market(ticker):
            raise HTTPException(422, "Market does not match the explicit listing symbol")
        return service.candles(ticker, range, interval)

    @router.get("/api/stocks/{ticker}/financial-trends", response_model=FinancialTrendsResponse)
    def financial_trends(ticker: str, market: Literal["US", "CA"] | None = None):
        ticker = symbol(ticker)
        if market and market != symbol_market(ticker):
            raise HTTPException(422, "Market does not match the explicit listing symbol")
        return service.financial_trends(ticker)

    @router.get("/api/stocks/{ticker}/earnings", response_model=EarningsResponse)
    def earnings(ticker: str, market: Literal["US", "CA"] | None = None):
        ticker = symbol(ticker)
        if market and market != symbol_market(ticker):
            raise HTTPException(422, "Market does not match the explicit listing symbol")
        return service.earnings(ticker)

    return router
