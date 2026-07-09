"""Router FastAPI para solicitacoes de prorrogacao."""

from fastapi import APIRouter, Depends, Query, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.extension import (
    ExtensionCreateRequest,
    ExtensionRejectRequest,
    ExtensionResponse,
)
from backend.app.services.extension_service import ExtensionService

router = APIRouter()

service = ExtensionService()


@router.get("/extensions", response_model=list[ExtensionResponse])
@requires_role("aluno", "orientador", "coordenacao")
async def list_extensions(
    user: CurrentUser = Depends(get_current_user),
) -> list[ExtensionResponse]:
    """Lista prorrogacoes visiveis para o usuario autenticado."""
    return await service.list_extensions(user)


@router.get("/extensions/pending", response_model=list[ExtensionResponse])
@requires_role("coordenacao")
async def list_pending_extensions(
    status_filtro: str = Query("pendente", alias="status"),
    user: CurrentUser = Depends(get_current_user),
) -> list[ExtensionResponse]:
    """Lista as prorrogacoes do programa da coordenacao (fila de aprovacao)."""
    return await service.list_pending_for_coordination(user, status_filtro)


@router.post(
    "/extensions",
    response_model=ExtensionResponse,
    status_code=status.HTTP_201_CREATED,
)
@requires_role("aluno", "orientador")
@audit_operation
async def create_extension(
    body: ExtensionCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ExtensionResponse:
    """Cria uma solicitacao de prorrogacao para aluno ou orientando."""
    return await service.create_extension(body, user)


@router.post("/extensions/{extension_id}/approve", response_model=ExtensionResponse)
@requires_role("coordenacao")
@audit_operation
async def approve_extension(
    extension_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> ExtensionResponse:
    """Aprova prorrogacao/trancamento pendente e recalcula o prazo do aluno."""
    return await service.approve_extension(extension_id, user)


@router.post("/extensions/{extension_id}/reject", response_model=ExtensionResponse)
@requires_role("coordenacao")
@audit_operation
async def reject_extension(
    extension_id: str,
    body: ExtensionRejectRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ExtensionResponse:
    """Rejeita prorrogacao/trancamento pendente, com motivo obrigatorio."""
    return await service.reject_extension(extension_id, body.motivo, user)
