from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.fetch_log_service import FetchLogService
from apps.api.app_api.serializers import to_jsonable


router = APIRouter(prefix="/fetch-logs", tags=["fetch logs"])


@router.get("")
def list_fetch_logs(
    location_id: int | None = Query(default=None),
    failed_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=200),
) -> dict:
    logs = FetchLogService().get_logs(
        location_id=location_id,
        failed_only=failed_only,
        limit=limit,
    )
    return to_jsonable({"items": logs, "total": len(logs)})


@router.get("/latest")
def latest_fetch_log() -> dict:
    log = FetchLogService().get_last_log()
    return to_jsonable({"item": log})

