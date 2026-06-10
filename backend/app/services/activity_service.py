"""
Serviço de negócio para registro e validação de atividades creditáveis.

Responsabilidades:
- submit_activity(): aluno registra atividade. Executa motor RL04 via InferenceService para
  calcular elegibilidade_preliminar. Decorado com @requires_role('aluno'),
  @audit_operation, @check_deadlines e @trigger_alerts.
- advisor_review(): orientador emite parecer (sem aprovar). Decorado com
  @requires_role('orientador') e @audit_operation.
- validate_activity(): coordenação aprova ou rejeita atividade definitivamente.
  Atualiza creditos_gerados, status e gera fato producao_bibliografica_validada se aplicável.
  Decorado com @requires_role('coordenacao'), @audit_operation e @trigger_alerts.
- list_activities(): filtra atividades por student_id, status e categoria respeitando
  permissões por papel.
- Calcular créditos por categoria para verificação dos fatos creditos_grupo_* do motor.
"""
"""
Service de atividades.

Lógica de negócio para validação de atividades.
Aspectos A01 (autorização por propriedade) e A02 (auditoria) são aplicados aqui.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_ownership, requires_role
from backend.app.models.activity import (
    ActivityResponse,
    ActivityStatus,
    ValidateAction,
    ValidateActivityRequest,
)
from backend.app.repositories.activity_repository import ActivityRepository

logger = logging.getLogger(__name__)

_repo = ActivityRepository()


async def _get_advisor_uid_for_activity(kwargs: dict) -> str | None:
    """
    Resolve o uid do orientador responsável pela atividade.
    Usado pelo A01 (requires_ownership) para verificação por propriedade.
    """
    activity_id: str = kwargs.get("activity_id", "")
    activity = _repo.get_by_id(activity_id)
    if not activity:
        return None
    student_id = activity.get("student_id", "")
    return _repo.get_advisor_uid_by_student(student_id)


@requires_role("orientador", "coordenacao")
@requires_ownership(_get_advisor_uid_for_activity)
@audit_operation(
    operacao="parecer_orientador",
    entidade="activities",
    get_entity_id_fn=lambda kwargs: kwargs.get("activity_id"),
)
async def emitir_parecer_orientador(
    activity_id: str,
    payload: ValidateActivityRequest,
    current_user: dict,
) -> ActivityResponse:
    """
    Emite o parecer do orientador sobre uma atividade submetida.

    - A01: apenas orientador do próprio aluno (por propriedade) ou coordenação
    - A02: operação auditada no Firestore
    """
    if payload.acao != ValidateAction.parecer_orientador:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta função aceita apenas a ação 'parecer_orientador'.",
        )

    if not payload.parecer_orientador:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campo 'parecer_orientador' é obrigatório para esta ação.",
        )

    activity = _repo.get_by_id(activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atividade não encontrada.",
        )

    if activity["status"] not in (
        ActivityStatus.pendente,
        ActivityStatus.parecer_emitido,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Atividade com status '{activity['status']}' não pode receber parecer.",
        )

    update_data = {
        "status": ActivityStatus.parecer_emitido,
        "parecer_orientador": payload.parecer_orientador.model_dump(),
        "parecer_orientador_em": datetime.now(timezone.utc),
        "parecer_orientador_por": current_user["uid"],
    }

    updated = _repo.update(activity_id, update_data)
    return ActivityResponse(**updated)  