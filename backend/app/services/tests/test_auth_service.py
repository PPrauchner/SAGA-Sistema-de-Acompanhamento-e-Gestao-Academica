"""
Testes do AuthService (convite, primeiro acesso e perfil).

Usa repositórios fake em memória e um cliente de auth fake — nenhum acesso
real ao Firebase. Cobre os cenários de sucesso e os erros 409/400/404.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from firebase_admin import auth as firebase_auth

from backend.app.core.auth import CurrentUser
from backend.app.models.user import InviteRequest
from backend.app.services.auth_service import AuthService


class _FakeRepo:
    """Repositório em memória com a mesma interface assíncrona do FirebaseRepository."""

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
    """Cliente Firebase Auth fake: get_user_by_email/create_user/set_custom_user_claims."""

    def __init__(self, emails_existentes: tuple[str, ...] = ()) -> None:
        self.existentes = set(emails_existentes)
        self.criados: dict[str, dict[str, Any]] = {}
        self.claims: dict[str, dict[str, Any]] = {}
        self._contador = 0

    def get_user_by_email(self, email: str) -> SimpleNamespace:
        if email in self.existentes:
            return SimpleNamespace(uid="existente")
        raise firebase_auth.UserNotFoundError("usuário não encontrado")

    def create_user(self, email: str, password: str) -> SimpleNamespace:
        self._contador += 1
        uid = f"uid{self._contador}"
        self.criados[uid] = {"email": email, "password": password}
        return SimpleNamespace(uid=uid)

    def set_custom_user_claims(self, uid: str, claims: dict[str, Any]) -> None:
        self.claims[uid] = claims


def _coordenacao() -> CurrentUser:
    return CurrentUser(uid="coord1", role="coordenacao", programa_id="prog_default", email="c@x.com")


def _service(auth: _FakeAuth) -> tuple[AuthService, _FakeRepo, _FakeRepo]:
    invites, users = _FakeRepo(), _FakeRepo()
    return AuthService(invite_repo=invites, user_repo=users, auth_client=auth), invites, users


async def test_create_invite_persiste_convite() -> None:
    auth = _FakeAuth()
    service, invites, _ = _service(auth)

    resp = await service.create_invite(
        InviteRequest(email="aluno@x.com", role="aluno", nome="Aluno X"), _coordenacao()
    )

    assert resp.token in invites.store
    salvo = invites.store[resp.token]
    assert salvo["usado"] is False
    assert salvo["criado_por"] == "coord1"
    assert salvo["programa_id"] == "prog_default"
    assert resp.message == "Convite enviado para aluno@x.com"


async def test_create_invite_email_existente_409() -> None:
    auth = _FakeAuth(emails_existentes=("aluno@x.com",))
    service, _, _ = _service(auth)

    with pytest.raises(HTTPException) as exc:
        await service.create_invite(
            InviteRequest(email="aluno@x.com", role="aluno", nome="Aluno X"), _coordenacao()
        )
    assert exc.value.status_code == 409


async def test_first_access_ativa_conta() -> None:
    auth = _FakeAuth()
    service, invites, users = _service(auth)
    token = "tok-abc"
    invites.store[token] = {
        "email": "aluno@x.com",
        "role": "aluno",
        "nome": "Aluno X",
        "programa_id": "prog_default",
        "usado": False,
        "expira_em": datetime.now(timezone.utc) + timedelta(hours=10),
    }

    resp = await service.activate_first_access(token, "Senha123")

    assert resp.uid in users.store
    assert resp.role == "aluno"
    assert auth.claims[resp.uid] == {"role": "aluno", "programa_id": "prog_default"}
    assert auth.criados[resp.uid]["password"] == "Senha123"
    assert invites.store[token]["usado"] is True
    assert users.store[resp.uid]["primeiro_acesso_completo"] is True


async def test_first_access_token_inexistente_400() -> None:
    service, _, _ = _service(_FakeAuth())
    with pytest.raises(HTTPException) as exc:
        await service.activate_first_access("nao-existe", "Senha123")
    assert exc.value.status_code == 400


async def test_first_access_token_usado_400() -> None:
    service, invites, _ = _service(_FakeAuth())
    invites.store["t"] = {
        "email": "a@x.com", "role": "aluno", "nome": "A", "programa_id": "p",
        "usado": True, "expira_em": datetime.now(timezone.utc) + timedelta(hours=10),
    }
    with pytest.raises(HTTPException) as exc:
        await service.activate_first_access("t", "Senha123")
    assert exc.value.status_code == 400


async def test_first_access_token_expirado_400() -> None:
    service, invites, _ = _service(_FakeAuth())
    invites.store["t"] = {
        "email": "a@x.com", "role": "aluno", "nome": "A", "programa_id": "p",
        "usado": False, "expira_em": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    with pytest.raises(HTTPException) as exc:
        await service.activate_first_access("t", "Senha123")
    assert exc.value.status_code == 400


async def test_get_me_retorna_perfil() -> None:
    service, _, users = _service(_FakeAuth())
    users.store["u1"] = {
        "uid": "u1", "email": "a@x.com", "nome": "A", "role": "aluno",
        "programa_id": "p", "ativo": True,
    }
    user = CurrentUser(uid="u1", role="aluno", programa_id="p", email="a@x.com")

    resp = await service.get_me(user)
    assert resp.uid == "u1"
    assert resp.role == "aluno"
    assert resp.student_id is None


async def test_get_me_perfil_inexistente_404() -> None:
    service, _, _ = _service(_FakeAuth())
    user = CurrentUser(uid="u1", role="aluno", programa_id="p", email="a@x.com")
    with pytest.raises(HTTPException) as exc:
        await service.get_me(user)
    assert exc.value.status_code == 404
