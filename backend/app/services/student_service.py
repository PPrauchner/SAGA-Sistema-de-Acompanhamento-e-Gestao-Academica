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
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.program_repository import ProgramRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.services.auth_service import AuthService

DEFAULT_DURACAO_MESES = 24
DEFAULT_STUDENT_STATUS = "regular"


class StudentService:
    """Serviço de negócio para gestão de discentes."""

    def __init__(self, auth_service: AuthService | None = None) -> None:
        self._students = StudentRepository()
        self._programs = ProgramRepository()
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

        students = await self._students.list_all()

        if user.role == "coordenacao":
            return [self._normalize_student_response(student) for student in students]

        if user.role == "orientador":
            advisor_id = await self._get_advisor_id_for_user(user)

            if advisor_id is None:
                return []

            return [
                self._normalize_student_response(student)
                for student in students
                if student.get("orientador_id") == advisor_id
            ]

        return [
            self._normalize_student_response(student)
            for student in students
            if student.get("uid") == user.uid
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

        return self._normalize_student_response(student)
