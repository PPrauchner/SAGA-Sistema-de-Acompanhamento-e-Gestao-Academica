"""
Router FastAPI para os endpoints de atividades creditáveis.
Responsabilidades:
- GET /api/v1/activities: lista atividades com filtros de student_id, status e categoria.
  Aluno vê as próprias; orientador vê dos orientandos; coordenação vê todas.
- POST /api/v1/activities: aluno registra nova atividade. Motor RL04 verifica elegibilidade
  preliminar imediatamente. Aplica @requires_role('aluno'), @audit_operation,
  @check_deadlines (verifica data_realizacao dentro do período do curso) e @trigger_alerts
  (notifica orientador após submissão).
- POST /api/v1/activities/orientador: orientador cria atividade para um orientando seu. A
  criação já é o endosso — nasce em 'enviado' com o parecer preenchido, direto na fila da
  coordenação. Aplica @requires_role('orientador'), @requires_ownership (A01 por
  propriedade → 403 para não-orientandos), @audit_operation, @check_deadlines e
  @trigger_alerts (notifica a coordenação do programa).
- POST /api/v1/activities/{activity_id}/comprovante: aluno faz upload real do comprovante
  (PDF/JPEG/PNG) ao Firebase Storage. Backend persiste no bucket via Admin SDK e devolve a
  URL de download tokenizada. Aplica @requires_role('aluno') e @audit_operation.
- PATCH /api/v1/activities/{activity_id}/parecer: orientador emite parecer sobre a atividade
  do próprio orientando. Aplica @requires_role('orientador'), @requires_ownership (A01 por
  propriedade) e @audit_operation. O parecer é um campo; não altera o status.
- PATCH /api/v1/activities/{activity_id}/validate: coordenação aprova/rejeita definitivamente.
  Operação mais crítica do fluxo — aplica @requires_role('coordenacao'), @audit_operation e
  @trigger_alerts (notifica o aluno do resultado). Motor verifica elegibilidade (RL04) e gera
  fato producao_bibliografica_validada quando aplicável.
"""
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_ownership, requires_role
from backend.app.aspects.deadline_validation import check_deadlines
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.models.activity import (
    ActivityCreateByAdvisorRequest,
    ActivityCreateRequest,
    ActivityCreateResponse,
    ActivityResponse,
    ActivityStatus,
    ComprovanteUploadResponse,
    ParecerRequest,
    ValidateActivityRequest,
    ValidateActivityResponse,
)
from backend.app.services import activity_service
from backend.app.services.activity_service import ActivityService
from backend.app.services.comprovante_service import ComprovanteService

router = APIRouter()

_activity_service = ActivityService()
_comprovante_service = ComprovanteService()


def _build_notificacao_submissao(result, args, kwargs):
    """Notifica o orientador após submissão de atividade pelo aluno."""
    if not isinstance(result, dict):
        return None
    orientador_uid = result.get("orientador_uid")
    if not orientador_uid:
        return None
    activity_id = result.get("id", "")
    aluno_nome = result.get("aluno_nome", "")
    return {
        "tipo": "atividade_submetida",
        "titulo": "Nova atividade para revisão",
        "mensagem": f"O aluno {aluno_nome} submeteu uma nova atividade (ID: {activity_id}).",
        "destinatario_id": orientador_uid,
        "entidade_tipo": "activities",
        "entidade_id": activity_id,
    }


# ---------------------------------------------------------------------------
# GET /activities
# ---------------------------------------------------------------------------

