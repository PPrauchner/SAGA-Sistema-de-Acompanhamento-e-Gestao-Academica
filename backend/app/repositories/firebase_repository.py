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
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from google.cloud import firestore
from google.cloud.firestore import Client, DocumentReference
from google.cloud.firestore_v1.base_query import FieldFilter

from backend.app.core.firebase import get_firestore_client

Filter = tuple[str, str, Any] | FieldFilter
OrderBy = str | tuple[str, str]


class FirebaseRepository:
    """Camada base para acesso a coleções e subcoleções do Firestore."""

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_firestore_client()

    def _collection(self, collection: str):
        return self.client.collection(collection)

    def _document(self, collection: str, doc_id: str) -> DocumentReference:
        return self._collection(collection).document(doc_id)

    def _with_create_timestamps(self, data: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        payload.setdefault("criado_em", firestore.SERVER_TIMESTAMP)
        payload.setdefault("atualizado_em", firestore.SERVER_TIMESTAMP)
        return payload

    def _with_update_timestamp(self, data: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        payload["atualizado_em"] = firestore.SERVER_TIMESTAMP
        return payload

    def _snapshot_to_dict(self, snapshot) -> dict[str, Any]:
        data = snapshot.to_dict() or {}
        return {"id": snapshot.id, **data}

    def _not_found(self, collection: str, doc_id: str) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento não encontrado: {collection}/{doc_id}",
        )

    async def get(self, collection: str, doc_id: str) -> dict[str, Any]:
        snapshot = await asyncio.to_thread(
            lambda: self._document(collection, doc_id).get()
        )
        if not snapshot.exists:
            raise self._not_found(collection, doc_id)
        return self._snapshot_to_dict(snapshot)

    async def create(
        self,
        collection: str,
        data: Mapping[str, Any],
        doc_id: str | None = None,
    ) -> dict[str, Any]:
        payload = self._with_create_timestamps(data)
        doc_ref = (
            self._document(collection, doc_id)
            if doc_id
            else self._collection(collection).document()
        )
        await asyncio.to_thread(lambda: doc_ref.create(payload))
        return await self.get(collection, doc_ref.id)

    async def set(
        self,
        collection: str,
        doc_id: str,
        data: Mapping[str, Any],
        merge: bool = True,
    ) -> dict[str, Any]:
        payload = self._with_update_timestamp(data)
        doc_ref = self._document(collection, doc_id)
        await asyncio.to_thread(lambda: doc_ref.set(payload, merge=merge))
        return await self.get(collection, doc_id)

    async def update(
        self,
        collection: str,
        doc_id: str,
        data: Mapping[str, Any],
    ) -> dict[str, Any]:
        doc_ref = self._document(collection, doc_id)
        exists = await asyncio.to_thread(lambda: doc_ref.get().exists)
        if not exists:
            raise self._not_found(collection, doc_id)

        await asyncio.to_thread(
            lambda: doc_ref.update(self._with_update_timestamp(data))
        )
        return await self.get(collection, doc_id)

    async def delete(self, collection: str, doc_id: str) -> None:
        doc_ref = self._document(collection, doc_id)
        exists = await asyncio.to_thread(lambda: doc_ref.get().exists)
        if not exists:
            raise self._not_found(collection, doc_id)
        await asyncio.to_thread(lambda: doc_ref.delete())

    async def list(
        self,
        collection: str,
        filters: Iterable[Filter] | None = None,
        order_by: OrderBy | Iterable[OrderBy] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        def _execute_query():
            query: Any = self._collection(collection)

            for filter_value in filters or []:
                if isinstance(filter_value, FieldFilter):
                    query = query.where(filter=filter_value)
                    continue

                field_path, op_string, value = filter_value
                query = query.where(filter=FieldFilter(field_path, op_string, value))

            order_values: Iterable[OrderBy]
            if order_by is None:
                order_values = []
            elif isinstance(order_by, str):
                order_values = [order_by]
            elif isinstance(order_by, tuple):
                order_values = [order_by]
            else:
                order_values = order_by

            for order_value in order_values:
                if isinstance(order_value, str):
                    query = query.order_by(order_value)
                else:
                    field_path, direction = order_value
                    firestore_direction = (
                        firestore.Query.DESCENDING
                        if direction.lower() in {"desc", "descending"}
                        else firestore.Query.ASCENDING
                    )
                    query = query.order_by(field_path, direction=firestore_direction)

            if limit is not None:
                query = query.limit(limit)

            return [self._snapshot_to_dict(snapshot) for snapshot in query.stream()]

        return await asyncio.to_thread(_execute_query)
