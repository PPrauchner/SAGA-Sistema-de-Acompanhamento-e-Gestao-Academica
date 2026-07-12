"""
Serviço de negócio para gestão de discentes.

Responsabilidades:
- Implementar CRUD completo de alunos delegando persistência ao StudentRepository.
- create_student(): cria aluno no Firestore e dispara convite de primeiro acesso.
- update_student(): atualiza campos editáveis do aluno.
- delete_student(): remove aluno verificando ausência de dependências ativas.
- update_qualificacao(): registra aprovação na qualificação. Gera fato qualificacao_aprovada
  para o motor.
- update_proficiencia(): registra comprovação de proficiência em língua estrangeira.
- update_situacao_registrada(): atualiza situação registrada manualmente.
- A01/A02/A03 são aplicados nos endpoints, conforme ordem canônica do projeto.
"""

from __future__ import annotations

import asyncio
from calendar import monthrange
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.student import (
    ProficienciaRequest,
    QualificacaoRequest,
    SituacaoRequest,
    StudentCreateRequest,
    StudentUpdateRequest,
)
from backend.app.models.user import InviteRequest
from backend.app.models.work_plan import STATUS_CONCLUIDO
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.program_repository import ProgramRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.work_plan_repository import WorkPlanRepository
from backend.app.services.auth_service import AuthService

DEFAULT_DURACAO_MESES = 24
DEFAULT_STUDENT_STATUS = "regular"


def _progress_by_student(tasks: list[dict[str, Any]]) -> dict[str, float]:
    """Percentual de tasks concluídas por aluno a partir da lista agregada.

    Args:
        tasks: Tasks de todos os alunos, com student_id e status canônico.

    Returns:
        Mapa student_id → percentual (0-100) arredondado a 1 casa; alunos sem
        task não aparecem no mapa (progresso 0).
    """
    totais: dict[str, list[int]] = {}
    for task in tasks:
        sid = task.get("student_id") or ""
        acc = totais.setdefault(sid, [0, 0])
        acc[1] += 1
        if task.get("status") == STATUS_CONCLUIDO:
            acc[0] += 1
    return {
        sid: round(concluidas / total * 100.0, 1)
        for sid, (concluidas, total) in totais.items()
        if total > 0
    }


