"""
Testes do aspecto A01 — @requires_role (autorização por papel).

Cobre os cenários: papel autorizado, papel incorreto (403), usuário ausente
(401), aspecto desativado por flag e preservação da assinatura para o FastAPI.
"""

from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException

from backend.app.aspects import aspect_config
from backend.app.aspects.authorization import requires_role
from backend.app.core.auth import CurrentUser


def _fake_user(role: str) -> CurrentUser:
    return CurrentUser(uid="u1", role=role, programa_id="prog_default", email="a@b.com")


@requires_role("coordenacao")
async def _endpoint_coord(user: CurrentUser) -> str:
    return f"ok:{user.role}"


@requires_role("aluno", "orientador", "coordenacao")
async def _endpoint_todos(user: CurrentUser) -> str:
    return "ok"


@requires_role("adm")
async def _endpoint_adm(user: CurrentUser) -> str:
    return f"ok:{user.role}"


async def test_papel_autorizado_executa() -> None:
    assert await _endpoint_coord(user=_fake_user("coordenacao")) == "ok:coordenacao"


async def test_papel_incorreto_403() -> None:
    with pytest.raises(HTTPException) as exc:
        await _endpoint_coord(user=_fake_user("aluno"))
    assert exc.value.status_code == 403


async def test_usuario_ausente_401() -> None:
    with pytest.raises(HTTPException) as exc:
        await _endpoint_coord()
    assert exc.value.status_code == 401


async def test_qualquer_papel_aceito_quando_listado() -> None:
    assert await _endpoint_todos(user=_fake_user("aluno")) == "ok"


async def test_adm_autorizado() -> None:
    assert await _endpoint_adm(user=_fake_user("adm")) == "ok:adm"


async def test_coordenacao_nao_acessa_endpoint_adm() -> None:
    with pytest.raises(HTTPException) as exc:
        await _endpoint_adm(user=_fake_user("coordenacao"))
    assert exc.value.status_code == 403


async def test_flag_desativada_passa_direto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aspect_config, "AUTHORIZATION_ENABLED", False)
    # Papel que normalmente seria rejeitado passa quando o aspecto está desligado.
    assert await _endpoint_coord(user=_fake_user("aluno")) == "ok:aluno"


def test_assinatura_preservada_para_fastapi() -> None:
    # functools.wraps + __wrapped__ deve manter o parâmetro 'user' visível,
    # para que o FastAPI consiga resolver e injetar a dependência.
    params = inspect.signature(_endpoint_coord).parameters
    assert "user" in params
