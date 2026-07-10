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
from firebase_admin import firestore
from pydantic import ValidationError

from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser
from backend.app.models.user import (
    CreateCoordinatorRequest,
    NotificationPreferences,
    ProfileUpdateRequest,
)
from backend.app.services.user_service import UserService


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeRepo:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, Any]] = {}

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        value = self.store.get(doc_id)
        if value is None:
            return None
        doc = dict(value)
        doc["id"] = doc_id
        return doc

    async def set(self, doc_id: str, data: dict[str, Any]) -> None:
        self.store[doc_id] = dict(data)

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        target = self.store.setdefault(doc_id, {})
        for key, value in data.items():
            if value is firestore.DELETE_FIELD:
                target.pop(key, None)
            else:
                target[key] = value

    async def query(
        self,
        filters: list[tuple] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        subcollection_path: str | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for doc_id, value in self.store.items():
            if all(value.get(field) == val for field, op, val in (filters or [])):
                item = dict(value)
                item["id"] = doc_id
                results.append(item)
        return results[:limit] if limit else results


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
    service, users, _ = _service_with_advisors(auth)
    return service, users


def _service_with_advisors(
    auth: _FakeAuth | None = None,
) -> tuple[UserService, _FakeRepo, _FakeRepo]:
    """UserService com repositórios fakes, incluindo o de advisors (issue #309)."""
    users = _FakeRepo()
    advisors = _FakeRepo()
    service = UserService(
        user_repo=users,
        auth_client=auth or _FakeAuth(),
        advisor_repo=advisors,
    )
    return service, users, advisors


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
    assert doc["notification_preferences"] == NotificationPreferences().model_dump()
    assert doc["primeiro_acesso_completo"] is True
    assert auth.claims[resp.uid] == {"role": "coordenacao", "programa_id": "prog_default"}


async def test_create_coordinator_provisiona_advisor() -> None:
    """Issue #309/M5: o advisor do coordenador nasce na atribuição do papel,
    não como side-effect de GET /advisors."""
    service, _, advisors = _service_with_advisors()

    resp = await service.create_coordinator(_req())

    advisor = advisors.store[resp.uid]
    assert advisor["uid"] == resp.uid
    assert advisor["programa_id"] == "prog_default"
    assert advisor["limite_orientandos"] == 5


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


# ---------------------------------------------------------------------------
# Testes do update_profile (#195)
# ---------------------------------------------------------------------------

def _profile_service() -> tuple[UserService, _FakeRepo, _FakeRepo]:
    users = _FakeRepo()
    advisors = _FakeRepo()
    service = UserService(user_repo=users, auth_client=_FakeAuth(), advisor_repo=advisors)
    return service, users, advisors


def _user(uid: str, role: str, **extra: Any) -> CurrentUser:
    return CurrentUser(uid=uid, role=role, programa_id="prog_default", email=f"{uid}@x.com")


async def test_update_profile_atualiza_nome_aluno() -> None:
    service, users, _ = _profile_service()
    users.store["a1"] = {"uid": "a1", "nome": "Antigo", "role": "aluno"}

    resp = await service.update_profile(ProfileUpdateRequest(nome="Novo"), _user("a1", "aluno"))

    assert resp.nome == "Novo"
    assert resp.departamento is None
    assert users.store["a1"]["nome"] == "Novo"
    assert "atualizado_em" in users.store["a1"]


async def test_update_profile_atualiza_nome_coordenacao() -> None:
    service, users, _ = _profile_service()
    users.store["c1"] = {"uid": "c1", "nome": "Antigo", "role": "coordenacao"}

    resp = await service.update_profile(ProfileUpdateRequest(nome="Coord"), _user("c1", "coordenacao"))

    assert users.store["c1"]["nome"] == "Coord"
    assert resp.departamento is None


async def test_update_profile_orientador_departamento_por_advisor_id() -> None:
    service, users, advisors = _profile_service()
    users.store["o1"] = {"uid": "o1", "nome": "Orient", "role": "orientador", "advisor_id": "adv1"}
    advisors.store["adv1"] = {"uid": "o1", "nome": "Orient", "departamento": "Antigo"}

    resp = await service.update_profile(
        ProfileUpdateRequest(nome="Orient", departamento="Computação"), _user("o1", "orientador")
    )

    assert resp.departamento == "Computação"
    assert advisors.store["adv1"]["departamento"] == "Computação"


async def test_update_profile_orientador_departamento_por_query_uid() -> None:
    service, users, advisors = _profile_service()
    users.store["o2"] = {"uid": "o2", "nome": "Orient", "role": "orientador"}
    advisors.store["advX"] = {"uid": "o2", "departamento": "Antigo"}

    resp = await service.update_profile(
        ProfileUpdateRequest(nome="Orient", departamento="Física"), _user("o2", "orientador")
    )

    assert resp.departamento == "Física"
    assert advisors.store["advX"]["departamento"] == "Física"


async def test_update_profile_departamento_nao_orientador_422() -> None:
    service, users, _ = _profile_service()
    users.store["a1"] = {"uid": "a1", "nome": "Aluno", "role": "aluno"}

    with pytest.raises(HTTPException) as exc:
        await service.update_profile(
            ProfileUpdateRequest(nome="Aluno", departamento="Computação"), _user("a1", "aluno")
        )
    assert exc.value.status_code == 422


async def test_update_profile_remove_telefone() -> None:
    service, users, _ = _profile_service()
    users.store["a1"] = {"uid": "a1", "nome": "Antigo", "role": "aluno", "telefone": "55999"}

    await service.update_profile(ProfileUpdateRequest(nome="Novo"), _user("a1", "aluno"))

    assert "telefone" not in users.store["a1"]


async def test_update_profile_salva_preferencias_notificacao() -> None:
    service, users, _ = _profile_service()
    users.store["a1"] = {"uid": "a1", "nome": "Aluno", "role": "aluno"}
    preferences = NotificationPreferences(work_plan=False, transfers=False)

    resp = await service.update_profile(
        ProfileUpdateRequest(notification_preferences=preferences),
        _user("a1", "aluno"),
    )

    assert resp.nome == "Aluno"
    assert resp.notification_preferences.work_plan is False
    assert resp.notification_preferences.transfers is False
    assert users.store["a1"]["notification_preferences"] == preferences.model_dump()


async def test_update_profile_usuario_legado_recebe_preferencias_default() -> None:
    service, users, _ = _profile_service()
    users.store["a1"] = {"uid": "a1", "nome": "Aluno", "role": "aluno"}

    resp = await service.update_profile(ProfileUpdateRequest(nome="Aluno Novo"), _user("a1", "aluno"))

    assert resp.notification_preferences == NotificationPreferences()


async def test_update_profile_perfil_inexistente_404() -> None:
    service, _, _ = _profile_service()

    with pytest.raises(HTTPException) as exc:
        await service.update_profile(ProfileUpdateRequest(nome="X"), _user("ghost", "aluno"))
    assert exc.value.status_code == 404


async def test_update_profile_orientador_sem_advisor_404() -> None:
    service, users, _ = _profile_service()
    users.store["o3"] = {"uid": "o3", "nome": "Orient", "role": "orientador"}

    with pytest.raises(HTTPException) as exc:
        await service.update_profile(
            ProfileUpdateRequest(nome="Orient", departamento="Química"), _user("o3", "orientador")
        )
    assert exc.value.status_code == 404


@pytest.mark.parametrize("campo", ["email", "programa_id", "matricula"])
def test_profile_update_rejeita_campo_nao_editavel(campo: str) -> None:
    """Campo não editável no corpo é rejeitado por extra='forbid' (422 na API)."""
    with pytest.raises(ValidationError):
        ProfileUpdateRequest(nome="Novo", **{campo: "x"})
