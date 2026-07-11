from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_PRIVATE_KEY", "test-key")
os.environ.setdefault("FIREBASE_CLIENT_EMAIL", "test@test-project.iam.gserviceaccount.com")

import pytest
from fastapi.testclient import TestClient

from backend.app.aspects import aspect_config
from backend.app.api.v1 import departments as departments_router
from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app


class _FakeDepartmentRepository:
    def __init__(self, store: dict[str, dict[str, Any]], linked: bool = False) -> None:
        self.store = store
        self.linked = linked

    async def list_all(self) -> list[dict[str, Any]]:
        return [{"id": key, **value} for key, value in self.store.items()]

    async def get(self, department_id: str) -> dict[str, Any] | None:
        data = self.store.get(department_id)
        return {"id": department_id, **data} if data is not None else None

    async def create(self, data: dict[str, Any]) -> str:
        doc_id = f"dept{len(self.store) + 1}"
        self.store[doc_id] = dict(data)
        return doc_id

    async def update(self, department_id: str, data: dict[str, Any]) -> None:
        self.store.setdefault(department_id, {}).update(data)

    async def delete(self, department_id: str) -> None:
        self.store.pop(department_id, None)

    async def has_programs(self, department_id: str) -> bool:
        return self.linked


def _adm() -> CurrentUser:
    return CurrentUser(uid="adm1", role="adm", programa_id=None, email="adm@saga.edu")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    original = departments_router.service._departments
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    app.dependency_overrides[get_current_user] = _adm
    yield TestClient(app)
    departments_router.service._departments = original
    app.dependency_overrides.clear()


def test_list_departments(client: TestClient) -> None:
    departments_router.service._departments = _FakeDepartmentRepository(
        {"dept1": {"nome": "Computação", "instituicao": "UNIPAMPA"}}
    )

    response = client.get("/api/v1/departments")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "dept1",
            "nome": "Computação",
            "instituicao": "UNIPAMPA",
            "criado_em": None,
            "atualizado_em": None,
        }
    ]


def test_get_department_inexistente_404(client: TestClient) -> None:
    departments_router.service._departments = _FakeDepartmentRepository({})

    response = client.get("/api/v1/departments/nao-existe")

    assert response.status_code == 404


def test_create_department(client: TestClient) -> None:
    departments_router.service._departments = _FakeDepartmentRepository({})

    response = client.post("/api/v1/departments", json={"nome": "Engenharia"})

    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "Engenharia"
    assert body["id"] == "dept1"


def test_update_department(client: TestClient) -> None:
    store = {"dept1": {"nome": "Antigo"}}
    departments_router.service._departments = _FakeDepartmentRepository(store)

    response = client.put("/api/v1/departments/dept1", json={"nome": "Novo"})

    assert response.status_code == 200
    assert store["dept1"]["nome"] == "Novo"


def test_delete_department_sem_programa(client: TestClient) -> None:
    departments_router.service._departments = _FakeDepartmentRepository(
        {"dept1": {"nome": "Removível"}}, linked=False
    )

    response = client.delete("/api/v1/departments/dept1")

    assert response.status_code == 200


def test_delete_department_com_programa_vinculado_400(client: TestClient) -> None:
    departments_router.service._departments = _FakeDepartmentRepository(
        {"dept1": {"nome": "Vinculado"}}, linked=True
    )

    response = client.delete("/api/v1/departments/dept1")

    assert response.status_code == 400
