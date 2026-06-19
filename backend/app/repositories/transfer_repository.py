"""Repositorio da colecao transfer_requests/."""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository


class TransferRepository(FirebaseRepository):
    def __init__(self) -> None:
        super().__init__("transfer_requests")

    async def get_pending_by_student(self, student_id: str) -> dict[str, Any] | None:
        requests = await self.list_all()

        return next(
            (
                request
                for request in requests
                if request.get("student_id") == student_id
                and request.get("status") == "pendente"
            ),
            None,
        )
