"""Repositorio Firestore para coordination_transfers/."""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository


class CoordinationTransferRepository(FirebaseRepository):
    def __init__(self) -> None:
        super().__init__("coordination_transfers")

    async def create_transfer(self, data: dict[str, Any]) -> str:
        return await self.create(data)

    async def get_transfer(self, transfer_id: str) -> dict[str, Any] | None:
        return await self.get(transfer_id)

    async def get_pending_by_program(self, programa_id: str) -> dict[str, Any] | None:
        items = await self.query(
            filters=[
                ("programa_id", "==", programa_id),
                ("status", "==", "pendente"),
            ],
            limit=1,
        )
        return items[0] if items else None

    async def list_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return await self.query(
            filters=[("programa_id", "==", programa_id)],
        )

    async def list_pending_for_successor(self, successor_uid: str) -> list[dict[str, Any]]:
        return await self.query(
            filters=[
                ("successor_uid", "==", successor_uid),
                ("status", "==", "pendente"),
            ],
        )

    async def update_status(
        self,
        transfer_id: str,
        data: dict[str, Any],
    ) -> bool:
        return await self.update(transfer_id, data)

    async def accept(
        self,
        transfer_id: str,
        data: dict[str, Any],
    ) -> bool:
        return await self.update_status(transfer_id, data)

    async def reject(
        self,
        transfer_id: str,
        data: dict[str, Any],
    ) -> bool:
        return await self.update_status(transfer_id, data)

    async def cancel(
        self,
        transfer_id: str,
        data: dict[str, Any],
    ) -> bool:
        return await self.update_status(transfer_id, data)
