from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from backend.app.aspects import aspect_config
from backend.app.aspects import alerts as alerts_module
from backend.app.api.v1 import registration_requests as router_module
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app


def _request_payload(request_id: str = "req1", status_value: str = "pendente") -> dict[str, Any]:
    return {
        "id": request_id,
        "nome": "Aluno",
        "email": "aluno@saga.test",
        "orientador_id": "advisor1",
        "orientador_nome": "Profa. Ada",
        "programa_id": "prog",
        "status": status_value,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "reviewed_by": None,
        "reviewed_at": None,
    }


class _FakeRegistrationRequestService:
    calls: list[tuple[str, Any]] = []

    async def list_active_advisors(self) -> list[dict[str, Any]]:
        self.calls.append(("list_active_advisors", None))
        return [{"id": "advisor1", "uid": "uid-advisor", "nome": "Profa. Ada"}]

    async def create_request(self, body: Any) -> dict[str, Any]:
        self.calls.append(("create", body))
        return _request_payload()

    async def list_pending(self, user: CurrentUser) -> list[dict[str, Any]]:
        self.calls.append(("list", user))
        return [_request_payload()]

    async def approve_request(self, request_id: str, body: Any, user: CurrentUser) -> dict[str, Any]:
        self.calls.append(("approve", (request_id, body, user)))
        return {
            **_request_payload(request_id, "aprovado"),
            "reviewed_by": user.uid,
            "reviewed_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "student_id": "student1",
            "invite_token": "tok-aluno",
        }

    async def reject_request(self, request_id: str, body: Any, user: CurrentUser) -> dict[str, Any]:
        self.calls.append(("reject", (request_id, body, user)))
        return {
            **_request_payload(request_id, "rejeitado"),
            "reviewed_by": user.uid,
            "reviewed_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "rejection_reason": getattr(body, "motivo", None),
        }


class _DuplicateEmailService(_FakeRegistrationRequestService):
    async def create_request(self, body: Any) -> dict[str, Any]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ja existe uma solicitacao pendente para este e-mail",
        )


class _FakeAlertRepository:
    docs: list[dict[str, Any]] = []

    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def create(self, data: dict[str, Any]) -> str:
        self.docs.append(data)
        return f"notification{len(self.docs)}"


def _user(role: str = "coordenacao") -> CurrentUser:
    return CurrentUser(
        uid=f"uid-{role}",
        role=role,
        programa_id="prog",
        email=f"{role}@saga.test",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    original_service = router_module.service
    _FakeRegistrationRequestService.calls = []
    _FakeAlertRepository.docs = []
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    monkeypatch.setattr(aspect_config, "ALERTS_ENABLED", True)
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _FakeAlertRepository)
    router_module.service = _FakeRegistrationRequestService()
    app.dependency_overrides[get_current_user] = lambda: _user()
    yield TestClient(app)
    router_module.service = original_service
    app.dependency_overrides.clear()


def test_post_registration_request_publico_sem_token(client: TestClient) -> None:
    app.dependency_overrides.clear()

    response = client.post(
        "/api/v1/registration-requests",
        json={"nome": "Aluno", "email": "aluno@saga.test", "advisor_id": "advisor1"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pendente"
    assert _FakeRegistrationRequestService.calls[0][0] == "create"


def test_public_advisors_lista_sem_token(client: TestClient) -> None:
    app.dependency_overrides.clear()

    response = client.get("/api/v1/registration-requests/advisors")

    assert response.status_code == 200
    assert response.json() == [{"id": "advisor1", "uid": "uid-advisor", "nome": "Profa. Ada"}]


def test_post_registration_request_duplicado_retorna_409(
    client: TestClient,
) -> None:
    router_module.service = _DuplicateEmailService()
    app.dependency_overrides.clear()

    response = client.post(
        "/api/v1/registration-requests",
        json={"nome": "Aluno", "email": "aluno@saga.test", "orientador_id": "advisor1"},
    )

    assert response.status_code == 409
    assert "pendente" in response.json()["detail"]


def test_get_registration_requests_exige_coordenacao(client: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _user("aluno")

    response = client.get("/api/v1/registration-requests")

    assert response.status_code == 403


def test_get_registration_requests_coordena_listagem(client: TestClient) -> None:
    response = client.get("/api/v1/registration-requests")

    assert response.status_code == 200
    assert response.json()[0]["email"] == "aluno@saga.test"
    assert _FakeRegistrationRequestService.calls[0][0] == "list"


def test_approve_registration_request_chama_service_e_dispara_a05(
    client: TestClient,
) -> None:
    response = client.patch(
        "/api/v1/registration-requests/req1/approve",
        json={"matricula": "2026001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "aprovado"
    assert body["student_id"] == "student1"
    assert _FakeRegistrationRequestService.calls[0][0] == "approve"
    assert _FakeAlertRepository.docs[0]["tipo"] == "solicitacao_cadastro_aprovada"
    assert _FakeAlertRepository.docs[0]["destinatario_id"] == "aluno@saga.test"


def test_reject_registration_request_chama_service_e_dispara_a05(
    client: TestClient,
) -> None:
    response = client.patch(
        "/api/v1/registration-requests/req1/reject",
        json={"motivo": "Dados incompletos"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejeitado"
    assert body["rejection_reason"] == "Dados incompletos"
    assert _FakeRegistrationRequestService.calls[0][0] == "reject"
    assert _FakeAlertRepository.docs[0]["tipo"] == "solicitacao_cadastro_rejeitada"
