"""
Testes do AuditService — consulta paginada e filtrada dos logs de auditoria.

Usa um repositório fake em memória (sem Firestore) para verificar filtros por
usuario_id/operacao/modulo/resultado_status, filtro por intervalo de datas,
ordenação decrescente por timestamp e paginação.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from backend.app.core.auth import CurrentUser
from backend.app.services import audit_service as audit_service_module
from backend.app.services.audit_service import AuditService

_LOGS: list[dict[str, Any]] = [
    {
        "id": "log1",
        "usuario_id": "coord1",
        "operacao": "create_student",
        "modulo": "backend.app.api.v1.students",
        "resultado_status": "sucesso",
        "timestamp": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
    },
    {
        "id": "log2",
        "usuario_id": "coord1",
        "operacao": "update_student",
        "modulo": "backend.app.api.v1.students",
        "resultado_status": "erro",
        "timestamp": datetime(2026, 1, 3, 10, 0, tzinfo=timezone.utc),
    },
    {
        "id": "log3",
        "usuario_id": "orient1",
        "operacao": "create_activity",
        "modulo": "backend.app.api.v1.activities",
        "resultado_status": "sucesso",
        "timestamp": datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
    },
]


class _FakeRepo:
    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def list_all(self) -> list[dict[str, Any]]:
        return [dict(log) for log in _LOGS]


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> AuditService:
    monkeypatch.setattr(audit_service_module, "FirebaseRepository", _FakeRepo)
    return AuditService()


async def test_sem_filtros_ordena_do_mais_recente(service: AuditService) -> None:
    page = await service.list_audit_logs()

    assert page.total == 3
    assert [item.id for item in page.items] == ["log2", "log3", "log1"]


async def test_filtra_por_usuario_id(service: AuditService) -> None:
    page = await service.list_audit_logs(usuario_id="coord1")

    assert page.total == 2
    assert {item.usuario_id for item in page.items} == {"coord1"}


async def test_filtra_por_resultado_status(service: AuditService) -> None:
    page = await service.list_audit_logs(resultado_status="erro")

    assert page.total == 1
    assert page.items[0].id == "log2"


async def test_filtra_por_intervalo_de_datas(service: AuditService) -> None:
    page = await service.list_audit_logs(
        data_inicio=datetime(2026, 1, 2, tzinfo=timezone.utc),
        data_fim=datetime(2026, 1, 2, 23, 59, tzinfo=timezone.utc),
    )

    assert page.total == 1
    assert page.items[0].id == "log3"


async def test_pagina_resultados(service: AuditService) -> None:
    primeira = await service.list_audit_logs(page=1, page_size=2)
    segunda = await service.list_audit_logs(page=2, page_size=2)

    assert primeira.total == 3
    assert [item.id for item in primeira.items] == ["log2", "log3"]
    assert [item.id for item in segunda.items] == ["log1"]


# --- Escopo por papel (orientador vê apenas os logs dos seus orientandos) ---------------

_SCOPE_LOGS: list[dict[str, Any]] = [
    {"id": "s1", "usuario_id": "stu1", "timestamp": datetime(2026, 2, 1, tzinfo=timezone.utc)},
    {"id": "s2", "usuario_id": "stu2", "timestamp": datetime(2026, 2, 2, tzinfo=timezone.utc)},
    {"id": "other", "usuario_id": "stu3", "timestamp": datetime(2026, 2, 3, tzinfo=timezone.utc)},
    {"id": "coord", "usuario_id": "coordX", "timestamp": datetime(2026, 2, 4, tzinfo=timezone.utc)},
]

_SCOPE_ADVISORS: list[dict[str, Any]] = [
    {"id": "adv1", "uid": "orient1"},
    {"id": "adv2", "uid": "orient2"},
]

_SCOPE_STUDENTS: list[dict[str, Any]] = [
    {"uid": "stu1", "orientador_id": "adv1"},
    {"uid": "stu2", "orientador_id": "adv1"},
    {"uid": "stu3", "orientador_id": "adv2"},
]


class _FakeListRepo:
    """Repositório fake genérico: devolve a lista fixada por list_all()."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self._items = items

    async def list_all(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._items]


