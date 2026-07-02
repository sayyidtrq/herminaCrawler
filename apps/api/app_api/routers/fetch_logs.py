from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.db.models import User
from app.services.fetch_log_service import FetchLogService
from apps.api.app_api.dependencies import get_current_user
from apps.api.app_api.serializers import to_jsonable


router = APIRouter(prefix="/fetch-logs", tags=["fetch logs"])


@router.get("")
def list_fetch_logs(
    location_id: int | None = Query(default=None),
    failed_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_user),
) -> dict:
    logs = FetchLogService(company_id=current_user.company_id).get_logs(
        location_id=location_id,
        failed_only=failed_only,
        limit=limit,
    )
    return to_jsonable({"items": logs, "total": len(logs)})


@router.get("/latest")
def latest_fetch_log(current_user: User = Depends(get_current_user)) -> dict:
    log = FetchLogService(company_id=current_user.company_id).get_last_log()
    return to_jsonable({"item": log})
