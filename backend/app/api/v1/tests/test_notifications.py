"""
Testes do endpoint PATCH /api/v1/notifications/{id}/read.

Usa FastAPI TestClient com app.dependency_overrides[get_current_user] e monkeypatch do
NotificationService (instância do router) para isolar a rota do Firebase. Cobre o caminho
feliz (usuário autenticado marca como lida) e o repasse de id/usuário ao service.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app
from backend.app.models.notification import MarkReadResponse


class _FakeNotificationService:
    calls: list[tuple[str, str]] = []

    async def mark_as_read(self, notification_id: str, user: CurrentUser) -> MarkReadResponse:
        _FakeNotificationService.calls.append((notification_id, user.uid))
        return MarkReadResponse(id=notification_id, lida=True, message="ok")


def _override_user(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="u1", role=role, programa_id="prog_default", email="u@x.com"
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "backend.app.api.v1.notifications.service", _FakeNotificationService()
    )
    _FakeNotificationService.calls = []
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_marca_como_lida_200(client: TestClient) -> None:
    _override_user("aluno")

    resp = client.patch("/api/v1/notifications/n1/read")

    assert resp.status_code == 200
    body = resp.json()
    assert body["lida"] is True
    assert _FakeNotificationService.calls[0] == ("n1", "u1")