@pytest.fixture
def scope_service(monkeypatch: pytest.MonkeyPatch) -> AuditService:
    monkeypatch.setattr(
        audit_service_module, "FirebaseRepository", lambda collection: _FakeListRepo(_SCOPE_LOGS)
    )
    return AuditService(
        advisors=_FakeListRepo(_SCOPE_ADVISORS),
        students=_FakeListRepo(_SCOPE_STUDENTS),
    )


async def test_orientador_ve_apenas_logs_dos_seus_orientandos(scope_service: AuditService) -> None:
    user = CurrentUser(uid="orient1", role="orientador")

    page = await scope_service.list_audit_logs(user=user)

    assert page.total == 2
    assert {item.id for item in page.items} == {"s1", "s2"}


async def test_coordenacao_ve_todos_os_logs(scope_service: AuditService) -> None:
    user = CurrentUser(uid="coordX", role="coordenacao")

    page = await scope_service.list_audit_logs(user=user)

    assert page.total == 4


async def test_orientador_sem_doc_advisors_nao_ve_nada(scope_service: AuditService) -> None:
    user = CurrentUser(uid="fantasma", role="orientador")

    page = await scope_service.list_audit_logs(user=user)

    assert page.total == 0
    assert page.items == []


# --- Resolução de nome do autor no read path -------------------------------------------


class _FakeNames:
    """Resolver fake de uid→nome (sem I/O)."""

    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping

    async def resolve(self, uids: Any) -> dict[str, str]:
        return {uid: self._mapping[uid] for uid in uids if uid in self._mapping}


async def test_resolve_usuario_nome_na_pagina(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit_service_module, "FirebaseRepository", _FakeRepo)
    service = AuditService(names=_FakeNames({"coord1": "Ana Souza", "orient1": "Bruno Lima"}))

    page = await service.list_audit_logs()

    por_id = {item.id: item for item in page.items}
    assert por_id["log1"].usuario_nome == "Ana Souza"
    assert por_id["log3"].usuario_nome == "Bruno Lima"
    # id permanece canônico e presente na resposta
    assert por_id["log1"].usuario_id == "coord1"


async def test_usuario_nome_none_quando_uid_desconhecido(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit_service_module, "FirebaseRepository", _FakeRepo)
    service = AuditService(names=_FakeNames({}))

    page = await service.list_audit_logs()

    assert all(item.usuario_nome is None for item in page.items)


# --- Opções de filtro (facetas) --------------------------------------------------------


async def test_filter_options_distintos_ordenados_com_nome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit_service_module, "FirebaseRepository", _FakeRepo)
    service = AuditService(names=_FakeNames({"coord1": "Ana Souza", "orient1": "Bruno Lima"}))

    options = await service.list_filter_options()

    assert options.operacoes == ["create_activity", "create_student", "update_student"]
    assert options.modulos == [
        "backend.app.api.v1.activities",
        "backend.app.api.v1.students",
    ]
    # usuários distintos, ordenados por nome, id canônico preservado
    assert [(u.id, u.nome) for u in options.usuarios] == [
        ("coord1", "Ana Souza"),
        ("orient1", "Bruno Lima"),
    ]


async def test_filter_options_usuario_sem_nome_cai_para_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit_service_module, "FirebaseRepository", _FakeRepo)
    service = AuditService(names=_FakeNames({}))

    options = await service.list_filter_options()

    assert {u.id for u in options.usuarios} == {"coord1", "orient1"}
    assert all(u.nome == u.id for u in options.usuarios)


async def test_filter_options_escopo_orientador(scope_service: AuditService) -> None:
    user = CurrentUser(uid="orient1", role="orientador")

    options = await scope_service.list_filter_options(user=user)

    # orientador só enxerga usuários dos seus orientandos (stu1, stu2)
    assert {u.id for u in options.usuarios} == {"stu1", "stu2"}
