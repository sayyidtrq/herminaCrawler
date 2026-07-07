from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field
from fastapi import APIRouter, Query, Depends

from app.db.models import User
from app.services.location_service import LocationService
from apps.api.app_api.dependencies import get_current_user
from apps.api.app_api.schemas import (
    DeleteResponse,
    LocationListResponse,
    LocationResponse,
)
from apps.api.app_api.serializers import location_to_dict


router = APIRouter(prefix="/locations", tags=["locations"])


class LocationCreateRequest(BaseModel):
    hospital_name: str = "Hermina"
    branch_name: str = Field(min_length=1)
    city: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source: str = Field(default="selenium", min_length=1)
    external_place_id: str = Field(min_length=1)
    google_maps_url: str | None = None
    google_reviews_url: str | None = None
    target_review_count: int = Field(default=100, ge=1, le=300)
    is_active: bool = True


class LocationUpdateRequest(BaseModel):
    hospital_name: str | None = None
    branch_name: str | None = None
    city: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source: str | None = None
    external_place_id: str | None = None
    google_maps_url: str | None = None
    google_reviews_url: str | None = None
    target_review_count: int | None = Field(default=None, ge=1, le=300)
    is_active: bool | None = None


@router.get(
    "",
    response_model=LocationListResponse,
    summary="List lokasi/cabang RS",
    description="Ambil semua lokasi milik company. Set `active_only=true` untuk hanya lokasi aktif.",
)
def list_locations(
    current_user: Annotated[User, Depends(get_current_user)],
    active_only: bool = Query(default=False),
) -> dict:
    service = LocationService(company_id=current_user.company_id)
    locations = service.get_all_locations(active_only=active_only)
    return {
        "items": [location_to_dict(location) for location in locations],
        "total": len(locations),
    }


@router.post(
    "",
    response_model=LocationResponse,
    summary="Tambah lokasi",
    description="Buat lokasi/cabang RS baru. Field wajib: `branch_name`, `external_place_id`.",
)
def create_location(
    payload: LocationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    service = LocationService(company_id=current_user.company_id)
    location = service.add_location(**payload.model_dump())
    return location_to_dict(location)


@router.get(
    "/{location_id}",
    response_model=LocationResponse,
    summary="Detail lokasi",
    responses={404: {"description": "Location not found"}},
)
def get_location(
    location_id: int,
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    service = LocationService(company_id=current_user.company_id)
    location = service.get_location(location_id)
    if location is None:
        raise ValueError("Location not found.")
    return location_to_dict(location)


@router.patch(
    "/{location_id}",
    response_model=LocationResponse,
    summary="Update sebagian field lokasi",
    description="Update field lokasi (partial). Hanya field yang dikirim yang diubah.",
    responses={404: {"description": "Location not found"}},
)
def update_location(
    location_id: int, 
    payload: LocationUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    service = LocationService(company_id=current_user.company_id)
    changed = None
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        location = service.get_location(location_id)
        if location is None:
            raise ValueError("Location not found.")
        return location_to_dict(location)
    for field, value in updates.items():
        changed = service.update_location(location_id, field, value)
    return location_to_dict(changed)


@router.post(
    "/{location_id}/toggle-active",
    response_model=LocationResponse,
    summary="Aktif/nonaktifkan lokasi",
)
def toggle_location_active(
    location_id: int,
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    service = LocationService(company_id=current_user.company_id)
    return location_to_dict(service.toggle_active(location_id))


@router.delete(
    "/{location_id}",
    response_model=DeleteResponse,
    summary="Hapus lokasi",
    responses={404: {"description": "Location not found"}},
)
def delete_location(
    location_id: int,
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    service = LocationService(company_id=current_user.company_id)
    branch_name = service.delete_location(location_id)
    return {"status": "success", "deleted": branch_name}
