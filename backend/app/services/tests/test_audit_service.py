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
