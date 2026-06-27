"""
Testes da validação da coordenação (issue #49) — aprovação/rejeição de atividade,
o resolver de uid do aluno e o disparo de alerta A05 que notifica o resultado.

Os singletons de repositório (`_repo`, `_student_repo`) e as classes de inferência
(`InferenceService`, `InferenceRepository`) são resolvidos no módulo do service, então
são substituídos diretamente via monkeypatch no módulo (não nas classes originais).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status

from backend.app.api.v1.activities import _build_notificacao_validacao
from backend.app.core.auth import CurrentUser
from backend.app.models.activity import (
    ActivityResponse,
    ActivityStatus,
    ValidateAction,
    ValidateActivityRequest,
    ValidateActivityResponse,
)
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
        "status": ActivityStatus.enviado,
        "creditos_gerados": 4.0,
        "creditos_concedidos": None,
    }
    base.update(overrides)
    return base


# --- validate_activity (aprovar) --------------------------------------------------------


def test_activity_response_emite_campos_canonicos_de_validacao() -> None:
    response = ActivityResponse(
        id="act1",
        status=ActivityStatus.aprovado,
        aprovado_por="uid-legado",
    )

    data = response.model_dump()
    assert data["validado_por"] == "uid-legado"
    assert "aprovado_por" not in data


async def test_aprovar_muda_status_e_contabiliza_pontuacao_base(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity()
    fake_repo.get_activity_type.return_value = {"pontuacao_base": 4.0}
    fake_students = AsyncMock()
    fake_students.get.return_value = {"programa_id": "prog_default"}
    monkeypatch.setattr(svc, "_repo", fake_repo)
    monkeypatch.setattr(svc, "_student_repo", fake_students)
    _patch_inference(monkeypatch)

    resp = await svc.validate_activity(
        "act1", ValidateActivityRequest(acao=ValidateAction.aprovar), _coord()
    )

    assert resp.novo_status == ActivityStatus.aprovado
    assert resp.creditos_contabilizados == 4.0
    assert resp.motor_inferencia_executado is True
    assert resp.fato_gerado is None  # sem producao_id
    assert _FakeInference.chamado_com == ("s1", "prog_default")

    _, update_data = fake_repo.update_by_id.call_args.args
    assert update_data["status"] == ActivityStatus.aprovado.value
    assert update_data["validado_por"] == "uid-coord"
    assert update_data["validado_em"] is not None
    assert "aprovado_por" not in update_data
    assert "aprovado_em" not in update_data
    assert "creditos_gerados" not in update_data
    assert "creditos_concedidos" not in update_data


async def test_aprovar_com_creditos_concedidos_preserva_creditos_gerados(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity()
    fake_students = AsyncMock()
    fake_students.get.return_value = {"programa_id": "prog_default"}
    monkeypatch.setattr(svc, "_repo", fake_repo)
    monkeypatch.setattr(svc, "_student_repo", fake_students)
    _patch_inference(monkeypatch)

    resp = await svc.validate_activity(
        "act1",
        ValidateActivityRequest(acao=ValidateAction.aprovar, creditos_concedidos=2.5),
        _coord(),
    )

    assert resp.creditos_contabilizados == 2.5
    fake_repo.get_activity_type.assert_not_called()  # override pula o lookup do tipo

    _, update_data = fake_repo.update_by_id.call_args.args
    assert update_data["creditos_concedidos"] == 2.5
    assert update_data["validado_por"] == "uid-coord"
    assert "creditos_gerados" not in update_data
    assert "aprovado_por" not in update_data


async def test_aprovar_producao_gera_fato_para_o_motor(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity(producao_id="prod1")
    fake_repo.get_activity_type.return_value = {"pontuacao_base": 4.0}
    fake_students = AsyncMock()
    fake_students.get.return_value = {"programa_id": "prog_default"}
    monkeypatch.setattr(svc, "_repo", fake_repo)
    monkeypatch.setattr(svc, "_student_repo", fake_students)
    _patch_inference(monkeypatch)

    resp = await svc.validate_activity(
        "act1", ValidateActivityRequest(acao=ValidateAction.aprovar), _coord()
    )

    assert resp.fato_gerado == "producao_bibliografica_validada(s1)"


# --- validate_activity (rejeitar / erros) -----------------------------------------------


async def test_rejeitar_preserva_creditos_e_nao_roda_motor(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = _activity()
    monkeypatch.setattr(svc, "_repo", fake_repo)
    _patch_inference(monkeypatch)

    resp = await svc.validate_activity(
        "act1",
        ValidateActivityRequest(acao=ValidateAction.rejeitar, observacao="Comprovante inválido"),
        _coord(),
    )

    assert resp.novo_status == ActivityStatus.rejeitado
    assert resp.creditos_contabilizados is None
    assert resp.motor_inferencia_executado is False
    assert resp.fato_gerado is None
    assert _FakeInference.chamado_com is None

    _, update_data = fake_repo.update_by_id.call_args.args
    assert "creditos_gerados" not in update_data
    assert "creditos_concedidos" not in update_data
    assert update_data["validado_por"] == "uid-coord"
    assert update_data["observacao_coordenacao"] == "Comprovante inválido"


async def test_validate_atividade_inexistente_404(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = None
    monkeypatch.setattr(svc, "_repo", fake_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.validate_activity(
            "nope", ValidateActivityRequest(acao=ValidateAction.aprovar), _coord()
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    fake_repo.update_by_id.assert_not_called()


# --- resolve_student_uid_for_activity ---------------------------------------------------


async def test_resolver_uid_do_aluno(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = {"id": "act1", "student_id": "s1"}
    fake_students = AsyncMock()
    fake_students.get.return_value = {"id": "s1", "uid": "uid-aluno"}
    monkeypatch.setattr(svc, "_repo", fake_repo)
    monkeypatch.setattr(svc, "_student_repo", fake_students)

    assert await svc.resolve_student_uid_for_activity("act1") == "uid-aluno"
    fake_students.get.assert_awaited_once_with("s1")


async def test_resolver_none_quando_atividade_inexistente(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = None
    monkeypatch.setattr(svc, "_repo", fake_repo)

    assert await svc.resolve_student_uid_for_activity("nope") is None


# --- _build_notificacao_validacao (A05) -------------------------------------------------


async def test_build_notifica_aluno_de_aprovacao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(svc, "resolve_student_uid_for_activity", AsyncMock(return_value="uid-aluno"))
    result = ValidateActivityResponse(message="ok", novo_status=ActivityStatus.aprovado)

    doc = await _build_notificacao_validacao(result, (), {"activity_id": "act1"})

    assert doc is not None
    assert doc["tipo"] == "atividade_validada"
    assert doc["destinatario_id"] == "uid-aluno"
    assert doc["entidade_id"] == "act1"
    assert "aprovada" in doc["mensagem"]


async def test_build_notifica_aluno_de_rejeicao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(svc, "resolve_student_uid_for_activity", AsyncMock(return_value="uid-aluno"))
    result = ValidateActivityResponse(message="ok", novo_status=ActivityStatus.rejeitado)

    doc = await _build_notificacao_validacao(result, (), {"activity_id": "act1"})

    assert doc is not None
    assert "rejeitada" in doc["mensagem"]


async def test_build_retorna_none_sem_aluno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(svc, "resolve_student_uid_for_activity", AsyncMock(return_value=None))
    result = ValidateActivityResponse(message="ok", novo_status=ActivityStatus.aprovado)

    assert await _build_notificacao_validacao(result, (), {"activity_id": "act1"}) is None
