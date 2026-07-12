"""
Testes da exclusão de atividade creditável aprovada (issue #306) — só coordenação,
reversão de créditos (efeito da exclusão do documento) e re-execução do motor.

Segue o mesmo padrão de substituição do InferenceService usado em
test_activity_validate.py: o motor real não roda, só se verifica que
run_inference foi chamado com o aluno/programa corretos.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from backend.app.core.auth import CurrentUser
from backend.app.models.activity import ActivityStatus
from backend.app.services import activity_service as svc


def _coord() -> CurrentUser:
    return CurrentUser(uid="uid-coord", role="coordenacao", programa_id="prog_default", email="c@x.com")


class _FakeInference:
    """Substituto do InferenceService: registra a chamada sem rodar o motor real."""

    chamado_com: tuple[str, str] | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def run_inference(self, student_id: str, programa_id: str) -> None:
        type(self).chamado_com = (student_id, programa_id)


def _patch_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeInference.chamado_com = None
    monkeypatch.setattr(svc, "InferenceService", _FakeInference)
    monkeypatch.setattr(svc, "InferenceRepository", lambda: object())


def _activity(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "act1",
        "student_id": "s1",
        "tipo_id": "t1",
        "status": ActivityStatus.aprovado,
        "creditos_concedidos": 4.0,
        "producao_id": None,
    }
    base.update(overrides)
    return base


async def test_coordenacao_exclui_atividade_aprovada_e_reexecuta_motor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity()
    fake_students = AsyncMock()
    fake_students.get.return_value = {"programa_id": "prog_default"}
    monkeypatch.setattr(svc, "_repo", fake_repo)
    monkeypatch.setattr(svc, "_student_repo", fake_students)
    _patch_inference(monkeypatch)

    await svc.delete_activity("act1", _coord())

    fake_repo.delete_by_id.assert_awaited_once_with("act1")
    assert _FakeInference.chamado_com == ("s1", "prog_default")


async def test_exclusao_de_nao_aprovada_nao_reexecuta_motor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity(status=ActivityStatus.rascunho)
    fake_students = AsyncMock()
    monkeypatch.setattr(svc, "_repo", fake_repo)
    monkeypatch.setattr(svc, "_student_repo", fake_students)
    _patch_inference(monkeypatch)

    await svc.delete_activity("act1", _coord())

    fake_repo.delete_by_id.assert_awaited_once_with("act1")
    fake_students.get.assert_not_called()
    assert _FakeInference.chamado_com is None


async def test_falha_no_motor_nao_impede_a_exclusao_ja_efetivada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A atividade já foi excluída antes da re-inferência: uma falha no motor é
    logada, não propagada — o hard delete não deve ser desfeito nem a resposta
    virar erro por causa de uma falha em uma etapa pós-exclusão."""
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity()
    fake_students = AsyncMock()
    fake_students.get.side_effect = RuntimeError("firestore indisponível")
    monkeypatch.setattr(svc, "_repo", fake_repo)
    monkeypatch.setattr(svc, "_student_repo", fake_students)
    _patch_inference(monkeypatch)

    await svc.delete_activity("act1", _coord())

    fake_repo.delete_by_id.assert_awaited_once_with("act1")