class StudentService:
    """Serviço de negócio para gestão de discentes."""

    def __init__(self, auth_service: AuthService | None = None) -> None:
        self._students = StudentRepository()
        self._programs = ProgramRepository()
        self._work_plan = WorkPlanRepository()
        self._auth = auth_service

    @staticmethod
    def _add_months(date_value: datetime, months: int) -> datetime:
        month_index = date_value.month - 1 + months
        year = date_value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(date_value.day, monthrange(year, month)[1])

        return date_value.replace(year=year, month=month, day=day)

    @staticmethod
    def _normalize_student_response(student: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(student)
        if normalized.get("coorientador_id") is None:
            normalized["coorientador_id"] = None
        if normalized.get("situacao_registrada") is None:
            normalized["situacao_registrada"] = DEFAULT_STUDENT_STATUS
        if normalized.get("situacao_inferida") is None:
            normalized["situacao_inferida"] = normalized["situacao_registrada"]
        if normalized.get("qualificacao_aprovada") is None:
            normalized["qualificacao_aprovada"] = False
        if normalized.get("proficiencia_comprovada") is None:
            normalized["proficiencia_comprovada"] = False
        if normalized.get("qualificacao_data") is None:
            normalized["qualificacao_data"] = None
        if normalized.get("proficiencia_data") is None:
            normalized["proficiencia_data"] = None
        if normalized.get("prazo_final") is None:
            normalized["prazo_final"] = None
        return normalized

    async def _get_program_duration_months(self, programa_id: str) -> int:
        program = await self._programs.get_config(programa_id)
        if program is None:
            return DEFAULT_DURACAO_MESES

        return int(program.get("duracao_meses") or DEFAULT_DURACAO_MESES)

    async def _get_advisor_id_for_user(
        self,
        user: CurrentUser,
    ) -> str | None:
        advisors = await AdvisorRepository().list_all()

        advisor = next(
            (
                item
                for item in advisors
                if item.get("uid") == user.uid
            ),
            None,
        )

        if advisor is None:
            return None

        return advisor["id"]

    async def list_students(
        self,
        user: CurrentUser,
    ) -> list[dict]:
        # Alunos e tasks agregadas em paralelo: o progresso do plano de cada aluno
        # é calculado em leitura a partir de uma única consulta (issue #317).
        students, all_tasks = await asyncio.gather(
            self._students.list_all(),
            self._work_plan.list_all_tasks_grouped(),
        )
        progresso_por_aluno = _progress_by_student(all_tasks)

        if user.role == "orientador":
            advisor_id = await self._get_advisor_id_for_user(user)
            if advisor_id is None:
                return []
            students = [
                student
                for student in students
                if student.get("orientador_id") == advisor_id
            ]
        elif user.role != "coordenacao":
            students = [
                student for student in students if student.get("uid") == user.uid
            ]

        return [
            {
                **self._normalize_student_response(student),
                "progresso_plano": progresso_por_aluno.get(student.get("id", ""), 0.0),
            }
            for student in students
        ]

    async def create_student(
        self,
        data: StudentCreateRequest,
        user: CurrentUser,
    ) -> dict:
        if user.role == "orientador" and data.programa_id != user.programa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Orientador só pode criar aluno no próprio programa",
            )

        duracao_meses = await self._get_program_duration_months(data.programa_id)
        student_id = await self._students.create(
            {
                **data.model_dump(),
                "uid": None,
                "situacao_registrada": "regular",
                "situacao_inferida": "regular",
                "prazo_final": self._add_months(data.data_ingresso, duracao_meses),
                "qualificacao_aprovada": False,
                "proficiencia_comprovada": False,
                "qualificacao_data": None,
                "proficiencia_data": None,
            },
        )
        auth = self._auth or AuthService()
        try:
            invite = await auth.create_invite(
                InviteRequest(
                    email=data.email,
                    role="aluno",
                    nome=data.nome,
                ),
                user,
                {"student_id": student_id},
            )
        except Exception:
            await self._students.delete(student_id)
            raise

        return {
            "id": student_id,
            "nome": data.nome,
            "invite_token": invite.token,
        }

    async def update_student(
        self,
        student_id: str,
        data: StudentUpdateRequest,
        user: CurrentUser,
    ) -> dict:
        await self._students.update(
            student_id,
            data.model_dump(exclude_none=True),
        )

        return {
            "id": student_id,
            "message": "Aluno atualizado",
        }

    async def delete_student(
        self,
        student_id: str,
        user: CurrentUser,
    ) -> dict:
        await self._students.delete(student_id)

        return {
            "message": "Aluno removido",
        }

    async def update_qualificacao(
        self,
        student_id: str,
        data: QualificacaoRequest,
        user: CurrentUser,
    ) -> dict:
        await self._students.update(
            student_id,
            {
                "qualificacao_aprovada": data.aprovada,
                "qualificacao_data": data.data_qualificacao,
            },
        )

        return {
            "message": "Qualificação registrada",
            "situacao_inferida_atualizada": False,
        }

    async def update_proficiencia(
        self,
        student_id: str,
        data: ProficienciaRequest,
        user: CurrentUser,
    ) -> dict:
        await self._students.update(
            student_id,
            {
                "proficiencia_comprovada": data.comprovada,
                "proficiencia_data": data.data_proficiencia,
            },
        )

        return {
            "message": "Proficiência registrada",
        }

    async def update_situacao(
        self,
        student_id: str,
        data: SituacaoRequest,
        user: CurrentUser,
    ) -> dict:
        await self._students.update(
            student_id,
            {
                "situacao_registrada": data.situacao_registrada,
            },
        )

        return {
            "message": "Situação atualizada",
            "historico_criado": True,
        }

    async def get_student(
        self,
        student_id: str,
        user: CurrentUser,
    ) -> dict:

        student = await self._students.get(student_id)

        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno não encontrado",
            )

        student["id"] = student_id

        if user.role == "aluno" and student.get("uid") != user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado ao aluno",
            )

        if user.role == "orientador":
            advisor_id = await self._get_advisor_id_for_user(user)

            if advisor_id is None or student.get("orientador_id") != advisor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado ao orientando",
                )

        tasks = await self._work_plan.get_all_tasks_for_student(student_id)
        concluidas = sum(1 for task in tasks if task.get("status") == STATUS_CONCLUIDO)
        return {
            **self._normalize_student_response(student),
            "progresso_plano": round(concluidas / len(tasks) * 100.0, 1) if tasks else 0.0,
        }

    async def list_coauthor_candidates(self, user: CurrentUser) -> list[dict]:
        """Lista alunos cadastrados do programa para o seletor de co-autores (issue #310).

        Não escopa por papel do chamador (diferente de list_students): qualquer aluno
        cadastrado no programa é um co-autor elegível de produção/atividade (ADR-0006).
        Devolve só uid/nome — não o StudentResponse completo — para não vazar dados de
        outros alunos (matrícula, orientador, situação) a um par que só precisa escolher
        um co-autor pelo nome.

        Args:
            user: Usuário autenticado; define o programa (escopo de tenant).

        Returns:
            Lista de {uid, nome} de alunos com uid vinculado (conta ativada) no programa,
            incluindo o próprio usuário — a exclusão de si mesmo é feita pelo chamador.
        """
        students = await self._students.list_by_program(user.programa_id)
        return [
            {"uid": student["uid"], "nome": student.get("nome", "")}
            for student in students
            if student.get("uid")
        ]
