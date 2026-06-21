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

    # -- usado pelo fluxo de validação (PATCH /validate), que só tem activity_id na URL --
    # síncronos de propósito, pra não mudar o comportamento dos decoradores já testados

    def get_by_id(self, activity_id: str) -> dict[str, Any] | None:
        for snapshot in get_firestore_client().collection_group("activities").stream():
            if snapshot.id == activity_id:
                item = snapshot.to_dict()
                item["id"] = snapshot.id
                item["student_id"] = snapshot.reference.parent.parent.id
                return item
        return None

    def update_by_id(self, activity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        for snapshot in get_firestore_client().collection_group("activities").stream():
            if snapshot.id == activity_id:
                snapshot.reference.update(data)
                updated = snapshot.reference.get()
                item = updated.to_dict()
                item["id"] = updated.id
                item["student_id"] = updated.reference.parent.parent.id
                return item
        raise ValueError(f"Atividade {activity_id} não encontrada.")

    def get_advisor_uid_by_student(self, student_id: str) -> str | None:
        doc = get_firestore_client().collection("students").document(student_id).get()
        if not doc.exists:
            return None
        return doc.to_dict().get("orientador_uid")

    def get_activity_type(self, tipo_id: str) -> dict[str, Any] | None:
        doc = get_firestore_client().collection("activity_types").document(tipo_id).get()
        if not doc.exists:
            return None
        return {"id": doc.id, **doc.to_dict()}

    def count_approved_productions(self, student_id: str) -> int:
        docs = (
            get_firestore_client()
            .collection("students")
            .document(student_id)
            .collection("activities")
            .where("categoria", "==", "producao_bibliografica")
            .where("status", "==", "aprovado")
            .stream()
        )
        return sum(1 for _ in docs)