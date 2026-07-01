from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import extensions as router_module
from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app


def _extension_payload(extension_id: str = "ext1") -> dict[str, Any]:
    return {
        "id": extension_id,
        "tipo": "prazo_defesa",
        "status": "pendente",
        "student_id": "student1",
        "aluno_id": "student1",
        "aluno_nome": "Aluno SAGA",
        "aluno": "Aluno SAGA",
        "matricula": "2026001",
        "nivel": "mestrado",
        "nova_data": date(2028, 7, 1),
        "prazo_novo": date(2028, 7, 1),
        "data_atual": date(2028, 1, 1),
        "prazo_atual": date(2028, 1, 1),
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "solicitacao": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "motivo": "Ajuste de cronograma",
        "justificativa": "Ajuste de cronograma",
        "parecer": None,
    }


class _FakeExtensionService:
    calls: list[tuple[str, Any]] = []

    async def list_extensions(self, user: CurrentUser) -> list[dict[str, Any]]:
        self.calls.append(("list", user))
        return [_extension_payload()]

    async def list_pending_for_coordination(
        self, user: CurrentUser, status: str = "pendente"
    ) -> list[dict[str, Any]]:
        self.calls.append(("pending", (user, status)))
        return [_extension_payload()]

    async def create_extension(self, body: Any, user: CurrentUser) -> dict[str, Any]:
        self.calls.append(("create", (body, user)))
        return _extension_payload("ext2")


def _user(role: str = "coordenacao") -> CurrentUser:
    return CurrentUser(
        uid=f"uid-{role}",
        role=role,
        programa_id="prog",
        email=f"{role}@saga.test",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    original_service = router_module.service
    _FakeExtensionService.calls = []
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    router_module.service = _FakeExtensionService()
    app.dependency_overrides[get_current_user] = lambda: _user()
    yield TestClient(app)
    router_module.service = original_service
    app.dependency_overrides.clear()


def test_get_extensions_lista_solicitacoes_visiveis(client: TestClient) -> None:
    response = client.get("/api/v1/extensions")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "ext1"
    assert body[0]["aluno_nome"] == "Aluno SAGA"
    assert _FakeExtensionService.calls[0][0] == "list"


def test_get_pending_extensions_coordenacao(client: TestClient) -> None:
    response = client.get("/api/v1/extensions/pending")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "ext1"
    assert _FakeExtensionService.calls[0][0] == "pending"


def test_get_pending_extensions_bloqueia_aluno(client: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _user("aluno")

    response = client.get("/api/v1/extensions/pending")

    assert response.status_code == 403


def test_post_extensions_aluno_cria_solicitacao(client: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _user("aluno")

    response = client.post(
        "/api/v1/extensions",
        json={
            "tipo": "prazo_defesa",
            "nova_data": "2028-07-01",
            "motivo": "Ajuste de cronograma",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == "ext2"
    assert _FakeExtensionService.calls[0][0] == "create"


def test_post_extensions_orientador_cria_para_orientando(client: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _user("orientador")

    response = client.post(
        "/api/v1/extensions",
        json={
            "tipo": "prazo_defesa",
            "student_id": "student1",
            "nova_data": "2028-07-01",
            "motivo": "Ajuste de cronograma",
        },
    )

    assert response.status_code == 201
    sent_body = _FakeExtensionService.calls[0][1][0]
    assert sent_body.student_id == "student1"


def test_post_extensions_bloqueia_coordenacao(client: TestClient) -> None:
    response = client.post(
        "/api/v1/extensions",
        json={
            "tipo": "prazo_defesa",
            "nova_data": "2028-07-01",
            "motivo": "Ajuste de cronograma",
        },
    )

    assert response.status_code == 403
