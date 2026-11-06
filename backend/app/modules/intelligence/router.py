from fastapi import APIRouter, HTTPException

from app.contracts.api import ChatResponse
from app.modules.intelligence.service import IntelligenceService
from app.modules.market_data.errors import DataUnavailable
from app.modules.research.errors import ModelError


def create_router(intel: IntelligenceService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/daily-review")
    def daily_review() -> dict:
        return intel.daily_review()

    @router.get("/api/intelligence/news")
    def news() -> dict:
        return intel.news()

    @router.post("/api/intelligence/news/summary", response_model=ChatResponse)
    def news_summary():
        try:
            return intel.summarize_news()
        except (DataUnavailable, ModelError):
            raise
        except ValueError:
            raise HTTPException(
                502, "Headline summary failed evidence validation; no summary published"
            ) from None

    @router.get("/api/intelligence/signals")
    def signals() -> dict:
        return intel.signals()

    @router.get("/api/industries")
    def industries() -> list[dict]:
        return intel.industries()

    @router.get("/api/industries/{slug}")
    def industry(slug: str) -> dict:
        if len(slug) > 60:
            raise HTTPException(422, "Industry slug too long")
        try:
            return intel.industry(slug)
        except KeyError:
            raise HTTPException(404, "Industry template not found") from None

    return router
