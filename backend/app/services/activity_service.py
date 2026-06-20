"""
Serviço de negócio para atividades creditáveis.

- ActivityService (classe): submit_activity / list_activities — registro e listagem
  (restaurado da development, removido indevidamente na pr-68).
- emitir_parecer_orientador / validate_activity (funções de módulo, decoradas):
  validação pela coordenação/orientador — issue #49, implementada nesta PR (#68).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_ownership, requires_role
from backend.app.core.auth import CurrentUser
from backend.app.models.activity import (
    ActivityCreateRequest,
    ActivityResponse,
    ActivityStatus,
    ValidateAction,
    ValidateActivityRequest,
    ValidateActivityResponse,
)
from backend.app.repositories.activity_repository import ActivityRepository
from backend.app.repositories.activity_type_repository import ActivityTypeRepository
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.inference_repository import InferenceRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.services.inference_service import InferenceService

logger = logging.getLogger(__name__)


def _to_iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value) or None


class ActivityService:
    """Serviço de negócio para registro e listagem de atividades creditáveis."""

    def __init__(self, inference_service: InferenceService | None = None) -> None:
        self._activities = ActivityRepository()
        self._students = StudentRepository()
        self._types = ActivityTypeRepository()
        self._advisors = AdvisorRepository()
        self._inference = inference_service or InferenceService(InferenceRepository())

    async def submit_activity(self, data: ActivityCreateRequest, user: CurrentUser) -> dict:
        student = await self._resolve_student(user)
        student_id = student["id"]

        activity_type = await self._types.get(data.tipo_id)
        if activity_type is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de atividade não encontrado",
            )

        pontuacao_base = float(activity_type.get("pontuacao_base", 0))
        categoria = activity_type.get("categoria")
        limite = activity_type.get("limite_maximo_creditos")
        tipo_ativo = bool(activity_type.get("ativo", False))

        creditos_aprovados = await self._approved_credits_in_category(student_id, categoria)

        now = datetime.now(timezone.utc)
        activity_id = await self._activities.create_activity(
            student_id,
            {
                "tipo_id": data.tipo_id,
                "aluno_id": student_id,
                "descricao": data.descricao,
                "data_realizacao": data.data_realizacao,
                "comprovante_url": data.comprovante_url,
                "creditos_gerados": pontuacao_base,
                "creditos_concedidos": None,
                "status": data.status,
                "parecer_orientador": None,
                "observacao_coordenacao": None,
                "validado_por": None,
                "validado_em": None,
                "criado_em": now,
                "atualizado_em": now,
            },
        )

        elegibilidade = self._inference.evaluate_activity_eligibility(
            activity_id=activity_id,
            student_id=student_id,
            data_ingresso=_to_iso_date(student.get("data_ingresso")),
            data_realizacao=_to_iso_date(data.data_realizacao),
            tem_comprovante=bool(data.comprovante_url),
            tipo_ativo=tipo_ativo,
            categoria_creditos_aprovados=creditos_aprovados,
            pontuacao_base=pontuacao_base,
            limite_categoria=None if limite is None else float(limite),
        )

        orientador_uid = await self._resolve_orientador_uid(student.get("orientador_id"))
        notificacao_enviada = data.status == "enviado" and orientador_uid is not None

        return {
            "id": activity_id,
            "elegibilidade_preliminar": elegibilidade,
            "notificacao_enviada": notificacao_enviada,
            "aluno_nome": student.get("nome", ""),
            "orientador_uid": orientador_uid,
            "programa_id": student.get("programa_id"),
        }

    async def list_activities(
        self,
        user: CurrentUser,
        student_id: str | None = None,
        status_filter: str | None = None,
        categoria: str | None = None,
    ) -> list[dict]:
        visible_ids = await self._visible_student_ids(user, student_id)
        types_map = {item["id"]: item for item in await self._types.list_all()}

        result: list[dict] = []
        for sid in visible_ids:
            for activity in await self._activities.list_by_student(sid):
                tipo = types_map.get(activity.get("tipo_id"), {})
                activity_categoria = tipo.get("categoria")
                if status_filter is not None and activity.get("status") != status_filter:
                    continue
                if categoria is not None and activity_categoria != categoria:
                    continue
                result.append(
                    {
                        **activity,
                        "student_id": sid,
                        "tipo_nome": tipo.get("nome"),
                        "categoria": activity_categoria,
                    }
                )
        return result

    # -- helpers ------------------------------------------------------------------------

    async def _approved_credits_in_category(self, student_id: str, categoria: str | None) -> float:
        if categoria is None:
            return 0.0
        types_map = {item["id"]: item for item in await self._types.list_all()}
        total = 0.0
        for activity in await self._activities.list_by_student(student_id):
            if activity.get("status") != "aprovado":
                continue
            tipo = types_map.get(activity.get("tipo_id"), {})
            if tipo.get("categoria") == categoria:
                total += float(activity.get("creditos_gerados", 0))
        return total

    async def _resolve_student(self, user: CurrentUser) -> dict:
        students = await self._students.list_all()
        student = next((item for item in students if item.get("uid") == user.uid), None)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")
        return student

    async def _resolve_orientador_uid(self, orientador_id: str | None) -> str | None:
        if not orientador_id:
            return None
        advisor = await self._advisors.get(orientador_id)
        return advisor.get("uid") if advisor else None

    async def _advisor_id_for_user(self, user: CurrentUser) -> str | None:
        advisors = await self._advisors.list_all()
        advisor = next((item for item in advisors if item.get("uid") == user.uid), None)
        return advisor["id"] if advisor else None

    async def _visible_student_ids(self, user: CurrentUser, student_id: str | None) -> list[str]:
        students = await self._students.list_all()

        if user.role == "aluno":
            own = next((item for item in students if item.get("uid") == user.uid), None)
            ids = [own["id"]] if own else []
        elif user.role == "orientador":
            advisor_id = await self._advisor_id_for_user(user)
            ids = [
                item["id"]
                for item in students
                if advisor_id is not None and item.get("orientador_id") == advisor_id
            ]
        else:
            ids = [item["id"] for item in students]

        if student_id is not None:
            ids = [sid for sid in ids if sid == student_id]
        return ids


# ---------------------------------------------------------------------------------------
# Validação (issue #49 / PATCH /activities/{id}/validate) — funções de módulo, decoradas
# ---------------------------------------------------------------------------------------

_repo = ActivityRepository()


def _get_advisor_uid_for_activity(kwargs: dict) -> str | None:
    activity_id: str = kwargs.get("activity_id", "")
    activity = _repo.get_by_id(activity_id)
    if not activity:
        return None
    student_id = activity.get("student_id", "")
    return _repo.get_advisor_uid_by_student(student_id)


def _get_aluno_uid_para_notificacao(kwargs: dict) -> str | None:
    activity_id: str = kwargs.get("activity_id", "")
    activity = _repo.get_by_id(activity_id)
    return activity.get("student_id") if activity else None


def _build_notificacao_validacao(result, args, kwargs):
    activity_id = kwargs.get("activity_id", "")
    destinatario_id = _get_aluno_uid_para_notificacao(kwargs)
    if not destinatario_id:
        return None
    acao_label = "aprovada" if result.novo_status == ActivityStatus.aprovado else "rejeitada"
    payload = kwargs.get("payload")
    observacao = payload.observacao if payload and payload.observacao else ""
    mensagem = f"Sua atividade (ID: {activity_id}) foi {acao_label}."
    if observacao:
        mensagem += f" Observacao: {observacao}"
    return {
        "tipo": "atividade_validada",
        "titulo": "Resultado da validacao de atividade",
        "mensagem": mensagem,
        "destinatario_id": destinatario_id,
        "entidade_tipo": "activities",
        "entidade_id": activity_id,
    }


@requires_role("orientador", "coordenacao")
@requires_ownership(_get_advisor_uid_for_activity)
@audit_operation
async def emitir_parecer_orientador(
    activity_id: str,
    payload: ValidateActivityRequest,
    current_user: dict,
) -> ActivityResponse:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")

    if activity["status"] != ActivityStatus.enviado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Atividade com status '{activity['status']}' não pode receber parecer.",
        )

    update_data = {
        "parecer_orientador": payload.parecer_orientador.model_dump(),
        "parecer_orientador_em": datetime.now(timezone.utc),
        "parecer_orientador_por": current_user["uid"],
    }
    updated = _repo.update_by_id(activity_id, update_data)
    return ActivityResponse(**updated)


@requires_role("coordenacao")
@audit_operation
@trigger_alerts(_build_notificacao_validacao)
async def validate_activity(
    activity_id: str,
    payload: ValidateActivityRequest,
    current_user: dict,
) -> ValidateActivityResponse:
    if payload.acao not in (ValidateAction.aprovar, ValidateAction.rejeitar):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta função aceita apenas as ações 'aprovar' ou 'rejeitar'.",
        )

    activity = _repo.get_by_id(activity_id)
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")

    if activity["status"] != ActivityStatus.enviado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Atividade com status '{activity['status']}' não pode ser aprovada ou rejeitada.",
        )

    aprovando = payload.acao == ValidateAction.aprovar
    novo_status = ActivityStatus.aprovado if aprovando else ActivityStatus.rejeitado

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
        if payload.creditos_concedidos is not None:
            creditos_contabilizados = payload.creditos_concedidos
        else:
            tipo_id = activity.get("tipo_id", "")
            tipo = _repo.get_activity_type(tipo_id)
            creditos_contabilizados = (
                float(tipo["pontuacao_base"]) if tipo and "pontuacao_base" in tipo else 0.0
            )
        update_data["creditos_gerados"] = creditos_contabilizados

        student_id: str = activity.get("student_id", "")
        categoria: str = activity.get("categoria", "")

        if categoria == "producao_bibliografica" and student_id:
            aprovadas_anteriores = _repo.count_approved_productions(student_id)
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

    _repo.update_by_id(activity_id, update_data)

    acao_label = "aprovada" if aprovando else "rejeitada"
    logger.info(
        "[S6b] Atividade %s %s pela coordenação (uid=%s). Créditos: %s. Fato: %s",
        activity_id, acao_label, current_user.get("uid"), creditos_contabilizados, fato_gerado,
    )

    return ValidateActivityResponse(
        message=f"Atividade {acao_label} com sucesso.",
        novo_status=novo_status,
        creditos_contabilizados=creditos_contabilizados,
        motor_inferencia_executado=motor_executado,
        fato_gerado=fato_gerado,
    )