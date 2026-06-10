"""
Router FastAPI para os endpoints de atividades creditáveis.

Responsabilidades:
- GET /api/v1/activities: lista atividades com filtros de student_id, status e categoria.
  Aluno vê as próprias; orientador vê dos orientandos; coordenação vê todas.
- POST /api/v1/activities: aluno registra nova atividade. Motor RL04 verifica elegibilidade
  preliminar imediatamente. Aplica @requires_role('aluno'), @audit_operation,
  @check_deadlines (verifica data_realizacao dentro do período do curso) e @trigger_alerts
  (notifica orientador após submissão).
- PATCH /api/v1/activities/{activity_id}/validate: orientador emite parecer ou coordenação
  aprova/rejeita. Operação mais crítica do fluxo — aplica @requires_role, @audit_operation
  e @trigger_alerts (notifica aluno após decisão). Motor verifica elegibilidade (RL04).
"""
"""
Router de atividades — PATCH /activities/{id}/validate
"""
"""
Router de atividades — PATCH /activities/{id}/validate
"""

from fastapi import APIRouter, Depends

from backend.app.core.auth_dependency import get_current_user
from backend.app.models.activity import ActivityResponse, ValidateActivityRequest
from backend.app.services import activity_service

router = APIRouter()


@router.patch("/activities/{activity_id}/validate", response_model=ActivityResponse)
async def validate_activity(
    activity_id: str,
    payload: ValidateActivityRequest,
    current_user: dict = Depends(get_current_user),
) -> ActivityResponse:
    """
    Valida uma atividade submetida.

    Ação `parecer_orientador`:
    - Apenas o orientador do próprio aluno pode emitir (A01 por propriedade)
    - Operação auditada (A02)
    """
    if payload.acao.value == "parecer_orientador":
        return await activity_service.emitir_parecer_orientador(
            activity_id=activity_id,
            payload=payload,
            current_user=current_user,
        )

    # Outras ações (aprovar, rejeitar) serão implementadas em issues futuras
    from fastapi import HTTPException, status
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Ação '{payload.acao}' ainda não implementada.",
    )