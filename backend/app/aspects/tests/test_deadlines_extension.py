"""
Testes do Before advice do A04 no join point de prorrogação (#240).

Cobre os três cenários da spec 08: dentro do prazo e sob o limite (segue),
`max_prorrogacoes` atingido (bloqueio 409) e prazo final expirado além da
janela de 30 dias (bloqueio 422).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.aspects import aspect_config
from backend.app.aspects import deadline_validation as deadline_module
from backend.app.aspects.deadline_validation import check_deadlines
from backend.app.core.auth import CurrentUser
from backend.app.models.extension import ExtensionCreateRequest


class _FakeExtensionRepository:
    def __init__(self, approved: int) -> None:
        self._approved = approved

    async def count_approved_for_student(self, student_id: str) -> int:
        return self._approved


class _FakeExtensionService:
    def __init__(self, student: dict[str, Any], approved: int) -> None:
        self._student = student
        self._repo = _FakeExtensionRepository(approved)

    async def _resolve_target_student(
        self, student_id: str | None, user: CurrentUser
    ) -> dict[str, Any]:
        return self._student


def _patch_program(monkeypatch: pytest.MonkeyPatch, max_prorrogacoes: int) -> None:
    class _FakeProgramRepository:
        async def get_config(self, programa_id: str) -> dict[str, Any]:
            return {"max_prorrogacoes": max_prorrogacoes}

    monkeypatch.setattr(deadline_module, "ProgramRepository", _FakeProgramRepository)


def _user() -> CurrentUser:
    return CurrentUser(uid="uid-aluno", role="aluno", programa_id="prog", email="a@saga.test")


def _body() -> ExtensionCreateRequest:
    return ExtensionCreateRequest(
        tipo="prazo_defesa",
        nova_data=date(2030, 1, 1),
        motivo="Ajuste no cronograma da defesa",
        plano_atualizado="http://plano.test/doc.pdf",
    )


def _student(prazo_final: datetime | None) -> dict[str, Any]:
    return {"id": "student1", "programa_id": "prog", "prazo_final": prazo_final}


@check_deadlines
async def _create_extension(
    body: ExtensionCreateRequest,
    user: CurrentUser,
    service: _FakeExtensionService,
) -> dict[str, str]:
    return {"id": "ext_new"}


async def test_dentro_do_prazo_e_sob_limite_cria(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_program(monkeypatch, max_prorrogacoes=1)
    service = _FakeExtensionService(_student(datetime.now(timezone.utc)), approved=0)

    result = await _create_extension(body=_body(), user=_user(), service=service)

    assert result == {"id": "ext_new"}


async def test_max_prorrogacoes_atingido_bloqueia(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_program(monkeypatch, max_prorrogacoes=1)
    service = _FakeExtensionService(_student(datetime.now(timezone.utc)), approved=1)

    with pytest.raises(HTTPException) as exc:
        await _create_extension(body=_body(), user=_user(), service=service)

    assert exc.value.status_code == 409


async def test_prazo_expirado_alem_da_janela_bloqueia(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_program(monkeypatch, max_prorrogacoes=1)
    prazo_expirado = datetime.now(timezone.utc) - timedelta(days=40)
    service = _FakeExtensionService(_student(prazo_expirado), approved=0)

    with pytest.raises(HTTPException) as exc:
        await _create_extension(body=_body(), user=_user(), service=service)

    assert exc.value.status_code == 422


async def test_flag_desativada_nao_bloqueia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aspect_config, "DEADLINE_VALIDATION_ENABLED", False)
    _patch_program(monkeypatch, max_prorrogacoes=1)
    service = _FakeExtensionService(_student(datetime.now(timezone.utc)), approved=5)

    result = await _create_extension(body=_body(), user=_user(), service=service)

    assert result == {"id": "ext_new"}
