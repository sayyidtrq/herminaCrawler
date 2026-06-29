from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.services.export_service import ExportService
from apps.api.app_api.serializers import to_jsonable


router = APIRouter(prefix="/exports", tags=["exports"])


def _export_response(path: Path) -> dict:
    return to_jsonable(
        {
            "status": "success",
            "filename": path.name,
            "path": path,
        }
    )


@router.post("/reviews/all.csv")
def export_all_reviews_csv() -> dict:
    return _export_response(ExportService().export_all_reviews_csv())


@router.post("/reviews/location/{location_id}.csv")
def export_location_reviews_csv(location_id: int) -> dict:
    return _export_response(ExportService().export_location_reviews_csv(location_id))


@router.post("/analysis-summary.csv")
def export_analysis_summary_csv() -> dict:
    return _export_response(ExportService().export_analysis_summary_csv())


@router.post("/raw-reviews.json")
def export_raw_reviews_json() -> dict:
    return _export_response(ExportService().export_raw_reviews_json())

