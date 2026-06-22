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

    async def list_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        requests = await self.list_all()
        return [
            request
            for request in requests
            if request.get("programa_id") == programa_id
        ]

    async def list_by_requester(self, solicitante_id: str) -> list[dict[str, Any]]:
        requests = await self.list_all()
        return [
            request
            for request in requests
            if request.get("solicitante_id") == solicitante_id
        ]

    async def create_request(self, data: dict[str, Any]) -> str:
        return await self.create(data)

    async def update_status(
        self,
        transfer_id: str,
        data: dict[str, Any],
    ) -> None:
        await self.update(transfer_id, data)

    async def approve(self, transfer_id: str, data: dict[str, Any]) -> None:
        await self.update_status(transfer_id, {"status": "aprovada", **data})

    async def reject(self, transfer_id: str, data: dict[str, Any]) -> None:
        await self.update_status(transfer_id, {"status": "rejeitada", **data})

    async def cancel(self, transfer_id: str, data: dict[str, Any]) -> None:
        await self.update_status(transfer_id, {"status": "cancelada", **data})
