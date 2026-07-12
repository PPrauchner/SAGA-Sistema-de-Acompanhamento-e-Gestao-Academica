"""Serviço de negócio para solicitações públicas de cadastro."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.registration_request import (
    RegistrationRequestApprove,
    RegistrationRequestCreate,
    RegistrationRequestReject,
)
from backend.app.models.student import StudentCreateRequest
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.registration_request_repository import (
    STATUS_PENDING,
    RegistrationRequestRepository,
)
from backend.app.services.student_service import StudentService


class RegistrationRequestService:
    """Orquestra criação pública e revisão de solicitações de cadastro."""

    def __init__(
        self,
        repo: RegistrationRequestRepository | None = None,
        advisor_repo: AdvisorRepository | None = None,
        student_service: StudentService | None = None,
    ) -> None:
        self._repo = repo or RegistrationRequestRepository()
        self._advisors = advisor_repo or AdvisorRepository()
        self._students = student_service or StudentService()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _default_matricula(request_id: str) -> str:
        return f"pendente-{request_id[:8]}"

    @staticmethod
    def _normalize_response(
        request: dict[str, Any],
        advisor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = dict(request)
        if advisor is not None:
            result["orientador_nome"] = advisor.get("nome")
        return result

    async def _get_active_advisor(self, orientador_id: str) -> dict[str, Any]:
        advisor = await self._advisors.get(orientador_id)

        if advisor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orientador nao encontrado",
            )

        if not advisor.get("uid"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Orientador ainda nao ativado",
            )

        if not advisor.get("programa_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Orientador sem programa vinculado",
            )

        return advisor

    async def list_active_advisors(self) -> list[dict[str, Any]]:
        advisors = await self._advisors.list_all()
        return [
            {
                "id": advisor["id"],
                "uid": advisor.get("uid"),
                "nome": advisor.get("nome", ""),
            }
            for advisor in advisors
            if advisor.get("uid")
        ]

    async def create_request(self, data: RegistrationRequestCreate) -> dict[str, Any]:
        advisor = await self._get_active_advisor(data.orientador_id)

        existing = await self._repo.find_pending_by_email(data.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ja existe uma solicitacao pendente para este e-mail",
            )

        payload = {
            "nome": data.nome,
            "email": data.email,
            "orientador_id": data.orientador_id,
            "programa_id": advisor["programa_id"],
            "status": STATUS_PENDING,
            "created_at": self._now(),
            "reviewed_by": None,
            "reviewed_at": None,
        }
        request_id = await self._repo.create(payload)
        return self._normalize_response({"id": request_id, **payload}, advisor)

    async def list_pending(self, user: CurrentUser) -> list[dict[str, Any]]:
        requests = await self._repo.list_pending_by_program(user.programa_id)
        # Ordenação em memória: a query usa só igualdades para não exigir índice composto.
        requests.sort(
            key=lambda request: request.get("created_at")
            or datetime.min.replace(tzinfo=timezone.utc)
        )
        advisors = {advisor["id"]: advisor for advisor in await self._advisors.list_all()}

        return [
            self._normalize_response(request, advisors.get(request.get("orientador_id")))
            for request in requests
        ]

    async def approve_request(
        self,
        request_id: str,
        data: RegistrationRequestApprove,
        user: CurrentUser,
    ) -> dict[str, Any]:
        request = await self._get_pending_for_review(request_id, user)
        reviewed_at = self._now()
        student_payload = StudentCreateRequest(
            nome=request["nome"],
            email=request["email"],
            matricula=data.matricula or self._default_matricula(request_id),
            orientador_id=request["orientador_id"],
            nivel=data.nivel,
            data_ingresso=data.data_ingresso or reviewed_at,
            programa_id=request["programa_id"],
        )
        student = await self._students.create_student(student_payload, user)

        update = {
            "reviewed_by": user.uid,
            "reviewed_at": reviewed_at,
            "student_id": student["id"],
            "invite_token": student.get("invite_token"),
        }
        await self._repo.approve(request_id, update)

        return {
            **request,
            **update,
            "id": request_id,
            "status": "aprovado",
            "message": "Solicitacao de cadastro aprovada",
        }

    async def reject_request(
        self,
        request_id: str,
        data: RegistrationRequestReject,
        user: CurrentUser,
    ) -> dict[str, Any]:
        request = await self._get_pending_for_review(request_id, user)
        reviewed_at = self._now()
        update = {
            "reviewed_by": user.uid,
            "reviewed_at": reviewed_at,
        }
        if data.motivo:
            update["rejection_reason"] = data.motivo

        await self._repo.reject(request_id, update)

        return {
            **request,
            **update,
            "id": request_id,
            "status": "rejeitado",
            "message": "Solicitacao de cadastro rejeitada",
        }

    async def _get_pending_for_review(
        self,
        request_id: str,
        user: CurrentUser,
    ) -> dict[str, Any]:
        request = await self._repo.get(request_id)

        if request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitacao de cadastro nao encontrada",
            )

        if request.get("programa_id") != user.programa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solicitacao pertence a outro programa",
            )

        if request.get("status") != STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solicitacao ja revisada",
            )

        return request
