from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from app.db.models import User
from app.services.analysis_service import AnalysisService
from app.services.entitlement_service import EntitlementError, EntitlementService
from apps.api.app_api.dependencies import get_current_user
from apps.api.app_api.serializers import to_jsonable


router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalyzePendingRequest(BaseModel):
    location_id: int | None = None
    rating: int | None = Field(default=None, ge=1, le=5)


def _require_ai_enabled(company_id: int) -> None:
    try:
        EntitlementService(company_id).require_ai_enabled()
    except EntitlementError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/pending")
def analyze_pending(payload: AnalyzePendingRequest, current_user: User = Depends(get_current_user)) -> dict:
    _require_ai_enabled(current_user.company_id)
    result = AnalysisService(company_id=current_user.company_id).analyze_pending(
        location_id=payload.location_id, rating=payload.rating,
    )
    return to_jsonable(result)


@router.post("/locations/{location_id}/rerun")
def rerun_location(location_id: int, current_user: User = Depends(get_current_user)) -> dict:
    _require_ai_enabled(current_user.company_id)
    return to_jsonable(AnalysisService(company_id=current_user.company_id).rerun_location(location_id))


@router.post("/reviews/{review_id}/rerun")
def rerun_review(review_id: int, current_user: User = Depends(get_current_user)) -> dict:
    _require_ai_enabled(current_user.company_id)
    return to_jsonable(AnalysisService(company_id=current_user.company_id).rerun_review(review_id))
