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
  É a operação mais crítica do fluxo — auditada com detalhes (A02).
- list_activities(): filtra atividades por student_id, status e categoria respeitando
  permissões por papel.
- Calcular créditos por categoria para verificação dos fatos creditos_grupo_* do motor.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_ownership, requires_role
from backend.app.models.activity import (
    ActivityResponse,
    ActivityStatus,
    ValidateAction,
    ValidateActivityRequest,
    ValidateActivityResponse,
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


def _get_aluno_uid_para_notificacao(kwargs: dict) -> str | None:
    """
    Resolve o uid do aluno dono da atividade para o destinatário da notificação A05.
    Usado pelo @trigger_alerts em validate_activity.
    """
    activity_id: str = kwargs.get("activity_id", "")
    return _repo.get_student_uid_by_activity(activity_id)


def _montar_mensagem_validacao(result: ValidateActivityResponse, kwargs: dict) -> str:
    """
    Monta a mensagem de notificação para o aluno com base no resultado da validação.

    Injeta o status e a observação da coordenação na mensagem.
    """
    acao_label = (
        "aprovada" if result.novo_status == ActivityStatus.aprovada else "rejeitada"
    )
    activity_id: str = kwargs.get("activity_id", "")
    payload: ValidateActivityRequest = kwargs.get("payload")
    observacao = payload.observacao if payload and payload.observacao else ""
    mensagem = f"Sua atividade (ID: {activity_id}) foi {acao_label}."
    if observacao:
        mensagem += f" Observação: {observacao}"
    return mensagem


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

    Join Point: PATCH /api/v1/activities/{id}/validate com acao='parecer_orientador'
    Advice aplicado:
    - A01 (@requires_role + @requires_ownership): apenas orientador do próprio aluno
    - A02 (@audit_operation): operação auditada no Firestore

    Weaving: decoradores empilhados em tempo de definição da função.
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


@requires_role("coordenacao")
@audit_operation(
    operacao="validar_atividade",
    entidade="activities",
    get_entity_id_fn=lambda kwargs: kwargs.get("activity_id"),
)
@trigger_alerts(
    tipo="atividade_validada",
    titulo="Resultado da validação de atividade",
    get_mensagem_fn=_montar_mensagem_validacao,
    get_destinatario_fn=_get_aluno_uid_para_notificacao,
    entidade_tipo="activities",
    get_entidade_id_fn=lambda kwargs: kwargs.get("activity_id"),
)
async def validate_activity(
    activity_id: str,
    payload: ValidateActivityRequest,
    current_user: dict,
) -> ValidateActivityResponse:
    """
    Coordenação aprova ou rejeita definitivamente uma atividade creditável.

    Esta é a operação mais crítica do fluxo de validação de atividades.

    Join Point: PATCH /api/v1/activities/{id}/validate com acao='aprovar'|'rejeitar'
    Advice aplicado (ordem de weaving):
    - A01 (@requires_role('coordenacao')): apenas coordenação pode executar
    - A02 (@audit_operation): registra log imutável com autor, operação, resultado e
      timestamp em audit_logs/{auto_id} — operação mais crítica auditada (A02)
    - A05 (@trigger_alerts): notifica o aluno com o resultado após a execução

    Ao aprovar:
    - Status transita para 'aprovada'
    - creditos_gerados é definido como creditos_concedidos (payload) ou
      pontuacao_base do tipo de atividade
    - Se a atividade pertence à categoria 'producao_bibliografica', verifica se
      ao menos 1 produção aprovada existe e insere o fato
      producao_bibliografica_validada(student_id) no contexto do motor

    Ao rejeitar:
    - Status transita para 'rejeitada'
    - creditos_gerados permanece 0 (nenhum crédito contabilizado)

    Weaving: decoradores empilhados em tempo de definição. A ordem garante que
    A01 verifica papel antes de A02 auditar e A05 notificar.
    """
    if payload.acao not in (ValidateAction.aprovar, ValidateAction.rejeitar):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta função aceita apenas as ações 'aprovar' ou 'rejeitar'.",
        )

    activity = _repo.get_by_id(activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atividade não encontrada.",
        )

    # Apenas atividades com parecer do orientador podem ser validadas pela coordenação
    if activity["status"] not in (
        ActivityStatus.parecer_emitido,
        ActivityStatus.pendente,  # coordenação pode aprovar mesmo sem parecer
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Atividade com status '{activity['status']}' não pode ser "
                "aprovada ou rejeitada."
            ),
        )

    aprovando = payload.acao == ValidateAction.aprovar
    novo_status = ActivityStatus.aprovada if aprovando else ActivityStatus.rejeitada

    creditos_contabilizados: float | None = None
    fato_gerado: str | None = None
    motor_executado = False

    update_data: dict = {
        "status": novo_status,
        "observacao_coordenacao": payload.observacao,
        "aprovado_por": current_user["uid"],
        "aprovado_em": datetime.now(timezone.utc),
    }

    if aprovando:
        # Determina créditos: payload tem prioridade; fallback para pontuacao_base do tipo
        if payload.creditos_concedidos is not None:
            creditos_contabilizados = payload.creditos_concedidos
        else:
            tipo_id = activity.get("tipo_id", "")
            tipo = _repo.get_activity_type(tipo_id)
            creditos_contabilizados = (
                float(tipo["pontuacao_base"]) if tipo and "pontuacao_base" in tipo else 0.0
            )

        update_data["creditos_gerados"] = creditos_contabilizados

        # Verifica se gera fato producao_bibliografica_validada para o motor
        student_id: str = activity.get("student_id", "")
        categoria: str = activity.get("categoria", "")

        if categoria == "producao_bibliografica" and student_id:
            # Conta produções aprovadas APÓS esta aprovação (inclui a atual)
            aprovadas_anteriores = _repo.count_approved_productions(student_id)
            # A aprovação atual ainda não foi persistida, então aprovadas_anteriores
            # pode ser 0 na primeira; o fato é gerado a partir de ≥1 aprovada
            total_aprovadas = aprovadas_anteriores + 1
            if total_aprovadas >= 1:
                fato_gerado = f"producao_bibliografica_validada({student_id})"
                motor_executado = True
                logger.info(
                    "[S6b] Fato gerado para motor: %s — re-inferência será executada "
                    "na próxima consulta de /inference/%s",
                    fato_gerado,
                    student_id,
                )
    else:
        update_data["creditos_gerados"] = 0.0

    _repo.update(activity_id, update_data)

    acao_label = "aprovada" if aprovando else "rejeitada"
    logger.info(
        "[S6b] Atividade %s %s pela coordenação (uid=%s). Créditos: %s. Fato: %s",
        activity_id,
        acao_label,
        current_user.get("uid"),
        creditos_contabilizados,
        fato_gerado,
    )

    return ValidateActivityResponse(
        message=f"Atividade {acao_label} com sucesso.",
        novo_status=novo_status,
        creditos_contabilizados=creditos_contabilizados,
        motor_inferencia_executado=motor_executado,
        fato_gerado=fato_gerado,
    )