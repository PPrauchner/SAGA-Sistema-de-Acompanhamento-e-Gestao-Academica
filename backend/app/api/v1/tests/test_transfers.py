from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.aspects import aspect_config
from backend.app.api.v1.transfers import _build_direct_transfer_alerts
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app


class _FakeTransferService:
    calls: list[tuple[str, str, str]] = []

    async def direct_transfer(self, body: Any, user: CurrentUser) -> dict[str, Any]:
        self.calls.append((body.student_id, body.orientador_destino_id, user.uid))
        return {
            "id": "transfer1",
            "student_id": body.student_id,
            "student_uid": "uid-student",
            "student_nome": "Aluno",
            "orientador_origem_id": "advisor1",
            "orientador_origem_uid": "uid-origin",
            "orientador_origem_nome": "Origem",
            "orientador_destino_id": body.orientador_destino_id,
            "orientador_destino_uid": "uid-destination",
            "orientador_destino_nome": "Destino",
            "programa_id": "prog",
            "coorientador_limpo": False,
            "pending_cancelled": False,
            "pending_request_id": None,
            "pending_solicitante_id": None,
            "message": "Aluno transferido com sucesso",
        }


def _override_user(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid=f"uid-{role}",
        role=role,
        programa_id="prog",
        email=f"{role}@saga.test",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    fake_service = _FakeTransferService()
    _FakeTransferService.calls = []
    monkeypatch.setattr("backend.app.api.v1.transfers.service", fake_service)
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    monkeypatch.setattr(aspect_config, "HISTORY_ENABLED", False)
    monkeypatch.setattr(aspect_config, "ALERTS_ENABLED", False)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_transfer_direct_permite_coordenacao(client: TestClient) -> None:
    _override_user("coordenacao")

    response = client.post(
        "/api/v1/transfers/direct",
        json={"student_id": "student1", "orientador_destino_id": "advisor2"},
    )

    assert response.status_code == 200
    assert response.json()["orientador_destino_id"] == "advisor2"
    assert _FakeTransferService.calls == [("student1", "advisor2", "uid-coordenacao")]


@pytest.mark.parametrize("role", ["aluno", "orientador"])
def test_transfer_direct_bloqueia_papeis_nao_coordenacao(
    client: TestClient,
    role: str,
) -> None:
    _override_user(role)

    response = client.post(
        "/api/v1/transfers/direct",
        json={"student_id": "student1", "orientador_destino_id": "advisor2"},
    )

    assert response.status_code == 403
    assert _FakeTransferService.calls == []


def test_direct_transfer_alerts_notificam_partes_envolvidas() -> None:
    result = {
        "student_id": "student1",
        "student_uid": "uid-student",
        "student_nome": "Aluno",
        "orientador_origem_uid": "uid-origin",
        "orientador_destino_uid": "uid-destination",
        "orientador_destino_nome": "Destino",
        "programa_id": "prog",
        "pending_cancelled": True,
        "pending_solicitante_id": "uid-requester",
    }

    alerts = _build_direct_transfer_alerts(result, (), {})

    assert {alert["destinatario_id"] for alert in alerts} == {
        "uid-origin",
        "uid-destination",
        "uid-student",
        "uid-requester",
    }
    assert all(alert["entidade_tipo"] == "student" for alert in alerts)
    assert all(alert["entidade_id"] == "student1" for alert in alerts)
