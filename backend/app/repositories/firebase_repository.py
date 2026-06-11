"""
Repositório base genérico para operações no Firestore via Firebase Admin SDK.

Responsabilidades:
- Definir a classe FirebaseRepository com métodos assíncronos genéricos reutilizados por
  todos os repositórios concretos: get(collection, doc_id), create(collection, data),
  update(collection, doc_id, data), delete(collection, doc_id), query(collection,
  filters, order_by, limit).
- Encapsular o cliente Firestore assíncrono obtido de backend/app/core/firebase.py.
- Converter Timestamps do Firestore para datetime Python e vice-versa.
- Tratar DocumentNotFoundError lançando HTTPException(404) padronizada.
- Ser a única camada que importa google.cloud.firestore — todos os outros módulos
  acessam dados exclusivamente através dos repositórios concretos.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.core.firebase import get_firestore_client


class FirebaseRepository:
    """Repositório base genérico para operações no Firestore.

    O Firebase Admin SDK expõe um cliente síncrono; cada operação de I/O é
    executada em uma thread separada via asyncio.to_thread para não bloquear
    o event loop do FastAPI. Repositórios concretos herdam esta classe e
    fixam sua coleção no construtor.

    Attributes:
        collection: Nome da coleção Firestore manipulada por esta instância.
    """

    def __init__(self, collection: str) -> None:
        self.collection = collection

    def _document(self, doc_id: str):
        """Retorna a referência síncrona do documento na coleção desta instância."""
        return get_firestore_client().collection(self.collection).document(doc_id)

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        """Lê um documento por id.

        Args:
            doc_id: Identificador do documento na coleção.

        Returns:
            O documento como dict, ou None se não existir.
        """

        def _read() -> dict[str, Any] | None:
            snapshot = self._document(doc_id).get()
            return snapshot.to_dict() if snapshot.exists else None

        return await asyncio.to_thread(_read)

    async def set(self, doc_id: str, data: dict[str, Any]) -> None:
        """Cria ou sobrescreve um documento com id explícito.

        Args:
            doc_id: Identificador do documento (ex: token do convite, uid do usuário).
            data: Conteúdo completo a persistir.
        """
        await asyncio.to_thread(self._document(doc_id).set, data)

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        """Atualiza parcialmente os campos de um documento existente.

        Args:
            doc_id: Identificador do documento a atualizar.
            data: Mapa dos campos a alterar.
        """
        await asyncio.to_thread(self._document(doc_id).update, data)

    async def delete(self, doc_id: str) -> None:
        """Remove um documento da coleção."""

        await asyncio.to_thread(
            self._document(doc_id).delete,
        )

    async def list_all(self) -> list[dict[str, Any]]:
        """Lista todos os documentos da coleção."""

        def _list() -> list[dict[str, Any]]:
            docs = get_firestore_client().collection(self.collection).stream()

            result = []

            for doc in docs:
                item = doc.to_dict()
                item["id"] = doc.id
                result.append(item)

            return result

        return await asyncio.to_thread(_list)
