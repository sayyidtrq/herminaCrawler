from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.models import User, Competitor
from app.services.competitor_service import CompetitorService
from apps.api.app_api.dependencies import get_current_user

router = APIRouter(prefix="/competitors", tags=["competitors"])

class CompetitorCreateRequest(BaseModel):
    name: str = Field(min_length=1)
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

class CompetitorUpdateRequest(BaseModel):
    name: str | None = None
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

def competitor_to_dict(competitor: Competitor) -> dict:
    return {
        "id": competitor.id,
        "name": competitor.name,
        "city": competitor.city,
        "address": competitor.address,
        "latitude": float(competitor.latitude) if competitor.latitude else None,
        "longitude": float(competitor.longitude) if competitor.longitude else None,
        "source": competitor.source,
        "external_place_id": competitor.external_place_id,
        "google_maps_url": competitor.google_maps_url,
        "google_reviews_url": competitor.google_reviews_url,
        "target_review_count": competitor.target_review_count,
        "is_active": competitor.is_active,
        "created_at": competitor.created_at.isoformat() if competitor.created_at else None,
        "updated_at": competitor.updated_at.isoformat() if competitor.updated_at else None,
    }

@router.get("")
def list_competitors(
    current_user: Annotated[User, Depends(get_current_user)],
    active_only: bool = Query(default=False),
) -> dict:
    service = CompetitorService(company_id=current_user.company_id)
    competitors = service.get_all_competitors(active_only=active_only)
    return {
        "items": [competitor_to_dict(c) for c in competitors],
        "total": len(competitors),
    }

@router.post("")
def create_competitor(
    payload: CompetitorCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    service = CompetitorService(company_id=current_user.company_id)
    competitor = service.add_competitor(**payload.model_dump())
    return competitor_to_dict(competitor)

@router.get("/{competitor_id}")
def get_competitor(
    competitor_id: int,
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    service = CompetitorService(company_id=current_user.company_id)
    competitor = service.get_competitor(competitor_id)
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found.")
    return competitor_to_dict(competitor)

@router.patch("/{competitor_id}")
def update_competitor(
    competitor_id: int, 
    payload: CompetitorUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    service = CompetitorService(company_id=current_user.company_id)
    changed = None
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        competitor = service.get_competitor(competitor_id)
        if competitor is None:
            raise HTTPException(status_code=404, detail="Competitor not found.")
        return competitor_to_dict(competitor)
    for field, value in updates.items():
        try:
            changed = service.update_competitor(competitor_id, field, value)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return competitor_to_dict(changed)

@router.post("/{competitor_id}/toggle-active")
def toggle_competitor_active(
    competitor_id: int,
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    service = CompetitorService(company_id=current_user.company_id)
    try:
        return competitor_to_dict(service.toggle_active(competitor_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{competitor_id}")
def delete_competitor(
    competitor_id: int,
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    service = CompetitorService(company_id=current_user.company_id)
    try:
        name = service.delete_competitor(competitor_id)
        return {"status": "success", "deleted": name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
