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
  e @trigger_alerts (notifica aluno após decisão da coordenação). Motor verifica
  elegibilidade (RL04) e gera fato producao_bibliografica_validada quando aplicável.
"""
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, File, UploadFile

from backend.app.core.auth import get_current_user
from backend.app.models.activity import (
    ActivityCreateRequest,
    ActivityCreateResponse,
    ActivityResponse,
    ComprovanteUploadResponse,
    ValidateActivityRequest,
    ValidateActivityResponse,
)
from backend.app.services import activity_service
from backend.app.services.activity_service import ActivityService
from backend.app.services.comprovante_service import ComprovanteService

router = APIRouter()

_activity_service = ActivityService()
_comprovante_service = ComprovanteService()


# ---------------------------------------------------------------------------
# GET /activities
# ---------------------------------------------------------------------------

@router.get(
    "/activities",
    response_model=List[ActivityResponse],
)
async def list_activities(
    student_id: Optional[str] = None,
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
) -> List[ActivityResponse]:
    """
    Lista atividades visíveis para o usuário autenticado.
    - Aluno: vê apenas as próprias atividades.
    - Orientador: vê atividades dos seus orientandos.
    - Coordenação: vê todas.
    Suporta filtros opcionais de student_id, status e categoria.
    """
    rows = await _activity_service.list_activities(
        user=current_user,
        student_id=student_id,
        status_filter=status,
        categoria=categoria,
    )
    return [ActivityResponse(**row) for row in rows]


# ---------------------------------------------------------------------------
# POST /activities
# ---------------------------------------------------------------------------

@router.post(
    "/activities",
    response_model=ActivityCreateResponse,
    status_code=201,
)
async def submit_activity(
    payload: ActivityCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> ActivityCreateResponse:
    """
    Registra nova atividade creditável para o aluno autenticado.
    O motor RL04 verifica elegibilidade preliminar imediatamente após a criação.
    Notifica o orientador caso o status inicial seja 'enviado'.
    """
    result = await _activity_service.submit_activity(data=payload, user=current_user)
    return ActivityCreateResponse(
        id=result["id"],
        elegibilidade_preliminar=result["elegibilidade_preliminar"],
        notificacao_enviada=result["notificacao_enviada"],
    )


# ---------------------------------------------------------------------------
# POST /activities/{activity_id}/comprovante
# ---------------------------------------------------------------------------

@router.post(
    "/activities/{activity_id}/comprovante",
    response_model=ComprovanteUploadResponse,
)
async def upload_comprovante(
    activity_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> ComprovanteUploadResponse:
    """
    Faz upload do comprovante (PDF/JPEG/PNG) para o Firebase Storage.
    Persiste a URL tokenizada de download na atividade correspondente.
    Restrito ao aluno dono da atividade.
    """
    result = await _comprovante_service.upload(
        activity_id=activity_id,
        arquivo=file,
        user=current_user,
    )
    return ComprovanteUploadResponse(
        comprovante_url=result["comprovante_url"],
        path_bucket=result["path_bucket"],
    )


# ---------------------------------------------------------------------------
# PATCH /activities/{activity_id}/validate
# ---------------------------------------------------------------------------

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