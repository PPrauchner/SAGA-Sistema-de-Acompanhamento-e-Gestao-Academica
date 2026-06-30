"""
Serviço de negócio para atividades creditáveis.

- ActivityService (classe): submit_activity / list_activities — registro e listagem.
- emitir_parecer_orientador (função de módulo): parecer do orientador (issue #48).
- validate_activity (função de módulo): aprovação/rejeição da coordenação (issue #49).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.activity import (
    ActivityCreateRequest,
    ActivityResponse,
    ActivityStatus,
    ParecerRequest,
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


def _uid(user: CurrentUser) -> str:
    """Extrai o uid do usuário autenticado."""
    return user.uid


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
        student_by_id = {item["id"]: item for item in await self._students.list_all()}
        advisor_name_by_id = {
            item["id"]: item.get("nome", "") for item in await self._advisors.list_all()
        }

        result: list[dict] = []
        for sid in visible_ids:
            student = student_by_id.get(sid, {})
            orientador_nome = advisor_name_by_id.get(student.get("orientador_id"))
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
                        "aluno_nome": student.get("nome", ""),
                        "orientador_nome": orientador_nome,
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
                creditos = activity.get("creditos_concedidos")
                if creditos is None:
                    creditos = activity.get("creditos_gerados", 0)
                total += float(creditos)
        return total

    async def _resolve_student(self, user: CurrentUser) -> dict:
        students = await self._students.list_all()
        student = next((item for item in students if item.get("uid") == _uid(user)), None)
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
        advisor = next((item for item in advisors if item.get("uid") == _uid(user)), None)
        return advisor["id"] if advisor else None

    async def _visible_student_ids(self, user: CurrentUser, student_id: str | None) -> list[str]:
        students = await self._students.list_all()

        if user.role == "aluno":
            own = next((item for item in students if item.get("uid") == _uid(user)), None)
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
# Validação — funções de módulo puras (sem aspectos; a autorização vive no router).
# - emitir_parecer_orientador: parecer do orientador (issue #48 / PATCH /parecer)
# - validate_activity: aprovação/rejeição da coordenação (issue #49 / PATCH /validate)
# ---------------------------------------------------------------------------------------

_repo = ActivityRepository()
_student_repo = StudentRepository()
_advisor_repo = AdvisorRepository()


async def resolve_advisor_uid_for_activity(activity_id: str) -> str | None:
    """Resolve o uid do orientador responsável pela atividade (suporte ao A01 por propriedade).

    Faz a resolução em dois saltos a partir da atividade, pois `students.orientador_id`
    aponta para o auto-id em `advisors` (não para o uid):
    atividade → `students.orientador_id` → `advisors.uid`.

    Args:
        activity_id: ID da atividade alvo do parecer.

    Returns:
        O uid do orientador, ou None se a atividade, o aluno ou o orientador não existirem.
    """
    activity = await _repo.get_by_id(activity_id)
    if not activity:
        return None
    student = await _student_repo.get(activity["student_id"])
    if not student or not student.get("orientador_id"):
        return None
    advisor = await _advisor_repo.get(student["orientador_id"])
    return advisor.get("uid") if advisor else None


async def resolve_student_uid_for_activity(activity_id: str) -> str | None:
    """Resolve o uid do aluno dono da atividade (suporte ao A05 — notificar o resultado).

    A notificação de validação é endereçada ao aluno; o `student_id` da atividade aponta
    para o auto-id em `students`, de onde se obtém o uid de destino.

    Args:
        activity_id: ID da atividade validada pela coordenação.

    Returns:
        O uid do aluno, ou None se a atividade ou o aluno não existirem.
    """
    activity = await _repo.get_by_id(activity_id)
    if not activity:
        return None
    student = await _student_repo.get(activity["student_id"])
    return student.get("uid") if student else None


async def emitir_parecer_orientador(
    activity_id: str,
    payload: ParecerRequest,
    current_user: CurrentUser,
) -> ActivityResponse:
    """Grava o parecer textual do orientador sobre uma atividade submetida.

    O parecer é um campo (`activities.parecer_orientador`), não um estado: o status
    permanece `enviado` até a decisão da coordenação. A autoria/horário ficam no
    registro de auditoria (A02); não são duplicados no documento da atividade.

    Args:
        activity_id: ID da atividade que recebe o parecer.
        payload: Texto do parecer.
        current_user: Orientador autenticado (propriedade já garantida pelo A01 no router).

    Returns:
        A atividade atualizada.

    Raises:
        HTTPException: 404 se a atividade não existir; 409 se não estiver em `enviado`.
    """
    activity = await _repo.get_by_id(activity_id)
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")

    if activity["status"] != ActivityStatus.enviado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Atividade com status '{activity['status']}' não pode receber parecer.",
        )

    updated = await _repo.update_by_id(
        activity_id,
        {
            "parecer_orientador": payload.parecer,
            "atualizado_em": datetime.now(timezone.utc),
        },
    )
    return ActivityResponse(**updated)


async def validate_activity(
    activity_id: str,
    payload: ValidateActivityRequest,
    current_user: CurrentUser,
) -> ValidateActivityResponse:
    if payload.acao not in (ValidateAction.aprovar, ValidateAction.rejeitar):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta função aceita apenas as ações 'aprovar' ou 'rejeitar'.",
        )

    activity = await _repo.get_by_id(activity_id)
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
        "status": novo_status.value,
        "observacao_coordenacao": payload.observacao,
        "validado_por": current_user.uid,
        "validado_em": datetime.now(timezone.utc),
    }

    if aprovando:
        if payload.creditos_concedidos is not None:
            creditos_contabilizados = payload.creditos_concedidos
            update_data["creditos_concedidos"] = payload.creditos_concedidos
        else:
            creditos_gerados = activity.get("creditos_gerados")
            if creditos_gerados is None:
                tipo_id = activity.get("tipo_id", "")
                tipo = await _repo.get_activity_type(tipo_id)
                creditos_gerados = (
                    float(tipo["pontuacao_base"]) if tipo and "pontuacao_base" in tipo else 0.0
                )
            creditos_contabilizados = float(creditos_gerados)

        student_id: str = activity.get("student_id", "")

        producao_id = activity.get("producao_id")
        if producao_id and student_id:
            fato_gerado = f"producao_bibliografica_validada({student_id})"
            logger.info("[S6b] Fato gerado para motor: %s", fato_gerado)

        if student_id:
            try:
                _inference_svc = InferenceService(InferenceRepository())
                student_data = await _student_repo.get(student_id)
                programa_id = student_data.get("programa_id", "") if student_data else ""
                await _inference_svc.run_inference(student_id, programa_id)
                motor_executado = True
                logger.info(
                    "[S6b] Motor executado para aluno %s após aprovação de atividade %s",
                    student_id,
                    activity_id,
                )
            except Exception as exc:
                logger.error("[S6b] Falha ao executar motor de inferência: %s", exc)
    await _repo.update_by_id(activity_id, update_data)

    acao_label = "aprovada" if aprovando else "rejeitada"
    logger.info(
        "[S6b] Atividade %s %s pela coordenação (uid=%s). Créditos: %s. Fato: %s",
        activity_id, acao_label, current_user.uid, creditos_contabilizados, fato_gerado,
    )

    return ValidateActivityResponse(
        message=f"Atividade {acao_label} com sucesso.",
        novo_status=novo_status,
        creditos_contabilizados=creditos_contabilizados,
        motor_inferencia_executado=motor_executado,
        fato_gerado=fato_gerado,
    )
