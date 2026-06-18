"""
Router FastAPI para os endpoints de atividades creditáveis.

Responsabilidades:
- GET /api/v1/activities: lista atividades com filtros de student_id, status e categoria.
  Aluno vê as próprias; orientador vê dos orientandos; coordenação vê todas.
- POST /api/v1/activities: aluno registra nova atividade. Motor RL04 verifica elegibilidade
  preliminar imediatamente. Aplica @requires_role('aluno'), @audit_operation,
  @check_deadlines (verifica data_realizacao dentro do período do curso) e @trigger_alerts
  (notifica orientador após submissão).
- POST /api/v1/activities/{activity_id}/comprovante: aluno faz upload real do comprovante
  (PDF/JPEG/PNG) ao Firebase Storage. Backend persiste no bucket via Admin SDK e devolve a
  URL de download tokenizada. Aplica @requires_role('aluno') e @audit_operation.
- PATCH /api/v1/activities/{activity_id}/validate: orientador emite parecer ou coordenação
  aprova/rejeita. Operação mais crítica do fluxo — aplica @requires_role, @audit_operation
  e @trigger_alerts (notifica aluno após decisão). Motor verifica elegibilidade (RL04).
"""

from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.deadline_validation import check_deadlines
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.activity import (
    ActivityCreateRequest,
    ActivityCreateResponse,
    ActivityResponse,
    ComprovanteUploadResponse,
)
from backend.app.services.activity_service import ActivityService
from backend.app.services.comprovante_service import ComprovanteService

router = APIRouter()

service = ActivityService()
comprovante_service = ComprovanteService()


def _build_submission_alert(
    result: dict[str, Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any] | None:
    """Builder do aspecto A05: notifica o orientador quando a atividade é submetida.

    Retorna None quando a atividade ficou em rascunho ou não há orientador resolvido —
    nesses casos nenhuma notificação é emitida.
    """
    if not result.get("notificacao_enviada") or not result.get("orientador_uid"):
        return None
    return {
        "tipo": "atividade_submetida",
        "titulo": "Nova atividade submetida",
        "mensagem": f"Aluno {result.get('aluno_nome', '')} submeteu atividade para validação",
        "destinatario_id": result["orientador_uid"],
        "entidade_tipo": "activity",
        "entidade_id": result["id"],
        "programa_id": result.get("programa_id"),
    }


@router.get("/activities", response_model=list[ActivityResponse])
@requires_role("aluno", "orientador", "coordenacao")
async def list_activities(
    student_id: str | None = Query(None),
    status: str | None = Query(None),
    categoria: str | None = Query(None),
    user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await service.list_activities(user, student_id, status, categoria)


@router.post(
    "/activities",
    response_model=ActivityCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
@requires_role("aluno")
@audit_operation
@check_deadlines
@trigger_alerts(_build_submission_alert)
async def create_activity(
    body: ActivityCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.submit_activity(body, user)


@router.post("/activities/{activity_id}/comprovante")
@requires_role("aluno")
@audit_operation
async def upload_comprovante(
    activity_id: str,
    arquivo: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> ComprovanteUploadResponse:
    result = await comprovante_service.upload(activity_id, arquivo, user)
    return ComprovanteUploadResponse(**result)
