"""
Testes do fluxo de parecer do orientador (issue #48) — funções de módulo do
activity_service e a checagem de propriedade (A01) que protege o endpoint.

Os singletons de repositório (`_repo`, `_student_repo`, `_advisor_repo`) são criados
no import do módulo, então são substituídos diretamente via monkeypatch nas instâncias
do módulo (não nas classes).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status

from backend.app.aspects.authorization import requires_ownership
from backend.app.core.auth import CurrentUser
from backend.app.models.activity import (
    ActivityStatus,
    ParecerRequest,
    ValidateAction,
    ValidateActivityRequest,
)
from backend.app.services import activity_service as svc


def _orientador(uid: str = "uid-orient") -> CurrentUser:
    return CurrentUser(uid=uid, role="orientador", programa_id="prog_default", email="o@x.com")


def _coord() -> CurrentUser:
    return CurrentUser(uid="uid-coord", role="coordenacao", programa_id="prog_default", email="c@x.com")


# --- emitir_parecer_orientador (#48) ----------------------------------------------------


async def test_emitir_parecer_grava_texto_e_mantem_status(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = {
        "id": "act1", "student_id": "s1", "tipo_id": "t1", "status": ActivityStatus.enviado,
    }
    fake_repo.update_by_id.return_value = {
        "id": "act1", "student_id": "s1", "tipo_id": "t1",
        "status": ActivityStatus.enviado, "parecer_orientador": "Parecer favorável.",
    }
    monkeypatch.setattr(svc, "_repo", fake_repo)

    resp = await svc.emitir_parecer_orientador(
        "act1", ParecerRequest(parecer="Parecer favorável."), _orientador()
    )

    # Parecer persistido como string; status preservado (parecer é campo, não estado).
    assert resp.parecer_orientador == "Parecer favorável."
    assert resp.status == ActivityStatus.enviado
    activity_id_arg, update_data = fake_repo.update_by_id.call_args.args
    assert activity_id_arg == "act1"
    assert update_data["parecer_orientador"] == "Parecer favorável."
    assert "status" not in update_data


async def test_emitir_parecer_status_invalido_409(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = {
        "id": "act1", "student_id": "s1", "tipo_id": "t1", "status": ActivityStatus.aprovado,
    }
    monkeypatch.setattr(svc, "_repo", fake_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.emitir_parecer_orientador("act1", ParecerRequest(parecer="x"), _orientador())

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    fake_repo.update_by_id.assert_not_called()


async def test_emitir_parecer_nao_encontrada_404(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = None
    monkeypatch.setattr(svc, "_repo", fake_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.emitir_parecer_orientador("nope", ParecerRequest(parecer="x"), _orientador())

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


# --- resolve_advisor_uid_for_activity (suporte ao A01 por propriedade) -------------------


async def test_resolver_uid_do_orientador_em_dois_saltos(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = {"id": "act1", "student_id": "s1"}
    fake_students = AsyncMock()
    fake_students.get.return_value = {"id": "s1", "orientador_id": "adv1"}
    fake_advisors = AsyncMock()
    fake_advisors.get.return_value = {"id": "adv1", "uid": "uid-orient"}
    monkeypatch.setattr(svc, "_repo", fake_repo)
    monkeypatch.setattr(svc, "_student_repo", fake_students)
    monkeypatch.setattr(svc, "_advisor_repo", fake_advisors)

    uid = await svc.resolve_advisor_uid_for_activity("act1")

    assert uid == "uid-orient"
    fake_students.get.assert_awaited_once_with("s1")
    fake_advisors.get.assert_awaited_once_with("adv1")


async def test_resolver_none_quando_atividade_inexistente(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = None
    monkeypatch.setattr(svc, "_repo", fake_repo)

    assert await svc.resolve_advisor_uid_for_activity("nope") is None


async def test_resolver_none_quando_aluno_sem_orientador(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = {"id": "act1", "student_id": "s1"}
    fake_students = AsyncMock()
    fake_students.get.return_value = {"id": "s1"}  # sem orientador_id
    monkeypatch.setattr(svc, "_repo", fake_repo)
    monkeypatch.setattr(svc, "_student_repo", fake_students)

    assert await svc.resolve_advisor_uid_for_activity("act1") is None


# --- AC2: @requires_ownership + resolver real garantem que só o dono emite parecer -------


def _guarded_endpoint():
    @requires_ownership(lambda kw: svc.resolve_advisor_uid_for_activity(kw["activity_id"]))
    async def _endpoint(activity_id: str, user: CurrentUser) -> str:
        return "ok"

    return _endpoint


def _mock_owner_chain(monkeypatch: pytest.MonkeyPatch, owner_uid: str) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = {"id": "act1", "student_id": "s1"}
    fake_students = AsyncMock()
    fake_students.get.return_value = {"id": "s1", "orientador_id": "adv1"}
    fake_advisors = AsyncMock()
    fake_advisors.get.return_value = {"id": "adv1", "uid": owner_uid}
    monkeypatch.setattr(svc, "_repo", fake_repo)
    monkeypatch.setattr(svc, "_student_repo", fake_students)
    monkeypatch.setattr(svc, "_advisor_repo", fake_advisors)


async def test_ownership_permite_orientador_dono(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_owner_chain(monkeypatch, owner_uid="uid-orient")
    endpoint = _guarded_endpoint()

    assert await endpoint(activity_id="act1", user=_orientador("uid-orient")) == "ok"


async def test_ownership_bloqueia_orientador_nao_dono(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_owner_chain(monkeypatch, owner_uid="uid-orient")
    endpoint = _guarded_endpoint()

    with pytest.raises(HTTPException) as exc:
        await endpoint(activity_id="act1", user=_orientador("uid-outro"))

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


async def test_ownership_coordenacao_bypassa(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_owner_chain(monkeypatch, owner_uid="uid-orient")
    endpoint = _guarded_endpoint()

    # Coordenação não precisa ser dona — o aspecto a libera direto.
    assert await endpoint(activity_id="act1", user=_coord()) == "ok"


# --- Regressão #49: validate continua barrando status inválido --------------------------


async def test_validate_status_invalido_409(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = AsyncMock()
    fake_repo.get_by_id.return_value = {
        "id": "act1", "student_id": "s1", "tipo_id": "t1", "status": ActivityStatus.aprovado,
    }
    monkeypatch.setattr(svc, "_repo", fake_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.validate_activity(
            "act1", ValidateActivityRequest(acao=ValidateAction.rejeitar, observacao="x"), _coord()
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT
