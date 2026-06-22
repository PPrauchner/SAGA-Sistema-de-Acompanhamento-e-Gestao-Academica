from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app
from backend.app.models.coordination_transfer import CoordinationTransferResponse


class _FakeCoordinationTransferService:
    chamadas: list[tuple[str, tuple[Any, ...]]] = []

    async def start_transfer(self, data: Any, user: CurrentUser) -> CoordinationTransferResponse:
        self.chamadas.append(("start_transfer", (data, user)))
        return _response("pendente")

    async def list_transfers(self, user: CurrentUser) -> list[CoordinationTransferResponse]:
        self.chamadas.append(("list_transfers", (user,)))
        return [_response("pendente")]

    async def accept_transfer(self, transfer_id: str, user: CurrentUser) -> CoordinationTransferResponse:
        self.chamadas.append(("accept_transfer", (transfer_id, user)))
        return _response("aceita")

    async def reject_transfer(self, transfer_id: str, user: CurrentUser) -> CoordinationTransferResponse:
        self.chamadas.append(("reject_transfer", (transfer_id, user)))
        return _response("rejeitada")

    async def cancel_transfer(self, transfer_id: str, user: CurrentUser) -> CoordinationTransferResponse:
        self.chamadas.append(("cancel_transfer", (transfer_id, user)))
        return _response("cancelada")


class _FakeAspectRepo:
    created: list[tuple[str, dict[str, Any]]] = []

    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def create(self, data: dict[str, Any]) -> str:
        self.created.append((self.collection, data))
        return f"{self.collection}-1"


def _response(status: str) -> CoordinationTransferResponse:
    now = datetime.now(timezone.utc)
    return CoordinationTransferResponse(
        id="tr1",
        programa_id="prog1",
        initiator_uid="coord",
        successor_uid="adv",
        status=status,
        created_at=now,
        updated_at=now,
    )


def _override_user(role: str, uid: str = "u1") -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid=uid,
        role=role,
        programa_id="prog1",
        email="u@x.com",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "backend.app.api.v1.coordination_transfers.CoordinationTransferService",
        _FakeCoordinationTransferService,
    )
    monkeypatch.setattr("backend.app.aspects.aspect_config.AUDIT_ENABLED", False)
    monkeypatch.setattr("backend.app.aspects.aspect_config.ALERTS_ENABLED", False)
    _FakeCoordinationTransferService.chamadas = []
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_iniciar_apenas_coordenacao(client: TestClient) -> None:
    _override_user("coordenacao", "coord")

    resp = client.post("/api/v1/coordination-transfers", json={"successor_uid": "adv"})

    assert resp.status_code == 201
    assert resp.json()["status"] == "pendente"
    assert _FakeCoordinationTransferService.chamadas[0][0] == "start_transfer"


def test_iniciar_registra_auditoria_e_notifica_sucessor(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.app.aspects.aspect_config.AUDIT_ENABLED", True)
    monkeypatch.setattr("backend.app.aspects.aspect_config.ALERTS_ENABLED", True)
    monkeypatch.setattr("backend.app.aspects.audit.FirebaseRepository", _FakeAspectRepo)
    monkeypatch.setattr("backend.app.aspects.alerts.FirebaseRepository", _FakeAspectRepo)
    _FakeAspectRepo.created = []
    _override_user("coordenacao", "coord")

    resp = client.post("/api/v1/coordination-transfers", json={"successor_uid": "adv"})

    assert resp.status_code == 201
    collections = [collection for collection, _data in _FakeAspectRepo.created]
    assert "audit_logs" in collections
    notification = next(data for collection, data in _FakeAspectRepo.created if collection == "notifications")
    assert notification["destinatario_id"] == "adv"


def test_usuario_que_nao_e_coordenacao_nao_inicia(client: TestClient) -> None:
    _override_user("orientador", "adv")

    resp = client.post("/api/v1/coordination-transfers", json={"successor_uid": "adv"})

    assert resp.status_code == 403
    assert _FakeCoordinationTransferService.chamadas == []


def test_orientador_lista_convites(client: TestClient) -> None:
    _override_user("orientador", "adv")

    resp = client.get("/api/v1/coordination-transfers")

    assert resp.status_code == 200
    assert resp.json()[0]["successor_uid"] == "adv"


def test_sucessor_aceita(client: TestClient) -> None:
    _override_user("orientador", "adv")

    resp = client.post("/api/v1/coordination-transfers/tr1/accept")

    assert resp.status_code == 200
    assert resp.json()["status"] == "aceita"


def test_aceitar_notifica_ex_coordenador(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.app.aspects.aspect_config.AUDIT_ENABLED", False)
    monkeypatch.setattr("backend.app.aspects.aspect_config.ALERTS_ENABLED", True)
    monkeypatch.setattr("backend.app.aspects.alerts.FirebaseRepository", _FakeAspectRepo)
    _FakeAspectRepo.created = []
    _override_user("orientador", "adv")

    resp = client.post("/api/v1/coordination-transfers/tr1/accept")

    assert resp.status_code == 200
    notification = next(data for collection, data in _FakeAspectRepo.created if collection == "notifications")
    assert notification["destinatario_id"] == "coord"


def test_sucessor_rejeita(client: TestClient) -> None:
    _override_user("orientador", "adv")

    resp = client.post("/api/v1/coordination-transfers/tr1/reject")

    assert resp.status_code == 200
    assert resp.json()["status"] == "rejeitada"


def test_iniciador_cancela(client: TestClient) -> None:
    _override_user("coordenacao", "coord")

    resp = client.post("/api/v1/coordination-transfers/tr1/cancel")

    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelada"
