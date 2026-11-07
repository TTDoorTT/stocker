from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.contracts.api import ChatResponse
from app.modules.intelligence.service import IntelligenceService
from app.modules.market_data.errors import DataUnavailable
from app.modules.research.errors import ModelError


class RSSHighlightsRequest(BaseModel):
    category: str = Field(default="ai", min_length=1, max_length=30, pattern=r"^[a-z]+$")


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

    @router.get("/api/intelligence/rss")
    def rss(category: str = "ai") -> dict:
        try:
            return intel.rss_feed(category)
        except ValueError:
            raise HTTPException(422, "Unknown RSS industry category") from None

    @router.post("/api/intelligence/rss/refresh")
    def rss_refresh() -> dict:
        return intel.rss_refresh()

    @router.get("/api/intelligence/rss/highlights")
    def rss_saved_highlights(
        category: str = Query(default="ai", min_length=1, max_length=30, pattern=r"^[a-z]+$"),
    ) -> dict:
        try:
            return intel.rss_saved_highlights(category)
        except ValueError:
            raise HTTPException(422, "Unknown RSS industry category") from None

    @router.post("/api/intelligence/rss/highlights", response_model=ChatResponse)
    def rss_highlights(body: RSSHighlightsRequest):
        try:
            intel.rss_collector.validate_category(body.category)
        except ValueError:
            raise HTTPException(422, "Unknown RSS industry category") from None
        try:
            return intel.rss_highlights(body.category)
        except (ModelError, DataUnavailable):
            raise
        except ValueError:
            raise HTTPException(502, "Industry highlights failed evidence validation") from None

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
