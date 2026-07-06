from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from app.db.models import User
from app.services.export_service import ExportService
from apps.api.app_api.dependencies import get_current_user
from apps.api.app_api.schemas import ExportResponse
from apps.api.app_api.serializers import to_jsonable


router = APIRouter(prefix="/exports", tags=["exports"])

_EXPORT_NOTE = (
    "Membuat file export di server dan mengembalikan nama + path file "
    "(bukan konten file). Catatan integrasi: path bersifat server-side."
)


def _export_response(path: Path) -> dict:
    return to_jsonable(
        {
            "status": "success",
            "filename": path.name,
            "path": path,
        }
    )


@router.post(
    "/reviews/all.csv",
    response_model=ExportResponse,
    summary="Export semua review ke CSV",
    description=_EXPORT_NOTE,
)
def export_all_reviews_csv(current_user: User = Depends(get_current_user)) -> dict:
    return _export_response(ExportService(company_id=current_user.company_id).export_all_reviews_csv())


@router.post(
    "/reviews/location/{location_id}.csv",
    response_model=ExportResponse,
    summary="Export review 1 lokasi ke CSV",
    description=_EXPORT_NOTE,
)
def export_location_reviews_csv(location_id: int, current_user: User = Depends(get_current_user)) -> dict:
    return _export_response(ExportService(company_id=current_user.company_id).export_location_reviews_csv(location_id))


@router.post(
    "/analysis-summary.csv",
    response_model=ExportResponse,
    summary="Export ringkasan analisis ke CSV",
    description=_EXPORT_NOTE,
)
def export_analysis_summary_csv(current_user: User = Depends(get_current_user)) -> dict:
    return _export_response(ExportService(company_id=current_user.company_id).export_analysis_summary_csv())


@router.post(
    "/raw-reviews.json",
    response_model=ExportResponse,
    summary="Export review mentah ke JSON",
    description=_EXPORT_NOTE,
)
def export_raw_reviews_json(current_user: User = Depends(get_current_user)) -> dict:
    return _export_response(ExportService(company_id=current_user.company_id).export_raw_reviews_json())
