"""
extensions.py — Router FastAPI para o módulo de Prorrogações de Prazo.

Cada endpoint aplica os decoradores AOP na ordem canônica obrigatória:
    @requires_role     → A01: Controle de acesso por papel
    @audit_operation   → A02: Gravação em audit_logs
    @check_deadlines   → A04: Recalcula prazos para o motor lógico
    @trigger_alerts    → A05: Notificação in-app em tempo real

Os endpoints NÃO contêm lógica de segurança, logs ou notificações —
toda essa responsabilidade pertence exclusivamente aos decoradores acima.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.aspects.audit      import audit_operation       # A02
from app.aspects.deadlines  import check_deadlines       # A04
from app.aspects.alerts     import trigger_alerts        # A05
from app.aspects.auth       import requires_role, get_current_user  # A01
from app.models.extension   import (
    ExtensionCreateRequest,
    ReviewRequest,
    DecisionRequest,
    ExtensionResponse,
)
from app.services.extensions_service import ExtensionsService
from app.dependencies import get_extensions_service  # injeção de dependência do serviço

router = APIRouter(
    prefix="/api/v1/extensions",
    tags=["Prorrogações"],
)

# ---------------------------------------------------------------------------
# Alias de tipo para o usuário autenticado injetado
# ---------------------------------------------------------------------------
CurrentUser = Annotated[dict, Depends(get_current_user)]
Service     = Annotated[ExtensionsService, Depends(get_extensions_service)]


# ---------------------------------------------------------------------------
# POST /api/v1/extensions
# Role: aluno (apenas o próprio)
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ExtensionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar solicitação de prorrogação (aluno)",
)
@requires_role("aluno")
@audit_operation
@check_deadlines
@trigger_alerts
async def create_extension(
    payload:      ExtensionCreateRequest,
    current_user: CurrentUser,
    service:      Service,
) -> ExtensionResponse:
    """
    Cria uma nova solicitação de prorrogação de prazo com status 'pendente'.

    Regras de negócio aplicadas pelo serviço:
    - Não pode existir outra solicitação pendente para o aluno.
    - O número de prorrogações aprovadas não pode exceder o limite configurado.
    """
    return await service.create_extension(
        student_id=current_user["uid"],
        payload=payload,
        requesting_uid=current_user["uid"],
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/extensions/{student_id}/{extension_id}/review
# Role: orientador (apenas de seus orientandos)
# ---------------------------------------------------------------------------

@router.patch(
    "/{student_id}/{extension_id}/review",
    response_model=ExtensionResponse,
    summary="Emitir parecer técnico (orientador)",
)
@requires_role("orientador")
@audit_operation
@check_deadlines
@trigger_alerts
async def review_extension(
    student_id:   str,
    extension_id: str,
    payload:      ReviewRequest,
    current_user: CurrentUser,
    service:      Service,
) -> ExtensionResponse:
    """
    Permite ao orientador emitir o parecer técnico de uma prorrogação pendente.

    Validação de vínculo: o UID do token deve corresponder ao `orientador_id`
    registrado no documento do discente — verificado dentro do serviço.
    """
    return await service.add_review(
        student_id=student_id,
        extension_id=extension_id,
        parecer=payload.parecer_orientador,
        orientador_uid=current_user["uid"],
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/extensions/{student_id}/{extension_id}/decision
# Role: coordenacao
# ---------------------------------------------------------------------------

@router.patch(
    "/{student_id}/{extension_id}/decision",
    response_model=ExtensionResponse,
    summary="Deferir ou indeferir prorrogação (coordenação)",
)
@requires_role("coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts
async def decide_extension(
    student_id:   str,
    extension_id: str,
    payload:      DecisionRequest,
    current_user: CurrentUser,
    service:      Service,
) -> ExtensionResponse:
    """
    Processa a decisão final da coordenação via transação atômica do Firestore.

    Em caso de aprovação:
    - Altera o status da prorrogação para 'aprovada'.
    - Atualiza `situacao_registrada` e `prazo_final` no documento do aluno
      dentro da mesma transação.
    """
    return await service.process_decision(
        student_id=student_id,
        extension_id=extension_id,
        payload=payload,
        coordinator_uid=current_user["uid"],
    )


# ---------------------------------------------------------------------------
# GET  — Listagens por papel
# ---------------------------------------------------------------------------

@router.get(
    "/{student_id}",
    response_model=list[ExtensionResponse],
    summary="Listar prorrogações do aluno",
)
@requires_role("aluno", "coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts
async def list_student_extensions(
    student_id:   str,
    current_user: CurrentUser,
    service:      Service,
) -> list[ExtensionResponse]:
    """Retorna o histórico completo de prorrogações de um aluno."""
    return await service.list_by_student(student_id)


@router.get(
    "",
    response_model=list[ExtensionResponse],
    summary="Listar pendentes para o orientador",
)
@requires_role("orientador")
@audit_operation
@check_deadlines
@trigger_alerts
async def list_advisor_pending(
    current_user: CurrentUser,
    service:      Service,
) -> list[ExtensionResponse]:
    """Retorna prorrogações pendentes de todos os orientandos do orientador autenticado."""
    return await service.list_pending_for_advisor(current_user["uid"])


@router.get(
    "/all/pending",
    response_model=list[ExtensionResponse],
    summary="Listar todas as pendências (coordenação)",
)
@requires_role("coordenacao")
@audit_operation
@check_deadlines
@trigger_alerts
async def list_all_pending(
    current_user: CurrentUser,
    service:      Service,
) -> list[ExtensionResponse]:
    """Retorna todas as prorrogações pendentes do sistema para deliberação."""
    return await service.list_all_pending()