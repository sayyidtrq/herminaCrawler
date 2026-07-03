from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from app.config import get_settings
from app.db.models import User
from app.services.fetch_service import FetchService
from app.services.selenium_fetch_service import SeleniumFetchService
from apps.api.app_api.dependencies import get_current_user
from apps.api.app_api.serializers import to_jsonable


router = APIRouter(prefix="/fetch-jobs", tags=["fetch jobs"])


class FetchJobRequest(BaseModel):
    location_id: int
    source: str | None = None
    target_review_count: int | None = Field(default=None, ge=1, le=300)
    dry_run: bool = False


class FetchAllActiveRequest(BaseModel):
    dry_run: bool = False


@router.post("")
def run_fetch_job(payload: FetchJobRequest, current_user: User = Depends(get_current_user)) -> dict:
    source = (payload.source or get_settings().review_source_mode).lower()
    if payload.dry_run:
        result = FetchService(company_id=current_user.company_id).dry_run_location(payload.location_id)
    elif source in {"selenium", "selenium_google_maps"}:
        result = SeleniumFetchService().fetch_location(
            payload.location_id,
            target=payload.target_review_count,
        )
    else:
        result = FetchService(company_id=current_user.company_id).fetch_location(payload.location_id)
    return to_jsonable(result)


@router.post("/all-active")
def run_fetch_all_active(payload: FetchAllActiveRequest | None = None, current_user: User = Depends(get_current_user)) -> dict:
    dry_run = bool(payload and payload.dry_run)
    service = FetchService(company_id=current_user.company_id)
    if not dry_run:
        return to_jsonable(service.fetch_all_active_locations())

    locations = service.location_service.get_all_locations(active_only=True)
    results = [service.dry_run_location(location.id) for location in locations]
    return to_jsonable(
        {
            "status": "dry_run",
            "total_locations": len(locations),
            "total_fetched": sum(result.get("total_fetched", 0) for result in results),
            "results": results,
        }
    )
