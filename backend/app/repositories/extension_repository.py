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