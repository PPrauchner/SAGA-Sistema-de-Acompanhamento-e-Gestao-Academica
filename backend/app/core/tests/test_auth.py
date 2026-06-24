"""
Testes da dependência get_current_user — extração de identidade do JWT.

Cobre a exceção do papel `adm` (superusuário global, ADR-0001) à exigência de
'programa_id': adm autentica com programa_id nulo, enquanto os demais papéis sem
programa_id (conta não ativada) e tokens sem 'role' continuam recebendo 403.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.core import auth as auth_module
from backend.app.core.auth import get_current_user


async def test_adm_autentica_com_programa_id_nulo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_module.firebase_auth,
        "verify_id_token",
        lambda _token: {"uid": "adm1", "role": "adm", "email": "adm@saga.local"},
    )
    user = await get_current_user(authorization="Bearer faketoken")
    assert user.role == "adm"
    assert user.programa_id is None


async def test_papel_comum_sem_programa_id_403(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_module.firebase_auth,
        "verify_id_token",
        lambda _token: {"uid": "u1", "role": "aluno"},
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(authorization="Bearer faketoken")
    assert exc.value.status_code == 403


async def test_token_sem_role_403(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_module.firebase_auth,
        "verify_id_token",
        lambda _token: {"uid": "u1", "programa_id": "prog_default"},
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(authorization="Bearer faketoken")
    assert exc.value.status_code == 403
