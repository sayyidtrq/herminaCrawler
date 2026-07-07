from __future__ import annotations

import logging

from fastapi import APIRouter

from app.config import get_settings
from app.services.settings_service import SettingsService
from apps.api.app_api.schemas import HealthResponse


router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Cek status service beserta nama aplikasi, environment, dan "
        "konektivitas database. Endpoint publik (tanpa auth)."
    ),
)
def health_check() -> dict:
    settings = get_settings()
    try:
        database = SettingsService().check_database_connection()
    except Exception as exc:  # keep /api/health always responding
        logger.exception("Health check database probe failed")
        database = {"ok": False, "message": str(exc)}
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "database": database,
    }