@router.get(
    "/activities",
    response_model=list[ActivityResponse],
)
@requires_role("aluno", "orientador", "coordenacao")
async def list_activities(
    student_id: str | None = None,
    status: str | None = None,
    categoria: str | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> list[ActivityResponse]:
    """
    Lista atividades visíveis para o usuário autenticado.
    - Aluno: vê apenas as próprias atividades.
    - Orientador: vê atividades dos seus orientandos.
    - Coordenação: vê todas.
    Suporta filtros opcionais de student_id, status e categoria.
    """
    rows = await _activity_service.list_activities(
        user=user,
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
@requires_role("aluno")
@audit_operation
@check_deadlines
@trigger_alerts(_build_notificacao_submissao)
async def submit_activity(
    payload: ActivityCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ActivityCreateResponse:
    """
    Registra nova atividade creditável para o aluno autenticado.
    O motor RL04 verifica elegibilidade preliminar imediatamente após a criação.
    Notifica o orientador caso o status inicial seja 'enviado'.
    """
    result = await _activity_service.submit_activity(data=payload, user=user)
    return ActivityCreateResponse(
        id=result["id"],
        elegibilidade_preliminar=result["elegibilidade_preliminar"],
        notificacao_enviada=result["notificacao_enviada"],
        created_activity_ids=result.get("created_activity_ids", [result["id"]]),
        activity_group_id=result.get("activity_group_id"),
    )


# ---------------------------------------------------------------------------
# POST /activities/orientador  (orientador cria para orientando — issue #263)
# ---------------------------------------------------------------------------

def _owner_uid_do_orientando(kwargs: dict[str, Any]):
    """Resolver do A01 por propriedade: uid do orientador do aluno alvo (via payload).

    Lê o `aluno_id` do corpo da requisição e delega ao service a resolução
    aluno → orientador. Retorna None (→ 404 no aspecto) quando não há `aluno_id`.
    """
    payload = kwargs.get("payload")
    aluno_id = getattr(payload, "aluno_id", None)
    if not aluno_id:
        return None
    return activity_service.resolve_advisor_uid_for_student(aluno_id)


def _build_notificacao_criacao_orientador(result, args, kwargs) -> list[dict[str, Any]]:
    """Notifica a coordenação do programa quando o orientador cria uma atividade.

    A atividade nasce direto na fila da coordenação; emite uma notificação (A05) por
    coordenador do programa (`coord_uids` resolvido pelo service).
    """
    if not isinstance(result, dict):
        return []
    activity_id = result.get("id", "")
    aluno_nome = result.get("aluno_nome", "")
    return [
        {
            "tipo": "atividade_submetida",
            "titulo": "Nova atividade para validação",
            "mensagem": f"O orientador registrou uma atividade de {aluno_nome} para validação.",
            "destinatario_id": coord_uid,
            "entidade_tipo": "activities",
            "entidade_id": activity_id,
            "programa_id": result.get("programa_id"),
        }
        for coord_uid in result.get("coord_uids", [])
    ]


@router.post(
    "/activities/orientador",
    response_model=ActivityCreateResponse,
    status_code=201,
)
@requires_role("orientador")
@requires_ownership(_owner_uid_do_orientando)
@audit_operation
@check_deadlines
@trigger_alerts(_build_notificacao_criacao_orientador)
async def submit_activity_by_advisor(
    payload: ActivityCreateByAdvisorRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Orientador cria atividade creditável para um orientando seu.
    - Apenas o orientador do próprio aluno pode criar (A01 por propriedade → 403)
    - A atividade nasce em 'enviado' com o parecer preenchido (pula o passo de parecer)
    - Créditos só são contabilizados na validação da coordenação (US-CR01 intacto)
    - Notifica a coordenação do programa (A05) — a atividade entra direto na fila dela

    Retorna o dict do service (não o ActivityCreateResponse) para que @trigger_alerts leia
    `coord_uids`; o response_model=ActivityCreateResponse serializa a resposta HTTP,
    descartando as chaves auxiliares.
    """
    return await _activity_service.submit_activity_for_orientando(data=payload, user=user)


# ---------------------------------------------------------------------------
# POST /activities/{activity_id}/comprovante
# ---------------------------------------------------------------------------

@router.post(
    "/activities/{activity_id}/comprovante",
    response_model=ComprovanteUploadResponse,
)
@requires_role("aluno")
@audit_operation
async def upload_comprovante(
    activity_id: str,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> ComprovanteUploadResponse:
    """
    Faz upload do comprovante (PDF/JPEG/PNG) para o Firebase Storage.
    Persiste a URL tokenizada de download na atividade correspondente.
    Restrito ao aluno dono da atividade.
    """
    result = await _comprovante_service.upload(
        activity_id=activity_id,
        arquivo=file,
        user=user,
    )
    return ComprovanteUploadResponse(
        comprovante_url=result["comprovante_url"],
        path_bucket=result["path_bucket"],
    )


# ---------------------------------------------------------------------------
# PATCH /activities/{activity_id}/parecer  (orientador — issue #48)
# ---------------------------------------------------------------------------

def _owner_uid_da_atividade(kwargs: dict[str, Any]):
    """Resolver do A01 por propriedade: uid do orientador responsável pela atividade.

    Recebe os kwargs do endpoint (contêm `activity_id`) e delega a resolução em dois
    saltos ao service. Retorna uma coroutine — o aspecto @requires_ownership a aguarda.
    """
    return activity_service.resolve_advisor_uid_for_activity(kwargs.get("activity_id"))


@router.patch(
    "/activities/{activity_id}/parecer",
    response_model=ActivityResponse,
)
@requires_role("orientador")
@requires_ownership(_owner_uid_da_atividade)
@audit_operation
async def emitir_parecer(
    activity_id: str,
    payload: ParecerRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ActivityResponse:
    """
    Orientador emite parecer textual sobre uma atividade submetida pelo orientando.
    - Apenas o orientador do próprio aluno pode emitir (A01 por propriedade)
    - Operação auditada (A02)
    - O parecer é um campo da atividade; o status permanece 'enviado' até a coordenação decidir
    """
    return await activity_service.emitir_parecer_orientador(
        activity_id=activity_id,
        payload=payload,
        current_user=user,
    )


# ---------------------------------------------------------------------------
# PATCH /activities/{activity_id}/validate  (coordenação — issue #49)
# ---------------------------------------------------------------------------

async def _build_notificacao_validacao(result, args, kwargs):
    """Notifica o aluno após a decisão da coordenação (A05 — After advice).

    Resolve o destinatário (uid do aluno dono da atividade) a partir do activity_id dos
    kwargs e usa o novo_status do resultado para compor a mensagem. Retorna None quando o
    aluno não pode ser resolvido — nesse caso nenhuma notificação é emitida.
    """
    activity_id = kwargs.get("activity_id")
    if not activity_id:
        return None
    aluno_uid = await activity_service.resolve_student_uid_for_activity(activity_id)
    if not aluno_uid:
        return None
    aprovada = getattr(result, "novo_status", None) == ActivityStatus.aprovado
    label = "aprovada" if aprovada else "rejeitada"
    return {
        "tipo": "atividade_validada",
        "titulo": "Atividade validada",
        "mensagem": f"Sua atividade foi {label} pela coordenação.",
        "destinatario_id": aluno_uid,
        "entidade_tipo": "activities",
        "entidade_id": activity_id,
    }


@router.patch(
    "/activities/{activity_id}/validate",
    response_model=ValidateActivityResponse,
)
@requires_role("coordenacao")
@audit_operation
@trigger_alerts(_build_notificacao_validacao)
async def validate_activity(
    activity_id: str,
    payload: ValidateActivityRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ValidateActivityResponse:
    """
    Coordenação aprova ou rejeita definitivamente a atividade submetida.
    - Apenas coordenação (A01)
    - Operação mais crítica — auditada com detalhes (A02)
    - Contabiliza créditos e gera fato para o motor se produção bibliográfica (RL04/RL05)
    - Retorna ValidateActivityResponse com novo_status, creditos_contabilizados e fato_gerado
    """
    return await activity_service.validate_activity(
        activity_id=activity_id,
        payload=payload,
        current_user=user,
    )
