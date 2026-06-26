"""Repositório da coleção registration_requests."""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository

STATUS_PENDING = "pendente"
STATUS_APPROVED = "aprovado"
STATUS_REJECTED = "rejeitado"


class RegistrationRequestRepository(FirebaseRepository):
    def __init__(self) -> None:
        super().__init__("registration_requests")

    async def find_pending_by_email(self, email: str) -> dict[str, Any] | None:
        matches = await self.query(
            filters=[
                ("email", "==", email.lower()),
                ("status", "==", STATUS_PENDING),
            ],
            limit=1,
        )
        return matches[0] if matches else None

    async def list_pending_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return await self.query(
            filters=[
                ("programa_id", "==", programa_id),
                ("status", "==", STATUS_PENDING),
            ],
            order_by="created_at",
        )

    async def approve(self, request_id: str, data: dict[str, Any]) -> bool:
        return await self.update(request_id, {"status": STATUS_APPROVED, **data})

    async def reject(self, request_id: str, data: dict[str, Any]) -> bool:
        return await self.update(request_id, {"status": STATUS_REJECTED, **data})
