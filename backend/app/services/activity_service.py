"""
Serviço de negócio para registro de atividades creditáveis.

Responsabilidades:
- submit_activity(): aluno registra atividade. Calcula elegibilidade_preliminar (RL04) via
  InferenceService e resolve o orientador a notificar. O endpoint aplica @requires_role('aluno'),
  @audit_operation, @check_deadlines e @trigger_alerts (notifica o orientador na submissão).
- list_activities(): lista atividades respeitando o papel (aluno vê as próprias; orientador
  vê dos orientandos; coordenação vê todas), com filtros opcionais de student_id, status e
  categoria, enriquecendo cada item com tipo_nome/categoria do activity_type.

A validação (parecer/aprovação) é a issue #49 e não faz parte deste serviço ainda.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.activity import ActivityCreateRequest
from backend.app.repositories.activity_repository import ActivityRepository
from backend.app.repositories.activity_type_repository import ActivityTypeRepository
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.inference_repository import InferenceRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.services.inference_service import InferenceService


def _to_iso_date(value: Any) -> str | None:
    """Converte datetime/date/string para 'YYYY-MM-DD', ou None."""
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

    async def submit_activity(
        self,
        data: ActivityCreateRequest,
        user: CurrentUser,
    ) -> dict:
        """Registra uma atividade do aluno e calcula a elegibilidade preliminar (RL04).

        Args:
            data: Dados da atividade (tipo_id, descricao, data_realizacao, comprovante_url,
                status inicial).
            user: Aluno autenticado dono da atividade.

        Returns:
            dict com id, elegibilidade_preliminar e notificacao_enviada, além de campos
            internos (aluno_nome, orientador_uid, programa_id) consumidos pelo @trigger_alerts
            e filtrados pelo response_model do endpoint.

        Raises:
            HTTPException: 404 se o aluno ou o tipo de atividade não existirem.
        """
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
        """Lista atividades visíveis ao usuário, com filtros e enriquecimento de tipo.

        Args:
            user: Usuário autenticado (define o escopo de visibilidade por papel).
            student_id: Filtra por um aluno específico (respeitando a permissão do papel).
            status_filter: Filtra por status da atividade.
            categoria: Filtra pela categoria do tipo de atividade.

        Returns:
            Lista de atividades (dicts) enriquecidas com tipo_nome e categoria.
        """
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
                        "tipo_nome": tipo.get("nome"),
                        "categoria": activity_categoria,
                    }
                )
        return result

    # -- helpers ------------------------------------------------------------------------

    async def _approved_credits_in_category(
        self,
        student_id: str,
        categoria: str | None,
    ) -> float:
        """Soma creditos_gerados das atividades aprovadas do aluno na categoria informada."""
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
        """Resolve o documento do aluno autenticado pelo uid, ou 404 se não existir."""
        students = await self._students.list_all()
        student = next((item for item in students if item.get("uid") == user.uid), None)
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno não encontrado",
            )
        return student

    async def _resolve_orientador_uid(self, orientador_id: str | None) -> str | None:
        """Resolve o uid do usuário orientador a partir do orientador_id (advisors auto-id)."""
        if not orientador_id:
            return None
        advisor = await self._advisors.get(orientador_id)
        return advisor.get("uid") if advisor else None

    async def _advisor_id_for_user(self, user: CurrentUser) -> str | None:
        """Resolve o advisor_id (auto-id) do usuário orientador pelo seu uid."""
        advisors = await self._advisors.list_all()
        advisor = next((item for item in advisors if item.get("uid") == user.uid), None)
        return advisor["id"] if advisor else None

    async def _visible_student_ids(
        self,
        user: CurrentUser,
        student_id: str | None,
    ) -> list[str]:
        """Determina os IDs de alunos visíveis ao usuário, aplicando o filtro student_id."""
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
