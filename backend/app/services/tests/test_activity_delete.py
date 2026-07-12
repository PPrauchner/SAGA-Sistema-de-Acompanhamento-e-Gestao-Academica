"""
Testes da exclusão de atividade creditável (issue #305) — hard delete em
rascunho/enviado/rejeitado, bloqueio de atividade lastreada em produção e a
regra de que só a coordenação exclui atividade rejeitada.

A exclusão de atividade `aprovado` (issue #306, com reversão de créditos e
re-execução do motor) tem cobertura própria em test_activity_delete_aprovado.py.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.activity import ActivityStatus
from backend.app.services import activity_service as svc


def _aluno() -> CurrentUser:
    return CurrentUser(uid="uid-aluno", role="aluno", programa_id="prog_default", email="a@x.com")


def _coord() -> CurrentUser:
    return CurrentUser(uid="uid-coord", role="coordenacao", programa_id="prog_default", email="c@x.com")


def _activity(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "act1",
        "student_id": "s1",
        "tipo_id": "t1",
        "status": ActivityStatus.rascunho,
        "producao_id": None,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("activity_status", [ActivityStatus.rascunho, ActivityStatus.enviado])
async def test_aluno_exclui_propria_atividade_rascunho_ou_enviado(
    monkeypatch: pytest.MonkeyPatch, activity_status: ActivityStatus
) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity(status=activity_status)
    monkeypatch.setattr(svc, "_repo", fake_repo)

    await svc.delete_activity("act1", _aluno())

    fake_repo.delete_by_id.assert_awaited_once_with("act1")


async def test_aluno_nao_exclui_atividade_rejeitada(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity(status=ActivityStatus.rejeitado)
    monkeypatch.setattr(svc, "_repo", fake_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.delete_activity("act1", _aluno())

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    fake_repo.delete_by_id.assert_not_called()


async def test_coordenacao_exclui_atividade_rejeitada(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity(status=ActivityStatus.rejeitado)
    monkeypatch.setattr(svc, "_repo", fake_repo)

    await svc.delete_activity("act1", _coord())

    fake_repo.delete_by_id.assert_awaited_once_with("act1")


async def test_bloqueia_exclusao_de_atividade_lastreada_em_producao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity(
        status=ActivityStatus.enviado, producao_id="prod1"
    )
    monkeypatch.setattr(svc, "_repo", fake_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.delete_activity("act1", _coord())

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    fake_repo.delete_by_id.assert_not_called()


async def test_aluno_nao_exclui_atividade_aprovada(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity(status=ActivityStatus.aprovado)
    monkeypatch.setattr(svc, "_repo", fake_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.delete_activity("act1", _aluno())

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    fake_repo.delete_by_id.assert_not_called()


async def test_excluir_atividade_inexistente_404(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = None
    monkeypatch.setattr(svc, "_repo", fake_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.delete_activity("nope", _coord())

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    fake_repo.delete_by_id.assert_not_called()
