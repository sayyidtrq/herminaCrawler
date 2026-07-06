from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from apps.api.app_api.schemas import HealthResponse


router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Cek status service beserta nama aplikasi dan environment. Endpoint publik (tanpa auth).",
)
def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }

