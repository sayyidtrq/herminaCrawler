from __future__ import annotations

from fastapi import APIRouter

from app.services.summary_service import SummaryService
from apps.api.app_api.serializers import to_jsonable


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview() -> dict:
    return to_jsonable(SummaryService().overall_summary())


@router.get("/locations/{location_id}")
def location_summary(location_id: int) -> dict:
    return to_jsonable(SummaryService().location_summary(location_id))


@router.get("/critical-issues")
def critical_issues() -> dict:
    items = SummaryService().critical_issues()
    return to_jsonable({"items": items, "total": len(items)})


@router.get("/negative-reviews")
def negative_reviews() -> dict:
    items = SummaryService().negative_reviews()
    return to_jsonable({"items": items, "total": len(items)})

