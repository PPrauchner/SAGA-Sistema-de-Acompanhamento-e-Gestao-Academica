"""Router FastAPI para solicitacoes de prorrogacao."""

from typing import Any

from fastapi import APIRouter, Depends, Query, status

from backend.app.aspects.alerts import trigger_alerts
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


def _build_notificacao_aprovacao(
    result: Any, args: tuple, kwargs: dict
) -> dict[str, Any] | None:
    """Notifica o aluno após a aprovação da prorrogação/trancamento (A05 — After advice).

    Lê o uid do aluno e o novo prazo do resultado do service e compõe a mensagem. Retorna
    None quando o aluno não pode ser resolvido — nesse caso nenhuma notificação é emitida.
    """
    if not isinstance(result, dict):
        return None
    aluno_uid = result.get("aluno_uid")
    if not aluno_uid:
        return None
    label = "trancamento" if result.get("tipo") == "trancamento" else "prorrogação"
    nova_data = result.get("nova_data")
    if nova_data is not None and hasattr(nova_data, "strftime"):
        mensagem = f"Sua solicitação de {label} foi aprovada. Novo prazo: {nova_data.strftime('%d/%m/%Y')}."
    else:
        mensagem = f"Sua solicitação de {label} foi aprovada."
    return {
        "tipo": "prorrogacao_aprovada",
        "titulo": "Solicitação aprovada",
        "mensagem": mensagem,
        "destinatario_id": aluno_uid,
        "entidade_tipo": "extensions",
        "entidade_id": result.get("id", ""),
        "programa_id": result.get("programa_id"),
    }


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
@trigger_alerts(_build_notificacao_aprovacao)
async def approve_extension(
    extension_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> ExtensionResponse:
    """Aprova prorrogacao/trancamento pendente e recalcula o prazo do aluno.

    Aplica @trigger_alerts (A05) para notificar o aluno do resultado e do novo prazo.
    """
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
