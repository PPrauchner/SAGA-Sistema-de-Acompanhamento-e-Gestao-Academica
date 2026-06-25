from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test@test-project.iam.gserviceaccount.com")

import pytest
from fastapi.testclient import TestClient

from backend.app.aspects import aspect_config
from backend.app.api.v1 import advisors as advisors_router
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app


class _FakeAdvisorRepository:
    def __init__(self, store: dict[str, dict[str, Any]], active_count: int = 0) -> None:
        self.store = store
        self.active_count = active_count

    async def get_advisors_with_student_count(self) -> list[dict[str, Any]]:
        return [{"id": key, **value} for key, value in self.store.items()]

    async def get(self, advisor_id: str) -> dict[str, Any] | None:
        advisor = self.store.get(advisor_id)
        return {"id": advisor_id, **advisor} if advisor is not None else None

    async def count_active_students(self, advisor_id: str) -> int:
        return self.active_count


def _coord() -> CurrentUser:
    return CurrentUser(uid="coord1", role="coordenacao", programa_id="prog", email="coord@saga.edu")


def _legacy_advisor() -> dict[str, Any]:
    return {
        "nome": "Orientador Legado",
        "email": "orientador@saga.edu",
        "departamento": "Computacao",
        "programa_id": "prog",
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    original_advisors = advisors_router.service._advisors
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    app.dependency_overrides[get_current_user] = _coord
    yield TestClient(app)
    advisors_router.service._advisors = original_advisors
    app.dependency_overrides.clear()


def test_get_advisors_response_model_normaliza_documento_legado(client: TestClient) -> None:
    advisors_router.service._advisors = _FakeAdvisorRepository({"advisor1": _legacy_advisor()})

    response = client.get("/api/v1/advisors")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "advisor1",
            "uid": None,
            "nome": "Orientador Legado",
            "email": "orientador@saga.edu",
            "departamento": "Computacao",
            "programa_id": "prog",
            "lattes": None,
            "limite_orientandos": 5,
            "orientandos_ativos": 0,
        },
    ]


def test_get_advisor_response_model_inclui_orientandos_ativos(client: TestClient) -> None:
    advisors_router.service._advisors = _FakeAdvisorRepository({"advisor1": _legacy_advisor()}, active_count=3)

    response = client.get("/api/v1/advisors/advisor1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "advisor1"
    assert body["uid"] is None
    assert body["lattes"] is None
    assert body["limite_orientandos"] == 5
    assert body["orientandos_ativos"] == 3
