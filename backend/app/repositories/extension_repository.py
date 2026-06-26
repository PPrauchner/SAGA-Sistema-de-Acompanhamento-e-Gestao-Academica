<<<<<<< HEAD
"""
Camada de persistência (Repository) para isolamento das operações do Firestore.
"""

from __future__ import annotations
from typing import Optional
from google.cloud import firestore

class ExtensionRepository:
    def __init__(self, db: Optional[firestore.AsyncClient] = None) -> None:
        # Pega a instância global ou injetada para evitar quebras
        self._db = db if db is not None else firestore.AsyncClient()

    def extensions_col(self, student_id: str):
        return self._db.collection("students").document(student_id).collection("extensions")

    def student_ref(self, student_id: str):
        return self._db.collection("students").document(student_id)

    def collection_group_extensions(self):
        return self._db.collection_group("extensions")

    async def get_program_config(self) -> dict:
        snap = await self._db.collection("programs").document("prog_default").get()
        return snap.to_dict() or {}

    def transaction(self):
        return self._db.transaction()
    async def get_advisor_doc_id_by_uid(self, advisor_uid: str) -> str | None:
        query = (
            self._db.collection("advisors")
            .where("advisor_uid", "==", advisor_uid)
            .limit(1)
        )
        docs = [doc async for doc in query.stream()]
        return docs[0].id if docs else None
=======
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
>>>>>>> 0161ba8854c4238232217a8a4715b9d5484d34b9
