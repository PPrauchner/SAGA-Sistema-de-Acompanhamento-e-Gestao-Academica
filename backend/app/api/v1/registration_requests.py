"""Router FastAPI para solicitações públicas de cadastro."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.registration_request import (
    RegistrationRequestApprove,
    RegistrationRequestCreate,
    RegistrationRequestReject,
    RegistrationRequestResponse,
)
from backend.app.services.registration_request_service import RegistrationRequestService

router = APIRouter()

service = RegistrationRequestService()


def _build_review_alert(
    result: dict[str, Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    approved = result.get("status") == "aprovado"
    return {
        "tipo": "solicitacao_cadastro_aprovada" if approved else "solicitacao_cadastro_rejeitada",
        "titulo": "Solicitacao de cadastro aprovada" if approved else "Solicitacao de cadastro rejeitada",
        "mensagem": (
            "Sua solicitacao de cadastro foi aprovada. Use o convite de primeiro acesso para ativar sua conta."
            if approved
            else "Sua solicitacao de cadastro foi rejeitada pela coordenacao."
        ),
        "destinatario_id": result["email"],
        "entidade_tipo": "registration_requests",
        "entidade_id": result["id"],
        "programa_id": result.get("programa_id"),
    }


@router.get(
    "/registration-requests/advisors",
)
async def list_public_active_advisors() -> list[dict[str, Any]]:
    return await service.list_active_advisors()


@router.post(
    "/registration-requests",
    status_code=status.HTTP_201_CREATED,
    response_model=RegistrationRequestResponse,
)
async def create_registration_request(
    body: RegistrationRequestCreate,
) -> RegistrationRequestResponse:
    return await service.create_request(body)


@router.get(
    "/registration-requests",
    response_model=list[RegistrationRequestResponse],
)
@requires_role("coordenacao")
async def list_registration_requests(
    user: CurrentUser = Depends(get_current_user),
) -> list[RegistrationRequestResponse]:
    return await service.list_pending(user)


@router.patch(
    "/registration-requests/{request_id}/approve",
    response_model=RegistrationRequestResponse,
)
@requires_role("coordenacao")
@audit_operation
@trigger_alerts(_build_review_alert)
async def approve_registration_request(
    request_id: str,
    body: RegistrationRequestApprove | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> RegistrationRequestResponse:
    return await service.approve_request(
        request_id,
        body or RegistrationRequestApprove(),
        user,
    )


@router.patch(
    "/registration-requests/{request_id}/reject",
    response_model=RegistrationRequestResponse,
)
@requires_role("coordenacao")
@audit_operation
@trigger_alerts(_build_review_alert)
async def reject_registration_request(
    request_id: str,
    body: RegistrationRequestReject | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> RegistrationRequestResponse:
    return await service.reject_request(
        request_id,
        body or RegistrationRequestReject(),
        user,
    )
