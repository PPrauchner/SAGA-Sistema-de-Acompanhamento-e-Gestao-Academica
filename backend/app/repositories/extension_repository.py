"""
Repositório concreto para prorrogações de prazo (extensions).

Usa Firebase Admin SDK síncrono (get_firestore_client) + asyncio.to_thread,
alinhado com FirebaseRepository e todos os outros repositórios do projeto.
Não herda FirebaseRepository porque gerencia duas coleções raiz distintas
(students/ e config/) além das subcoleções de extensions.

Contrato exigido por ExtensionService:
  extensions_col(student_id)      → _ExtensionsCol  (proxy de subcoleção)
  student_ref(student_id)         → _StudentRef      (proxy de documento)
  get_program_config()            → dict             (async)
  get_advisor_doc_id_by_uid(uid)  → Optional[str]   (async)
  transaction()                   → google.cloud.firestore.Client
  collection_group_extensions()   → _CollectionGroupProxy
  _db                             → google.cloud.firestore.Client
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from google.cloud import firestore as _fs

from backend.app.core.firebase import get_firestore_client

_COL_STUDENTS:   str = "students"
_COL_EXTENSIONS: str = "extensions"
_COL_USERS:      str = "users"
_COL_CONFIG:     str = "config"
_DOC_PROGRAM:    str = "program"


# ---------------------------------------------------------------------------
# Proxies síncronos — imitam a API de referência usada pelo service,
# mas executam toda I/O dentro de asyncio.to_thread.
# ---------------------------------------------------------------------------

class _ExtensionsCol:
    """
    Proxy para students/{student_id}/extensions.

    O service encadeia chamadas como:
        self._repo.extensions_col(sid).where(...).stream()   → async for
        self._repo.extensions_col(sid).document(eid)         → _DocRef
        self._repo.extensions_col(sid).document()            → _DocRef (auto-id)
        self._repo.extensions_col(sid).order_by(...).stream()
    """

    def __init__(self, student_id: str) -> None:
        self._student_id = student_id
        self._filters: list[tuple[str, str, Any]] = []
        self._order:   Optional[tuple[str, Any]]  = None

    def _col_ref(self):
        return (
            get_firestore_client()
            .collection(_COL_STUDENTS)
            .document(self._student_id)
            .collection(_COL_EXTENSIONS)
        )

    # -- fluent API -----------------------------------------------------------

    def where(self, field: str, op: str, value: Any) -> "_ExtensionsCol":
        clone = _ExtensionsCol(self._student_id)
        clone._filters = self._filters + [(field, op, value)]
        clone._order   = self._order
        return clone

    def order_by(self, field: str, direction: Any = None) -> "_ExtensionsCol":
        clone = _ExtensionsCol(self._student_id)
        clone._filters = list(self._filters)
        clone._order   = (field, direction)
        return clone

    def document(self, doc_id: Optional[str] = None) -> "_DocRef":
        return _DocRef(self._col_ref, doc_id)

    # -- async stream ---------------------------------------------------------

    def stream(self):
        """
        Retorna um async-iterator que executa o stream síncrono em to_thread.
        O service usa:  [d async for d in query.stream()]
        """
        return _SyncStreamAsAsyncIter(self._build_query)

    def _build_query(self):
        q = self._col_ref()
        for field, op, value in self._filters:
            q = q.where(field, op, value)
        if self._order:
            field, direction = self._order
            if direction is not None:
                q = q.order_by(field, direction=direction)
            else:
                q = q.order_by(field)
        return list(q.stream())


class _DocRef:
    """
    Proxy para um documento (existente ou novo) dentro de uma subcoleção.

    O service usa:
        ref.id                          → str
        await ref.get()                 → _Snapshot
        await ref.set(data)
        await ref.update(data)
    """

    def __init__(self, col_ref_factory, doc_id: Optional[str]) -> None:
        self._col_ref_factory = col_ref_factory
        self._doc_id = doc_id
        # Se auto-id: gera um id local imediatamente para expor via .id
        if doc_id is None:
            self._doc_id = get_firestore_client().collection("_").document().id

    @property
    def id(self) -> str:
        return self._doc_id

    def _ref(self):
        return self._col_ref_factory().document(self._doc_id)

    async def get(self) -> "_Snapshot":
        snap = await asyncio.to_thread(self._ref().get)
        return _Snapshot(snap)

    async def set(self, data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._ref().set, data)

    async def update(self, data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._ref().update, data)


class _Snapshot:
    """Thin wrapper sobre DocumentSnapshot síncrono."""

    def __init__(self, snap) -> None:
        self._snap = snap

    @property
    def exists(self) -> bool:
        return self._snap.exists

    @property
    def id(self) -> str:
        return self._snap.id

    def to_dict(self) -> dict[str, Any]:
        return self._snap.to_dict() or {}


class _SyncStreamAsAsyncIter:
    """
    Executa uma query síncrona em to_thread e expõe os resultados
    como async-iterator, permitindo `async for doc in query.stream()`.
    """

    def __init__(self, query_fn) -> None:
        self._query_fn = query_fn
        self._docs: Optional[list] = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._docs is None:
            self._docs = await asyncio.to_thread(self._query_fn)
            self._idx = 0
        if self._idx >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._idx]
        self._idx += 1
        return _Snapshot(doc)


class _StudentRef:
    """
    Proxy para students/{student_id}.

    O service usa:
        await self._repo.student_ref(sid).get()  → _Snapshot
    O service também passa o ref diretamente para transaction.get(ref)
    → neste caso, devolvemos o DocumentReference síncrono real via .sync_ref.
    """

    def __init__(self, student_id: str) -> None:
        self._student_id = student_id

    @property
    def sync_ref(self):
        return (
            get_firestore_client()
            .collection(_COL_STUDENTS)
            .document(self._student_id)
        )

    async def get(self) -> _Snapshot:
        snap = await asyncio.to_thread(self.sync_ref.get)
        return _Snapshot(snap)


class _CollectionGroupProxy:
    """
    Proxy para collection_group("extensions").

    O service usa:
        .where(...).order_by(...).stream()  → async for
    """

    def __init__(self) -> None:
        self._filters: list[tuple[str, str, Any]] = []
        self._order:   Optional[tuple[str, Any]]  = None

    def where(self, field: str, op: str, value: Any) -> "_CollectionGroupProxy":
        clone = _CollectionGroupProxy()
        clone._filters = self._filters + [(field, op, value)]
        clone._order   = self._order
        return clone

    def order_by(self, field: str, direction: Any = None) -> "_CollectionGroupProxy":
        clone = _CollectionGroupProxy()
        clone._filters = list(self._filters)
        clone._order   = (field, direction)
        return clone

    def stream(self) -> _SyncStreamAsAsyncIter:
        return _SyncStreamAsAsyncIter(self._run)

    def _run(self) -> list:
        db = get_firestore_client()
        q = db.collection_group(_COL_EXTENSIONS)
        for field, op, value in self._filters:
            q = q.where(field, op, value)
        if self._order:
            field, direction = self._order
            if direction is not None:
                q = q.order_by(field, direction=direction)
            else:
                q = q.order_by(field)
        return list(q.stream())


# ---------------------------------------------------------------------------
# Repositório principal
# ---------------------------------------------------------------------------

class ExtensionRepository:
    """
    Repositório de prorrogações alinhado com o padrão Admin SDK síncrono
    do projeto (get_firestore_client + asyncio.to_thread).

    Não herda FirebaseRepository porque opera em múltiplas coleções raiz;
    a lógica de to_thread está encapsulada nos proxies acima.
    """

    @property
    def _db(self):
        """
        Exposto para o service em list_pending_for_advisor:
            self._repo._db.collection("students").where(...).stream()
        Devolve o cliente síncrono; o service precisará de ajuste pontual
        nesse método (ver docstring de list_pending_for_advisor no service).
        """
        return get_firestore_client()

    # -- API exigida pelo service --------------------------------------------

    def extensions_col(self, student_id: str) -> _ExtensionsCol:
        """Proxy de students/{student_id}/extensions com API fluente async."""
        return _ExtensionsCol(student_id)

    def student_ref(self, student_id: str) -> _StudentRef:
        """Proxy de students/{student_id} com .get() async e .sync_ref síncrono."""
        return _StudentRef(student_id)

    def transaction(self):
        """
        Devolve o cliente Firestore síncrono.

        process_decision no service usa @firestore.async_transactional —
        ver nota em extension_service.py: essa seção precisa ser convertida
        para @firestore.transactional + asyncio.to_thread.
        """
        return get_firestore_client()

    def collection_group_extensions(self) -> _CollectionGroupProxy:
        """Proxy do collection_group('extensions') com API fluente async."""
        return _CollectionGroupProxy()

    # -- async helpers -------------------------------------------------------

    async def get_program_config(self) -> dict[str, Any]:
        """
        Lê config/program.
        Retorna {} se o documento não existir (callers usam .get(key, default)).
        """
        def _read():
            snap = (
                get_firestore_client()
                .collection(_COL_CONFIG)
                .document(_DOC_PROGRAM)
                .get()
            )
            return snap.to_dict() if snap.exists else {}

        return await asyncio.to_thread(_read)

    async def get_advisor_doc_id_by_uid(self, uid: str) -> Optional[str]:
        """
        Resolve uid de autenticação → doc id em users/.
        Retorna None se não encontrado.
        """
        def _query():
            docs = list(
                get_firestore_client()
                .collection(_COL_USERS)
                .where("uid", "==", uid)
                .limit(1)
                .stream()
            )
            return docs[0].id if docs else None

        return await asyncio.to_thread(_query)