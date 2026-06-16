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

from fastapi import APIRouter, Depends, File, UploadFile

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.activity import ComprovanteUploadResponse
from backend.app.services.comprovante_service import ComprovanteService

router = APIRouter()

comprovante_service = ComprovanteService()


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
