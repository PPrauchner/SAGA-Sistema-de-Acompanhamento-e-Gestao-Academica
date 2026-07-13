"""Fake in-process do Firestore para testes de repositorio.

Implementa o subconjunto da API do Admin SDK usado por WorkPlanRepository:
collection/document, add, set/update/delete, get, stream, where, limit, order_by e
collection_group. Os documentos guardam python dicts em memoria; `to_dict()` devolve
copias profundas para que mutacoes do codigo de negocio nao corrompam o store.

Uso tipico:
    fake = FakeFirestore()
    with patch("backend.app.repositories.work_plan_repository.get_firestore_client", return_value=fake):
        ...
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class _Doc:
    """No de armazenamento de um documento (dados + sub-colecoes)."""

    def __init__(self, doc_id: str) -> None:
        self.id = doc_id
        self.data: dict[str, Any] | None = None
        self.subs: dict[str, _Collection] = {}

    def sub(self, name: str) -> _Collection:
        return self.subs.setdefault(name, _Collection(name))


class _Collection:
    """No de armazenamento de uma colecao (mapa id -> _Doc)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.docs: dict[str, _Doc] = {}

    def doc(self, doc_id: str) -> _Doc:
        return self.docs.setdefault(doc_id, _Doc(doc_id))


class FakeSnapshot:
    """Equivalente a um DocumentSnapshot."""

    def __init__(self, doc: _Doc) -> None:
        self._doc = doc

    @property
    def id(self) -> str:
        return self._doc.id

    @property
    def exists(self) -> bool:
        return self._doc.data is not None

    @property
    def reference(self) -> FakeDocRef:
        return FakeDocRef(self._doc)

    def to_dict(self) -> dict[str, Any] | None:
        return deepcopy(self._doc.data) if self._doc.data is not None else None


class FakeDocRef:
    """Equivalente a um DocumentReference."""

    def __init__(self, doc: _Doc) -> None:
        self._doc = doc

    @property
    def id(self) -> str:
        return self._doc.id

    def get(self) -> FakeSnapshot:
        return FakeSnapshot(self._doc)

    def set(self, data: dict[str, Any]) -> None:
        self._doc.data = deepcopy(data)

    def update(self, data: dict[str, Any]) -> None:
        if self._doc.data is None:
            raise KeyError(self._doc.id)
        self._doc.data.update(deepcopy(data))

    def delete(self) -> None:
        self._doc.data = None

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self._doc.sub(name))


class FakeQuery:
    """Consulta sobre um conjunto candidato de documentos (colecao ou collection group)."""

    def __init__(self, candidates: list[_Doc]) -> None:
        self._candidates = candidates
        self._filters: list[tuple[str, str, Any]] = []
        self._limit: int | None = None
        self._order_by: str | None = None

    def where(self, field: str, op: str, value: Any) -> FakeQuery:
        self._filters.append((field, op, value))
        return self

    def limit(self, n: int) -> FakeQuery:
        self._limit = n
        return self

    def order_by(self, field: str) -> FakeQuery:
        self._order_by = field
        return self

    def stream(self) -> list[FakeSnapshot]:
        docs = [doc for doc in self._candidates if doc.data is not None]
        for field, op, value in self._filters:
            if op != "==":
                raise NotImplementedError(f"operador nao suportado no fake: {op}")
            docs = [doc for doc in docs if (doc.data or {}).get(field) == value]
        if self._order_by is not None:
            docs.sort(key=lambda doc: (doc.data or {}).get(self._order_by))
        if self._limit is not None:
            docs = docs[: self._limit]
        return [FakeSnapshot(doc) for doc in docs]


class FakeCollection:
    """Equivalente a um CollectionReference."""

    def __init__(self, col: _Collection) -> None:
        self._col = col

    def document(self, doc_id: str | None = None) -> FakeDocRef:
        return FakeDocRef(self._col.doc(doc_id or uuid4().hex))

    def add(self, data: dict[str, Any]) -> tuple[datetime, FakeDocRef]:
        ref = self.document()
        ref.set(data)
        return datetime.now(timezone.utc), ref

    def where(self, field: str, op: str, value: Any) -> FakeQuery:
        return FakeQuery(list(self._col.docs.values())).where(field, op, value)

    def limit(self, n: int) -> FakeQuery:
        return FakeQuery(list(self._col.docs.values())).limit(n)

    def order_by(self, field: str) -> FakeQuery:
        return FakeQuery(list(self._col.docs.values())).order_by(field)

    def stream(self) -> list[FakeSnapshot]:
        return FakeQuery(list(self._col.docs.values())).stream()


class FakeFirestore:
    """Cliente Firestore fake com colecoes raiz e collection groups."""

    def __init__(self) -> None:
        self._root: dict[str, _Collection] = {}

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self._root.setdefault(name, _Collection(name)))

    def collection_group(self, name: str) -> FakeQuery:
        candidates: list[_Doc] = []
        for col in self._root.values():
            _collect_group(col, name, candidates)
        return FakeQuery(candidates)


def _collect_group(col: _Collection, group: str, out: list[_Doc]) -> None:
    if col.name == group:
        out.extend(col.docs.values())
    for doc in col.docs.values():
        for sub in doc.subs.values():
            _collect_group(sub, group, out)
