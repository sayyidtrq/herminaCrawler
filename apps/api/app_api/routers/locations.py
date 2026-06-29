from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Query

from app.services.location_service import LocationService
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


@router.get("")
def list_locations(
    active_only: bool = Query(default=False),
) -> dict:
    service = LocationService()
    locations = service.get_all_locations(active_only=active_only)
    return {
        "items": [location_to_dict(location) for location in locations],
        "total": len(locations),
    }


@router.post("")
def create_location(payload: LocationCreateRequest) -> dict:
    location = LocationService().add_location(**payload.model_dump())
    return location_to_dict(location)


@router.get("/{location_id}")
def get_location(location_id: int) -> dict:
    service = LocationService()
    location = service.get_location(location_id)
    if location is None:
        raise ValueError("Location not found.")
    return location_to_dict(location)


@router.patch("/{location_id}")
def update_location(location_id: int, payload: LocationUpdateRequest) -> dict:
    service = LocationService()
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


@router.post("/{location_id}/toggle-active")
def toggle_location_active(location_id: int) -> dict:
    return location_to_dict(LocationService().toggle_active(location_id))


@router.delete("/{location_id}")
def delete_location(location_id: int) -> dict:
    branch_name = LocationService().delete_location(location_id)
    return {"status": "success", "deleted": branch_name}
