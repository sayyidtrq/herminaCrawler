"""OneBox integration contract v1.

Additive: nothing here touches GET /api/reviews, which the FE depends on.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Query, Request

from app.db.session import get_session_factory
from app.services.integration_review_service import (
    IntegrationRequestError,
    IntegrationReviewService,
)
from apps.api.app_api.integration_schemas import (
    API_VERSION,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MIN_LIMIT,
    IntegrationErrorResponse,
    IntegrationReviewListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integration/v1", tags=["integration"])

REQUIRED_SCOPE = "reviews:read"


@dataclass(frozen=True)
class ServicePrincipal:
    """Shape is fixed by VOC-CS-03; only the way it is obtained changes."""

    client_id: int
    key_id: str
    company_id: int
    scopes: frozenset[str]


def require_service_principal() -> ServicePrincipal:
    """PLACEHOLDER — real service-token verification lands in VOC-CS-03.

    It refuses every request rather than returning a permissive stub: an endpoint
    that reads another tenant's reviews must never be reachable unauthenticated,
    not even for the window between these two tasks. Tests supply a principal via
    ``app.dependency_overrides[require_service_principal]``.

    VOC-CS-03 replaces the body with the HTTPBearer dependency from
    ``apps/api/app_api/service_auth.py`` and enforces REQUIRED_SCOPE; the
    signature stays the same so no caller here has to change.
    """
    raise IntegrationRequestError(
        503,
        "SERVICE_AUTH_NOT_READY",
        "Service token authentication is not configured yet (VOC-CS-03).",
    )


def get_integration_session_factory():
    """Seam for tests to point the contract at a disposable database."""
    return get_session_factory()


def _parse_updated_since(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    candidate = raw.strip()
    if candidate.endswith(("z", "Z")):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise IntegrationRequestError(
            400,
            "INVALID_PARAMETER",
            "updated_since must be a UTC ISO 8601 timestamp, e.g. 2026-07-01T00:00:00Z.",
        ) from exc
    if parsed.tzinfo is None:
        raise IntegrationRequestError(
            400,
            "INVALID_PARAMETER",
            "updated_since must carry an explicit UTC offset (Z).",
        )
    return parsed.astimezone(timezone.utc)


@router.get(
    "/reviews",
    response_model=IntegrationReviewListResponse,
    summary="Pull review + analysis untuk OneBox (contract v1)",
    description=(
        "Endpoint pull khusus integrasi OneBox. Contract dibekukan di v1: field "
        "hanya bertambah (additive), tidak pernah dihapus atau berubah tipe. "
        "raw_payload/raw_response tidak pernah dikirim, dan company_id tidak "
        "muncul sebagai parameter maupun field response — tenant ditentukan oleh "
        "service token."
    ),
    responses={
        400: {"model": IntegrationErrorResponse, "description": "Parameter/cursor invalid"},
        401: {"model": IntegrationErrorResponse, "description": "Service token invalid"},
        403: {"model": IntegrationErrorResponse, "description": "Scope tidak cukup"},
        404: {"model": IntegrationErrorResponse, "description": "Location tidak ditemukan"},
        503: {"model": IntegrationErrorResponse, "description": "Service auth belum siap"},
    },
)
def list_integration_reviews(
    request: Request,
    limit: int = Query(default=DEFAULT_LIMIT, description="1..200"),
    cursor: str | None = Query(
        default=None,
        description="Opaque cursor dari next_cursor. Tidak boleh digabung dengan updated_since.",
    ),
    updated_since: str | None = Query(
        default=None,
        description="UTC ISO 8601 (Z). Hanya untuk request pertama tanpa cursor.",
    ),
    location_id: int | None = Query(default=None),
    principal: ServicePrincipal = Depends(require_service_principal),
    session_factory=Depends(get_integration_session_factory),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> dict:
    started = time.perf_counter()
    request_id = x_request_id or str(uuid4())
    request.state.request_id = request_id

    if not (MIN_LIMIT <= limit <= MAX_LIMIT):
        raise IntegrationRequestError(
            400,
            "INVALID_PARAMETER",
            f"limit must be between {MIN_LIMIT} and {MAX_LIMIT}.",
        )
    if REQUIRED_SCOPE not in principal.scopes:
        raise IntegrationRequestError(
            403, "INSUFFICIENT_SCOPE", "Token lacks the reviews:read scope."
        )

    parsed_updated_since = _parse_updated_since(updated_since)

    service = IntegrationReviewService(
        company_id=principal.company_id, session_factory=session_factory
    )
    result = service.list_reviews(
        limit=limit,
        cursor=cursor,
        updated_since=parsed_updated_since,
        location_id=location_id,
    )

    # Deliberately omits the token, the cursor body, and review_text (VOC-CS-01 §13).
    logger.info(
        "integration.reviews.request",
        extra={
            "request_id": request_id,
            "key_id": principal.key_id,
            "company_id": principal.company_id,
            "limit": limit,
            "location_id": location_id,
            "item_count": len(result["items"]),
            "has_more": result["has_more"],
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        },
    )

    return {
        "data": result["items"],
        "page": {
            "limit": limit,
            "has_more": result["has_more"],
            "next_cursor": result["next_cursor"],
            "snapshot_at": result["snapshot_at"],
        },
        "meta": {"api_version": API_VERSION, "request_id": request_id},
    }
