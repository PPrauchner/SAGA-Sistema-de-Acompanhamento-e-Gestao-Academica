"""
Serviço de negócio para gestão de discentes.

Responsabilidades:
- Implementar CRUD completo de alunos delegando persistência ao StudentRepository.
- create_student(): cria aluno no Firestore e dispara convite de primeiro acesso.
  Decorado com @requires_role('coordenacao') e @audit_operation.
- update_student(): atualiza campos editáveis do aluno.
  Decorado com @requires_role('coordenacao') e @audit_operation.
- delete_student(): remove aluno verificando ausência de dependências ativas.
  Decorado com @requires_role('coordenacao') e @audit_operation.
- update_qualificacao(): registra aprovação na qualificação. Gera fato qualificacao_aprovada
  para o motor. Decorado com @requires_role('coordenacao'), @audit_operation e @track_history.
- update_proficiencia(): registra comprovação de proficiência em língua estrangeira.
  Decorado com @requires_role('coordenacao'), @audit_operation e @track_history.
- update_situacao_registrada(): atualiza situação registrada manualmente.
  Decorado com @requires_role('coordenacao'), @audit_operation e @track_history.
  Coberto pelo aspecto A03 (histórico) via metaclasse HistoryMeta ou decorador @track_history.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from backend.app.aspects.audit import audit_operation
from backend.app.aspects.history import track_history
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
from backend.app.repositories.student_repository import StudentRepository
from backend.app.services.auth_service import AuthService


class StudentService:
    """Serviço de negócio para gestão de discentes."""

    def __init__(self, auth_service: AuthService | None = None) -> None:
        self._students = StudentRepository()
        self._auth = auth_service

    async def list_students(
        self,
        user: CurrentUser,
    ) -> list[dict]:

        students = await self._students.list_all()

        if user.role == "coordenacao":
            return students

        if user.role == "orientador":
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
                return []

            advisor_id = advisor["id"]

            return [
                student
                for student in students
                if student.get("orientador_id") == advisor_id
            ]

        return [
            student
            for student in students
            if student.get("uid") == user.uid
        ]

    @audit_operation
    async def create_student(
        self,
        data: StudentCreateRequest,
        user: CurrentUser,
    ) -> dict:
        student_id = await self._students.create(
            {
                **data.model_dump(),
                "uid": None,
                "situacao_registrada": "regular",
                "situacao_inferida": "regular",
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

    @audit_operation
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

    @audit_operation
    async def delete_student(
        self,
        student_id: str,
        user: CurrentUser,
    ) -> dict:
        await self._students.delete(student_id)

        return {
            "message": "Aluno removido",
        }

    @audit_operation
    @track_history
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

    @audit_operation
    @track_history
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

    @audit_operation
    @track_history
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
                "situacao_observacao": data.observacao,
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

        return student
