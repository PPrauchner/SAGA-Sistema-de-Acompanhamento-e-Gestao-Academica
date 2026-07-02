"""
Testes do endpoint GET /api/v1/audit-logs.

Usa FastAPI TestClient com app.dependency_overrides[get_current_user] para injetar
um CurrentUser fake e monkeypatch do AuditService (instância do router) para isolar a
rota da lógica de negócio e do Firebase. Cobre a autorização por papel (@requires_role
'coordenacao','orientador'), o repasse dos filtros e do usuário e o envelope de paginação.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app
from backend.app.models.audit import AuditLogPage


class _FakeAuditService:
    """AuditService fake: registra os filtros recebidos e devolve uma página vazia."""

    calls: list[dict[str, Any]] = []

    async def list_audit_logs(self, **kwargs: Any) -> AuditLogPage:
        _FakeAuditService.calls.append(kwargs)
        return AuditLogPage(
            items=[],
            page=kwargs["page"],
            page_size=kwargs["page_size"],
            total=0,
        )


def _override_user(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="u1", role=role, programa_id="prog_default", email="u@x.com"
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "backend.app.api.v1.audit_logs.service", _FakeAuditService()
    )
    _FakeAuditService.calls = []
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_coordenacao_recebe_pagina_e_repassa_filtros(client: TestClient) -> None:
    _override_user("coordenacao")

    resp = client.get(
        "/api/v1/audit-logs",
        params={"page": 2, "page_size": 5, "operacao": "create_student"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 2
    assert body["page_size"] == 5
    assert _FakeAuditService.calls[0]["operacao"] == "create_student"


def test_orientador_autorizado_e_repassa_user(client: TestClient) -> None:
    _override_user("orientador")

    resp = client.get("/api/v1/audit-logs")

    assert resp.status_code == 200
    assert _FakeAuditService.calls[0]["user"].role == "orientador"


def test_papel_insuficiente_403(client: TestClient) -> None:
    _override_user("aluno")

    resp = client.get("/api/v1/audit-logs")

    assert resp.status_code == 403
    assert _FakeAuditService.calls == []


def test_page_size_acima_do_maximo_422(client: TestClient) -> None:
    _override_user("coordenacao")

    resp = client.get("/api/v1/audit-logs", params={"page_size": 500})

    assert resp.status_code == 422
