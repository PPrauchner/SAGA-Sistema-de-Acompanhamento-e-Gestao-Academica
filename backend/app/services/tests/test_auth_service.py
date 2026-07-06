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
from backend.app.core.config import settings
from backend.app.core.email import EmailError
from backend.app.models.user import InviteRequest, NotificationPreferences
from backend.app.services.auth_service import AuthService


class _FakeEmail:
    """EmailSender fake: registra os envios ou simula falha de envio."""

    def __init__(self, falha: bool = False) -> None:
        self.falha = falha
        self.enviados: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, html_body: str) -> None:
        if self.falha:
            raise EmailError("falha simulada")
        self.enviados.append((to, subject, html_body))


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

    async def query(
        self,
        filters: list[tuple] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        subcollection_path: str | None = None
    ) -> list[dict[str, Any]]:
        results = []
        for doc_id, doc in self.store.items():
            match = True
            if filters:
                for field, op, value in filters:
                    if op == "==" and doc.get(field) != value:
                        match = False
                        break
            if match:
                data = dict(doc)
                data["id"] = doc_id
                results.append(data)
        return results


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

    def verify_id_token(self, id_token: str) -> dict[str, Any]:
        if id_token == "invalid_token":
            raise ValueError("Token inválido")
        if id_token == "no_email_token":
            return {"uid": "uid_google", "firebase": {"sign_in_provider": "google.com"}}
        if id_token == "unverified_email_token":
            return {"uid": "uid_google", "email": "a@x.com", "email_verified": False, "firebase": {"sign_in_provider": "google.com"}}
        if id_token == "wrong_provider_token":
            return {"uid": "uid_google", "email": "a@x.com", "email_verified": True, "firebase": {"sign_in_provider": "password"}}
        return {"uid": "uid_google", "email": id_token, "email_verified": True, "firebase": {"sign_in_provider": "google.com"}}


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


async def test_create_invite_envia_email() -> None:
    invites, users = _FakeRepo(), _FakeRepo()
    email = _FakeEmail()
    service = AuthService(
        invite_repo=invites, user_repo=users, auth_client=_FakeAuth(), email_sender=email
    )

    resp = await service.create_invite(
        InviteRequest(email="aluno@x.com", role="aluno", nome="Aluno X"), _coordenacao()
    )

    assert len(email.enviados) == 1
    destinatario, _assunto, corpo = email.enviados[0]
    assert destinatario == "aluno@x.com"
    # O corpo carrega o código (token) e o link de primeiro acesso.
    assert resp.token in corpo
    assert "/first-access" in corpo


async def test_create_invite_token_oculto_quando_nao_exposto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "expose_invite_token", False)
    invites, users = _FakeRepo(), _FakeRepo()
    email = _FakeEmail()
    service = AuthService(
        invite_repo=invites, user_repo=users, auth_client=_FakeAuth(), email_sender=email
    )

    resp = await service.create_invite(
        InviteRequest(email="aluno@x.com", role="aluno", nome="Aluno X"), _coordenacao()
    )

    # Token sai só por e-mail; a resposta não o expõe, mas o convite foi persistido.
    assert resp.token is None
    assert len(invites.store) == 1
    assert email.enviados[0][0] == "aluno@x.com"


async def test_create_invite_falha_email_nao_derruba_convite() -> None:
    invites, users = _FakeRepo(), _FakeRepo()
    service = AuthService(
        invite_repo=invites,
        user_repo=users,
        auth_client=_FakeAuth(),
        email_sender=_FakeEmail(falha=True),
    )

    resp = await service.create_invite(
        InviteRequest(email="aluno@x.com", role="aluno", nome="Aluno X"), _coordenacao()
    )

    # Falha de envio é tratada: o convite persiste e o token segue como fallback.
    assert resp.token in invites.store
    assert invites.store[resp.token]["usado"] is False


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
    assert users.store[resp.uid]["notification_preferences"] == NotificationPreferences().model_dump()


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
    assert resp.notification_preferences == NotificationPreferences()


async def test_get_me_perfil_inexistente_404() -> None:
    service, _, _ = _service(_FakeAuth())
    user = CurrentUser(uid="u1", role="aluno", programa_id="p", email="a@x.com")
    with pytest.raises(HTTPException) as exc:
        await service.get_me(user)
    assert exc.value.status_code == 404


async def test_activate_google_first_access_success() -> None:
    auth = _FakeAuth()
    service, invites, users = _service(auth)
    token = "tok-google"
    invites.store[token] = {
        "email": "a@x.com",
        "role": "aluno",
        "nome": "Aluno X",
        "programa_id": "prog_default",
        "usado": False,
        "expira_em": datetime.now(timezone.utc) + timedelta(hours=10),
    }

    # Passa "a@x.com" como id_token pois o _FakeAuth.verify_id_token mapeia id_token para o email
    resp = await service.activate_google_first_access("a@x.com")

    assert resp.uid == "uid_google"
    assert resp.role == "aluno"
    assert auth.claims[resp.uid] == {"role": "aluno", "programa_id": "prog_default"}
    assert invites.store[token]["usado"] is True
    assert users.store[resp.uid]["primeiro_acesso_completo"] is True
    assert users.store[resp.uid]["email"] == "a@x.com"


async def test_activate_google_first_access_invalid_token_401() -> None:
    service, _, _ = _service(_FakeAuth())
    with pytest.raises(HTTPException) as exc:
        await service.activate_google_first_access("invalid_token")
    assert exc.value.status_code == 401


async def test_activate_google_first_access_no_email_400() -> None:
    service, _, _ = _service(_FakeAuth())
    with pytest.raises(HTTPException) as exc:
        await service.activate_google_first_access("no_email_token")
    assert exc.value.status_code == 400


async def test_activate_google_first_access_no_invite_403() -> None:
    service, _, _ = _service(_FakeAuth())
    # Não há convite no _FakeRepo
    with pytest.raises(HTTPException) as exc:
        await service.activate_google_first_access("nobody@x.com")
    assert exc.value.status_code == 403


async def test_activate_google_first_access_expired_invite_403() -> None:
    service, invites, _ = _service(_FakeAuth())
    invites.store["tok"] = {
        "email": "a@x.com",
        "role": "aluno",
        "nome": "Aluno X",
        "programa_id": "prog_default",
        "usado": False,
        "expira_em": datetime.now(timezone.utc) - timedelta(hours=10),
    }
    with pytest.raises(HTTPException) as exc:
        await service.activate_google_first_access("a@x.com")
    assert exc.value.status_code == 403


async def test_activate_google_first_access_unverified_email_403() -> None:
    service, _, _ = _service(_FakeAuth())
    with pytest.raises(HTTPException) as exc:
        await service.activate_google_first_access("unverified_email_token")
    assert exc.value.status_code == 403
    assert "não verificado" in exc.value.detail


async def test_activate_google_first_access_wrong_provider_403() -> None:
    service, _, _ = _service(_FakeAuth())
    with pytest.raises(HTTPException) as exc:
        await service.activate_google_first_access("wrong_provider_token")
    assert exc.value.status_code == 403
    assert "via Google" in exc.value.detail
