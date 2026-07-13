"""
Repositório concreto para a sub-coleção students/{id}/activities/ no Firestore.
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
        return (
            get_firestore_client()
            .collection("students")
            .document(student_id)
            .collection("activities")
            .document(activity_id)
        )

    # -- usado por submit_activity / list_activities / comprovante (async, original) --

    async def create_activity(self, student_id: str, data: dict[str, Any]) -> str:
        return await self.set_subcollection_auto(student_id, "activities", data)

    async def get_activity(self, student_id: str, activity_id: str) -> dict[str, Any] | None:
        def _read():
            snapshot = self._activity_doc(student_id, activity_id).get()
            if not snapshot.exists:
                return None
            item = snapshot.to_dict()
            item["id"] = snapshot.id
            item["student_id"] = student_id
            return item
        return await asyncio.to_thread(_read)

    async def update_activity(self, student_id: str, activity_id: str, data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._activity_doc(student_id, activity_id).update, data)

    async def list_by_student(self, student_id: str) -> list[dict[str, Any]]:
        return await self.list_subcollection(student_id, "activities")

    async def list_all_grouped(self) -> list[dict[str, Any]]:
        """Lista as atividades de todos os alunos em uma única consulta.

        Um único stream de collection_group("activities") substitui os loops
        N×list_by_student dos services (padrão N+1 — issue #319). O student_id
        de cada atividade é extraído do path do documento.

        Returns:
            Lista de atividades com 'id' e 'student_id' injetados.
        """

        def _list() -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            for snapshot in get_firestore_client().collection_group("activities").stream():
                item = snapshot.to_dict() or {}
                item["id"] = snapshot.id
                item["student_id"] = snapshot.reference.parent.parent.id
                result.append(item)
            return result

        return await asyncio.to_thread(_list)

    # -- usado pelos fluxos de validação (PATCH /parecer e /validate), que só têm --
    # activity_id na URL: localiza o documento via collection_group, sem o student_id.
    # O scan roda em thread separada (asyncio.to_thread) para não bloquear o event loop.

    async def get_by_id(self, activity_id: str) -> dict[str, Any] | None:
        def _find() -> dict[str, Any] | None:
            for snapshot in get_firestore_client().collection_group("activities").stream():
                if snapshot.id == activity_id:
                    item = snapshot.to_dict()
                    item["id"] = snapshot.id
                    item["student_id"] = snapshot.reference.parent.parent.id
                    return item
            return None

        return await asyncio.to_thread(_find)

    async def update_by_id(self, activity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        def _update() -> dict[str, Any]:
            for snapshot in get_firestore_client().collection_group("activities").stream():
                if snapshot.id == activity_id:
                    snapshot.reference.update(data)
                    updated = snapshot.reference.get()
                    item = updated.to_dict()
                    item["id"] = updated.id
                    item["student_id"] = updated.reference.parent.parent.id
                    return item
            raise ValueError(f"Atividade {activity_id} não encontrada.")

        return await asyncio.to_thread(_update)

    async def delete_by_id(self, activity_id: str) -> None:
        """Exclui (hard delete) a atividade localizada por collection_group scan.

        Usado pelo DELETE /activities/{activity_id} (issue #305), que só tem o
        activity_id na URL — igual padrão de get_by_id/update_by_id.
        """

        def _delete() -> None:
            for snapshot in get_firestore_client().collection_group("activities").stream():
                if snapshot.id == activity_id:
                    snapshot.reference.delete()
                    return
            raise ValueError(f"Atividade {activity_id} não encontrada.")

        await asyncio.to_thread(_delete)

    async def update_group_comprovante(
        self,
        activity_group_id: str,
        comprovante_url: str,
        atualizado_em: Any,
    ) -> list[str]:
        def _update_group() -> list[str]:
            updated_ids: list[str] = []
            for snapshot in get_firestore_client().collection_group("activities").stream():
                data = snapshot.to_dict()
                if data.get("activity_group_id") != activity_group_id:
                    continue
                snapshot.reference.update(
                    {
                        "comprovante_url": comprovante_url,
                        "atualizado_em": atualizado_em,
                    }
                )
                updated_ids.append(snapshot.id)
            return updated_ids

        return await asyncio.to_thread(_update_group)

    async def get_activity_type(self, tipo_id: str) -> dict[str, Any] | None:
        def _read() -> dict[str, Any] | None:
            doc = get_firestore_client().collection("activity_types").document(tipo_id).get()
            if not doc.exists:
                return None
            return {"id": doc.id, **doc.to_dict()}

        return await asyncio.to_thread(_read)
