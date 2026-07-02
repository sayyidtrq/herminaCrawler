from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.models import User
from app.services.summary_service import SummaryService
from apps.api.app_api.dependencies import get_current_user
from apps.api.app_api.serializers import to_jsonable


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview(current_user: User = Depends(get_current_user)) -> dict:
    return to_jsonable(SummaryService(company_id=current_user.company_id).overall_summary())


@router.get("/locations/{location_id}")
def location_summary(location_id: int, current_user: User = Depends(get_current_user)) -> dict:
    return to_jsonable(SummaryService(company_id=current_user.company_id).location_summary(location_id))


@router.get("/critical-issues")
def critical_issues(current_user: User = Depends(get_current_user)) -> dict:
    items = SummaryService(company_id=current_user.company_id).critical_issues()
    return to_jsonable({"items": items, "total": len(items)})


@router.get("/negative-reviews")
def negative_reviews(current_user: User = Depends(get_current_user)) -> dict:
    items = SummaryService(company_id=current_user.company_id).negative_reviews()
    return to_jsonable({"items": items, "total": len(items)})
