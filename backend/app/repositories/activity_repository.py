"""
Repositório concreto para a sub-coleção students/{id}/activities/ no Firestore.

Responsabilidades:
- create_activity(student_id, data): cria atividade com auto-id na sub-coleção do aluno.
- get_activity(student_id, activity_id): lê uma atividade específica.
- update_activity(student_id, activity_id, data): atualiza campos de uma atividade.
- list_by_student(student_id): lista todas as atividades do aluno (id injetado).
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.core.firebase import get_firestore_client
from backend.app.repositories.firebase_repository import FirebaseRepository


class ActivityRepository(FirebaseRepository):
    """Repositório da sub-coleção students/{id}/activities/."""

    def __init__(self) -> None:
        super().__init__("students")

    def _activity_doc(self, student_id: str, activity_id: str):
        """Referência síncrona ao documento students/{student_id}/activities/{activity_id}."""
        return (
            get_firestore_client()
            .collection("students")
            .document(student_id)
            .collection("activities")
            .document(activity_id)
        )

    async def create_activity(self, student_id: str, data: dict[str, Any]) -> str:
        """Cria uma atividade na sub-coleção do aluno e retorna o id gerado."""
        return await self.set_subcollection_auto(student_id, "activities", data)

    async def get_activity(self, student_id: str, activity_id: str) -> dict[str, Any] | None:
        """Lê uma atividade do aluno, com o id injetado, ou None se não existir."""

        def _read() -> dict[str, Any] | None:
            snapshot = self._activity_doc(student_id, activity_id).get()
            if not snapshot.exists:
                return None
            item = snapshot.to_dict()
            item["id"] = snapshot.id
            return item

        return await asyncio.to_thread(_read)

    async def update_activity(
        self,
        student_id: str,
        activity_id: str,
        data: dict[str, Any],
    ) -> None:
        """Atualiza parcialmente os campos de uma atividade do aluno."""
        await asyncio.to_thread(self._activity_doc(student_id, activity_id).update, data)

    async def list_by_student(self, student_id: str) -> list[dict[str, Any]]:
        """Lista todas as atividades do aluno (id injetado em cada item)."""
        return await self.list_subcollection(student_id, "activities")
