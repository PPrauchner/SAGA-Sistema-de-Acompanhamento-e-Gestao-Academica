"""Repositorio da colecao raiz extensions/."""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository

STATUS_PENDING = "pendente"


class ExtensionRepository(FirebaseRepository):
    def __init__(self) -> None:
        super().__init__("extensions")

    async def list_by_student_ids(self, student_ids: set[str]) -> list[dict[str, Any]]:
        if not student_ids:
            return []
        extensions = await self.list_all()
        return [
            extension
            for extension in extensions
            if extension.get("student_id") in student_ids
        ]

    async def has_pending_for_student(self, student_id: str) -> bool:
        matches = await self.query(
            filters=[
                ("student_id", "==", student_id),
                ("status", "==", STATUS_PENDING),
            ],
            limit=1,
        )
        return bool(matches)
