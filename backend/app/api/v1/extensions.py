"""
Router FastAPI para os endpoints de prorrogação de prazo (Spec 08).

Responsabilidades:
- Expor as rotas de solicitação, parecer, decisão e listagem, delegando toda a
  lógica ao ExtensionService.
- Aplicar os aspectos AOP nos join points da Spec 08, na ordem canônica.

Nota sobre A04: `@check_deadlines` não é aplicado aqui. O aspecto A04 é específico
do fluxo de tasks do plano de trabalho (`WorkPlanService.add_progress_update`) —
depende de `_repo.get_task_context(task_id)`, inexistente no domínio de prorrogações.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from backend.app.aspects.alerts import trigger_alerts, build_extension_alert
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.extension import (
    DecisionRequest,
    ExtensionCreateRequest,
    ExtensionResponse,
    ReviewRequest,
)
from backend.app.services.extension_service import ExtensionService

router = APIRouter(prefix="/extensions", tags=["Prorrogações"])


async def get_extension_service() -> ExtensionService:
    return ExtensionService()


AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
Service = Annotated[ExtensionService, Depends(get_extension_service)]


@router.post(
    "",
    response_model=ExtensionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar prorrogação (aluno)",
)
@requires_role("aluno")
@audit_operation
async def create_extension(
    payload: ExtensionCreateRequest,
    current_user: AuthUser,
    service: Service,
) -> ExtensionResponse:
    """Cria uma solicitação de prorrogação com status 'pendente'."""
    return await service.create_extension(payload=payload, requester_uid=current_user.uid)


@router.get(
    "",
    response_model=list[ExtensionResponse],
    summary="Listar prorrogações (escopo por papel)",
)
@requires_role("aluno", "orientador", "coordenacao")
async def list_extensions(
    current_user: AuthUser,
    service: Service,
) -> list[ExtensionResponse]:
    """Lista prorrogações conforme o papel: aluno (próprias), orientador
    (orientandos), coordenação (programa)."""
    return await service.list_for_user(current_user)


@router.patch(
    "/{extension_id}/review",
    response_model=ExtensionResponse,
    summary="Emitir parecer técnico (orientador)",
)
@requires_role("orientador")
@audit_operation
async def review_extension(
    extension_id: str,
    payload: ReviewRequest,
    current_user: AuthUser,
    service: Service,
) -> ExtensionResponse:
    """Registra o parecer técnico do orientador sobre a solicitação."""
    return await service.add_review(
        extension_id=extension_id,
        payload=payload,
        orientador_uid=current_user.uid,
    )


@router.patch(
    "/{extension_id}/approve",
    response_model=ExtensionResponse,
    summary="Homologar decisão (coordenação)",
)
@requires_role("coordenacao")
@audit_operation
@trigger_alerts(build_extension_alert)
async def decide_extension(
    extension_id: str,
    payload: DecisionRequest,
    current_user: AuthUser,
    service: Service,
) -> ExtensionResponse:
    """Homologa a decisão (aprovar/rejeitar); na aprovação recalcula o prazo."""
    return await service.process_decision(
        extension_id=extension_id,
        payload=payload,
        coordinator_uid=current_user.uid,
    )
