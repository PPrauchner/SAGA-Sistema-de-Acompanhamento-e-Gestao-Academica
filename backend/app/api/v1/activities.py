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
  e @trigger_alerts (notifica aluno após decisão da coordenação). Motor verifica
  elegibilidade (RL04) e gera fato producao_bibliografica_validada quando aplicável.
"""

from fastapi import APIRouter, Depends
from typing import Union

from backend.app.core.auth_dependency import get_current_user
from backend.app.models.activity import (
    ActivityResponse,
    ValidateActivityRequest,
    ValidateActivityResponse,
)
from backend.app.services import activity_service

router = APIRouter()


@router.patch(
    "/activities/{activity_id}/validate",
    response_model=Union[ActivityResponse, ValidateActivityResponse],
)
async def validate_activity(
    activity_id: str,
    payload: ValidateActivityRequest,
    current_user: dict = Depends(get_current_user),
) -> Union[ActivityResponse, ValidateActivityResponse]:
    """
    Valida uma atividade submetida.

    Ação `parecer_orientador`:
    - Apenas o orientador do próprio aluno pode emitir (A01 por propriedade)
    - Operação auditada (A02)
    - Retorna ActivityResponse com status atualizado para 'parecer_emitido'

    Ação `aprovar` | `rejeitar` (coordenação):
    - Apenas coordenação (A01)
    - Operação mais crítica — auditada com detalhes (A02)
    - Contabiliza créditos e gera fato para o motor se produção bibliográfica (RL04/RL05)
    - Notifica o aluno do resultado (A05 — história 26)
    - Retorna ValidateActivityResponse com novo_status, creditos_contabilizados e fato_gerado
    """
    if payload.acao.value == "parecer_orientador":
        return await activity_service.emitir_parecer_orientador(
            activity_id=activity_id,
            payload=payload,
            current_user=current_user,
        )

    return await activity_service.validate_activity(
        activity_id=activity_id,
        payload=payload,
        current_user=current_user,
    )