"""
Testes do FirebaseRepository (base genérica de acesso ao Firestore).

Usa um cliente Firestore fake em memória — não requer Firebase real — para
verificar get/set/update e a conversão para None quando o documento não existe.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.app.repositories import firebase_repository
from backend.app.repositories.firebase_repository import FirebaseRepository


class _FakeSnapshot:
    def __init__(self, doc_id: str, data: dict[str, Any] | None) -> None:
        self.id = doc_id
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return dict(self._data) if self._data is not None else None


class _FakeDocument:
    def __init__(self, store: dict[str, dict[str, Any]], doc_id: str) -> None:
        self._store = store
        self._id = doc_id

    def get(self) -> _FakeSnapshot:
        return _FakeSnapshot(self._id, self._store.get(self._id))

    def set(self, data: dict[str, Any]) -> None:
        self._store[self._id] = dict(data)

    def update(self, data: dict[str, Any]) -> None:
        self._store.setdefault(self._id, {}).update(data)


class _FakeCollection:
    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self._store = store

    def document(self, doc_id: str) -> _FakeDocument:
        return _FakeDocument(self._store, doc_id)


class _FakeClient:
    def __init__(self) -> None:
        self._collections: dict[str, dict[str, dict[str, Any]]] = {}

    def collection(self, name: str) -> _FakeCollection:
        return _FakeCollection(self._collections.setdefault(name, {}))


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch) -> FirebaseRepository:
    client = _FakeClient()
    monkeypatch.setattr(firebase_repository, "get_firestore_client", lambda: client)
    return FirebaseRepository("invites")


async def test_set_then_get_retorna_dados(repo: FirebaseRepository) -> None:
    await repo.set("tok1", {"email": "a@b.com", "usado": False})
    assert await repo.get("tok1") == {"id": "tok1", "email": "a@b.com", "usado": False}


async def test_get_inexistente_retorna_none(repo: FirebaseRepository) -> None:
    assert await repo.get("nao-existe") is None


async def test_update_altera_apenas_campos_informados(repo: FirebaseRepository) -> None:
    await repo.set("tok1", {"email": "a@b.com", "usado": False})
    await repo.update("tok1", {"usado": True})
    assert await repo.get("tok1") == {"id": "tok1", "email": "a@b.com", "usado": True}
