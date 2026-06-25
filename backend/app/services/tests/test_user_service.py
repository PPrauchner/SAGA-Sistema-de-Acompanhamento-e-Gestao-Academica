"""
Testes do UserService (criação de coordenadores).

Cobre: 201 para adm, 403 via requires_role para coordenacao, 409 e-mail duplicado.
Sem acesso real ao Firebase — repositórios e auth_client são fakes em memória.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from firebase_admin import auth as firebase_auth

from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser
from backend.app.models.user import CreateCoordinatorRequest
from backend.app.services.user_service import UserService


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeRepo:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, Any]] = {}

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        value = self.store.get(doc_id)
        return dict(value) if value is not None else None

    async def set(self, doc_id: str, data: dict[str, Any]) -> None:
        self.store[doc_id] = dict(data)

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        self.store.setdefault(doc_id, {}).update(data)


class _FakeAuth:
    def __init__(self, emails_existentes: tuple[str, ...] = ()) -> None:
        self.existentes = set(emails_existentes)
        self.criados: dict[str, dict[str, Any]] = {}
        self.claims: dict[str, dict[str, Any]] = {}
        self._contador = 0

    def get_user_by_email(self, email: str) -> SimpleNamespace:
        if email in self.existentes:
            return SimpleNamespace(uid="existente")
        raise firebase_auth.UserNotFoundError("não encontrado")

    def create_user(self, email: str, password: str) -> SimpleNamespace:
        self._contador += 1
        uid = f"uid{self._contador}"
        self.criados[uid] = {"email": email, "password": password}
        return SimpleNamespace(uid=uid)

    def set_custom_user_claims(self, uid: str, claims: dict[str, Any]) -> None:
        self.claims[uid] = claims


def _service(auth: _FakeAuth | None = None) -> tuple[UserService, _FakeRepo]:
    users = _FakeRepo()
    return UserService(user_repo=users, auth_client=auth or _FakeAuth()), users


def _req(**kwargs: Any) -> CreateCoordinatorRequest:
    defaults = {
        "email": "coord@univ.br",
        "nome": "Nova Coordenação",
        "senha": "Senha123",
        "programa_id": "prog_default",
    }
    defaults.update(kwargs)
    return CreateCoordinatorRequest(**defaults)


# ---------------------------------------------------------------------------
# Testes do UserService
# ---------------------------------------------------------------------------

async def test_create_coordinator_persiste_usuario() -> None:
    auth = _FakeAuth()
    service, users = _service(auth)

    resp = await service.create_coordinator(_req())

    assert resp.uid in users.store
    doc = users.store[resp.uid]
    assert doc["role"] == "coordenacao"
    assert doc["programa_id"] == "prog_default"
    assert doc["ativo"] is True
    assert doc["primeiro_acesso_completo"] is True
    assert auth.claims[resp.uid] == {"role": "coordenacao", "programa_id": "prog_default"}


async def test_create_coordinator_email_existente_409() -> None:
    service, _ = _service(_FakeAuth(emails_existentes=("coord@univ.br",)))

    with pytest.raises(HTTPException) as exc:
        await service.create_coordinator(_req())
    assert exc.value.status_code == 409


async def test_create_coordinator_retorna_response_correto() -> None:
    service, _ = _service()

    resp = await service.create_coordinator(_req(email="novo@univ.br"))

    assert resp.email == "novo@univ.br"
    assert "novo@univ.br" in resp.message


# ---------------------------------------------------------------------------
# Teste de autorização via requires_role (US-PA05)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coordenacao_criar_coordenador_403() -> None:
    """Coordenador tentando criar coordenador deve receber 403 (US-PA05)."""
    user_coord = CurrentUser(
        uid="coord-1", role="coordenacao", programa_id="prog_default", email="c@x.com"
    )

    with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
        @requires_role("adm")
        async def handler(current_user: CurrentUser) -> str:
            return "ok"

        with pytest.raises(HTTPException) as exc:
            await handler(current_user=user_coord)
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_adm_criar_coordenador_permitido() -> None:
    """Adm pode chamar o endpoint de criação de coordenador."""
    user_adm = CurrentUser(uid="adm-1", role="adm", programa_id=None, email="adm@x.com")

    with patch("backend.app.aspects.aspect_config.AUTHORIZATION_ENABLED", True):
        @requires_role("adm")
        async def handler(current_user: CurrentUser) -> str:
            return "ok"

        result = await handler(current_user=user_adm)
        assert result == "ok"
