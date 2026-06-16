"""
Testes dos endpoints do auth router.

Usa FastAPI TestClient com app.dependency_overrides[get_current_user] para
injetar um CurrentUser fake e monkeypatch do AuthService para isolar a camada
de rota da lógica de negócio e do Firebase. Cobre autorização por papel
(@requires_role), endpoint público e validação de corpo.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app
from backend.app.models.user import (
    FirstAccessResponse,
    InviteResponse,
    UserResponse,
)


class _FakeAuthService:
    """AuthService fake: registra as chamadas e devolve respostas canônicas."""

    chamadas: list[tuple[str, tuple[Any, ...]]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def create_invite(self, data: Any, current_user: CurrentUser) -> InviteResponse:
        _FakeAuthService.chamadas.append(("create_invite", (data, current_user)))
        return InviteResponse(
            message=f"Convite enviado para {data.email}",
            token="tok-fake",
            expira_em="2026-01-01T00:00:00+00:00",
        )

    async def activate_first_access(self, token: str, senha: str) -> FirstAccessResponse:
        _FakeAuthService.chamadas.append(("activate_first_access", (token, senha)))
        return FirstAccessResponse(
            message="Conta ativada com sucesso",
            uid="uid-fake",
            role="aluno",
            email="aluno@x.com",
        )

    async def get_me(self, current_user: CurrentUser) -> UserResponse:
        _FakeAuthService.chamadas.append(("get_me", (current_user,)))
        return UserResponse(
            uid=current_user.uid,
            email="aluno@x.com",
            nome="Aluno X",
            role=current_user.role,
            programa_id=current_user.programa_id,
            ativo=True,
        )


def _override_user(role: str) -> None:
    """Injeta um CurrentUser fake com o papel informado na dependência de auth."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="u1", role=role, programa_id="prog_default", email="u@x.com"
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("backend.app.api.v1.auth.AuthService", _FakeAuthService)
    # Desliga o aspecto A02 (@audit_operation) para isolar a rota do Firestore;
    # a auditoria em si é coberta pelos testes do próprio aspecto.
    monkeypatch.setattr("backend.app.aspects.aspect_config.AUDIT_ENABLED", False)
    _FakeAuthService.chamadas = []
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_invite_coordenacao_201(client: TestClient) -> None:
    _override_user("coordenacao")

    resp = client.post(
        "/api/v1/auth/invite",
        json={"email": "aluno@x.com", "role": "aluno", "nome": "Aluno X"},
    )

    assert resp.status_code == 201
    assert resp.json()["token"] == "tok-fake"
    assert _FakeAuthService.chamadas[0][0] == "create_invite"


def test_invite_papel_insuficiente_403(client: TestClient) -> None:
    _override_user("aluno")

    resp = client.post(
        "/api/v1/auth/invite",
        json={"email": "aluno@x.com", "role": "aluno", "nome": "Aluno X"},
    )

    assert resp.status_code == 403
    assert _FakeAuthService.chamadas == []


def test_first_access_publico_200(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/first-access",
        json={"token": "tok-abc", "senha": "Senha123"},
    )

    assert resp.status_code == 200
    assert resp.json()["uid"] == "uid-fake"
    assert _FakeAuthService.chamadas[0] == ("activate_first_access", ("tok-abc", "Senha123"))


def test_first_access_senha_invalida_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/first-access",
        json={"token": "tok-abc", "senha": "fraca"},
    )

    assert resp.status_code == 422
    assert _FakeAuthService.chamadas == []


def test_me_autenticado_200(client: TestClient) -> None:
    _override_user("aluno")

    resp = client.get("/api/v1/auth/me")

    assert resp.status_code == 200
    body = resp.json()
    assert body["uid"] == "u1"
    assert body["role"] == "aluno"
    assert _FakeAuthService.chamadas[0][0] == "get_me"
