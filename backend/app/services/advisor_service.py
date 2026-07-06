"""
Serviço de negócio para gestão de orientadores.

Responsabilidades:
- Implementar CRUD de orientadores delegando persistência ao AdvisorRepository.
- create_advisor(): cria orientador no Firestore e dispara convite de primeiro acesso via
  AuthService.
- update_advisor(): atualiza dados editaveis do orientador (nome, lattes, limite).
- get_advisors_with_count(): lista orientadores enriquecendo cada registro com contagem
  de orientandos_ativos calculada por query na coleção students/.
- Verificar limite_orientandos antes de permitir associação de novo orientando ao orientador.
- A01/A02 são aplicados nos endpoints, conforme ordem canônica do projeto.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

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

DEFAULT_ADVISOR_LIMIT = 5
DEFAULT_ORIENTANDOS_ATIVOS = 0
DEFAULT_LEGACY_ADVISOR_UID = ""


class AdvisorService:
    def __init__(self, auth_service: AuthService | None = None) -> None:
        self._advisors = AdvisorRepository()
        self._auth = auth_service

    @staticmethod
    def _normalize_advisor_response(advisor: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(advisor)
        if normalized.get("uid") is None:
            normalized["uid"] = DEFAULT_LEGACY_ADVISOR_UID
        if normalized.get("lattes") is None:
            normalized["lattes"] = None
        if normalized.get("limite_orientandos") is None:
            normalized["limite_orientandos"] = DEFAULT_ADVISOR_LIMIT
        if normalized.get("orientandos_ativos") is None:
            normalized["orientandos_ativos"] = DEFAULT_ORIENTANDOS_ATIVOS
        return normalized

    async def list_advisors(self, user: CurrentUser | None = None) -> list[dict]:
        advisors = await self._advisors.get_advisors_with_student_count()
        normalized_advisors = [
            self._normalize_advisor_response(advisor)
            for advisor in advisors
        ]

        if user and user.role == "coordenacao":
            return normalized_advisors

        active_advisors = [
            advisor
            for advisor in normalized_advisors
            if advisor.get("uid")
        ]

        if user and user.role == "orientador" and user.programa_id:
            return [
                advisor
                for advisor in active_advisors
                if advisor.get("programa_id") == user.programa_id
            ]

        return active_advisors

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
        advisor["orientandos_ativos"] = await self._advisors.count_active_students(
            advisor_id,
        )

        return self._normalize_advisor_response(advisor)

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

    async def update_advisor(
        self,
        advisor_id: str,
        data: AdvisorUpdateRequest,
        user: CurrentUser,
    ) -> dict:
        update_data = data.model_dump(exclude_none=True)

        if "limite_orientandos" in update_data:
            active_students = await self._advisors.count_active_students(
                advisor_id,
            )
            if update_data["limite_orientandos"] < active_students:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Limite nao pode ser menor que orientandos ativos",
                )

        await self._advisors.update(
            advisor_id,
            update_data,
        )

        return {
            "message": "Orientador atualizado",
        }

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
