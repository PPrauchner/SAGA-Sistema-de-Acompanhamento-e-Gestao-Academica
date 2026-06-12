"""
Serviço de negócio para gestão de orientadores.

Responsabilidades:
- Implementar CRUD de orientadores delegando persistência ao AdvisorRepository.
- create_advisor(): cria orientador no Firestore e dispara convite de primeiro acesso via
  AuthService. Decorado com @requires_role('coordenacao') e @audit_operation.
- update_advisor(): atualiza dados do orientador (nome, departamento, lattes, limite).
  Decorado com @requires_role('coordenacao') e @audit_operation.
- get_advisors_with_count(): lista orientadores enriquecendo cada registro com contagem
  de orientandos_ativos calculada por query na coleção students/.
- Verificar limite_orientandos antes de permitir associação de novo orientando ao orientador.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from backend.app.aspects.audit import audit_operation
from backend.app.core.auth import CurrentUser
from backend.app.models.advisor import (
    AdvisorCreateRequest,
    AdvisorUpdateRequest,
)
from backend.app.models.user import InviteRequest
from backend.app.repositories.advisor_repository import (
    AdvisorRepository,
)
from backend.app.repositories.student_repository import StudentRepository
from backend.app.services.auth_service import AuthService


class AdvisorService:
    def __init__(self, auth_service: AuthService | None = None) -> None:
        self._advisors = AdvisorRepository()
        self._auth = auth_service

    async def list_advisors(self) -> list[dict]:
        return await self._advisors.get_advisors_with_student_count()

    async def get_advisor(
        self,
        advisor_id: str,
    ) -> dict:
        advisor = await self._advisors.get(
            advisor_id,
        )

        if advisor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orientador não encontrado",
            )

        advisor["id"] = advisor_id

        return advisor

    @audit_operation
    async def create_advisor(
        self,
        data: AdvisorCreateRequest,
        user: CurrentUser,
    ) -> dict:
        advisor_id = await self._advisors.create(
            data.model_dump(),
        )
        auth = self._auth or AuthService()
        try:
            invite = await auth.create_invite(
                InviteRequest(
                    email=data.email,
                    role="orientador",
                    nome=data.nome,
                ),
                user,
                {"advisor_id": advisor_id},
            )
        except Exception:
            await self._advisors.delete(advisor_id)
            raise

        return {
            "id": advisor_id,
            "nome": data.nome,
            "invite_token": invite.token,
        }

    @audit_operation
    async def update_advisor(
        self,
        advisor_id: str,
        data: AdvisorUpdateRequest,
        user: CurrentUser,
    ) -> dict:
        await self._advisors.update(
            advisor_id,
            data.model_dump(exclude_none=True),
        )

        return {
            "message": "Orientador atualizado",
        }

    @audit_operation
    async def delete_advisor(
        self,
        advisor_id: str,
        user: CurrentUser,
    ) -> dict:
        students = await StudentRepository().list_all()

        has_students = any(
            student.get("orientador_id") == advisor_id
            for student in students
        )

        if has_students:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Orientador possui orientandos ativos",
            )

        await self._advisors.delete(
            advisor_id,
        )

        return {
            "message": "Orientador removido",
        }
