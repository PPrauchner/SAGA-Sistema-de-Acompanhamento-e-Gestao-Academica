# backend/app/repositories/transfer_firestore.py
from google.cloud import firestore

class FirestoreTransferRepo:
    def __init__(self):
        self.db = firestore.AsyncClient()
        self.collection = "transfer_requests"

    async def get_by_id(self, transfer_id: str) -> dict:
        doc = await self.db.collection(self.collection).document(transfer_id).get()
        return doc.to_dict() if doc.exists else None

    async def save(self, payload: dict) -> dict:
        doc_ref = self.db.collection(self.collection).document()
        payload["id"] = doc_ref.id
        await doc_ref.set(payload)
        return payload

    async def update(self, transfer_id: str, updates: dict) -> dict:
        doc_ref = self.db.collection(self.collection).document(transfer_id)
        await doc_ref.update(updates)
        updated_doc = await doc_ref.get()
        return updated_doc.to_dict()

    async def has_pending_request(self, student_id: str) -> bool:
        query = self.db.collection(self.collection)\
            .where("student_id", "==", student_id)\
            .where("status", "in", ["pendente_origem", "pendente_destino"])\
            .limit(1)
        docs = await query.get()
        return len(docs) > 0

    async def get_active_advising_count(self, orientador_id: str) -> int:
        query = self.db.collection("students")\
            .where("orientador_id", "==", orientador_id)\
            .where("situacao_registrada", "in", ["regular", "em_prorrogacao", "em_risco"])
        docs = await query.get()
        return len(docs)