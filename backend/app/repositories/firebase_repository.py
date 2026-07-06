"""
Repositório base genérico para operações no Firestore usando Firebase Admin SDK.

Responsabilidades:
- Fornecer métodos assíncronos genéricos para operações CRUD (get, create, update, delete, query).
- Encapsular o cliente Firestore assíncrono obtido de backend/app/core/firebase.py.
- Tratar exceções comuns de banco de dados, como DocumentNotFoundError.
- save_history_snapshot(doc_id, snapshot): persiste snapshot do aspecto A03 (history.py)
  em {collection}/{doc_id}/history/{auto_id}, reutilizado por todos os repositórios cujas
  entidades são versionadas (StudentRepository, ActivityTypeRepository, etc.).
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
            O documento como dict com 'id' incluído, ou None se não existir.
        """

        def _read() -> dict[str, Any] | None:
            snapshot = self._document(doc_id).get()
            if snapshot.exists:
                data = snapshot.to_dict() or {}
                data['id'] = snapshot.id
                return data
            return None

        return await asyncio.to_thread(_read)

    async def set(self, doc_id: str, data: dict[str, Any]) -> None:
        """Cria ou sobrescreve um documento com id explícito.

        Args:
            doc_id: Identificador do documento (ex: token do convite, uid do usuário).
            data: Conteúdo completo a persistir.
        """
        await asyncio.to_thread(self._document(doc_id).set, data)

    async def create(self, data: dict[str, Any], doc_id: str | None = None) -> str:
        """Cria um novo documento na coleção.

        Args:
            data: Os dados a serem armazenados.
            doc_id: ID fixo opcional para o documento.

        Returns:
            O ID do documento criado.
        """
        def _create() -> str:
            if doc_id:
                self._document(doc_id).set(data)
                return doc_id

            # Usando add() para auto-id se não fornecido
            _, doc_ref = get_firestore_client().collection(self.collection).add(data)
            return doc_ref.id

        return await asyncio.to_thread(_create)

    async def update(self, doc_id: str, data: dict[str, Any]) -> bool:
        """Atualiza parcialmente os campos de um documento existente.

        Args:
            doc_id: Identificador do documento a atualizar.
            data: Mapa dos campos a alterar.

        Returns:
            True se a atualização for executada.
        """
        await asyncio.to_thread(self._document(doc_id).update, data)
        return True

    async def delete(self, doc_id: str) -> bool:
        """Exclui um documento da coleção.

        Args:
            doc_id: Identificador do documento a excluir.

        Returns:
            True se a exclusão for executada.
        """
        await asyncio.to_thread(self._document(doc_id).delete)
        return True

    async def list_all(self) -> list[dict[str, Any]]:
        """Lista todos os documentos da coleção."""

        def _list() -> list[dict[str, Any]]:
            docs = get_firestore_client().collection(self.collection).stream()

            result = []

            for doc in docs:
                item = doc.to_dict() or {}
                item["id"] = doc.id
                result.append(item)

            return result

        return await asyncio.to_thread(_list)

    async def query(
        self,
        filters: list[tuple] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        subcollection_path: str | None = None
    ) -> list[dict[str, Any]]:
        """Realiza uma consulta na coleção ou subcoleção.

        Args:
            filters: Lista de tuplas (campo, operador, valor) para filtro.
            order_by: Nome do campo para ordenação.
            limit: Número máximo de resultados.
            subcollection_path: Opcional, permite consultar subcoleções ignorando self.collection.

        Returns:
            Lista de documentos (dicts) que atendem aos critérios.
        """
        def _execute_query() -> list[dict[str, Any]]:
            path = subcollection_path if subcollection_path else self.collection
            query_ref = get_firestore_client().collection(path)

            if filters:
                for field, op, value in filters:
                    query_ref = query_ref.where(field, op, value)

            if order_by:
                query_ref = query_ref.order_by(order_by)

            if limit:
                query_ref = query_ref.limit(limit)

            docs = query_ref.stream()
            results = []
            for doc in docs:
                data = doc.to_dict() or {}
                data['id'] = doc.id
                results.append(data)

            return results

        return await asyncio.to_thread(_execute_query)

    async def set_subcollection_auto(
        self,
        doc_id: str,
        subcollection: str,
        data: dict[str, Any],
    ) -> str:
        """Cria um documento com auto-id em uma subcoleção."""

        def _create() -> str:
            doc_ref = self._document(doc_id).collection(subcollection).document()
            doc_ref.set(data)
            return doc_ref.id

        return await asyncio.to_thread(_create)

    async def set_subcollection(
        self,
        doc_id: str,
        subcollection: str,
        sub_doc_id: str,
        data: dict[str, Any],
    ) -> None:
        """Cria ou sobrescreve um documento com id explícito em uma subcoleção."""
        await asyncio.to_thread(
            self._document(doc_id).collection(subcollection).document(sub_doc_id).set,
            data,
        )

    async def delete_subcollection(
        self,
        doc_id: str,
        subcollection: str,
        sub_doc_id: str,
    ) -> None:
        """Remove um documento de uma subcoleção."""
        await asyncio.to_thread(
            self._document(doc_id).collection(subcollection).document(sub_doc_id).delete,
        )

    async def save_history_snapshot(
        self,
        doc_id: str,
        snapshot: dict[str, Any],
    ) -> str:
        """Persiste snapshot do aspecto A03 (history.py) em {collection}/{doc_id}/history/."""

        return await self.set_subcollection_auto(doc_id, "history", snapshot)

    async def list_subcollection(
        self,
        doc_id: str,
        subcollection: str,
    ) -> list[dict[str, Any]]:
        """Lista os documentos de {collection}/{doc_id}/{subcollection}/ com o id injetado."""

        def _list() -> list[dict[str, Any]]:
            docs = self._document(doc_id).collection(subcollection).stream()
            result = []
            for doc in docs:
                item = doc.to_dict()
                item["id"] = doc.id
                result.append(item)
            return result

        return await asyncio.to_thread(_list)
