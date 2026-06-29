from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.services.analysis_service import AnalysisService
from apps.api.app_api.serializers import to_jsonable


router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalyzePendingRequest(BaseModel):
    location_id: int | None = None
    rating: int | None = Field(default=None, ge=1, le=5)


@router.post("/pending")
def analyze_pending(payload: AnalyzePendingRequest) -> dict:
    result = AnalysisService().analyze_pending(
        location_id=payload.location_id,
        rating=payload.rating,
    )
    return to_jsonable(result)


@router.post("/locations/{location_id}/rerun")
def rerun_location(location_id: int) -> dict:
    return to_jsonable(AnalysisService().rerun_location(location_id))


@router.post("/reviews/{review_id}/rerun")
def rerun_review(review_id: int) -> dict:
    return to_jsonable(AnalysisService().rerun_review(review_id))

