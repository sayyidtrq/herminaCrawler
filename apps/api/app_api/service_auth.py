"""HTTP authentication for OneBox service-to-service integration calls."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.api_client_service import ApiClientService, InvalidServiceToken
from app.services.integration_review_service import IntegrationRequestError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServicePrincipal:
    client_id: int
    key_id: str
    company_id: int
    scopes: frozenset[str]


bearer_scheme = HTTPBearer(auto_error=False)


def require_service_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> ServicePrincipal:
    """Verify a bearer token without ever accepting company_id from the request."""

    token = (
        credentials.credentials
        if credentials and credentials.scheme.lower() == "bearer"
        else None
    )
    if not token:
        raise IntegrationRequestError(
            401, "INVALID_SERVICE_TOKEN", "Invalid service token."
        )

    try:
        client = ApiClientService().verify(token)
    except InvalidServiceToken:
        raise IntegrationRequestError(
            401, "INVALID_SERVICE_TOKEN", "Invalid service token."
        )

    principal = ServicePrincipal(
        client_id=client.id,
        key_id=client.key_id,
        company_id=client.company_id,
        scopes=frozenset(client.scopes or []),
    )
    request.state.service_principal = principal
    logger.info(
        "service_auth.success",
        extra={"key_id": principal.key_id, "company_id": principal.company_id},
    )
    return principal
