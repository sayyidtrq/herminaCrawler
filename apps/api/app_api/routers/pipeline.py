from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.config import get_settings
from app.services.analysis_service import AnalysisService
from app.services.export_service import ExportService
from app.services.fetch_service import FetchService
from app.services.location_service import LocationService
from app.services.selenium_fetch_service import SeleniumFetchService
from apps.api.app_api.serializers import to_jsonable


router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class LocationPipelineRequest(BaseModel):
    location_id: int
    fetch: bool = True
    analyze: bool = True
    export_csv: bool = False
    dry_run: bool = False
    target_review_count: int | None = Field(default=None, ge=1, le=300)
    source: str | None = None


@router.post("/location")
def run_location_pipeline(payload: LocationPipelineRequest) -> dict:
    settings = get_settings()
    if LocationService().get_location(payload.location_id) is None:
        raise ValueError("Location not found.")

    source = (payload.source or settings.review_source_mode).lower()
    result: dict = {
        "location_id": payload.location_id,
        "source": source,
        "dry_run": payload.dry_run,
        "steps": {},
        "status": "success",
    }

    if payload.fetch:
        if payload.dry_run:
            fetch_result = FetchService().dry_run_location(payload.location_id)
        elif source in {"selenium", "selenium_google_maps"}:
            fetch_result = SeleniumFetchService().fetch_location(
                payload.location_id,
                target=payload.target_review_count,
            )
        else:
            fetch_result = FetchService().fetch_location(payload.location_id)
        result["steps"]["fetch"] = fetch_result
        if fetch_result.get("status") == "failed":
            result["status"] = "failed"
            return to_jsonable(result)

    if payload.analyze and not payload.dry_run:
        result["steps"]["analysis"] = AnalysisService().analyze_pending(
            location_id=payload.location_id
        )

    if payload.export_csv and not payload.dry_run:
        export_path = ExportService().export_location_reviews_csv(payload.location_id)
        result["steps"]["export"] = {
            "status": "success",
            "filename": export_path.name,
            "path": export_path,
        }

    return to_jsonable(result)
