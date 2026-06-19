from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.aspects import aspect_config
from backend.app.api.v1.transfers import (
    _build_direct_transfer_alerts,
    _build_request_cancelled_alerts,
    _build_request_created_alerts,
    _build_request_rejected_alerts,
)
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

    async def list_requests(self, user: CurrentUser) -> list[dict[str, Any]]:
        self.calls.append(("list", user.role, user.uid))
        return []

    async def create_request(self, body: Any, user: CurrentUser) -> dict[str, Any]:
        self.calls.append((body.student_id, body.orientador_destino_id, user.uid))
        return {
            "id": "transfer1",
            "student_id": body.student_id,
            "student_nome": "Aluno",
            "orientador_origem_id": "advisor1",
            "orientador_origem_uid": user.uid,
            "orientador_origem_nome": "Origem",
            "orientador_destino_id": body.orientador_destino_id,
            "orientador_destino_uid": "uid-destination",
            "orientador_destino_nome": "Destino",
            "solicitante_id": user.uid,
            "programa_id": "prog",
            "status": "pendente",
            "coord_uids": ["uid-coord"],
            "message": "Solicitacao de transferencia criada",
        }

    async def approve_request(self, transfer_id: str, user: CurrentUser) -> dict[str, Any]:
        self.calls.append(("approve", transfer_id, user.uid))
        return {
            "id": transfer_id,
            "student_id": "student1",
            "student_uid": "uid-student",
            "student_nome": "Aluno",
            "orientador_origem_id": "advisor1",
            "orientador_origem_uid": "uid-origin",
            "orientador_destino_id": "advisor2",
            "orientador_destino_uid": "uid-destination",
            "orientador_destino_nome": "Destino",
            "programa_id": "prog",
            "status": "aprovada",
            "coorientador_limpo": False,
            "message": "Solicitacao de transferencia aprovada",
        }

    async def reject_request(self, transfer_id: str, motivo: str, user: CurrentUser) -> dict[str, Any]:
        self.calls.append(("reject", transfer_id, user.uid))
        return {
            "id": transfer_id,
            "student_id": "student1",
            "solicitante_id": "uid-origin",
            "programa_id": "prog",
            "status": "rejeitada",
            "motivo": motivo,
            "message": "Solicitacao de transferencia rejeitada",
        }

    async def cancel_request(self, transfer_id: str, user: CurrentUser) -> dict[str, Any]:
        self.calls.append(("cancel", transfer_id, user.uid))
        return {
            "id": transfer_id,
            "student_id": "student1",
            "programa_id": "prog",
            "status": "cancelada",
            "coord_uids": ["uid-coord"],
            "message": "Solicitacao de transferencia cancelada",
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


def test_orientador_cria_solicitacao(client: TestClient) -> None:
    _override_user("orientador")

    response = client.post(
        "/api/v1/transfers",
        json={"student_id": "student1", "orientador_destino_id": "advisor2"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pendente"
    assert _FakeTransferService.calls == [("student1", "advisor2", "uid-orientador")]


def test_aluno_nao_cria_solicitacao(client: TestClient) -> None:
    _override_user("aluno")

    response = client.post(
        "/api/v1/transfers",
        json={"student_id": "student1", "orientador_destino_id": "advisor2"},
    )

    assert response.status_code == 403


def test_coordenacao_aprova_e_rejeita(client: TestClient) -> None:
    _override_user("coordenacao")

    approved = client.post("/api/v1/transfers/transfer1/approve")
    rejected = client.post(
        "/api/v1/transfers/transfer2/reject",
        json={"motivo": "Capacidade indisponivel"},
    )

    assert approved.status_code == 200
    assert rejected.status_code == 200
    assert ("approve", "transfer1", "uid-coordenacao") in _FakeTransferService.calls
    assert ("reject", "transfer2", "uid-coordenacao") in _FakeTransferService.calls


def test_orientador_nao_aprova_ou_rejeita(client: TestClient) -> None:
    _override_user("orientador")

    approved = client.post("/api/v1/transfers/transfer1/approve")
    rejected = client.post(
        "/api/v1/transfers/transfer1/reject",
        json={"motivo": "x"},
    )

    assert approved.status_code == 403
    assert rejected.status_code == 403


def test_orientador_cancela_solicitacao(client: TestClient) -> None:
    _override_user("orientador")

    response = client.post("/api/v1/transfers/transfer1/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelada"
    assert _FakeTransferService.calls == [("cancel", "transfer1", "uid-orientador")]


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


def test_request_transition_alerts() -> None:
    created = _build_request_created_alerts(
        {
            "student_id": "student1",
            "student_nome": "Aluno",
            "orientador_origem_nome": "Origem",
            "programa_id": "prog",
            "coord_uids": ["coord1"],
        },
        (),
        {},
    )
    rejected = _build_request_rejected_alerts(
        {
            "student_id": "student1",
            "solicitante_id": "uid-origin",
            "programa_id": "prog",
            "motivo": "Sem capacidade",
        },
        (),
        {},
    )
    cancelled = _build_request_cancelled_alerts(
        {
            "student_id": "student1",
            "programa_id": "prog",
            "coord_uids": ["coord1"],
        },
        (),
        {},
    )

    assert created[0]["destinatario_id"] == "coord1"
    assert rejected[0]["destinatario_id"] == "uid-origin"
    assert cancelled[0]["destinatario_id"] == "coord1"
