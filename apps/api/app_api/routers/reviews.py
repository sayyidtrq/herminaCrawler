from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.config import get_settings
from app.db.models import User
from app.services.review_service import ReviewService
from app.utils.date_parser import resolve_date_range
from apps.api.app_api.dependencies import get_current_user
from apps.api.app_api.serializers import hide_raw_payload, to_jsonable


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("")
def list_reviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    location_id: int | None = Query(default=None),
    rating: int | None = Query(default=None, ge=1, le=5),
    sentiment: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    latest_first: bool = Query(default=False),
    include_raw: bool = Query(default=False),
    date_preset: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    current_user: User = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    resolved_from, resolved_to = resolve_date_range(date_preset, date_from, date_to)
    service = ReviewService(company_id=current_user.company_id)
    items, total = service.get_reviews(
        page=page,
        page_size=page_size,
        location_id=location_id,
        rating=rating,
        sentiment=sentiment,
        keyword=keyword,
        latest_first=latest_first,
        date_from=resolved_from,
        date_to=resolved_to,
    )
    if not (settings.show_raw_payload or include_raw):
        items = [hide_raw_payload(item) for item in items]
    return to_jsonable(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    )


@router.get("/{review_id}")
def get_review(
    review_id: int,
    include_raw: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    service = ReviewService(company_id=current_user.company_id)
    review = service.get_review(review_id)
    if review is None:
        raise ValueError("Review not found.")
    if not (settings.show_raw_payload or include_raw):
        review = hide_raw_payload(review)
    return to_jsonable(review)
